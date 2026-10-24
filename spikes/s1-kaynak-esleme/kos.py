"""S1 koşucu: python kos.py <veri> <n> <yollar>   ör. kos.py cord 25 ABC"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor

from cikar import tahminler
from olc import eslestir, ozet
from ortak import CALISMA, CORD_SEMA, cord_belgeleri, ocr_onbellek

veri, n, yollar = sys.argv[1], int(sys.argv[2]), sys.argv[3]
belgeler = cord_belgeleri(n) if veri == "cord" else __import__("fatura").fatura_belgeleri(n)
sema = CORD_SEMA if veri == "cord" else __import__("fatura").SEMA
kel = {b.kimlik: ocr_onbellek(b) for b in belgeler}

def is_(arg):
    yol, b = arg
    try:
        return yol, b, tahminler(yol, b, kel[b.kimlik], sema)
    except Exception as e:  # noqa: BLE001
        print("HATA", yol, b.kimlik, str(e)[:200], flush=True)
        return yol, b, None

sonuc = {y: [] for y in yollar}
hatali = {y: 0 for y in yollar}
with ThreadPoolExecutor(4) as ex:
    for yol, b, t in ex.map(is_, [(y, b) for y in yollar for b in belgeler]):
        if t is None:
            hatali[yol] += 1
            continue
        sonuc[yol] += [(b.kimlik, g, tt, i, m) for g, tt, i, m in eslestir(b.alanlar, t, kapsama=(veri == "fatura"))]
rapor = {}
for y in yollar:
    rapor[y] = ozet([(g, t, i, m) for _, g, t, i, m in sonuc[y]]) | {"hatali_belge": hatali[y]}
    print(y, rapor[y])
(CALISMA / f"rapor-{veri}.json").write_text(json.dumps({"rapor": rapor, "ayrinti": {
    y: [{"belge": k, "alan": g.alan, "deger": g.deger, "tahmin": t and t["deger"], "iou": round(i, 3), "merkez": m} for k, g, t, i, m in sonuc[y]]
    for y in yollar}}, ensure_ascii=False, indent=1), "utf-8")
