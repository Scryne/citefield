import base64
import json
import subprocess
from types import SimpleNamespace

import pytest

from citefield import providers
from citefield.providers.anthropic import AnthropicProvider
from citefield.providers.openai_compat import OpenAICompatibleProvider


class Recorder:
    def __init__(self, response):
        self.calls, self.response = [], response

    def create(self, **kw):
        self.calls.append(kw)
        return self.response


def test_anthropic_sends_images_first_and_schema_through_output_config():
    msg = SimpleNamespace(
        content=[SimpleNamespace(type="text", text='{"fields": []}')],
        usage=SimpleNamespace(input_tokens=1_000_000, output_tokens=100_000),
    )
    rec = Recorder(msg)
    p = AnthropicProvider("claude-sonnet-5-5", client=SimpleNamespace(messages=rec))
    r = p.read("prompt", [b"PNG1", b"PNG2"], {"type": "object"})
    content = rec.calls[0]["messages"][0]["content"]
    assert [c["type"] for c in content] == ["image", "image", "text"]
    assert base64.b64decode(content[1]["source"]["data"]) == b"PNG2"
    assert rec.calls[0]["extra_body"] == {
        "output_config": {"format": {"type": "json_schema", "schema": {"type": "object"}}}
    }
    assert r.text == '{"fields": []}' and r.cost_usd == pytest.approx(2.0 + 1.0)


def test_anthropic_without_schema_and_unknown_price():
    msg = SimpleNamespace(content=[], usage=SimpleNamespace(input_tokens=1, output_tokens=1))
    rec = Recorder(msg)
    r = AnthropicProvider("some-new-model", client=SimpleNamespace(messages=rec)).read("p", [])
    assert rec.calls[0]["extra_body"] is None and r.cost_usd is None


def _openai(message):
    rec = Recorder(
        SimpleNamespace(
            choices=[SimpleNamespace(message=message)], usage=SimpleNamespace(prompt_tokens=7, completion_tokens=3)
        )
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=rec))
    return OpenAICompatibleProvider("openai", "some-vision-model", client=client), rec


class OllamaClient:
    """Answers in turn from `replies` ((status, body) pairs); the last one repeats."""

    def __init__(self, status=200, body=None, replies=None):
        self.calls, self.replies = [], replies or [(status, body or {})]

    def post(self, url, json):
        self.calls.append((url, json))
        status, body = self.replies[min(len(self.calls), len(self.replies)) - 1]
        return SimpleNamespace(status_code=status, content=b"x", text="", json=lambda: body)


def test_ollama_doubles_the_window_when_the_answer_was_cut_or_the_prompt_filled_it():
    cut = {
        "message": {"content": '{"fields": [{"fi'},
        "done_reason": "length",
        "prompt_eval_count": 5000,
        "eval_count": 3192,
    }
    full = {"message": {"content": "{}"}, "done_reason": "stop", "prompt_eval_count": 16380, "eval_count": 2}
    ok = {
        "message": {"content": '{"fields": []}'},
        "done_reason": "stop",
        "prompt_eval_count": 20000,
        "eval_count": 900,
    }
    c = OllamaClient(replies=[(200, cut), (200, full), (200, ok)])
    r = providers.get("ollama", client=c).read("p", [])
    assert [b["options"]["num_ctx"] for _, b in c.calls] == [8192, 16384, 32768] and r.text == '{"fields": []}'


def test_ollama_retries_a_refused_oversized_prompt_with_a_larger_window_and_stops_at_the_cap():
    refused = {"error": "request (9000 tokens) exceeds the available context size (8192 tokens)"}
    c = OllamaClient(replies=[(400, refused), (200, {"message": {"content": "{}"}, "prompt_eval_count": 9000})])
    providers.get("ollama", client=c).read("p", [])
    assert [b["options"]["num_ctx"] for _, b in c.calls] == [8192, 16384]
    capped = OllamaClient(status=400, body=refused)
    with pytest.raises(RuntimeError, match="context size"):
        providers.get("ollama", max_ctx=16384, client=capped).read("p", [])
    assert len(capped.calls) == 2


def test_ollama_uses_the_native_api_with_a_context_window_large_enough_for_a_receipt():
    """Ollama's /v1 ignores num_ctx and its default 4096 cut receipts short (2026-11-25)."""
    c = OllamaClient(body={"message": {"content": '{"fields": []}'}, "prompt_eval_count": 4792, "eval_count": 9})
    p = providers.get("ollama", client=c)
    r = p.read("prompt", [b"PNG"], {"type": "object"})
    url, body = c.calls[0]
    assert url == "http://127.0.0.1:11434/api/chat"
    assert body["options"]["num_ctx"] >= 8192 and body["options"]["temperature"] == 0
    assert body["messages"][0]["images"] == [base64.b64encode(b"PNG").decode()] and body["format"] == {"type": "object"}
    assert (r.text, r.input_tokens, r.output_tokens) == ('{"fields": []}', 4792, 9)


def test_ollama_turns_thinking_off_and_drops_the_switch_for_a_model_without_one():
    c = OllamaClient(body={"message": {"content": "{}"}})
    providers.get("ollama", client=c).read("p", [])
    assert c.calls[0][1]["think"] is False  # models.toml: qwen3-vl never answered with thinking on
    refuses = OllamaClient(replies=[(400, {"error": '"gemma3:4b" does not support thinking'}), (200, {"message": {}})])
    providers.get("ollama", think=False, client=refuses).read("p", [])
    assert "think" in refuses.calls[0][1] and "think" not in refuses.calls[1][1]


def test_ollama_accepts_an_old_v1_address_and_reads_the_thinking_channel():
    c = OllamaClient(body={"message": {"content": "", "thinking": '{"fields": [1]}'}})
    p = providers.get("ollama", base_url="http://gpu-box:11434/v1/", client=c)
    assert p.read("p", []).text == '{"fields": [1]}' and c.calls[0][0] == "http://gpu-box:11434/api/chat"
    assert c.calls[0][1]["format"] == "json"


def test_ollama_errors_are_raised_not_read_as_an_empty_answer():
    c = OllamaClient(status=400, body={"error": "exceeds the available context size"})
    with pytest.raises(RuntimeError, match="context size"):
        providers.get("ollama", client=c).read("p", [])


def test_openai_compatible_inlines_images_and_asks_for_json():
    p, rec = _openai(SimpleNamespace(content='{"fields": []}'))
    r = p.read("prompt", [b"PNG"])
    content = rec.calls[0]["messages"][0]["content"]
    assert content[1]["image_url"]["url"] == "data:image/png;base64," + base64.b64encode(b"PNG").decode()
    assert rec.calls[0]["response_format"] == {"type": "json_object"}
    assert (r.text, r.input_tokens, r.output_tokens) == ('{"fields": []}', 7, 3)


def test_openai_compatible_takes_the_answer_from_reasoning_when_content_is_empty():
    """S3: Ollama + qwen3-vl with JSON output put the answer in the thinking channel."""
    p, _ = _openai(SimpleNamespace(content="", reasoning='{"fields": [1]}'))
    assert p.read("p", []).text == '{"fields": [1]}'


def test_claude_code_isolates_the_call(monkeypatch):
    seen = {}

    def run(cmd, **kw):
        seen["cmd"], seen["kw"] = cmd, kw
        images = cmd[cmd.index("--add-dir") + 1]
        seen["listed"] = sorted(p.name for p in __import__("pathlib").Path(images).iterdir())
        out = {
            "result": "ok",
            "usage": {"input_tokens": 5, "cache_read_input_tokens": 10, "output_tokens": 2},
            "total_cost_usd": 0.01,
        }
        return subprocess.CompletedProcess(cmd, 0, json.dumps(out).encode(), b"")

    monkeypatch.setattr("shutil.which", lambda _: "claude")
    monkeypatch.setattr(subprocess, "run", run)
    r = providers.get("claude-code", model="haiku").read("extract this", [b"A", b"B"])
    assert seen["cmd"][:4] == ["claude", "-p", "--model", "haiku"] and "--allowedTools" in seen["cmd"]
    assert seen["listed"] == ["page-1.png", "page-2.png"]
    prompt = seen["kw"]["input"].decode()
    assert "page-1.png" in prompt and prompt.endswith("extract this")
    assert "pages" not in str(seen["kw"]["cwd"])  # runs outside the readable folder
    assert (r.text, r.input_tokens, r.output_tokens, r.cost_usd) == ("ok", 15, 2, 0.01)


def test_claude_code_without_images_disables_tools(monkeypatch):
    seen = {}
    monkeypatch.setattr("shutil.which", lambda _: "claude")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kw: seen.setdefault("cmd", cmd) and subprocess.CompletedProcess(cmd, 0, b'{"result": ""}', b""),
    )
    providers.get("claude-code").read("p", [])
    assert seen["cmd"][-2:] == ["--tools", ""]


def test_unknown_provider_and_defaults():
    with pytest.raises(ValueError, match="unknown provider"):
        providers.get("nope")
    d = providers.defaults()
    assert d["anthropic"]["model"] and d["ollama"]["model"] and d["claude-code"]["model"]
