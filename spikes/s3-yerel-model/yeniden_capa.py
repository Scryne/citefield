"""Post-hoc: alıntı değeri kurmuyorsa OCR'da değerle tek eşleşen kelimeye yeniden çapala; çok eşleşme ya da hiç yoksa kutu yok (incelemeye)."""
import sys, json
from pathlib import Path
K = Path("spikes")
sys.path[:0] = [str(K/"s1-kaynak-esleme"), str(K/"s2-guven"), str(K/"s3-yerel-model")]
import olc, fatura
from ortak import cord_belgeleri, ocr_onbellek, normalize as N, birlesim, CALISMA
from cikar import json_ayikla
from yerel import CORD_TIPLI, tip_kapisi
from s1_yeniden import eslestir
def duzelt(model, kol, b, w, sema):
    ham = json.loads((CALISMA/"cikti-yerel"/f"{kol}-{model.replace(':','_')}-{b.kimlik}.json").read_text("utf-8"))["ham"]
    idx = {k.id: k for k in w}; out = []; kutusuz = 0
    for a in json_ayikla(ham):
        from ortak import alan_adi
        t = {"alan": alan_adi(a.get("field")), "deger": str(a.get("value", ""))}
        h = N(t["deger"]); ids = [i for i in (a.get("word_ids") or []) if isinstance(i, int) and i in idx]
        ic = [i for i in ids if N(idx[i].text) and N(idx[i].text) in h]
        if ic: t["kutu"] = birlesim(idx[i].kutu for i in ic)
        else:
            es = [k for k in w if h and N(k.text) == h]
            t["kutu"] = es[0].kutu if len(es) == 1 else None; kutusuz += t["kutu"] is None
        if tip_kapisi(t["alan"], t["deger"]): out.append(t)
    return out, kutusuz
for veri in ("cord", "fatura"):
    for model, kol in (("qwen3-vl:8b", "C"), ("qwen3:8b", "B"), ("qwen3:4b-instruct", "B")):
        bl = cord_belgeleri(25) if veri == "cord" else fatura.fatura_belgeleri(30)
        es, kz = [], 0
        for b in bl:
            try: t, k = duzelt(model, kol, b, ocr_onbellek(b), None)
            except FileNotFoundError: continue
            kz += k
            es += eslestir(b.alanlar, t) if veri == "cord" else olc.eslestir(b.alanlar, t, kapsama=True)
        o = olc.ozet(es)
        # kutusu olmayan doğru değerler incelemeye gider: gösterilen kutuların isabeti ayrıca
        gos = [e for e in es if e[1] is not None and e[1].get("kutu")]
        print(veri, kol, model, "değer", o["deger_orani"], "merkez", o["konum_merkez"],
              "| kutusu gösterilenlerde merkez", round(sum(e[3] for e in gos)/max(len(gos),1), 3), "| kutusuz tahmin", kz)
