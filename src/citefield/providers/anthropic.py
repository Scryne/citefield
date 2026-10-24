"""Claude through the Anthropic API. The key comes from ANTHROPIC_API_KEY and stays on the server."""

from __future__ import annotations

import base64
import time
from typing import Any

from citefield.providers import ReadResult

# $ per million tokens (input, output), platform.claude.com pricing page, 2026-10-24. Unknown models report no cost.
PRICES = {"claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str, max_tokens: int = 8192, client: Any = None) -> None:
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.client, self.model, self.max_tokens = client, model, max_tokens

    def read(self, prompt: str, images: list[bytes], json_schema: dict[str, Any] | None = None) -> ReadResult:
        content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(png).decode()},
            }
            for png in images
        ]
        content.append({"type": "text", "text": prompt})
        extra = {"output_config": {"format": {"type": "json_schema", "schema": json_schema}}} if json_schema else None
        t0 = time.perf_counter()
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": content}],
            extra_body=extra,
        )
        seconds = time.perf_counter() - t0
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        tin, tout = int(msg.usage.input_tokens), int(msg.usage.output_tokens)
        price = PRICES.get(self.model)
        cost = (tin * price[0] + tout * price[1]) / 1e6 if price else None
        return ReadResult(text, self.model, tin, tout, cost, seconds)
