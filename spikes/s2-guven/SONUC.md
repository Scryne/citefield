# S2: Güven kalibrasyonu — sonuç (2026-10-24) ❌ CORD'da geçmedi · ⚪ S2b yetersiz örneklem · tasarıma çevrildi

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

## S2b: gürültüsüz etiketle (plan `PLAN-S2b.md`) — ⚪ YETERSİZ ÖRNEKLEM (önceden kayıtlı kural)
`synthetic-receipts-ocr` eval, 40 fiş × temiz + fotoğraf ikizi (perspektif, ışık, solma, gürültü, JPEG), 5 ülke biçimi,
düzeltilmiş istem ("yalnız basılı, yazımı düzeltme, uydurma"). 160 çağrı.

- **1.428 tahmin, 4 yanlış (%99,7 doğru), atlanan etiket 0/1.424.** Fotoğraf ikizinde de 2/714.
- Plan "yanlış < 20 → geçti/geçmedi denmez" diyordu: kalibrasyon bu veriyle ölçülemedi. (Birincil sözlük skoru AUROC 0,842,
  fotoğrafta 0,973; 4 yanlışla anlamsız.)
- **4 yanlışın hiçbiri okuma hatası değil, hepsi rol karışıklığı:** Alman fişinde "SUMME 37,44" toplam olarak doğru alınıp bir
  de ara toplam diye yazılmış (3); "MAESTRO £211,87" kartla ödenen tutar "verilen nakit" sanılmış (1). Değerler doğru, rol yanlış.
- Bu yanlışlarda çapraz okuma **uyuşuyor** (A da aynı hatayı yapıyor): aynı modelin ikinci okuması ilişkili hatayı yakalamaz.
  Kural da tutuyor (SUMME = Σ satır, tutarlı).
- Keşif: "basılı tek değer iki farklı role alıntılanamaz" (alıntı çakışması) kuralı 4'ün 1'ini yakaladı, 80 belgede yanlış
  alarm 0. Hipotez.

**Bağımsız doğrulama:** CORD'daki 62 yanlışın çoğunun etiket gürültüsü olduğu yargısı burada tutuyor; gürültüsüz etikette
model neredeyse yanılmıyor, kalan hata türü okuma değil anlam (rol).

## S2 genel kararı
Risk "güven skoru yanlışı ayıramaz" bu iki ölçümle **ne kanıtlandı ne çürütüldü**: CORD'da etiket gürültüsü, sentetikte hata
azlığı ölçümü engelledi. Spike'ın riski ise netleşti ve tasarıma çevrildi:

- **K-Güven (v1):** alan incelemeye düşer, eğer (1) ikinci okuma uyuşmuyorsa, (2) model güveni eşik altındaysa, (3) alanın
  girdiği kural tutmuyorsa (grup olarak), (4) alıntı yok ya da değeri kurmuyorsa, (5) aynı basılı değer iki role alıntılanmışsa.
  Tek bir skora indirgemek v1'de yok; kuyruk nedeni kullanıcıya **gerekçesiyle** gösterilir ("iki okuma farklı: 2.352.480 /
  2.352.460").
- **İkinci okuma çeşitli olmalı:** aynı modelin tekrarı ilişkili hatayı kaçırıyor → farklı model ya da farklı girdi (yalnız OCR
  metni, yalnız görsel). S3'te ölçülecek.
- **"Kalibre güven" README'de iddia edilmez**, ta ki v1'in değerlendirme koşucusu (bitti ölçütü a) daha zor bir sette
  (DocILE gerçek fatura, daha ağır bozulma) yeterli yanlışla ölçene kadar. Ölçüm v1'in teslimatı olur.
- İstem kuralları kalıcı: yalnız basılı değer, yazım düzeltme yok, basılı olmayan alan yok.
