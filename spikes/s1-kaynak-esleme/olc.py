"""S1 ölçer: değer doğruluğu ve (değeri doğru alanlarda) konum doğruluğu.

İki konum ölçütü birlikte raporlanır:
- iou: tahmin kutusu ile etiket kutusu IoU >= 0,5 (sıkı; tek haneli küçük kutularda kutu çizim farkı tek başına düşürür).
- merkez: tahmin kutusunun merkezi etiket kutusunun (3 px pay) içinde. FATURA'da etiket kutusu alan adını da kapsadığı için
  esas ölçüt budur. Ölçüt 2026-10-24 duman koşusundan sonra eklendi; gerekçe SONUC.md'de.
"""
from __future__ import annotations

from ortak import Alan, iou, normalize

ESIK = 0.5
PAY = 3


def merkez_icinde(t, g) -> bool:
    cx, cy = (t[0] + t[2]) / 2, (t[1] + t[3]) / 2
    return g[0] - PAY <= cx <= g[2] + PAY and g[1] - PAY <= cy <= g[3] + PAY


def deger_tutar(tahmin: str, gercek: str, kapsama: bool) -> bool:
    a, b = normalize(tahmin), normalize(gercek)
    if a == b:
        return True
    return kapsama and len(a) >= 3 and a in b


def eslestir(gercek: list[Alan], tahmin: list[dict], kapsama: bool = False):
    """Her gerçek alanı aynı adlı, değeri tutan, kullanılmamış bir tahminle eşler. Aynı değerden birden çok varsa en
    yakın kutulu tahmin seçilir: aynı değerli iki satırın çapraz eşlenmesini önler."""
    kullanildi = set()
    sonuc = []
    for g in gercek:
        adaylar = [(j, t) for j, t in enumerate(tahmin)
                   if j not in kullanildi and t.get("alan") == g.alan and deger_tutar(t.get("deger", ""), g.deger, kapsama)]
        if not adaylar:
            sonuc.append((g, None, 0.0, False))
            continue
        j, t = max(adaylar, key=lambda a: (merkez_icinde(a[1]["kutu"], g.kutu), iou(a[1]["kutu"], g.kutu)) if a[1].get("kutu") else (False, -1))
        kullanildi.add(j)
        k = t.get("kutu")
        sonuc.append((g, t, iou(k, g.kutu) if k else 0.0, bool(k) and merkez_icinde(k, g.kutu)))
    return sonuc


def ozet(eslesmeler) -> dict:
    n = len(eslesmeler)
    deger = [e for e in eslesmeler if e[1] is not None]
    o = lambda x, y: round(x / y, 3) if y else 0
    return {"alan": n, "deger_dogru": len(deger), "deger_orani": o(len(deger), n),
            "konum_iou": o(sum(e[2] >= ESIK for e in deger), len(deger)),
            "konum_merkez": o(sum(e[3] for e in deger), len(deger))}
