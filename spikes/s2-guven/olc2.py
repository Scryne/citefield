"""S2 ölçümü: sinyal başına AUROC, belge gruplu çapraz doğrulamalı birleşik skor, işletme noktası. `sina` argümanı ölçeri sınar."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guven import SATIRLAR  # noqa: E402

SINYALLER = ["alinti_uyumu", "ocr_guveni", "capraz", "kural_tuttu", "kural_tutmadi", "bicim", "model_guveni"]
HATA_TAVANI = 0.02


def ozellik(s: dict) -> list[float]:
    return [s["alinti_uyumu"], s["ocr_guveni"], s["capraz"], float(s["kural"] > 0), float(s["kural"] < 0), s["bicim"],
            s["model_guveni"]]


def auroc_yanlis(dogru: np.ndarray, guven: np.ndarray) -> float:
    """Yanlışı yakalama AUROC'u: düşük güven yanlışa işaret etmeli."""
    return float(roc_auc_score(~dogru, -guven))


def isletme(dogru: np.ndarray, guven: np.ndarray, tavan=HATA_TAVANI) -> dict:
    """Güvene göre sırala; otomatik onaylanan kümede hata ≤ tavan iken en büyük onay payı. Eşik yalnız farklı skorların
    arasından geçebilir: eşit skorlu tahminler birlikte onaylanır ya da birlikte incelemeye gider."""
    sira = np.argsort(-guven, kind="stable")
    d, g = dogru[sira], guven[sira]
    hata = np.cumsum(~d) / np.arange(1, len(d) + 1)
    sinir = np.r_[g[1:] != g[:-1], True]  # i'den sonra kesilebilir mi
    uygun = np.where((hata <= tavan) & sinir)[0]
    k = int(uygun.max()) + 1 if len(uygun) else 0
    return {"otomatik_pay": round(k / len(d), 3), "otomatik_hata": round(float(hata[k - 1]), 3) if k else None,
            "esik": round(float(guven[sira][k - 1]), 3) if k else None,
            "incelemeye_giden_yanlis": int((~d[k:]).sum()), "toplam_yanlis": int((~d).sum())}


def birlesik(satirlar: list[dict]) -> np.ndarray:
    X = np.array([ozellik(s) for s in satirlar])
    y = np.array([s["dogru"] for s in satirlar])
    gruplar = np.array([s["grup"] for s in satirlar])
    p = np.zeros(len(y))
    for egit, test in GroupKFold(5).split(X, y, gruplar):
        m = LogisticRegression(max_iter=1000).fit(X[egit], y[egit])
        p[test] = m.predict_proba(X[test])[:, 1]
    return p


def sina(satirlar):
    y = np.array([s["dogru"] for s in satirlar])
    rng = np.random.default_rng(0)
    print("ölçer sınaması: etiket", auroc_yanlis(y, y.astype(float)), "| rastgele", round(auroc_yanlis(y, rng.random(len(y))), 3),
          "| ters", auroc_yanlis(y, (~y).astype(float)))
    assert auroc_yanlis(y, y.astype(float)) == 1.0 and auroc_yanlis(y, (~y).astype(float)) == 0.0
    assert 0.4 < auroc_yanlis(y, rng.random(len(y))) < 0.6
    mukemmel = isletme(y, y.astype(float))  # %2 hata payı sıranın sonundaki birkaç yanlışın onayına izin verir
    assert mukemmel["otomatik_pay"] >= round(y.mean(), 3) and mukemmel["otomatik_hata"] <= HATA_TAVANI, mukemmel
    assert isletme(y, (~y).astype(float))["otomatik_pay"] < 0.05
    print("ölçer sınaması GEÇTİ")


def main():
    veri = json.loads(SATIRLAR.read_text("utf-8"))
    s, belgeler = veri["satirlar"], veri["belgeler"]
    if "sina" in sys.argv:
        sina(s)
    y = np.array([x["dogru"] for x in s])
    bozuk = np.array([x["bozuk"] for x in s])
    print(f"{len(s)} tahmin, {int((~y).sum())} yanlış (temiz {int((~y[~bozuk]).sum())}/{int((~bozuk).sum())}, "
          f"bozuk {int((~y[bozuk]).sum())}/{int(bozuk.sum())})")
    et = sum(b["etiket"] for b in belgeler)
    at = sum(b["atlanan"] for b in belgeler)
    print(f"atlanan etiket alanı: {at}/{et} (güven skoru bunları göremez)")
    rapor = {"tek_sinyal": {}}
    X = np.array([ozellik(x) for x in s])
    for i, ad in enumerate(SINYALLER):
        if len(set(X[:, i])) > 1:
            rapor["tek_sinyal"][ad] = round(auroc_yanlis(y, X[:, i]), 3)
    p = birlesik(s)
    rapor["birlesik_auroc"] = round(auroc_yanlis(y, p), 3)
    rapor["birlesik_isletme"] = isletme(y, p)
    rapor["model_isletme"] = isletme(y, X[:, SINYALLER.index("model_guveni")])
    rapor["ortalama_guven"] = {"temiz": round(float(p[~bozuk].mean()), 3), "bozuk": round(float(p[bozuk].mean()), 3)}
    m = LogisticRegression(max_iter=1000).fit(X, y)
    rapor["katsayilar"] = {ad: round(float(c), 2) for ad, c in zip(SINYALLER, m.coef_[0])}
    for k, v in rapor.items():
        print(k, v)
    (SATIRLAR.parent / "s2-rapor.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1), "utf-8")


if __name__ == "__main__":
    main()
