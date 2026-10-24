# S1: Kaynak eşleme — sonuç (2026-10-24) ✅ GEÇTİ

Soru: çıkarılan alan değeri belgedeki doğru kutuya geri bağlanabiliyor mu? Plan ve kabul eşikleri işten önce
`PLAN.md`'de yazıldı.

## Sonuç
**Yol C** (model görseli ve kimlikli OCR kelimelerini birlikte görür, değerle birlikte kullandığı kelime kimliklerini
söyler) + **alıntı doğrulama** (yalnız değerin içinde geçen kelimeler kutuya girer):

| Veri | Alan | Değer doğru | Konum doğru (merkez) | Konum (IoU ≥ 0,5) | Eşik |
|---|---|---|---|---|---|
| CORD v2, 25 gerçek fotoğraf fiş | 273 | %88,3 | **%97,1** | %92,1 | ≥ %80 ✅ |
| FATURA, 30 şablondan 30 fatura | 155 | %100 | **%100** | %31,0* | ≥ %90 ✅ |

\* FATURA'nın etiket kutusu alan adını da kapsıyor ("Date: 22-Apr-2018"), tahmin yalnız değeri; IoU bu yüzden yapısal
olarak düşük, esas ölçüt merkez.

## Üç yolun kıyası (alıntı doğrulamalı)
| Yol | CORD değer | CORD konum | FATURA değer | FATURA konum |
|---|---|---|---|---|
| A: görsel → değer → bulanık metin eşleme | **%92,3** | %88,1 | %100 | %99,4 |
| B: yalnız OCR kelimeleri + kimlik alıntısı | %85,0 | %95,3 | %97,4 | %100 |
| C: görsel + OCR kelimeleri + kimlik alıntısı | %88,3 | **%97,1** | %100 | %100 |

- **A neden kaybetti:** aynı değer belgede birden çok yerde geçiyor (adet "1", aynı fiyat hem satırda hem ara toplamda);
  metin araması hangisi olduğunu bilmiyor. Değeri en iyi A okuyor ama yerini en kötü A buluyor. Yedek yol olarak kalır.
- **B neden kaybetti:** görsel yokken OCR'ın yanlış okuduğu karakteri düzeltemiyor; değer doğruluğu en düşük.
- **C'nin açığı:** A'nın yakalayıp C'nin atladığı 9 alanın 8'i "adet = 1" (biri "para üstü = 0") (model miktarı 1 olunca yazmamayı seçiyor). v1 isteminde
  "miktar 1 olsa da yaz" kuralıyla kapatılmalı; ölçülmedi.

## Yolda bulunan ve düzeltilen hatalar (ölçüm dürüstlüğü)
1. **OCR seçimi asıl değişkendi.** Tesseract fotoğraf fişte alan kelimelerinin %45,7'sini birebir buldu, RapidOCR %91,6'sını
   (FATURA'da %98,8). OCR kelimeyi kaçırırsa kutu da olamaz → RapidOCR.
2. **Ölçer:** IoU tek başına tek haneli küçük kutularda etiketleyicinin kutu çizim farkı yüzünden yer doğruyken düşüyordu
   (duman koşusu: doğru yerde "1" için IoU 0,45). İkinci ölçüt (merkez) eklendi, ikisi birlikte raporlanıyor. Ölçer her iki
   ölçütle bozuk çıktıya karşı sınandı (`olcer_sinama.py`): kendi etiketi %100, karıştırılmış kutu %0 / %0,7, 30 px kayma %0 / %16,8.
3. **Benim şema hatam:** CORD etiketi `menu.sub.nm`, şemaya `menu.sub_nm` yazmıştım; model şemaya uyduğu için üç yolda da
   "kaçak" sayıldı. Şema düzeltildi, kayıtlı çıktılarda ad eşlendi (`alan_adi`). Etki (CORD değer): A %90,5 → %92,3,
   B %82,8 → %85,0, C %87,5 → %88,3.
4. **JSON ayrıştırma:** model bir cevapta iki blok döndü, açgözlü regex bozuldu (fatura-04). `raw_decode` ile düzeltildi.
5. **Alıntı doğrulama:** model bazen etiket kelimesini de alıntılıyor ("TOTAL" + "42,500") → kutu ikisini kapsıyor. Değerde
   geçmeyen kelime kutudan düşünce CORD konumu %95,9 → **%97,1** (C), %92,7 → %95,3 (B). Düzeltme öncesi sayılar
   `rapor-*-ham.json`'da.

## Ürün kararlarına etkisi
- **K-OCR:** varsayılan OCR RapidOCR (ONNX, CPU, ~1,6 sn/sayfa fiş). Tesseract varsayılan olmaz.
- **K-Yol:** çıkarım = görsel + kimlikli OCR kelimeleri → model kelime kimliği alıntılar → deterministik alıntı doğrulama
  → kutu. Bulanık eşleme yalnız model kimlik veremediğinde yedek.
- **K-Kanıt:** kutu modelin "yaptım" demesinden değil, OCR'ın gerçek kelime koordinatlarından gelir; model kutu uyduramaz.
- **S2'ye girdi:** `alinti_uyumu` (alıntılanan kelimeler değeri oluşturuyor mu) bedava bir güven sinyali; S2'de ölçülecek.

## Sınırlar
- Model: Claude Sonnet (`claude -p`, Scryne'ın aboneliği). Ürün katmanında model takılabilir olacak; başka/yerel modelle
  kalite S3'ün konusu.
- Örneklem küçük (25 + 30 belge). FATURA sentetik, CORD Endonezce; Türkçe ve el yazısı ölçülmedi.
- DocILE (gerçek İngilizce fatura) erişim formu bekliyor.

## Çalıştırma
```
uv run --no-project --with pyarrow --with pillow --with pytesseract --with rapidocr --with onnxruntime --with rapidfuzz \
  python spikes/s1-kaynak-esleme/kos.py cord 25 ABC        # ya da: fatura 30 ABC ; sona "ham" = alıntı doğrulamasız
```
Veri ve ara çıktılar `.veri/` altında (git dışı); model çıktıları önbellekli, yeniden puanlama ücretsiz.
