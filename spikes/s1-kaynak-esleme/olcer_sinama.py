"""Ölçeri bozuk çıktıyla sınar (PLAN.md): kendi etiketi %100, karıştırılmış kutu ~%0, kaydırılmış kutu düşer."""
import random

from olc import eslestir, ozet
from ortak import cord_belgeleri

belgeler = cord_belgeleri(25)
rng = random.Random(0)


def topla(fn):
    es = []
    for b in belgeler:
        es += eslestir(b.alanlar, fn(b))
    return ozet(es)


kendi = topla(lambda b: [{"alan": a.alan, "deger": a.deger, "kutu": a.kutu} for a in b.alanlar])
baska = {b.kimlik: belgeler[(i + 7) % len(belgeler)] for i, b in enumerate(belgeler)}
karisik = topla(lambda b: [{"alan": a.alan, "deger": a.deger,
                            "kutu": rng.choice(baska[b.kimlik].alanlar).kutu} for a in b.alanlar])
kayik = topla(lambda b: [{"alan": a.alan, "deger": a.deger,
                          "kutu": (a.kutu[0] + 30, a.kutu[1] + 30, a.kutu[2] + 30, a.kutu[3] + 30)} for a in b.alanlar])
yanlis_deger = topla(lambda b: [{"alan": a.alan, "deger": a.deger + "x", "kutu": a.kutu} for a in b.alanlar])
print("kendi etiketi  ", kendi)
print("karışık kutu   ", karisik)
print("30px kaymış    ", kayik)
print("yanlış değer   ", yanlis_deger)
assert kendi["konum_iou"] == 1 and kendi["konum_merkez"] == 1 and kendi["deger_orani"] == 1
assert karisik["konum_iou"] < 0.15 and karisik["konum_merkez"] < 0.15, karisik
assert kayik["konum_iou"] < 1 and kayik["konum_merkez"] < 1, kayik
assert yanlis_deger["deger_dogru"] == 0
print("ölçer sınaması GEÇTİ")
