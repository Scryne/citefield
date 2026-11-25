"""Ollama through its own chat API, so the context window can be set per request.

Ollama's OpenAI-compatible endpoint ignores `num_ctx` (measured 2026-11-25, Ollama 0.33.2: the prompt was cut at the
server's default either way), and that default is 4096 tokens. A receipt with its word list and the page image needs
about 4,800, so through `/v1` a busy receipt failed outright and a smaller one came back with its JSON cut short, which
read as "no fields". The native `/api/chat` honours `options.num_ctx`.
"""

from __future__ import annotations

import base64
import time
from typing import Any

from citefield.providers import ReadResult


class OllamaProvider:
    """The window starts at `num_ctx` and doubles once per read, up to `max_ctx`, when the answer shows it was too
    small. A fixed large window is no answer either: 16384 pushed qwen3-vl:8b a third onto the CPU of an 8 GB GPU and
    one receipt took over six minutes. Ollama does not always refuse an oversized prompt; it may cut it silently, so
    the check reads the token counts it reports."""

    name = "ollama"

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        num_ctx: int | str = 8192,
        max_ctx: int | str = 32768,
        think: bool | None = None,
        timeout: float = 900.0,
        client: Any = None,
        **_: Any,
    ):
        # qwen3-vl:8b thinks by default: on a receipt it wrote 9,000 characters of thought, hit the output limit and
        # never answered (257 s); with think=false it answered in 44 s and all 16 values matched CORD (2026-11-25)
        self.think = think
        base = (base_url or "http://127.0.0.1:11434").rstrip("/")
        # an OpenAI-style address (".../v1") from an older setting still reaches the native API
        self.base_url = base[: -len("/v1")] if base.endswith("/v1") else base
        self.model, self.num_ctx, self.max_ctx = model, int(num_ctx), int(max_ctx)
        if client is None:
            import httpx

            client = httpx.Client(timeout=timeout)
        self.client = client

    def read(self, prompt: str, images: list[bytes], json_schema: dict[str, Any] | None = None) -> ReadResult:
        ctx, t0 = self.num_ctx, time.perf_counter()
        while True:
            data, ctx = self._chat(prompt, images, json_schema, ctx)
            if not _too_small(data, ctx) or ctx >= self.max_ctx:
                break
            ctx = min(ctx * 2, self.max_ctx)
        msg = data.get("message") or {}
        # S3: with JSON output a thinking model can put the answer in the thinking channel; take it from there
        text = msg.get("content") or msg.get("thinking") or ""
        return ReadResult(
            text,
            self.model,
            int(data.get("prompt_eval_count") or 0),
            int(data.get("eval_count") or 0),
            None,
            time.perf_counter() - t0,
        )

    def _chat(
        self, prompt: str, images: list[bytes], json_schema: dict[str, Any] | None, ctx: int
    ) -> tuple[dict[str, Any], int]:
        """One request; a prompt refused as too long is sent again with a larger window. Returns the window used."""
        body = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "user", "content": prompt, "images": [base64.b64encode(p).decode() for p in images]}],
            "format": json_schema or "json",
            "options": {"temperature": 0, "num_ctx": ctx},
        }
        if self.think is not None:
            body["think"] = self.think
        r = self.client.post(f"{self.base_url}/api/chat", json=body)
        data: dict[str, Any] = r.json() if r.content else {}
        if r.status_code >= 400 or "error" in data:
            err = str(data.get("error") or r.text[:300])
            if "thinking" in err.lower() and self.think is not None:
                self.think = None  # a model without a thinking switch: ask again without it
                return self._chat(prompt, images, json_schema, ctx)
            if "context" in err.lower() and ctx < self.max_ctx:
                return self._chat(prompt, images, json_schema, min(ctx * 2, self.max_ctx))
            raise RuntimeError(f"Ollama answered {r.status_code}: {err}")
        return data, ctx


def _too_small(data: dict[str, Any], ctx: int) -> bool:
    """The answer stopped at the length limit, or prompt and answer filled the window (a silently cut prompt)."""
    used = int(data.get("prompt_eval_count") or 0) + int(data.get("eval_count") or 0)
    return data.get("done_reason") == "length" or used >= ctx - 64
