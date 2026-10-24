"""Turn a PDF or image into page images and cited-able words.

Born-digital PDF pages use their text layer; scanned pages and images go through OCR. Everything ends up in the same
pixel space as the rendered page image, because that image is what the reader model and the reviewer both look at.
"""

from __future__ import annotations

import hashlib
import io
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageOps

from citefield.geometry import Box
from citefield.ingest.models import Document, Page, Word, WordSource

PDF_SCALE = 2.0  # 144 dpi; S1 measured FATURA at this resolution with 100% location
MIN_TEXT_WORDS = 3
MAX_CID_SHARE = 0.2  # "(cid:12)" words mean the text layer has no usable font encoding


@dataclass(frozen=True)
class RawWord:
    text: str
    box: Box
    confidence: float = 1.0


OcrEngine = Callable[[bytes], list[RawWord]]


def read_document(data: bytes, *, ocr: OcrEngine | None = None, force_ocr: bool = False) -> Document:
    if ocr is None:
        from citefield.ingest.ocr import rapidocr_words

        ocr = rapidocr_words
    pairs = _pdf_pages(data, ocr, force_ocr) if data[:5] == b"%PDF-" else [_image_page(data, ocr)]
    return Document(hashlib.sha256(data).hexdigest(), _assign_ids(pairs))


def _png(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _image_page(data: bytes, ocr: OcrEngine) -> tuple[Page, list[RawWord]]:
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")  # phone photos carry rotation in EXIF
    png = _png(im)
    return Page(0, im.width, im.height, png, "ocr"), ocr(png)


def _pdf_pages(data: bytes, ocr: OcrEngine, force_ocr: bool) -> list[tuple[Page, list[RawWord]]]:
    out = []
    doc = pdfium.PdfDocument(data)
    with pdfplumber.open(io.BytesIO(data)) as plumber:
        for i in range(len(doc)):
            im = doc[i].render(scale=PDF_SCALE).to_pil().convert("RGB")
            png = _png(im)
            words = [] if force_ocr else _text_layer(plumber.pages[i], doc[i].get_rotation())
            source: WordSource = "pdf" if words else "ocr"
            out.append((Page(i, im.width, im.height, png, source), words or ocr(png)))
    return out


def _text_layer(page: pdfplumber.page.Page, rotation: int) -> list[RawWord]:
    """Words from the PDF text layer, or [] when it should not be trusted. Rotated pages go to OCR: pdfplumber
    reports unrotated coordinates while the render is rotated, and v1 does not reconcile the two."""
    if rotation:
        return []
    ws = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    if len(ws) < MIN_TEXT_WORDS or sum("(cid:" in w["text"] for w in ws) > MAX_CID_SHARE * len(ws):
        return []
    x0, top0 = float(page.bbox[0]), float(page.bbox[1])
    s = PDF_SCALE
    return [
        RawWord(w["text"], ((w["x0"] - x0) * s, (w["top"] - top0) * s, (w["x1"] - x0) * s, (w["bottom"] - top0) * s))
        for w in ws
    ]


def _group_lines(boxes: Sequence[Box]) -> list[int]:
    """Words whose vertical centres sit within half a word height of a line's centre share that line. Used for both
    sources: OCR detection boxes split one printed row (item name and price come back as separate detections), and
    K-Satır needs the printed row."""
    order = sorted(range(len(boxes)), key=lambda i: (boxes[i][1] + boxes[i][3]) / 2)
    line_of = [0] * len(boxes)
    line, centre, height = -1, float("-inf"), 0.0
    for i in order:
        b = boxes[i]
        c, h = (b[1] + b[3]) / 2, b[3] - b[1]
        if abs(c - centre) > max(height, h) / 2:
            line, centre, height = line + 1, c, h
        line_of[i] = line
    return line_of


def _assign_ids(pairs: list[tuple[Page, list[RawWord]]]) -> list[Page]:
    """Number words and lines across the whole document in reading order: page, line top to bottom, left to right."""
    next_id = next_line = 0
    for page, raw in pairs:
        lines = _group_lines([r.box for r in raw])  # already numbered top to bottom
        for k in sorted(range(len(raw)), key=lambda k: (lines[k], raw[k].box[0])):
            r = raw[k]
            page.words.append(Word(next_id, r.text, r.box, page.index, next_line + lines[k], page.source, r.confidence))
            next_id += 1
        next_line += max(lines, default=-1) + 1
    return [p for p, _ in pairs]
