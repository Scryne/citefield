"""S3: yerel model (Ollama) ile S1 hattı. Kullanım: python yerel.py <veri: cord|fatura> <n> <kol> [cpu]
Kollar: B (yalnız kimlikli OCR, metin modeli) · C (görsel + kimlikli OCR, görsel model)."""
from __future__ import annotations

import base64
import json
import sys
import time
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "s1-kaynak-esleme"))
sys.path.insert(0, str(KOK / "s2-guven"))
import olc  # noqa: E402
from cikar import json_ayikla, ocr_metni  # noqa: E402
from ortak import CALISMA, alan_adi, birlesim, cord_belgeleri, normalize, ocr_onbellek  # noqa: E402
from s1_yeniden import eslestir as eslestir_esdeger  # noqa: E402

OLLAMA = "http://127.0.0.1:11434/api/chat"
# Küçük modeller kısa şemada alanı yanlış anlıyor (qwen3:8b "menu.num"u fiyat sandı, "TOTAL"ı değer yazdı): yerel kollar
# tipli ve açıklamalı şema alır. Claude kıyas çizgisi (S1) kısa şemayla koşmuştu; bu fark SONUC'ta yazılı.
CORD_TIPLI = (
    "menu.nm (text: item name), menu.num (text: item code/SKU, only if a separate code is printed), menu.cnt (number: "
    "quantity), menu.unitprice (amount: unit price), menu.price (amount: line total price), menu.discountprice (amount), "
    "menu.sub.nm (text: sub-item/option name), menu.sub.cnt (number), menu.sub.price (amount), "
    "sub_total.subtotal_price (amount), sub_total.tax_price (amount), sub_total.service_price (amount), "
    "sub_total.discount_price (amount), total.total_price (amount: grand total), total.cashprice (amount: cash given), "
    "total.changeprice (amount: change returned), total.creditcardprice (amount), total.emoneyprice (amount), "
    "total.menuqty_cnt (number: total quantity), total.menutype_cnt (number: number of item types)")
KURAL = ("Only extract values that are printed on the document. Copy them exactly as printed: do not fix spelling, do not "
         "infer values that are not printed. Never output a label word (such as TOTAL, CASH, CHANGE) as a value. ")


def tip_kapisi(alan: str, deger: str) -> bool:
    """Tutar ve sayı alanına rakamsız değer giremez (deterministik; model ne derse desin)."""
    a = alan or ""
    sayisal = a.endswith(("price", "cnt", "TOTAL", "TAX", "SUB_TOTAL")) or a in {"menu.cnt", "menu.sub.cnt"}
    return not sayisal or any(ch.isdigit() for ch in deger)
CIKTI = ('Return ONLY a JSON object: {"fields": [{"field": "<field name>", "value": "<value exactly as printed>", '
         '"word_ids": [<ids of the OCR words this value was read from>]}]}. One entry per occurrence (each line item '
         'separately). Omit fields that are not printed.')


def istem(kol: str, sema: str, kelimeler) -> str:
    ocr = ("OCR words of the document, one OCR line per row, each word prefixed with its id in brackets:\n"
           + ocr_metni(kelimeler) + "\n")
    if kol == "B":
        return (f"You extract structured fields from a document. Schema fields: {sema}.\n{KURAL}\n" + ocr
                + "If OCR misread a character, give the corrected value but still cite the word ids.\n" + CIKTI)
    return (f"You extract structured fields from the attached document image. Schema fields: {sema}.\n{KURAL}\n"
            "Use the OCR words below to cite where each value is located. If OCR misread a character, give the value as "
            "printed in the image but still cite the word ids.\n" + ocr + CIKTI)


def ollama(model: str, prompt: str, resim: Path | None, cpu: bool) -> tuple[str, float]:
    mesaj = {"role": "user", "content": prompt}
    if resim is not None:
        mesaj["images"] = [base64.b64encode(resim.read_bytes()).decode()]
    govde = {"model": model, "messages": [mesaj], "format": "json", "stream": False, "think": False,
             "options": {"temperature": 0, "num_ctx": 8192, **({"num_gpu": 0} if cpu else {})}}
    t0 = time.time()
    r = urllib.request.urlopen(urllib.request.Request(OLLAMA, json.dumps(govde).encode(), {"Content-Type": "application/json"}),
                               timeout=1800)
    m = json.loads(r.read())["message"]
    # Ollama 0.33 + qwen3-vl: format=json ve think=false birlikteyken cevap "thinking" alanına düşüyor (S3'te ölçüldü)
    return (m.get("content") or m.get("thinking") or ""), time.time() - t0


def tahminler(kol: str, model: str, belge, kelimeler, sema: str, cpu: bool):
    ad = f"{kol}-{model.replace(':', '_')}{'-cpu' if cpu else ''}"
    on = CALISMA / "cikti-yerel" / f"{ad}-{belge.kimlik}.json"
    if on.exists():
        kayit = json.loads(on.read_text("utf-8"))
    else:
        ham, sure = ollama(model, istem(kol, sema, kelimeler), belge.resim if kol == "C" else None, cpu)
        kayit = {"ham": ham, "sure": sure}
        on.parent.mkdir(parents=True, exist_ok=True)
        on.write_text(json.dumps(kayit, ensure_ascii=False), "utf-8")
    idx = {k.id: k for k in kelimeler}
    out = []
    for a in json_ayikla(kayit["ham"]):
        t = {"alan": alan_adi(a.get("field")), "deger": str(a.get("value", ""))}
        ids = [i for i in (a.get("word_ids") or []) if isinstance(i, int) and i in idx]
        hedef = normalize(t["deger"])
        icinde = [i for i in ids if normalize(idx[i].text) and normalize(idx[i].text) in hedef]
        secilen = icinde or ids
        t["kutu"] = birlesim(idx[i].kutu for i in secilen) if secilen else None
        out.append(t)
    return out, kayit["sure"]


def main():
    veri, n, kol, model = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    cpu = "cpu" in sys.argv[5:]
    if veri == "cord":
        belgeler, sema = cord_belgeleri(n), CORD_TIPLI
    else:
        import fatura
        belgeler, sema = fatura.fatura_belgeleri(n), fatura.SEMA
    es, es_kapisiz, sureler, hatali = [], [], [], 0
    for b in belgeler:
        try:
            t, s = tahminler(kol, model, b, ocr_onbellek(b), sema, cpu)
        except Exception as e:  # noqa: BLE001
            print("HATA", b.kimlik, str(e)[:200], flush=True)
            hatali += 1
            continue
        sureler.append(s)
        esle = (lambda g, x: eslestir_esdeger(g, x)) if veri == "cord" else (lambda g, x: olc.eslestir(g, x, kapsama=True))
        es_kapisiz += esle(b.alanlar, t)
        es += esle(b.alanlar, [x for x in t if tip_kapisi(x["alan"], x["deger"])])
        print(f"  {b.kimlik} {s:.1f} sn", flush=True)
    oz = olc.ozet(es) | {"kapisiz": olc.ozet(es_kapisiz), "hatali_belge": hatali, "sn_belge_ort": round(sum(sureler) / max(len(sureler), 1), 1)}
    print(veri, kol, model, "cpu" if cpu else "gpu", oz, flush=True)
    rapor = CALISMA / "s3-rapor.json"
    hepsi = json.loads(rapor.read_text("utf-8")) if rapor.exists() else {}
    hepsi[f"{veri}|{kol}|{model}|{'cpu' if cpu else 'gpu'}|{n}"] = oz
    rapor.write_text(json.dumps(hepsi, ensure_ascii=False, indent=1), "utf-8")


if __name__ == "__main__":
    main()
