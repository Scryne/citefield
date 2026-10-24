"""Comparing printed values: what counts as the same string, number or amount."""

from __future__ import annotations

import re


def normalize(s: str) -> str:
    return re.sub(r"[^0-9a-z]", "", str(s).lower())


def digits(s: str) -> int | None:
    d = "".join(ch for ch in str(s) if ch.isdigit())
    return int(d) if d else None


def quantity(s: str) -> float | None:
    m = re.search(r"\d+(?:[.,]\d+)?", str(s))
    return float(m.group(0).replace(",", ".")) if m else None
