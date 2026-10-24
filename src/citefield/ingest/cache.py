"""Ingest results keyed by the document's SHA-256: OCR costs seconds per page, and the same file is often re-run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from citefield.ingest.models import Document, Page, Word
from citefield.ingest.reader import OcrEngine, read_document

FORMAT = 1  # bump when ingest output changes, so stale entries are ignored


def read_cached(data: bytes, cache_dir: Path, *, ocr: OcrEngine | None = None, force_ocr: bool = False) -> Document:
    sha = hashlib.sha256(data).hexdigest()
    d = cache_dir / f"{sha}{'-ocr' if force_ocr else ''}"
    meta = d / "words.json"
    if meta.exists():
        saved = json.loads(meta.read_text("utf-8"))
        if saved["format"] == FORMAT:
            pages = []
            for p in saved["pages"]:
                words = [Word(**{**w, "box": tuple(w["box"])}) for w in p.pop("words")]
                pages.append(Page(**p, image=(d / f"page-{p['index']}.png").read_bytes(), words=words))
            return Document(sha, pages)
    doc = read_document(data, ocr=ocr, force_ocr=force_ocr)
    d.mkdir(parents=True, exist_ok=True)
    for p in doc.pages:
        (d / f"page-{p.index}.png").write_bytes(p.image)
    pages_meta = [
        {
            "index": p.index,
            "width": p.width,
            "height": p.height,
            "source": p.source,
            "words": [w.__dict__ for w in p.words],
        }
        for p in doc.pages
    ]
    meta.write_text(json.dumps({"format": FORMAT, "pages": pages_meta}, ensure_ascii=False), "utf-8")
    return doc
