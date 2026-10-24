"""S2: alan başına güven sinyalleri ve etiketleme (PLAN.md). Ölçüm `olc2.py`'de."""
from __future__ import annotations

import json
import sys

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s1-kaynak-esleme"))
from cikar import CIKTI, claude, json_ayikla, ocr_metni, tahminler  # noqa: E402
import re  # noqa: E402

from olc import deger_tutar  # noqa: E402
from ortak import CALISMA, CORD_SEMA, Belge, alan_adi, birlesim, cord_belgeleri, normalize, ocr_onbellek  # noqa: E402

TUTAR = {"menu.price", "menu.unitprice", "menu.sub.price", "menu.discountprice", "sub_total.subtotal_price",
         "sub_total.tax_price", "sub_total.service_price", "sub_total.discount_price", "total.total_price",
         "total.cashprice", "total.changeprice", "total.creditcardprice", "total.emoneyprice"}
SATIRLAR = CALISMA / "s2-satirlar.json"


def boz(kaynak: Path, hedef: Path, tohum: int):
    """Geometriyi değiştirmeden bozar: yarıya küçült + büyüt, bulanıklık, gürültü, JPEG 20."""
    if hedef.exists():
        return
    im = Image.open(kaynak).convert("RGB")
    w, h = im.size
    im = im.resize((w // 2, h // 2), Image.BILINEAR).resize((w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.2))
    a = np.asarray(im).astype(np.int16)
    a = np.clip(a + np.random.default_rng(tohum).normal(0, 12, a.shape), 0, 255).astype(np.uint8)
    Image.fromarray(a).save(hedef, "JPEG", quality=20)


def belgeler(bas: int, son: int) -> list[Belge]:
    out = []
    for b in cord_belgeleri(son)[bas:son]:
        out.append(b)
        yol = b.resim.with_name(b.kimlik + "-bozuk.jpg")
        boz(b.resim, yol, int(b.kimlik[-3:]))
        out.append(Belge(b.kimlik + "-bozuk", yol, list(b.alanlar)))
    return out


def istem_d(belge: Belge, kelimeler) -> str:
    return (f"You extract structured fields from a document. Schema fields: {CORD_SEMA}.\n"
            f"Read the document image at {belge.resim.as_posix()} and use the OCR words below to cite where each value is "
            "located. If OCR misread a character, give the value as printed in the image but still cite the word ids. "
            "Always emit quantities, even when the quantity is 1.\n"
            "OCR words of the document, one OCR line per row, each word prefixed with its id in brackets:\n"
            + ocr_metni(kelimeler) + "\n"
            + CIKTI % (', "word_ids": [<ids of the OCR words this value was read from>], '
                       '"confidence": <0..1, how sure you are this value is correct>'))


def d_tahminleri(belge: Belge, kelimeler) -> list[dict]:
    on = CALISMA / "cikti" / f"D-{belge.kimlik}.json"
    if on.exists():
        ham = on.read_text("utf-8")
    else:
        ham = claude(istem_d(belge, kelimeler), gorsel=True)
        on.parent.mkdir(parents=True, exist_ok=True)
        on.write_text(ham, "utf-8")
    idx = {k.id: k for k in kelimeler}
    out = []
    for a in json_ayikla(ham):
        t = {"alan": alan_adi(a.get("field")), "deger": str(a.get("value", ""))}
        ids = [i for i in a.get("word_ids") or [] if i in idx]
        hedef = normalize(t["deger"])
        icinde = [i for i in ids if normalize(idx[i].text) and normalize(idx[i].text) in hedef]
        secilen = icinde or ids
        t["kutu"] = birlesim(idx[i].kutu for i in secilen) if secilen else None
        # Alıntı değeri yeniden kuruyor mu: değerde geçen alıntı kelimeleri birleşince değerin kendisi mi.
        # Alıntı değeri yeniden kuruyor mu: alıntılanan (etiketten arındırılmış) kelimeler değere eşdeğer mi.
        t["alinti_uyumu"] = float(bool(secilen) and esdeger(t["alan"] or "", t["deger"], " ".join(idx[i].text for i in secilen)))
        t["ocr_guveni"] = min((idx[i].skor for i in secilen), default=0.0)
        try:
            t["model_guveni"] = float(a.get("confidence", 0.5))
        except (TypeError, ValueError):
            t["model_guveni"] = 0.5
        out.append(t)
    return out


def sayi(s: str):
    d = "".join(ch for ch in str(s) if ch.isdigit())
    return int(d) if d else None


def kural_sinyali(tahmin: list[dict]) -> None:
    """Tahmin edilen değerler üzerinde aritmetik kurallar; her alana +1 (tuttu), -1 (tutmadı), 0 (kural yok)."""
    tek: dict[str, dict] = {}
    for t in tahmin:
        tek.setdefault(t["alan"], t)

    def v(ad):
        return sayi(tek[ad]["deger"]) if ad in tek else None

    kurallar = []
    satir = [t for t in tahmin if t["alan"] == "menu.price"]
    fiyatlar = [sayi(t["deger"]) for t in satir]
    if fiyatlar and None not in fiyatlar and v("sub_total.subtotal_price") is not None:
        kurallar.append((satir + [tek["sub_total.subtotal_price"]], sum(fiyatlar) == v("sub_total.subtotal_price")))
    ek = [a for a in ("sub_total.tax_price", "sub_total.service_price", "sub_total.discount_price") if a in tek]
    if v("total.total_price") is not None and v("sub_total.subtotal_price") is not None and None not in [v(a) for a in ek]:
        hesap = (v("sub_total.subtotal_price") + sum(v(a) for a in ek if a != "sub_total.discount_price")
                 - (v("sub_total.discount_price") or 0))
        kurallar.append(([tek["total.total_price"], tek["sub_total.subtotal_price"]] + [tek[a] for a in ek],
                         hesap == v("total.total_price")))
    if None not in (v("total.cashprice"), v("total.total_price"), v("total.changeprice")):
        kurallar.append(([tek["total.cashprice"], tek["total.total_price"], tek["total.changeprice"]],
                         v("total.cashprice") - v("total.total_price") == v("total.changeprice")))
    for t in tahmin:
        t["kural"] = 0.0
    for alanlar, tuttu in kurallar:
        for t in alanlar:
            if not tuttu:
                t["kural"] = -1.0
            elif t["kural"] == 0.0:
                t["kural"] = 1.0


def capraz_sinyali(tahmin: list[dict], a_tahmin: list[dict]) -> None:
    """İkinci, bağımsız okuma (A) aynı alan için eşdeğer bir değer okumuş mu; her A okuması bir kez kullanılır."""
    havuz = list(a_tahmin)
    for t in tahmin:
        j = next((i for i, a in enumerate(havuz) if a["alan"] == t["alan"] and esdeger(t["alan"] or "", t["deger"], a["deger"])), None)
        t["capraz"] = float(j is not None)
        if j is not None:
            havuz.pop(j)


def miktar(s: str):
    m = re.search(r"\d+(?:[.,]\d+)?", str(s))
    return float(m.group(0).replace(",", ".")) if m else None


def esdeger(alan: str, tahmin: str, gercek: str) -> bool:
    """Değer eşdeğerliği. CORD fişteki yazımı saklar ("1Prs", "1x"), model anlamı yazar ("1"): miktarlar sayı olarak,
    tutarlar yalnız rakamlarıyla karşılaştırılır; geri kalan S1 normalize eşitliği."""
    alan = alan or ""
    if alan.endswith("cnt"):
        return miktar(tahmin) is not None and miktar(tahmin) == miktar(gercek)
    if alan in TUTAR:
        return sayi(tahmin) is not None and sayi(tahmin) == sayi(gercek)
    return deger_tutar(tahmin, gercek, False)


def etiketle(belge: Belge, tahmin: list[dict]) -> int:
    """Tahmin doğru = aynı adlı, değeri tutan, kullanılmamış bir etiket alanı var. Atlanan etiket sayısını döner."""
    kalan = list(belge.alanlar)
    for t in tahmin:
        j = next((i for i, g in enumerate(kalan) if g.alan == t["alan"] and esdeger(t["alan"], t["deger"], g.deger)), None)
        t["dogru"] = j is not None
        if j is not None:
            kalan.pop(j)
    return len(kalan)


def topla(bas=25, son=65):
    bs = belgeler(bas, son)
    kel = {b.kimlik: ocr_onbellek(b) for b in bs}

    def is_(b):
        try:
            return b, d_tahminleri(b, kel[b.kimlik]), tahminler("A", b, kel[b.kimlik], CORD_SEMA)
        except Exception as e:  # noqa: BLE001
            print("HATA", b.kimlik, str(e)[:200], flush=True)
            return b, None, None

    satirlar, belge_ozet = [], []
    with ThreadPoolExecutor(4) as ex:
        for b, d, a in ex.map(is_, bs):
            if d is None:
                continue
            kural_sinyali(d)
            capraz_sinyali(d, a)
            atlanan = etiketle(b, d)
            bozuk = b.kimlik.endswith("bozuk")
            belge_ozet.append({"belge": b.kimlik, "bozuk": bozuk, "etiket": len(b.alanlar), "atlanan": atlanan, "tahmin": len(d)})
            for t in d:
                satirlar.append({"belge": b.kimlik, "grup": b.kimlik[:8], "bozuk": bozuk, "alan": t["alan"],
                                 "deger": t["deger"], "dogru": t["dogru"], "alinti_uyumu": t["alinti_uyumu"],
                                 "ocr_guveni": t["ocr_guveni"], "capraz": t["capraz"], "kural": t["kural"],
                                 "bicim": float(t["alan"] not in TUTAR or sayi(t["deger"]) is not None),
                                 "model_guveni": t["model_guveni"]})
    SATIRLAR.write_text(json.dumps({"satirlar": satirlar, "belgeler": belge_ozet}, ensure_ascii=False), "utf-8")
    return satirlar


if __name__ == "__main__":
    s = topla()
    print(len(s), "tahmin;", sum(not x["dogru"] for x in s), "yanlış")
