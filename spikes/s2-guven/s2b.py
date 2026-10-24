"""S2b: gürültüsüz etiketli sentetik fişlerde güven sinyalleri (PLAN-S2b.md). Ölçüm: `olc2.py s2b`."""
from __future__ import annotations

import io
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s1-kaynak-esleme"))
from cikar import claude, json_ayikla, ocr_metni  # noqa: E402
from ortak import CALISMA, VERI, Belge, normalize, ocr_onbellek  # noqa: E402

SATIRLAR = CALISMA / "s2b-satirlar.json"
PARA = {"line.unit_price", "line.total", "subtotal", "tax.amount", "total", "tendered", "change"}
RAKAM = {"date", "time"}
SEMA = ("merchant (store name), date, time, receipt_no, tax_id (VAT / USt-IdNr / P.IVA / SIRET number as printed), "
        "line.name, line.qty, line.unit_price, line.total (line fields carry the 1-based line number), subtotal, "
        "tax.amount (one entry per printed tax amount), total, tendered (cash given), change")
KURALLAR = ("Only extract values that are printed on the document. Copy them exactly as printed: do not fix spelling, do not "
            "normalise numbers, do not infer values that are not printed (no quantity if no quantity is printed). ")
CIKTI = ('Return ONLY a JSON object, no prose: {"fields": [{"field": "<field name>", "value": "<value exactly as printed>", '
         '"line": <line number for line.* fields, else null>%s}]}. Omit fields that are not printed.')


def belgeler(n: int) -> list[Belge]:
    t = pq.read_table(VERI / "sentetik" / "eval0.parquet", columns=["id", "image_clean", "image_photo", "fields"]).slice(0, n).to_pylist()
    out = []
    for r in t:
        alanlar = gercek_alanlar(json.loads(r["fields"]))
        for hal, sutun, uzanti in (("temiz", "image_clean", "png"), ("foto", "image_photo", "jpg")):
            yol = CALISMA / "resim" / f"sent-{r['id']}-{hal}.{uzanti}"
            if not yol.exists():
                yol.parent.mkdir(parents=True, exist_ok=True)
                Image.open(io.BytesIO(r[sutun]["bytes"])).convert("RGB").save(yol)
            b = Belge(f"sent-{r['id']}-{hal}", yol, alanlar)
            out.append(b)
    return out


def para_metni(v) -> str:
    return f"{v:.2f}"


def gercek_alanlar(f: dict) -> list:
    """Etiketi düz (alan, değer) listesine çevirir; kutu yok (S2b konumu ölçmez)."""
    from ortak import Alan
    a = []
    for ad in ("merchant", "date", "time", "receipt_no", "tax_id"):
        if f.get(ad):
            a.append(Alan(ad, str(f[ad]), (0, 0, 0, 0)))
    for i, s in enumerate(f.get("lines") or [], 1):
        a += [Alan("line.name", s["name"], (0, 0, 0, 0)), Alan("line.total", para_metni(s["total"]), (0, 0, 0, 0))]
        if s["qty"] != 1:  # adet ve birim fiyat yalnız adet > 1 iken basılı ("2 x 39,98")
            a += [Alan("line.qty", str(s["qty"]), (0, 0, 0, 0)), Alan("line.unit_price", para_metni(s["unit_price"]), (0, 0, 0, 0))]
    for vergi in f.get("taxes") or []:
        if vergi.get("amount") is not None:
            a.append(Alan("tax.amount", para_metni(vergi["amount"]), (0, 0, 0, 0)))
    for ad in ("subtotal", "total", "tendered", "change"):
        if f.get(ad) is not None:
            a.append(Alan(ad, para_metni(f[ad]), (0, 0, 0, 0)))
    return a


def rakamlar(s) -> str:
    return "".join(ch for ch in str(s) if ch.isdigit())


def miktar(s):
    m = re.search(r"\d+(?:[.,]\d+)?", str(s))
    return float(m.group(0).replace(",", ".")) if m else None


def esdeger(alan: str, tahmin: str, gercek: str) -> bool:
    alan = alan or ""
    if alan in PARA:
        return bool(rakamlar(tahmin)) and rakamlar(tahmin).lstrip("0") == rakamlar(gercek).lstrip("0")
    if alan == "line.qty":
        return miktar(tahmin) is not None and miktar(tahmin) == miktar(gercek)
    if alan == "tax_id":  # etiket ön ekiyle tutulur ("VAT NO GB878076490"), model numarayı yazar
        a, b = normalize(tahmin), normalize(gercek)
        return len(a) >= 5 and a in b
    if alan in RAKAM:
        return bool(rakamlar(tahmin)) and rakamlar(tahmin) == rakamlar(gercek)
    return normalize(tahmin) == normalize(gercek)


def okuma(yol: str, belge: Belge, kelimeler) -> list[dict]:
    on = CALISMA / "cikti" / f"{yol}2-{belge.kimlik}.json"
    if on.exists():
        ham = on.read_text("utf-8")
    else:
        bas = (f"You extract structured fields from a store receipt. Fields: {SEMA}.\n{KURALLAR}\n"
               f"Read the document image at {belge.resim.as_posix()}.\n")
        if yol == "D":
            istem = (bas + "Use the OCR words below to cite where each value is located; if OCR misread a character, give the "
                     "value as printed in the image but still cite the word ids.\nOCR words, one OCR line per row, each word "
                     "prefixed with its id:\n" + ocr_metni(kelimeler) + "\n"
                     + CIKTI % ', "word_ids": [<ids of the OCR words>], "confidence": <0..1, how sure you are this value is correct>')
        else:
            istem = bas + CIKTI % ""
        ham = claude(istem, gorsel=True)
        on.parent.mkdir(parents=True, exist_ok=True)
        on.write_text(ham, "utf-8")
    return json_ayikla(ham)


def sinyaller(belge: Belge, kelimeler, d: list[dict], a: list[dict]) -> list[dict]:
    idx = {k.id: k for k in kelimeler}
    out = []
    for f in d:
        t = {"alan": f.get("field"), "deger": str(f.get("value", "")), "satir": f.get("line")}
        ids = [i for i in f.get("word_ids") or [] if i in idx]
        hedef = normalize(t["deger"])
        icinde = [i for i in ids if normalize(idx[i].text) and normalize(idx[i].text) in hedef]
        secilen = icinde or ids
        t["alinti_uyumu"] = float(bool(secilen) and esdeger(t["alan"], t["deger"], " ".join(idx[i].text for i in secilen)))
        t["ocr_guveni"] = min((idx[i].skor for i in secilen), default=0.0)
        try:
            t["model_guveni"] = float(f.get("confidence", 0.5))
        except (TypeError, ValueError):
            t["model_guveni"] = 0.5
        out.append(t)
    # çapraz okuma
    havuz = [{"alan": x.get("field"), "deger": str(x.get("value", ""))} for x in a]
    for t in out:
        j = next((i for i, x in enumerate(havuz) if x["alan"] == t["alan"] and esdeger(t["alan"], t["deger"], x["deger"])), None)
        t["capraz"] = float(j is not None)
        if j is not None:
            havuz.pop(j)
    kurallar(out)
    # etiket
    kalan = list(belge.alanlar)
    for t in out:
        j = next((i for i, g in enumerate(kalan) if g.alan == t["alan"] and esdeger(t["alan"], t["deger"], g.deger)), None)
        t["dogru"] = j is not None
        if j is not None:
            kalan.pop(j)
    belge.atlanan = len(kalan)
    return out


def kurus(s):
    r = rakamlar(s)
    return int(r) if r else None


def kurallar(t: list[dict]) -> None:
    """Fişin kendi aritmetiği: adet × birim = satır, Σ satır = ara toplam, ara toplam + vergi = toplam (vergi dahil değilse),
    verilen − toplam = para üstü. Her alana +1 (tuttu) / -1 (tutmadı) / 0 (kural yok)."""
    for x in t:
        x["kural"] = 0.0
    sonuc = []
    satirlar: dict = {}
    for x in t:
        if (x["alan"] or "").startswith("line.") and x["satir"] is not None:
            satirlar.setdefault(x["satir"], {})[x["alan"]] = x
    for s in satirlar.values():
        if {"line.qty", "line.unit_price", "line.total"} <= s.keys():
            q, u, tt = miktar(s["line.qty"]["deger"]), kurus(s["line.unit_price"]["deger"]), kurus(s["line.total"]["deger"])
            if None not in (q, u, tt):
                sonuc.append((list(s.values()), round(q * u) == tt))
    tek = {}
    for x in t:
        tek.setdefault(x["alan"], x)
    toplamlar = [s["line.total"] for s in satirlar.values() if "line.total" in s]
    if toplamlar and "subtotal" in tek and None not in [kurus(x["deger"]) for x in toplamlar]:
        sonuc.append((toplamlar + [tek["subtotal"]], sum(kurus(x["deger"]) for x in toplamlar) == kurus(tek["subtotal"]["deger"])))
    vergiler = [x for x in t if x["alan"] == "tax.amount"]
    if "subtotal" in tek and "total" in tek:
        st, tp = kurus(tek["subtotal"]["deger"]), kurus(tek["total"]["deger"])
        vs = sum(kurus(x["deger"]) or 0 for x in vergiler)
        if st is not None and tp is not None:
            # vergi dahil fişlerde toplam = ara toplam; değilse ara toplam + vergi
            sonuc.append(([tek["subtotal"], tek["total"]] + vergiler, tp in (st, st + vs)))
    if {"tendered", "total", "change"} <= tek.keys():
        v = [kurus(tek[a]["deger"]) for a in ("tendered", "total", "change")]
        if None not in v:
            sonuc.append(([tek["tendered"], tek["total"], tek["change"]], v[0] - v[1] == v[2]))
    for alanlar, tuttu in sonuc:
        for x in alanlar:
            if not tuttu:
                x["kural"] = -1.0
            elif x["kural"] == 0.0:
                x["kural"] = 1.0


def topla(n=40):
    bs = belgeler(n)
    kel = {b.kimlik: ocr_onbellek(b) for b in bs}

    def is_(b):
        try:
            return b, okuma("D", b, kel[b.kimlik]), okuma("A", b, kel[b.kimlik])
        except Exception as e:  # noqa: BLE001
            print("HATA", b.kimlik, str(e)[:200], flush=True)
            return b, None, None

    satirlar, ozet = [], []
    with ThreadPoolExecutor(4) as ex:
        for b, d, a in ex.map(is_, bs):
            if d is None:
                continue
            t = sinyaller(b, kel[b.kimlik], d, a)
            bozuk = b.kimlik.endswith("foto")
            ozet.append({"belge": b.kimlik, "bozuk": bozuk, "etiket": len(b.alanlar), "atlanan": b.atlanan, "tahmin": len(t)})
            for x in t:
                satirlar.append({"belge": b.kimlik, "grup": b.kimlik.rsplit("-", 1)[0], "bozuk": bozuk, "alan": x["alan"],
                                 "deger": x["deger"], "dogru": x["dogru"], "alinti_uyumu": x["alinti_uyumu"],
                                 "ocr_guveni": x["ocr_guveni"], "capraz": x["capraz"], "kural": x["kural"],
                                 "bicim": float((x["alan"] or "") not in PARA or bool(rakamlar(x["deger"]))),
                                 "model_guveni": x["model_guveni"]})
    SATIRLAR.write_text(json.dumps({"satirlar": satirlar, "belgeler": ozet}, ensure_ascii=False), "utf-8")
    return satirlar


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    s = topla(n)
    print(len(s), "tahmin;", sum(not x["dogru"] for x in s), "yanlış")
