"""Any OpenAI-compatible chat endpoint: OpenAI, Ollama, vLLM, OpenRouter, NVIDIA NIM.

Images go inline as base64 data URLs (Ollama accepts nothing else). JSON mode only, not json_schema: Ollama's OpenAI
endpoint documents `response_format` but not schema enforcement, and the reader parses JSON defensively anyway.
"""

from __future__ import annotations

import base64
import os
import time
from typing import Any

from citefield.providers import ReadResult


class OpenAICompatibleProvider:
    def __init__(
        self, name: str, model: str, base_url: str | None = None, api_key: str | None = None, client: Any = None
    ):
        if client is None:
            from openai import OpenAI

            key = api_key or os.environ.get("OPENAI_API_KEY") or ("ollama" if name == "ollama" else None)
            client = OpenAI(base_url=base_url, api_key=key)
        self.name, self.model, self.client = name, model, client

    def read(self, prompt: str, images: list[bytes], json_schema: dict[str, Any] | None = None) -> ReadResult:
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        content += [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode()}}
            for png in images
        ]
        t0 = time.perf_counter()
        r = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        seconds = time.perf_counter() - t0
        m = r.choices[0].message
        # S3: Ollama with JSON output and thinking models put the answer in the reasoning channel; take it from there
        text = (
            m.content or getattr(m, "reasoning", None) or (getattr(m, "model_extra", None) or {}).get("reasoning") or ""
        )
        usage = r.usage
        return ReadResult(
            text,
            self.model,
            int(getattr(usage, "prompt_tokens", 0) or 0),
            int(getattr(usage, "completion_tokens", 0) or 0),
            None,
            seconds,
        )
