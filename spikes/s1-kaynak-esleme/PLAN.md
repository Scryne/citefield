# S1: Kaynak eşleme — plan (işten önce yazıldı, 2026-10-24)

## Soru
Çıkarılan bir alan değerini belgedeki doğru kutuya geri bağlayabiliyor muyuz? Citefield'in ana vaadi bu; tutmazsa
proje tutmaz.

## Veri
- FATURA (sentetik fatura, alan bbox'lı) — farklı şablonlardan 30 belge.
- CORD v2 doğrulama bölümü (gerçek fotoğraf fiş, alan kelimelerinin quad'ları) — 30 belge.
Veri `.veri/` altında, git dışı.

## Hat
1. OCR → kelime + kutu (Tesseract, kelime seviyesi; gerekirse RapidOCR ile kıyas).
2. Çıkarım iki yolla:
   - **A — değer + bulanık eşleme:** model değeri yazar, değer OCR kelime dizilerine bulanık eşlenir, en iyi dizinin
     kutularının birleşimi kaynak kutusudur.
   - **B — kelime kimliği alıntısı:** model OCR kelimelerini kimlikleriyle görür, değerle birlikte kullandığı kelime
     kimliklerini döner; kaynak kutusu o kelimelerin birleşimidir.
3. Model: Claude (`claude -p`, Scryne'ın aboneliği; yalnız spike için). Ürün katmanında model takılabilir olacak.

## Ölçü
- **Değer doğruluğu:** normalize edilmiş değer = etiket.
- **Konum doğruluğu:** değeri doğru olan alanlarda tahmin kutusu ile etiket kutusu IoU ≥ 0,5 (kutu, alanın tüm
  kelimelerini kapsayan dikdörtgen).
- Ayrıca: değeri yanlış alanda kutu nereye düştü (yanlış okumanın kaynağı görülebiliyor mu).

## Kabul (geçme eşiği)
- FATURA: değeri doğru alanların **≥ %90**'ı doğru konumlanır (A veya B).
- CORD: **≥ %80** (fotoğraf, eğik, buruşuk).
- Kazanan yol seçilir; kaybeden yolun neden kaybettiği yazılır.

## Ölçeri sınama (bozuk çıktıyla)
Ölçer kendisi yanlış olabilir. Koşudan önce: (1) etiket kutularını kendisine verince %100, (2) kutuları belgeler arası
karıştırınca ~%0, (3) kutuyu 30 px kaydırınca düşüş göstermeli. Üçü tutmazsa ölçer düzeltilmeden sonuç yazılmaz.

## Çıktı
`SONUC.md`: sayılar, kazanan yol, hata örnekleri (görselle), ürün kararına etkisi.
