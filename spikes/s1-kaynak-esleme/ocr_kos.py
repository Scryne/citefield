"""OCR'ı önbelleğe al ve kelime kapsamını ölç: gerçek alan değerlerinin kelimeleri OCR'da var mı."""
import sys
import time

from ortak import cord_belgeleri, normalize, ocr_onbellek

motor = sys.argv[2] if len(sys.argv) > 2 else "rapid"
belgeler = cord_belgeleri(int(sys.argv[1]) if len(sys.argv) > 1 else 25)
t0 = time.time()
var = top = 0
for b in belgeler:
    kel = {normalize(k.text) for k in ocr_onbellek(b, motor)}
    for a in b.alanlar:
        for w in a.deger.split():
            if normalize(w):
                top += 1
                var += normalize(w) in kel
print(f"{motor}: {len(belgeler)} belge, {time.time()-t0:.1f} sn; alan kelimelerinin OCR'da birebir bulunma oranı: {var}/{top} = {var/top:.1%}")
