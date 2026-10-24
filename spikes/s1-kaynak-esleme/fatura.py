"""FATURA yükleyici: her şablondan bir belge; görsel OCR için 2 kat büyütülür, kutular da aynı ölçekte."""
from __future__ import annotations

import io
import json
import zipfile

from PIL import Image

from ortak import CALISMA, VERI, Alan, Belge

ALANLAR = ["SELLER_NAME", "NUMBER", "DATE", "DUE_DATE", "SUB_TOTAL", "TAX", "TOTAL", "GSTIN_SELLER", "GSTIN_BUYER"]
SEMA = ("SELLER_NAME (seller company name), NUMBER (invoice number), DATE (invoice date), DUE_DATE, SUB_TOTAL (amount), "
        "TAX (tax amount), TOTAL (invoice total amount), GSTIN_SELLER (seller GSTIN/tax id), GSTIN_BUYER (buyer GSTIN/tax id)")
OLCEK = 2
KOK = "invoices_dataset_final/"


def fatura_belgeleri(n: int) -> list[Belge]:
    z = zipfile.ZipFile(VERI / "fatura" / "FATURA2.zip")
    out = []
    for sablon in range(1, n + 1):
        ad = f"Template{sablon}_Instance150"
        resim = CALISMA / "resim" / f"fatura-{sablon:02d}.png"
        im = Image.open(io.BytesIO(z.read(f"{KOK}images/{ad}.jpg"))).convert("RGB")
        H = im.height
        if not resim.exists():
            resim.parent.mkdir(parents=True, exist_ok=True)
            im.resize((im.width * OLCEK, im.height * OLCEK), Image.LANCZOS).save(resim)
        ann = json.loads(z.read(f"{KOK}Annotations/Original_Format/{ad}.json"))
        b = Belge(f"fatura-{sablon:02d}", resim)
        for alan in ALANLAR:
            v = ann.get(alan)
            if not isinstance(v, dict) or not v.get("text", "").strip():
                continue
            (x0, y0), (x1, y1) = v["bbox"]
            kutu = (x0 * OLCEK, (H - y1) * OLCEK, x1 * OLCEK, (H - y0) * OLCEK)
            b.alanlar.append(Alan(alan, v["text"].strip(), kutu))
        out.append(b)
    return out
