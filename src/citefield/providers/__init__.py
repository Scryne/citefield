"""Model providers behind one call: page images + a prompt in, text out, with usage recorded (K-Model, S3).

The provider is swappable on purpose. S3 measured a local vision model on par with Claude for values but weaker for
locations, and a text-only model collapsing on receipts, so the choice belongs to the user, not to the code.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib import resources
from typing import Any, Protocol


@dataclass(frozen=True)
class ReadResult:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None  # when the provider reports it
    seconds: float = 0.0


class Provider(Protocol):
    name: str
    model: str

    def read(self, prompt: str, images: list[bytes], json_schema: dict[str, Any] | None = None) -> ReadResult: ...


def defaults() -> dict[str, dict[str, str]]:
    text = resources.files("citefield").joinpath("models.toml").read_text("utf-8")
    providers: dict[str, dict[str, str]] = tomllib.loads(text)["providers"]
    return providers


def get(name: str, model: str | None = None, **options: Any) -> Provider:
    conf = {**defaults().get(name, {}), **({"model": model} if model else {}), **options}
    if name == "anthropic":
        from citefield.providers.anthropic import AnthropicProvider

        return AnthropicProvider(**conf)
    if name in ("openai", "ollama"):
        from citefield.providers.openai_compat import OpenAICompatibleProvider

        return OpenAICompatibleProvider(name=name, **conf)
    if name == "claude-code":
        from citefield.providers.claude_code import ClaudeCodeProvider

        return ClaudeCodeProvider(**conf)
    raise ValueError(f"unknown provider {name!r}; known: anthropic, openai, ollama, claude-code")
