"""RapidOCR word boxes (K-OCR, S1: 91.6% of receipt field words found, Tesseract 45.7%)."""

from __future__ import annotations

from functools import cache
from typing import Any

from citefield.ingest.reader import RawWord


@cache
def _engine() -> Any:
    from rapidocr import RapidOCR

    return RapidOCR()


def rapidocr_words(png: bytes) -> list[RawWord]:
    result = _engine()(png, return_word_box=True)
    out = []
    for words in result.word_results or ():
        for text, score, quad in words:
            text = text.strip()
            if text:
                xs, ys = [float(q[0]) for q in quad], [float(q[1]) for q in quad]
                out.append(RawWord(text, (min(xs), min(ys), max(xs), max(ys)), float(score)))
    return out
