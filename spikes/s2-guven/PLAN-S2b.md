# S2b: Güven kalibrasyonu, gürültüsüz etiketle — plan (işten önce, 2026-10-24)

S2 (CORD) önceden kayıtlı eşiklerde geçmedi; yanlışların çoğu etiket/şema belirsizliğiydi (`SONUC.md`). S2b aynı soruyu
etiketi üretilmiş veriyle sorar ve S2'nin keşfini **önceden kayıtlı hipotez** olarak sınar.

## Veri
`albertobarnabo/synthetic-receipts-ocr` (Apache-2.0) eval bölümü, ilk parke dosyası; 40 fiş, her biri iki hal:
`image_clean` (temiz render) ve `image_photo` (perspektif, ışık, gölge, solma, gürültü, bulanıklık, JPEG). Sözleşme: alan
yalnız fişte basılıysa doludur; fiş aritmetiği tutarlıdır.

## Çıkarım (istem S2 dersleriyle düzeltildi)
- "Yalnız basılı değerler; yazımı düzeltme; basılı olmayan alanı yazma." "Miktar 1 olsa da yaz" kuralı **yok**.
- Alanlar: merchant, date, time, receipt_no, tax_id, line.name, line.qty, line.unit_price, line.total (satır alanları satır
  numarasıyla), subtotal, tax.amount, total, tendered, change.
- D (görsel + kimlikli OCR + alıntı + model güveni) ve A (yalnız görsel, ikinci okuma). Sonnet, 40 × 2 × 2 = 160 çağrı.

## Eşdeğerlik
Tutar/miktar: rakamlar (etiket iki ondalıkla biçimlenir: 0.98 → "098", basılı "0,98" → "098"). Tarih/saat/fiş no: rakamlar.
Metin: S1 normalize eşitliği.

## Kurallar (belge türüne özgü, fişin kendi sözleşmesiyle)
satır: adet × birim = satır toplamı · Σ satır toplamı = ara toplam · ara toplam + vergi (vergi dahil değilse) = toplam ·
verilen − toplam = para üstü.

## Birincil skor (önceden kayıtlı hipotez)
Sözlük sırası: önce çapraz okuma uyuşuyor mu, sonra model güveni. İkincil: S2'deki lojistik birleşim (karşılaştırma için).

## Kabul
- Birincil skor AUROC **≥ 0,85** ve %2 hata altında otomatik onay **≥ %60** (tüm tahminlerde).
- Fotoğraf ikizlerinde ayrıca raporlanır.
- Yanlış sayısı < 20 ise sonuç "yetersiz örneklem" sayılır, geçti/geçmedi denmez.

## Ölçeri sınama
S2 ölçeri (`olc2.py`) aynen; etiket/rastgele/ters ve mükemmel skor sınamaları her koşuda.
