"""S3 soru 2: farklı modelin (yerel qwen3-vl) okuması, Claude D'nin yanlışlarında uyuşmazlık veriyor mu?
Veri: S2 CORD belgeleri (cord-025…064, temiz + bozuk). Claude tarafı S2'nin kayıtlı D çıktıları + etiketleri."""
from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "s1-kaynak-esleme"))
sys.path.insert(0, str(KOK / "s2-guven"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from guven import SATIRLAR, belgeler, esdeger  # noqa: E402
from ortak import ocr_onbellek  # noqa: E402
from yerel import CORD_TIPLI, tahminler  # noqa: E402

# S2 SONUC'ta elle "gerçek görsel okuma hatası" diye sınıflananlar (belge, alan, Claude'un değeri)
GERCEK = {("cord-041-bozuk", "menu.price", "160,000"), ("cord-041-bozuk", "total.total_price", "2,352,480"),
          ("cord-041-bozuk", "total.creditcardprice", "2,352,480"), ("cord-045-bozuk", "menu.nm", "ADP Seafood"),
          ("cord-048-bozuk", "menu.nm", "Chokocha Fit")}


def main():
    s = json.loads(SATIRLAR.read_text("utf-8"))["satirlar"]
    yerel = {}
    for b in belgeler(25, 65):
        t, _ = tahminler("C", "qwen3-vl:8b", b, ocr_onbellek(b), CORD_TIPLI, False)
        yerel[b.kimlik] = t
    kalan = {k: list(v) for k, v in yerel.items()}
    for x in s:
        havuz = kalan[x["belge"]]
        j = next((i for i, y in enumerate(havuz) if y["alan"] == x["alan"] and esdeger(x["alan"], x["deger"], y["deger"])), None)
        x["yerel_uyusur"] = j is not None
        if j is not None:
            havuz.pop(j)

    def oran(kume):
        return f"{sum(not x['yerel_uyusur'] for x in kume)}/{len(kume)}" if kume else "0/0"

    dogru = [x for x in s if x["dogru"]]
    yanlis = [x for x in s if not x["dogru"]]
    gercek = [x for x in s if (x["belge"], x["alan"], x["deger"]) in GERCEK]
    print("uyuşmazlık — doğru alanlarda (yanlış alarm):", oran(dogru))
    print("uyuşmazlık — tüm yanlışlarda:", oran(yanlis))
    print("uyuşmazlık — gerçek okuma hatalarında:", oran(gercek))
    for x in gercek:
        print("  ", x["belge"], x["alan"], x["deger"], "yerel uyuşuyor" if x["yerel_uyusur"] else "YEREL UYUŞMUYOR",
              "| Claude A çapraz:", x["capraz"])
    print("kıyas — Claude A (aynı model) uyuşmazlığı: doğru", f"{sum(x['capraz'] == 0 for x in dogru)}/{len(dogru)}",
          "| yanlış", f"{sum(x['capraz'] == 0 for x in yanlis)}/{len(yanlis)}")
    ikisi = [x for x in yanlis if x["capraz"] == 0 or not x["yerel_uyusur"]]
    print("A veya yerel uyuşmazlığı — yanlışlarda:", f"{len(ikisi)}/{len(yanlis)}",
          "| doğrularda:", f"{sum(x['capraz'] == 0 or not x['yerel_uyusur'] for x in dogru)}/{len(dogru)}")


if __name__ == "__main__":
    main()
