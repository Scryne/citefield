"""Labelled open datasets (docs/arastirma/veri-setleri.md). Files are read from a local data directory; nothing with
personal data is ever committed.

- CORD v2 validation (CC BY 4.0): Indonesian receipt photos, word quads per labelled line.
- FATURA (CC BY 4.0): synthetic invoice images; label boxes include the field caption, so values match by containment.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from citefield.eval.metrics import Gold

FATURA_FIELDS = (
    "SELLER_NAME",
    "NUMBER",
    "DATE",
    "DUE_DATE",
    "SUB_TOTAL",
    "TAX",
    "TOTAL",
    "GSTIN_SELLER",
    "GSTIN_BUYER",
)
FATURA_SCALE = 2  # 595x841 images; upscaled like a 144 dpi PDF render (S1)


@dataclass(frozen=True)
class Item:
    id: str
    image: bytes  # PNG or JPEG, already at the resolution the labels refer to
    gold: list[Gold]


def _png(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def cord(data_dir: Path, n: int, start: int = 0) -> Iterator[Item]:
    import pyarrow.parquet as pq

    rows = pq.read_table(data_dir / "cord" / "validation.parquet").slice(start, n).to_pylist()
    for i, r in enumerate(rows, start):
        gold = []
        for line in json.loads(r["ground_truth"])["valid_line"]:
            words = [w for w in line["words"] if not w["is_key"]]  # key words are captions such as "TOTAL"
            if not words:
                continue
            qs = [w["quad"] for w in words]
            box = (
                min(min(q[f"x{j}"] for j in range(1, 5)) for q in qs),
                min(min(q[f"y{j}"] for j in range(1, 5)) for q in qs),
                max(max(q[f"x{j}"] for j in range(1, 5)) for q in qs),
                max(max(q[f"y{j}"] for j in range(1, 5)) for q in qs),
            )
            gold.append(Gold(line["category"], " ".join(w["text"] for w in words), box))
        yield Item(f"cord-{i:03d}", r["image"]["bytes"], gold)


def fatura(data_dir: Path, n: int, start: int = 0) -> Iterator[Item]:
    """Instance 150 of templates start+1 .. start+n: one document per layout (FATURA has 50 templates)."""
    z = zipfile.ZipFile(data_dir / "fatura" / "FATURA2.zip")
    root = "invoices_dataset_final/"
    for t in range(start + 1, start + n + 1):
        name = f"Template{t}_Instance150"
        im = Image.open(io.BytesIO(z.read(f"{root}images/{name}.jpg"))).convert("RGB")
        h, s = im.height, FATURA_SCALE
        ann = json.loads(z.read(f"{root}Annotations/Original_Format/{name}.json"))
        gold = []
        for field in FATURA_FIELDS:
            v = ann.get(field)
            if isinstance(v, dict) and v.get("text", "").strip():
                (x0, y0), (x1, y1) = v["bbox"]  # PDF-style origin bottom-left
                gold.append(Gold(field, v["text"].strip(), (x0 * s, (h - y1) * s, x1 * s, (h - y0) * s)))
        yield Item(f"fatura-{t:02d}", _png(im.resize((im.width * s, im.height * s), Image.Resampling.LANCZOS)), gold)
