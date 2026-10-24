"""What the rest of the pipeline sees of a document: page images and words with ids, in page pixel coordinates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from citefield.geometry import Box

WordSource = Literal["pdf", "ocr"]


@dataclass(frozen=True)
class Word:
    """`id` is unique within the document; readers cite these ids, and boxes are only ever built from them."""

    id: int
    text: str
    box: Box
    page: int
    line: int  # unique within the document, in reading order
    source: WordSource
    confidence: float = 1.0  # OCR word score; 1.0 for the PDF text layer


@dataclass
class Page:
    index: int
    width: int
    height: int
    image: bytes  # PNG
    source: WordSource
    words: list[Word] = field(default_factory=list)


@dataclass
class Document:
    sha256: str
    pages: list[Page]

    @property
    def words(self) -> list[Word]:
        return [w for p in self.pages for w in p.words]
