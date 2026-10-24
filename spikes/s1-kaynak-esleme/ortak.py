"""S1 ortak parçalar: OCR, veri yükleyiciler, kutu işlemleri."""
from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

KOK = Path(__file__).resolve().parents[2]
VERI = KOK / ".veri"
CALISMA = VERI / "s1"


@dataclass
class Kelime:
    id: int
    text: str
    kutu: tuple[float, float, float, float]  # x0, y0, x1, y1
    satir: tuple[int, int, int]  # block, par, line
    skor: float = 1.0  # OCR kelime güveni (RapidOCR); eski önbellekte yok


@dataclass
class Alan:
    alan: str
    deger: str
    kutu: tuple[float, float, float, float]


@dataclass
class Belge:
    kimlik: str
    resim: Path
    alanlar: list[Alan] = field(default_factory=list)


def birlesim(kutular):
    kutular = list(kutular)
    return (min(k[0] for k in kutular), min(k[1] for k in kutular),
            max(k[2] for k in kutular), max(k[3] for k in kutular))


def iou(a, b) -> float:
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    kes = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    alan = lambda k: max(0.0, k[2] - k[0]) * max(0.0, k[3] - k[1])
    bir = alan(a) + alan(b) - kes
    return kes / bir if bir > 0 else 0.0


def normalize(s: str) -> str:
    return re.sub(r"[^0-9a-z]", "", str(s).lower())


def ocr(resim: Path) -> list[Kelime]:
    d = pytesseract.image_to_data(Image.open(resim), output_type=pytesseract.Output.DICT)
    out = []
    for i, t in enumerate(d["text"]):
        t = t.strip()
        if not t or float(d["conf"][i]) < 0:
            continue
        x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        out.append(Kelime(len(out), t, (x, y, x + w, y + h), (d["block_num"][i], d["par_num"][i], d["line_num"][i])))
    return out


_RAPID = None


def ocr_rapid(resim: Path) -> list[Kelime]:
    global _RAPID
    if _RAPID is None:
        from rapidocr import RapidOCR
        _RAPID = RapidOCR()
    r = _RAPID(str(resim), return_word_box=True)
    out = []
    for s, satir in enumerate(r.word_results or ()):
        for text, skor, quad in satir:
            text = text.strip()
            if not text:
                continue
            xs, ys = [q[0] for q in quad], [q[1] for q in quad]
            out.append(Kelime(len(out), text, (min(xs), min(ys), max(xs), max(ys)), (0, 0, s), float(skor)))
    return out


MOTORLAR = {"tesseract": ocr, "rapid": ocr_rapid}


def ocr_onbellek(belge: Belge, motor: str = "rapid") -> list[Kelime]:
    yol = CALISMA / f"ocr-{motor}" / f"{belge.kimlik}.json"
    if yol.exists():
        return [Kelime(k["id"], k["text"], tuple(k["kutu"]), tuple(k["satir"]), k.get("skor", 1.0)) for k in json.loads(yol.read_text("utf-8"))]
    kel = MOTORLAR[motor](belge.resim)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps([k.__dict__ for k in kel], ensure_ascii=False), "utf-8")
    return kel


def cord_belgeleri(n: int) -> list[Belge]:
    import pyarrow.parquet as pq

    t = pq.read_table(VERI / "cord" / "validation.parquet").slice(0, n).to_pylist()
    out = []
    for i, r in enumerate(t):
        resim = CALISMA / "resim" / f"cord-{i:03d}.png"
        if not resim.exists():
            resim.parent.mkdir(parents=True, exist_ok=True)
            Image.open(io.BytesIO(r["image"]["bytes"])).convert("RGB").save(resim)
        gt = json.loads(r["ground_truth"])
        b = Belge(f"cord-{i:03d}", resim)
        for satir in gt["valid_line"]:
            kel = [w for w in satir["words"] if not w["is_key"]]
            if not kel:
                continue
            kutu = birlesim(
                (min(w["quad"][f"x{j}"] for j in range(1, 5)), min(w["quad"][f"y{j}"] for j in range(1, 5)),
                 max(w["quad"][f"x{j}"] for j in range(1, 5)), max(w["quad"][f"y{j}"] for j in range(1, 5)))
                for w in kel)
            b.alanlar.append(Alan(satir["category"], " ".join(w["text"] for w in kel), kutu))
        out.append(b)
    return out


CORD_SEMA = (
    "menu.nm (item name), menu.num (item code), menu.cnt (quantity), menu.unitprice, menu.price (line price), "
    "menu.discountprice, menu.vatyn, menu.sub.nm (sub-item / option name), menu.sub.cnt, menu.sub.price, "
    "sub_total.subtotal_price, sub_total.tax_price, sub_total.service_price, sub_total.discount_price, sub_total.etc, "
    "total.total_price, total.cashprice, total.changeprice, total.creditcardprice, total.emoneyprice, "
    "total.menuqty_cnt, total.menutype_cnt, total.total_etc"
)


def alan_adi(ad: str) -> str:
    """2026-10-24 ilk koşudaki şema yazım hatasını (menu.sub_nm) gerçek CORD adına çevirir."""
    return ad.replace("menu.sub_", "menu.sub.") if ad else ad
