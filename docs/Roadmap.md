---
proje: Citefield
created: 2026-10-24
type: roadmap
status: aktif
---
# Citefield — Roadmap

Durum sütunu session-start hook'u tarafından otomatik okunur — format bozulmasın:
⏳ Bekliyor / 🔄 Devam Ediyor / ✅ Tamamlandı / ⛔ Engelli.

| Faz | Adı | Durum | Bitti Kriteri |
| --- | --- | --- | --- |
| 1 | İskelet ve sağlık | ✅ Tamamlandı | `citefield` paketi (uv) + `ui/` iskeleti; CI (ruff + mypy + pytest + ui build) master'da yeşil; `.github/dependabot.yml` (uv + npm); `config/models.toml`; spike ölçeri `citefield.eval`'e taşındı ve bozuk çıktı sınaması testte geçiyor |
| 2 | Okuma katmanı | ✅ Tamamlandı | PDF (metin katmanlı + taranmış) ve görselden sayfa görüntüsü + kimlikli kelimeler; CORD'da S1'in OCR kapsaması (%91,6 ± 1) yeniden üretildi; metin katmanı yolu sentetik PDF'te OCR yoluna karşı ölçüldü |
| 3 | Çıkarım ve kanıt | 🔄 Devam Ediyor | Sağlayıcı arayüzü (Anthropic + OpenAI-uyumlu/Ollama); okuma 1 + okuma 2 + alıntı doğrulama + K-Satır + tip kapısı; `citefield eval` S1 sayılarını (CORD değer ≥ %90, konum ≥ %95; FATURA ≥ %98/98) yeniden üretiyor; belge başı token/$ raporda |
| 4 | Doğrulama ve inceleme kararı | ⏳ Bekliyor | Kurallar (satır toplamı, ara toplam + vergi = toplam, tarih/para biçimi, VKN/TCKN/IBAN sağlama) + 5 inceleme tetiği; eval'da yakalama oranı ve otomatik onay payı raporlanıyor; otomatik onaylanan yanlışlar listeleniyor |
| 5 | Depolama, API, dışa aktarım | ⏳ Bekliyor | SQLite + Alembic; REST (yükle, durum, alanlar, düzelt/onayla, dışa aktar); JSON/CSV/XLSX; `citefield extract` CLI; API testleri gerçek bir belgeyi uçtan uca geçiriyor |
| 6 | İnceleme arayüzü | ⏳ Bekliyor | `DESIGN.md` dolu ve lint'ten geçti; yan yana belge/alanlar, kutu vurgusu, gerekçeli kuyruk, düzelt/kutu yeniden seç/onayla, klavye kısayolları; Playwright uçtan uca testi + `gorsel-dogrulama` dört genişlikte temiz |
| 7 | Paketleme ve ölçüm yayını | ⏳ Bekliyor | `uvx citefield serve` ve `docker compose up` temiz makinede tek komutla açılıyor; README İngilizce, ölçüm tablosu `citefield eval` çıktısından üretiliyor; demo GIF açık veri belgesiyle; `yayin-oncesi` çıkış 0 |
| 8 | Gerçek kullanım | ⏳ Bekliyor | Repo public + PyPI yayını (Scryne onayıyla); lansman gönderileri; ≥ 3 dış kişinin kendi belgesiyle çalıştırdığına dair kanıt; bulgular roadmap'e işlendi |

## Faz Detayları

Faz 1 ve son faz şablonla gelir: biri projenin sessizce çürümesini engeller (2026-09 denetiminde
7 vitrin projesinin 6'sında CI aylarca kırmızıydı, iki projenin LLM modeli emekliye ayrılmıştı), öbürü
"bitti"yi kullanıma bağlar. Aradaki fazlar projeye özeldir.

### Faz 1: İskelet ve sağlık
- **İşler:**
  - `pyproject.toml` (uv, src düzeni).
  - ruff, mypy, pytest.
  - `ui/`: Vite + React + TS iskeleti.
  - GitHub Actions.
  - Dependabot.
  - `config/models.toml`.
  - `citefield.eval`: S1/S2 ölçeri ve eşdeğerlik kuralı (`olc.py`, `s1_yeniden.py`, `guven.esdeger`). Yapı spike'tan kopyalanmaz, ölçülmüş kurallar taşınır. Ölçer sınaması (`olcer_sinama.py`) test olur.
- **Bitti Kriteri:** tabloda.
- **Notlar:** ✅ 2026-10-24 (`66049e4`, CI run 40112951389 iki iş yeşil). Ölçer sınaması ilk halinde bir mutasyonu kaçırdı (bir tahmin iki etikete sayılabiliyordu); test eklendi, dört mutasyon da yakalanıyor. Sağlık nöbeti (`saglik.py`) yalnız Jev ve NIM model kimliklerini deniyor; Anthropic/Ollama kimlikleri `config/models.toml`'da ama nöbet bunları denemiyor (açık). Makinede ANTHROPIC_API_KEY yok: ölçümler `claude-code` sağlayıcısıyla (Claude Code oturumu) koşar.

### Faz 2: Okuma katmanı
- **İşler:**
  - `Word` modeli: id, metin, kutu, satır, sayfa, kaynak, güven.
  - pypdfium2 ile render (2×) ve metin katmanından kelime.
  - RapidOCR (`return_word_box`).
  - Satır gruplama.
  - Önbellek: belge hash'iyle.
- **Bitti Kriteri:** tabloda.
- **Notlar:** ✅ 2026-10-24. Kapsama `citefield.eval.coverage` ile S1'in birebir aynısı: CORD 349/381 = %91,6, FATURA 409/414 = %98,8. Metin katmanı (`citefield.eval.textlayer`, 30 sentetik PDF, 5.461 kelime): bulma %100, konum %100, 0,09 sn/sayfa; aynı sayfalarda OCR %98,2 / %97,7, 2,98 sn/sayfa → metin katmanı varsa o kullanılır. FATURA'da kelime kutusu yok (blok düzeyi), bu yüzden PDF'ler kelime konumu bilinerek üretildi. Satır gruplama OCR'da da dikey merkezle yapılıyor: RapidOCR tespit kutusu bir basılı satırı bölüyor (kalem adı ve fiyat ayrı), K-Satır basılı satıra ihtiyaç duyar. Döndürülmüş PDF sayfası v1'de OCR'a gider. Testler mutasyonla sınandı (9 mutasyon, hepsi yakalanıyor).

### Faz 3: Çıkarım ve kanıt
- **İşler:**
  - Şema biçimi (tipli, açıklamalı; K-Şema) ve hazır şablonlar `receipt`, `invoice`.
  - İstem: S1 C yolu ve S2/S3 dersleri.
  - Sağlayıcılar.
  - JSON ayıklama (`raw_decode`).
  - Alıntı doğrulama, K-Satır, tip kapısı.
  - Eval bağdaştırıcıları: CORD, FATURA, sentetik fiş.
- **Bitti Kriteri:** tabloda. K-Satır'ın yerel kolda CORD konumunu %87'den nereye taşıdığı raporlanır (eşik yok, ölçüm).
- **Notlar:**

### Faz 4: Doğrulama ve inceleme kararı
- **İşler:**
  - Kural motoru (alan ve grup kuralları, şemada tanımlı).
  - İkinci okuma eşleştirmesi (eşdeğerlik).
  - Alıntı çakışması.
  - Model güveni eşiği.
  - Karar ve gerekçe listesi.
- **Bitti Kriteri:** tabloda. Bu fazda önceden kayıtlı bir hedef konmaz (S2'den ders: etiket gürültüsü ölçümü bozar). Sayılar olduğu gibi yayımlanır, otomatik onaylanan her yanlış elle sınıflandırılır.
- **Notlar:**

### Faz 5: Depolama, API, dışa aktarım
- **İşler:**
  - SQLAlchemy modelleri: belge, sayfa, kelime, alan, karar, düzeltme kaydı.
  - Süreç içi iş kuyruğu.
  - FastAPI uçları.
  - Dışa aktarım.
  - CLI.
- **Bitti Kriteri:** tabloda.
- **Notlar:**

### Faz 6: İnceleme arayüzü
- **İşler:**
  - `frontend-sistemi` yüklenir, `DESIGN.md` doldurulur.
  - Belge görüntüleyici: sayfa PNG + SVG kutular, yakınlaştırma.
  - Alan listesi ve kuyruk.
  - Düzeltme: değeri yaz ya da belgede kelimeleri seçerek kutuyu yeniden bağla.
  - Onay.
  - Dışa aktarım düğmesi.
- **Bitti Kriteri:** tabloda.
- **Notlar:**

### Faz 7: Paketleme ve ölçüm yayını
- **İşler:**
  - Tek Docker imajı ve compose.
  - PyPI paket meta verisi.
  - README: ne yapar, kurulum, ölçüm tablosu, sınırlar (Türkçe/el yazısı ölçülmedi, yerel mod konum açığı).
  - Demo.
  - `yayin-oncesi`.
- **Bitti Kriteri:** tabloda.
- **Notlar:**

### Faz 8: Gerçek kullanım
- **İşler:**
  - Scryne onayıyla: repo public, PyPI yayını, lansman (Show HN, r/selfhosted, ilgili topluluklar).
  - Gelen issue'lara cevap.
  - İlk 3 dış kullanıcının kanıtı.
- **Bitti Kriteri:** tabloda.
- **Notlar:**
