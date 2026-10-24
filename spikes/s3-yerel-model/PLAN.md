# S3: Yerel model ve çeşitli ikinci okuma — plan (işten önce, 2026-10-24)

## Sorular
1. **Bağımsızlık:** Citefield Claude aboneliğine bağlı olamaz. Yerel bir modelle (Ollama, RTX 4060 8 GB) S1'in hattı ne kadar
   kalite kaybeder? GPU'suz (CPU) çalışma mümkün mü, ne kadar yavaş?
2. **Çeşitli ikinci okuma:** S2'de aynı modelin ikinci okuması ilişkili hatayı kaçırdı. Farklı bir modelin okuması Claude'un
   gerçek okuma hatalarında uyuşmazlık veriyor mu, doğru alanlarda ne kadar yanlış alarm üretiyor?

## Kollar
- **B-yerel:** yalnız kimlikli OCR kelimeleri (görsel yok) → `qwen3:8b` (GPU), `qwen3:4b-instruct` (GPU ve CPU).
- **C-yerel:** görsel + kimlikli OCR kelimeleri → yerel görsel model (`qwen3-vl:8b`, yoksa `qwen2.5vl:7b`), GPU.
İstem S1 C/B ile aynı + S2 dersleri (yalnız basılı, yazımı düzeltme, uydurma); çıktı JSON (Ollama `format: json`).
Alıntı doğrulama aynı.

## Veri ve ölçü
- S1 ile kıyaslanabilir: CORD 25 (cord-000…024) + FATURA 30. S1 ölçeri + S2 eşdeğerlik (`s1_yeniden.py` mantığı).
  Kıyas çizgisi Claude C: CORD değer %91,9 / konum %97,2, FATURA %100 / %100.
- Hız: belge başı saniye (OCR hariç), GPU/CPU ayrı.
- Çeşitlilik: S2 CORD verisi (cord-025…064 temiz + bozuk). Claude D'nin her alanı için yerel okumayla eşdeğerlik. Elle
  sınıflandırılmış gerçek okuma hatalarında (S2 SONUC) uyuşmazlık oranı ve doğru alanlarda yanlış alarm oranı.

## Kabul
- **Yerel kullanılabilirlik (en iyi yerel kol):** CORD değer ≥ %80 ve konum ≥ %90; FATURA değer ≥ %95 ve konum ≥ %95;
  GPU'da belge başı ≤ 60 sn.
- **GPU'suz:** eşik yok, ölçülüp raporlanır (ürün kararı: CPU varsayılan mı, "yavaş mod" mu).
- **Çeşitlilik:** yerel okuma gerçek okuma hatalarının ≥ yarısında uyuşmazlık verir ve doğru alanlarda yanlış alarm ≤ %15.
  Gerçek hata sayısı < 5 ise yalnız betimsel raporlanır.

## Ölçeri sınama
S1 ölçer sınaması (`olcer_sinama.py`) koşudan önce yeniden; S2 eşdeğerlik kuralı değişmeden.
