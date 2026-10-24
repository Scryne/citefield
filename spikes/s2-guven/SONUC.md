# S2: Güven kalibrasyonu — sonuç (2026-10-24) ❌ ÖNCEDEN YAZILAN EŞİKLERDE GEÇMEDİ

Plan ve eşikler işten önce `PLAN.md`'de. Veri: CORD v2 doğrulama 25–64 (40 fiş), temiz + bozuk ikiz; D yolu (S1'in C'si +
model güveni) ve A yolu (ikinci bağımsız okuma), Claude Sonnet, 160 çağrı. 1.004 tahmin, 62 yanlış (temiz 27, bozuk 35);
82/1.024 etiket alanı hiç çıkarılmadı (güven skoru bunları göremez, ayrı bir geri çağırma sorunu).

## Önceden kayıtlı sonuç
| Ölçüt | Sonuç | Eşik |
|---|---|---|
| Birleşik skor AUROC (lojistik regresyon, belge gruplu 5 kat) | 0,814 | ≥ 0,85 ❌ |
| %2 hata altında otomatik onay payı | %46,4 | ≥ %60 ❌ |
| Bozuk belgede ortalama güven düşüyor | 0,951 → 0,930 | ✅ (zayıf) |
| Birleşik skor model öz beyanından iyi | hayır: öz beyan AUROC 0,83, pay %61,7 | ❌ |

Tek sinyal AUROC: model öz beyanı 0,83 · çapraz okuma 0,775 · OCR güveni 0,674 · kural tuttu 0,667 · alıntı uyumu 0,65 ·
kural tutmadı 0,497.

## Neden — 62 yanlışın elle sınıflandırması
| Tür | ~Adet | Not |
|---|---|---|
| **Benim istemimin ürettiği** | 14 | "Miktar 1 olsa da yaz" → fişte basılı olmayan adetler uyduruldu. S1 açığını kapatırken yeni hata. |
| Şema / bölümleme belirsizliği | ~20 | "4003-Blueberry Fuji" etikette tek ad, model kod + ad; "Thai Iced T. .x1" etikette miktar adın içinde; çok satırlı adlar farklı bölünmüş. |
| Etiket eksik / tartışmalı | ~15 | etikette olmayan toplam/ödeme alanları; "BRE/D" ↔ "BREAD"; model basılı yazım hatasını düzeltmiş ("Garlc" → "Garlic"). |
| **Gerçek görsel okuma hatası** | ~5–8 | 2.352.480 ↔ 2.352.460, 160.000 ↔ 150.000, "ADP" ↔ "AOP", "Fit" ↔ "Flt"; hepsi bozuk görselde. |

CORD'da yanlışların çoğu okuma değil, etiket ve şema belirsizliği. Bu, her güven skorunun tavanını düşürüyor; ölçüm sorusuyla
veri seti uyuşmuyor.

## Ölçerde bulunan ve düzeltilen kusurlar
1. Eşdeğerlik: CORD yazımı saklıyor ("1Prs"), model anlamı yazıyor ("1") → miktar sayı, tutar rakam olarak karşılaştırıldı.
   S1'e de geri uygulandı (S1 SONUC ekine bakın; S1 kararı değişmedi).
2. Eşit skorlar: model güveni kaba (0,9 / 0,95), işletme noktası eşitleri rastgele bölüyordu → eşik yalnız farklı skorlar
   arasından geçer. Model öz beyanının payı bu düzeltmeyle %74,1'den %61,7'ye indi (ilk hesap iyimserdi).
3. Ölçer sınaması (etiket = 1,0; rastgele = 0,46; ters = 0,0; mükemmel skorla hata ≤ %2) her düzeltmeden sonra geçti.

## Keşif (sonradan, aynı veride — kanıt değil, hipotez)
- **Sözlük sıralı kural:** önce çapraz okuma uyuşuyor mu, sonra model güveni → AUROC **0,902**, %2 hata altında onay payı
  **%77,1** (hata %1,7). Eşikleri geçiyor ama kural bu veriye bakılarak bulundu.
- **Gerçek okuma hatalarının 4/5'inde model %85–90 emin, çapraz okuma uyuşmuyor.** Model öz beyanı belirsizliği ve uydurmayı
  yakalıyor, gerçek yanlış okumayı yakalamıyor; ikinci bağımsız okuma yakalıyor.
- **Kurallar:** "tutmadı" 27 kez, 25'i doğru değerde → benim CORD kurallarım fişin gerçek düzenine uymuyor (alt kalemler,
  dahil vergi, indirim). Yine de gerçek aritmetik hataların 2'sinde ateşledi. Kural belge türüne özgü olmalı ve tek başına karar
  vermemeli, grubu incelemeye işaretlemeli.

## Ürün etkisi (şimdilik)
- "Kalibre güven" vaadi bu ölçümle **kanıtlanmadı**; README'de iddia edilmez.
- Güven tasarımı için hipotez: **iki bağımsız okuma + uyuşmazlık incelemeye** (Tezgah K-4'ün ölçülmüş dersiyle aynı yön),
  model öz beyanı ikincil sıralama.
- İstem: "yalnız basılı değerler, yazımı düzeltme, basılı olmayan alanı uydurma".

## Sıradaki: S2b
Aynı soru, etiket gürültüsü olmayan veriyle ve hipotez önceden kayıtlı: sentetik (etiketi üretilmiş) fiş/fatura + temiz/bozuk
ikiz (ör. `synthetic-receipts-ocr`, Apache-2.0), istem düzeltilmiş, birincil skor = çapraz > model sözlük sırası.
