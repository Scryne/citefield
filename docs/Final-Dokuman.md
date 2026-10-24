---
proje: Citefield
created: 2026-10-24
type: final-dokuman
status: kesin
---
# Citefield — Final Doküman

## Özet
Citefield, fatura ve fiş gibi belgelerden şemaya göre alan çıkaran, kendi sunucunda kurulan açık kaynak bir motor ve
inceleme arayüzüdür. Her alanın değeri belgedeki gerçek kelimelere bağlanır: kutu modelden değil, OCR'ın ya da PDF metin
katmanının koordinatından gelir. Her alan ya otomatik onaylanır ya da gerekçesiyle (ikinci okuma uyuşmuyor, toplam tutmuyor,
alıntı değeri kurmuyor…) inceleme kuyruğuna düşer. Doğruluk ve kuyruğun yanlışları yakalama oranı açık veride ölçülüp
README'de yayımlanır. v1 tek kullanıcılı self-host; barındırılan çok kiracılı sürüm v2.

**Fark (S1–S3 sonrası kesin hali):**
- Kaynak kutusu ve gerekçeli inceleme kuyruğu açık çekirdekte. Unstract ikisini ücretli sürüme kilitliyor.
- Doğrulama birinci sınıf.
- Ölçüm tekrarlanabilir: `citefield eval`.
- "Kalibre güven" iddiası yok. S2'de ölçülemedi; yerine yakalama oranı yayımlanır.

## Teknoloji Stack

| Katman | Seçim | Gerekçe |
| --- | --- | --- |
| Dil, paket | Python 3.13 (destek ≥ 3.11), `uv` 0.13 | OCR/PDF/ML ekosistemi Python'da. rapidocr 3.10 sınıflandırıcısı 3.13'te bitiyor, SQLAlchemy 2.1 ≥ 3.11 istiyor |
| PDF | `pypdfium2` 5.14 (render) + `pdfplumber` 0.11 (metin katmanı kelimeleri) | pypdfium2'de kelime gruplama yok (yalnız karakter kutusu); pdfplumber zaten pypdfium2 üstünde ve `extract_words` veriyor |
| OCR | `rapidocr` 3.10 (PP-OCRv6 small) + `onnxruntime` 1.31 (CPU) | K-OCR (S1): fişte kelime kapsaması %91,6, Tesseract %45,7. `return_word_box` sürüyor; onnxruntime ayrı kurulur |
| Çıkarım sağlayıcısı | Soyut arayüz: `anthropic` 2.3 (structured outputs GA, `output_config.format`) + OpenAI-uyumlu uç (`openai` 3.37; OpenAI, Ollama, vLLM, OpenRouter, NVIDIA NIM) + yalnız geliştirme/ölçüm için `claude-code` (`claude -p`) | K-Model (S3). Görsel + structured outputs birlikteliği dokümanda açık değil: Faz 3'te ilk test. Ollama OpenAI ucunda görsel yalnız base64 |
| API | FastAPI 0.162 + Pydantic 2.14 | Şema/doğrulama Pydantic'te, OpenAPI bedava |
| Depolama | SQLite (WAL) + SQLAlchemy 2.1 + Alembic 1.20 (SQLModel değil: hâlâ 0.0.x beta) | v1 tek kullanıcı; v2'de aynı modellerle Postgres |
| İş kuyruğu | Süreç içi işçi, SQLite tablosu üzerinde | v1'de Redis/Celery gereksiz parça; v2'de değişir |
| Dışa aktarım | JSON, CSV (stdlib), XLSX (`XlsxWriter`) | Yalnız yazma; openpyxl 2024-06'dan beri sürüm çıkarmadı |
| Arayüz | React 19 + TypeScript + Vite 8 (Node ≥ 20.19), TanStack Query 5; derlenmiş hali FastAPI'den statik servis | Sayfa PNG + SVG kutu katmanı; pdf.js gerekmez, kutular sunucu koordinatıyla birebir |
| Kurulum | `pip install citefield` / `uvx citefield serve`, ayrıca tek imajlı `docker compose` | "tek komut": kütüphane, CLI ve sunucu aynı paket. Emsal: docling-serve tek konteyner; Unstract ~24 servis (Redis, RabbitMQ, MinIO, 11 Celery işçisi). Tek konteyner + Redis'siz kurulum README'de fark olarak yazılır |
| Yerel model | Ollama + `qwen3-vl:8b` (GPU) | S3: değer eşit, fiş konumu %87; "gizli mod" |
| Test, kalite | pytest, ruff, mypy; Vitest + Playwright (arayüz) | CI'de lint + test + build |
| Model kimlikleri | `config/models.toml` | Sağlık nöbeti izler; kodda gömülü model adı yok |

Sürümler 2026-10-24 araştırmasından (PyPI/npm/GitHub sürüm sayfaları); kurulumda kilit dosyası (`uv.lock`, `package-lock.json`) esastır.

## Mimari

```
belge (PDF/PNG/JPG)
  → ingest: sayfa görüntüsü (2× render) + kelimeler [id, metin, kutu, satır, sayfa, kaynak: pdf|ocr]
            PDF'te metin katmanı varsa onu, yoksa RapidOCR
  → okuma 1 (K-Yol): görsel + kimlikli kelimeler → {alan, değer, kelime kimlikleri, model güveni}
  → okuma 2 (K-İkinci okuma): aynı sağlayıcı, yalnız görsel → {alan, değer}
  → kanıt: alıntı doğrulama (yalnız değerin içinde geçen alıntı kelimeleri kutuya girer) + K-Satır + tip kapısı
  → doğrulama: kurallar (aritmetik, biçim, sağlama hanesi) + alıntı çakışması
  → karar (K-Güven): alan "otomatik" ya da "inceleme" + gerekçe listesi
  → depolama → inceleme arayüzü (düzelt / kutuyu yeniden seç / onayla) → dışa aktarım
```

**Paket yapısı:**

| Modül | Sorumluluk |
| --- | --- |
| `citefield.ingest` | Belge → sayfa görüntüsü ve kelimeler |
| `citefield.schema` | Şema biçimi; hazır şablonlar `invoice`, `receipt` |
| `citefield.providers` | Sağlayıcılar |
| `citefield.extract` | İstemler, okumalar, alıntı doğrulama |
| `citefield.verify` | Kurallar, inceleme tetikleri |
| `citefield.store` | Depolama |
| `citefield.api` | REST API |
| `citefield.export` | Dışa aktarım |
| `citefield.eval` | Veri seti bağdaştırıcıları, ölçer, ölçer sınaması |
| `citefield.cli` | `extract`, `serve`, `eval` komutları |
| `ui/` | İnceleme arayüzü |

**Değişmez tasarım kararları (spike'lardan):**
- **K-Kanıt (S1):** kutu her zaman gerçek kelime koordinatından gelir. Model kutu uyduramaz. Alıntı değeri kurmuyorsa kutu verilmez ve alan incelemeye gider.
- **K-Yol (S1):** okuma 1 görsel + kimlikli kelimeler üzerinden yapılır, ardından deterministik alıntı doğrulama gelir. Sonuçlar: CORD konum %97,1, FATURA %100.
- **K-Güven (S2):** inceleme tetikleri
  1. İkinci okuma uyuşmuyor.
  2. Model güveni eşik altında.
  3. Grup kuralı tutmuyor.
  4. Alıntı yok ya da değeri kurmuyor.
  5. Aynı basılı değer iki role alıntılanmış.

  Her tetik arayüzde gerekçe olarak görünür.
- **K-İkinci okuma (S3):** OCR'sız, yalnız görselden okuma. Gerçek okuma hatalarının 4/5'ini %1,5 yanlış alarmla yakaladı. Farklı model 2/5'ini %16 ile yakaladı. n=5, v1 ölçümü bunu doğrular ya da çürütür.
- **K-Satır (S3 hipotezi) — çürütüldü (Faz 3):** konumu %96,8 → %92,0 düşürdü, yanlış yakalamadı (adet kalem adının üstünde de basılıyor, fotoğraf eğikliği satırı bozuyor). Kaldırıldı.
- **K-Şema (S3):** şema alanları tipli ve açıklamalı. Tipler: text, amount, count, date, id. Etiket kelimesini değer yazmak yasak. "Basılı değilse yazma, yazımı düzeltme" kuralı istemde.
- **K-İstem (S2):** istem modeli basılı olmayan değeri üretmeye zorlamaz. S2'de "adet 1 olsa da yaz" demek 14 uydurma üretti.
- **Sağlayıcı arayüzü:** `read(images, prompt, json_schema) -> (json, usage)`. Kullanım ve maliyet her belgeye kaydedilir.

**Anlam kararları ve TypeSafe:** v1'de çıkarımın dışında anlam kararı yok.
- Belge türünü kullanıcı şemayla seçer.
- Değer doğrulaması deterministik kural ve ikinci okumayla yapılır.
- Self-host açık kaynak bir motor, kapalı bir anahtar servisine bağlanamaz.
- TypeSafe adayı v2'de barındırılan sürüm için yeniden açılır (otomatik belge türü yönlendirme).

**Lisans:** AGPL-3.0 (motor). Proje-Fikri'deki open-core emsalleri (Plausible, Postiz) ile aynı yol.

## Kapsam (v1)
- **Süre tavanı:** ~4 hafta (2026-10-25 → 2026-11-22). v1 = motor + inceleme arayüzü, tek kullanıcı, self-host.
- **Belge:** fatura ve fiş (İngilizce/Latin alfabesi), PDF (metin katmanlı ya da taranmış) ve görsel. Çok sayfalı PDF'te sayfa başına okuma ve sayfa kimlikli kutu.
- **Bitti = kullanıldı.** İki parça:
  - **(a) Ölçüm yayını.** CORD, FATURA ve sentetik fişlerde `citefield eval` ile ölçülür ve README'de yayımlanır. Sağlayıcı başına:
    - değer doğruluğu,
    - konum doğruluğu,
    - kuyruğun yakalama oranı (yanlışların ne kadarı incelemeye düştü),
    - otomatik onay payı,
    - otomatik onaylanan yanlışların listesi.

    Ölçer, bozulmuş çıktıyla sınanmadan sayı yayımlanmaz.
  - **(b) Gerçek kullanım.** Public lansmandan sonra en az 3 dış kişi motoru kendi belgesiyle kurup çalıştırır. Kanıt issue, discussion ya da geri bildirim olur. (b) olmadan v1 "yayında" sayılır, "bitti" sayılmaz.
- **Temel özellikler:** Proje-Fikri'deki 7 madde. Değişiklik: madde 4 "güven skoru" yerine "gerekçeli inceleme kararı" (K-Güven).

## Riskler ve Doğrulamalar

| Risk | Durum | Kanıt / plan |
| --- | --- | --- |
| Model kutuyu doğru yere bağlayabilir mi | ✅ S1 | CORD %97,1, FATURA %100 (`spikes/s1-kaynak-esleme/SONUC.md`) |
| Güven skoru yanlışı ayırabilir mi | ⚪ S2 | Ölçülemedi; tasarıma çevrildi, v1'de yakalama oranı ölçülür |
| Claude'suz çalışır mı | ❌/kısmi S3 | Yerel değer eşit, fiş konumu %87; "gizli mod" + K-Satır |
| İkinci okuma hatayı yakalar mı | ✅ Faz 4 | En isabetli tetik: Sonnet CORD 4 yanlış / 1 doğru, Haiku 2 / 0 |
| PDF metin katmanı yolu | ✅ Faz 2 | 30 sentetik PDF: metin katmanı %100 bulma / %100 konum, OCR %98,2 / %97,7; metin katmanı öncelikli |
| İki okumanın maliyeti | ✅ Faz 3 | API tahmini iki okuma: Sonnet 5.5 ~0,02 $/belge, Haiku 5.5 ~0,001 $/belge. Haiku fişte değerde daha iyi (%97,1), konumda zayıf (%91,7); varsayılan Sonnet, Haiku README'de ekonomi seçeneği |
| K-Satır konumu düzeltir mi | ❌ Faz 3 | Düşürdü (%96,8 → %92,0); kaldırıldı. Yerel modelin %87 konumu için çözüm açık |
| Türkçe/el yazısı | kapsam dışı | v1'de ölçülmez, README'de sınır olarak yazılır |
| Talep (3 dış kullanıcı) | açık | Faz 8 lansman; HN talep sinyali doğrulanamamıştı |

## Kapsam Dışı
- Çok kiracılı SaaS, ödeme, ekip/rol, webhook (v2).
- e-Fatura XML/GİB entegrasyonu; muhasebe programı entegrasyonları.
- El yazısı; Türkçe arayüz (sonra).
- GPU'suz yerel model (K-CPU).
- Model eğitimi/ince ayar.
- "Kalibre güven" iddiası.
- Mobil uygulama.
