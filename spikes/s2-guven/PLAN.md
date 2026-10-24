# S2: Güven kalibrasyonu — plan (işten önce yazıldı, 2026-10-24)

## Soru
Alan başına bir güven skoru, yanlış çıkarılan alanları doğrulardan ayırabiliyor mu? Ürün vaadi "emin olmadığını söyler,
yanlış veri sessizce geçmez". Ayıramıyorsa inceleme kuyruğu ya her şeyi ister (değersiz) ya hataları kaçırır (tehlikeli).

## Veri
CORD v2 doğrulama bölümünden S1'de kullanılmayan 40 belge (25–64), iki hali:
- **temiz:** orijinal fotoğraf.
- **bozuk:** aynı görsel; yarıya küçült + geri büyüt, bulanıklaştır, gürültü ekle, JPEG kalite 20. Geometri değişmez, etiket
  kutuları geçerli kalır. Amaç daha çok ve gerçekçi hata üretmek.
FATURA'da aritmetik tutmuyor (sentetik; ör. ara toplam 239,18 + vergi 11,35 ≠ toplam 238,81), kural sinyali orada sınanamaz.

## Çıkarım
- **D** (S1'in C yolu + iki ek): görsel + kimlikli OCR kelimeleri → değer + kelime kimliği + modelin kendi 0–1 güveni.
  İstemde "miktar 1 olsa da yaz" kuralı (S1'deki C açığı).
- **A** (S1'deki gibi, yalnız görsel): ikinci, bağımsız okuma.
Model: Claude Sonnet (`claude -p`). 40 × 2 hal × 2 yol = 160 çağrı.

## Sinyaller (D'nin her tahmini için)
1. `alinti_uyumu`: alıntılanan kelimeler değeri oluşturuyor mu (S1'den).
2. `ocr_guveni`: alıntılanan kelimelerin RapidOCR skorlarının en küçüğü.
3. `capraz_okuma`: A aynı alan için aynı değeri okumuş mu.
4. `kural`: alan bir aritmetik kurala giriyor mu, kural tutuyor mu (satırlar toplamı = ara toplam; ara toplam + vergi +
   servis − indirim = toplam; nakit − toplam = para üstü). Tutar / tutmaz / kural yok.
5. `bicim`: tutar alanı sayıya çevrilebiliyor mu.
6. `model_guveni`: modelin kendi beyanı (taban çizgisi; LLM öz beyanı genelde kalibre değil).

## Etiket
D'nin bir tahmini **doğru** = aynı adlı bir etiket alanıyla değeri tutuyor (S1 ölçeri, normalize eşitlik). Etiketle eşleşmeyen
tahmin **yanlış** (yanlış değer, uydurma alan, alan adı karışıklığı). Atlanan alanlar güven alamaz; ayrıca raporlanır.

## Ölçü
- Her sinyal ve birleşik skor için yanlışı yakalama AUROC.
- Birleşik skor: sinyallerden basit lojistik regresyon, **belge bazında 5 katlı çapraz doğrulama** (aynı belge hem eğitimde
  hem testte olmaz).
- İşletme noktası: otomatik onaylanan alanlarda hata oranı ≤ %2 iken otomatik onay payı.

## Kabul (geçme eşiği)
- Birleşik skor AUROC **≥ 0,85** (çapraz doğrulamalı).
- Otomatik onaylanan alanlarda hata ≤ %2 iken otomatik onay payı **≥ %60**.
- Bozuk belgelerde ortalama güven temizdekinden düşük.
- Model öz beyanı tek başına raporlanır; birleşik skor ondan iyi değilse "kalibre güven" vaadi düşer.

## Ölçeri sınama
Etiketin kendisi skor olarak verilince AUROC = 1, rastgele skorla ~0,5, ters çevrilmiş etiketle ~0 çıkmalı.

## Çıktı
`SONUC.md`: sinyal tablosu, birleşik skorun eşik eğrisi, ürün kuralı (hangi sinyal, hangi eşik), sınırlar.
