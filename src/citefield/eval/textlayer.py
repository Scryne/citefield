"""Text layer vs OCR on born-digital PDFs with exact word boxes (synthpdf). A gold word counts as found when a word
with the same text exists, and as located when such a word's centre falls inside the gold box.
Usage: python -m citefield.eval.textlayer <data dir> [n]"""

from __future__ import annotations

import json
import sys
import time
import zipfile
from pathlib import Path

from citefield.eval.metrics import CENTER_MARGIN, normalize
from citefield.eval.synthpdf import make_pdf
from citefield.geometry import Box, center_inside
from citefield.ingest import read_document


def fatura_vocab(data_dir: Path, templates: int = 30) -> list[str]:
    z = zipfile.ZipFile(data_dir / "fatura" / "FATURA2.zip")
    root = "invoices_dataset_final/Annotations/layoutlm_HF_format/"
    wanted = tuple(f"{root}Template{t}_Instance150_" for t in range(1, templates + 1))  # suffix is the HF split
    words: set[str] = set()
    for name in z.namelist():
        if name.startswith(wanted):
            words |= set(json.loads(z.read(name))["words"])
    return sorted(w for w in words if w.isascii() and w.strip())  # base-14 fonts cannot draw the rest


def main() -> None:
    data, n = Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 30
    vocab = fatura_vocab(data)
    totals = {"pdf": [0, 0, 0, 0.0], "ocr": [0, 0, 0, 0.0]}  # found, located, gold, seconds
    for seed in range(n):
        pdf, gold = make_pdf(vocab, seed)
        for path, force in (("pdf", False), ("ocr", True)):
            t0 = time.perf_counter()
            doc = read_document(pdf, force_ocr=force)
            assert doc.pages[0].source == path
            t = totals[path]
            t[3] += time.perf_counter() - t0
            by_text: dict[str, list[Box]] = {}
            for w in doc.words:
                by_text.setdefault(normalize(w.text), []).append(w.box)
            for g in gold:
                boxes = by_text.get(normalize(g.text), [])
                t[0] += bool(boxes)
                t[1] += any(center_inside(b, g.box, CENTER_MARGIN) for b in boxes)
                t[2] += 1
    for path, (found, located, total, secs) in totals.items():
        print(
            f"{path}: found {found / total:.1%}, located {located / total:.1%} of {total} words; {secs / n:.2f} s/page"
        )


if __name__ == "__main__":
    main()
