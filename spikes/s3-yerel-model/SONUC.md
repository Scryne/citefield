# S3: Yerel model — sonuç (2026-10-24)

Plan: `PLAN.md` (işten önce yazıldı). Donanım RTX 4060 8 GB, Ollama 0.33.2. Ölçer S1 + S2 eşdeğerliği, değişmedi.

## Soru 1 — Bağımsızlık: ❌ (tek ölçüt: CORD konumu)

| Kol | CORD değer | CORD konum (merkez) | FATURA değer | FATURA konum | GPU sn/belge |
|---|---|---|---|---|---|
| Kıyas: Claude C (S1) | %91,9 | %97,2 | %100 | %100 | — |
| **C `qwen3-vl:8b`** (görsel + OCR) | **%93,0** ✅ | **%87,0** ❌ (eşik 90) | **%100** ✅ | **%100** ✅ | **19,0 / 16,4** ✅ |
| B `qwen3:8b` (yalnız OCR) | %50,2 | %79,6 | %98,0 (1 belge zaman aşımı) | %97,9 | 10,1 / 9,3 |
| B `qwen3:4b-instruct` | %45,1 | %75,6 | %98,1 | %100 | 6,9 / 4,9 |
| B `qwen3:4b-instruct` **CPU** (5 CORD) | %46,0 | %73,9 | — | — | **42,1** |

CORD 25 belge, 273 alan; FATURA 30 belge, 155 alan. Tip kapısı bu koşularda hiçbir şeyi değiştirmedi (kapılı = kapısız).

- **Değer okuma yerelde çözülmüş:** 8B görsel model fişte Claude'dan iyi değer okudu (%93,0 / %91,9), faturada eşit.
- **Konum açığı alıntıdan geliyor:** CORD'da değeri doğru ama kutusu yanlış 33 alan var: 28'i başka yeri gösteriyor, 5'inde kutu fazla geniş. Kaçanlar çoğunlukla belgede tekrar eden değerler, örneğin başka satırdaki "1" ya da "23.000". Claude'da bu sayı 7.
  - Post-hoc deneme (`yeniden_capa.py`): alıntı değeri kurmuyorsa OCR'da tek eşleşen kelimeye yeniden çapalandı. Sonuç: genel %85,4, kutusu gösterilenlerde %89,3. Yardım etmedi.
  - Neden: model değeri *içeren* ama yanlış satırdaki kelimeyi gösteriyor. Değer eşleştirmesiyle düzelmez.
- **Yalnız-metin yerel modeller fişte çöküyor:** gürültülü yerleşimde değerin yarısını kaçırıyorlar (%45–50). Temiz faturada yeterliler (%98).
- **GPU'suz:** küçük metin modeli CPU'da 42 sn/belge ve fişte kullanılamaz kalitede. CPU'da görsel model ölçülemedi: koşu, sistem belleği azaldığı için Claude Code tarafından durduruldu.

## Soru 2 — Çeşitli ikinci okuma: ⏳ koşulmadı

`cesitlilik.py` hazır. 80 S2 belgesinde yerel `qwen3-vl:8b` okuması gerekiyor (~25 dk GPU). Ollama sunucusu bellek
temizliğinde durduruldu; yeniden başlatma Scryne'ın onayını bekliyor.

## Ürün kararları

- **K-Model:** varsayılan çıkarıcı bir görsel model ve sağlayıcı soyut.
  - Barındırılan API (Claude/benzeri): referans kalite.
  - Yerel `qwen3-vl:8b`: "gizli mod". Değer kalitesi eşit; fişte konum %87, bu sayı README'de yazılır.
  - Yalnız-metin yerel model varsayılan olamaz.
- **K-Satır (v1 işi, hipotez):** kalem alanlarında (adet, birim fiyat, tutar) alıntılanan kelime, kalem adıyla aynı OCR satırında olmalı. Değilse aynı satırdaki eşleşen kelimeye çapalanır; o da yoksa kutu verilmez ve alan K-Güven kural 4 ile incelemeye gider. Ölçülmedi; v1'de bu ölçerle doğrulanacak.
- **K-CPU:** GPU'suz kurulum v1'de desteklenen yol değil. API sağlayıcısı ya da GPU gerekir. CPU görsel ölçümü açık.

## Kalıcı dersler

- Küçük modeller kısa şemayı yanlış anlıyor. qwen3:8b `menu.num`'u fiyat sandı ve "TOTAL"ı değer yazdı. Tipli ve açıklamalı şema ile etiket yasağı bunu düzeltti.
- Ollama 0.33 ile qwen3-vl'de `format: json` ve `think: false` birlikte verilince cevap `thinking` alanına düşüyor. `yerel.py` iki alanı da okuyor.
- İlk çağrı model yüklemesiyle ~80 sn sürüyor, ölçüme katılmaz. 8 GB VRAM'de görsel 8B rahat çalışıyor.

## Sınırlar
Örneklem S1 ile aynı ve küçük (25 fiş + 30 fatura). Türkçe ve el yazısı yok. Yerel kollar Claude'dan uzun, tipli bir şema aldı; değer kıyası bu farkla birlikte okunmalı.
