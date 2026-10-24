"""S1'in kayıtlı çıktılarını S2'nin anlamsal eşdeğerlik kuralıyla yeniden puanlar (yeni model çağrısı yok).
S1 ölçeri miktarları yazım eşitliğiyle karşılaştırıyordu ("1Prs" ≠ "1"); bu, değer doğruluğunu eksik gösteriyordu."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s1-kaynak-esleme"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import olc  # noqa: E402
from cikar import tahminler  # noqa: E402
from guven import esdeger  # noqa: E402
from ortak import CORD_SEMA, cord_belgeleri, ocr_onbellek  # noqa: E402

def eslestir(gercek, tahmin):
    """olc.eslestir'in eşi; tek fark değer karşılaştırmasının alan türüne göre (esdeger) yapılması."""
    kullanildi, sonuc = set(), []
    for g in gercek:
        ad = [(j, t) for j, t in enumerate(tahmin) if j not in kullanildi and t.get("alan") == g.alan
              and esdeger(g.alan, t.get("deger", ""), g.deger)]
        if not ad:
            sonuc.append((g, None, 0.0, False))
            continue
        j, t = max(ad, key=lambda a: (olc.merkez_icinde(a[1]["kutu"], g.kutu), olc.iou(a[1]["kutu"], g.kutu)) if a[1].get("kutu") else (False, -1))
        kullanildi.add(j)
        k = t.get("kutu")
        sonuc.append((g, t, olc.iou(k, g.kutu) if k else 0.0, bool(k) and olc.merkez_icinde(k, g.kutu)))
    return sonuc


belgeler = cord_belgeleri(25)
for yol in "ABC":
    es = []
    for b in belgeler:
        es += eslestir(b.alanlar, tahminler(yol, b, ocr_onbellek(b), CORD_SEMA))
    print(yol, olc.ozet(es))
