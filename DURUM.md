# DURUM — Citefield — kaynak kutulu belge çıkarımı ve inceleme

> **Ne bu dosya:** sertifika değil **envanter**. Ölçülen gerçek durum; "yok" yazan satır kusur değil, kayıt.
> Faz durumu `docs/Roadmap.md`'de; bu dosya son ölçümü tutar.

**Ölçüm tarihi:** 2026-11-25 (önceki: 2026-11-13)
**Tek cümle:** Fatura/fiş gibi belgelerden değer çıkaran, her değeri belgedeki kutusuna bağlayan, kurallardan ya da
ikinci okumadan geçemeyeni insana inceleme kuyruğuna koyan yerel uygulama (Python API + React arayüz). Faz 1–7.5
tamam; repo public. Kalan iş yayın ve gerçek kullanıcı (Faz 8), ikisi de dışarıya bağlı.

**Yayına hazır karnesi (2026-11-25):** Kod ✅ · Ürün ✅ · Ön yüz ✅ (cila) · Belge ✅ · Kapı ✅ · Dış adımlar listeli.
Bitiş çizgisi ScryneOS `🎯 100-Command-Center/Yayina-Hazir-Karnesi.md`'de. Bu çizgiden sonra bulunan şey projeyi yeniden
açmaz, aşağıdaki "v2 fikirleri"ne girer.

## Ne çalışıyor (2026-11-25'te ölçüldü)

- **Python:** `ruff` + `ruff format --check` + `mypy` temiz, pytest 99/99.
- **Arayüz:** `oxlint` 0, `tsc -b` 0, `vite build` 0; `npm audit` 0.
- **Playwright:** 6/6 (gerçek uygulama, sahte model).
- **Dependabot:** #9 (python, 10) ve #10 (ui, 7) yerelde birleştirildi, push edildi; açık PR yok.
- **Gerçek veriyle uçtan uca (yeni):** CORD doğrulama setinden iki taranmış fiş, `ollama` + `qwen3-vl:8b`, gerçek
  sunucu ve tarayıcı. Fiş 39: 16 alanın 16'sı CORD cevabıyla aynı, 2'si incelemeye (kısmi alıntı), arayüzde `a` ile
  onaylandı, "All 16 values checked"; CSV dışa aktarma her satırda sayfa + kutu. Fiş 41 (11 kalem, servis bedeli): 55
  alan, 37'si incelemede; kurallar yerel modelin hatalarını yakaladı (yalnız satır toplamı basılı fişte aynı sayıyı hem
  birim fiyat hem toplam yazması, bölünen ürün adları). Konsol hatası 0.
- **Gezi:** 9 rota (genel bakış, belgeler, inceleme süzgeci, gerçek fişin inceleme sayfası, şemalar, şema, yeni şema,
  ayarlar, bilinmeyen adres) × 4 genişlik × 2 tema = 72 kare, taşma 0, konsol 0, başarısız istek 0.

## Bu turda bulunan ve düzeltilen (2026-11-25)

Testlerin hepsi yeşilken gerçek veriyle ilk denemede çıktılar:

1. **Ollama'da fiş sığmıyordu.** OpenAI uyumlu `/v1` ucu `num_ctx`'i yok sayıyor; Ollama'nın varsayılan penceresi 4096,
   bir fişin istemi ~4.800 token. Fiş 39 doğrudan 400 aldı. Yeni `providers/ollama.py` yerel `/api/chat`'i kullanıyor;
   pencere 8.192'den başlıyor, cevap kesildiyse ya da istem pencereyi doldurduysa okuma başına bir kez ikiye katlanıyor
   (en çok 32.768). Sabit 16k denendi, 8 GB GPU'da modelin üçte biri CPU'ya taştı, bir fiş 6 dakikayı geçti.
2. **`qwen3-vl:8b` düşünüp hiç cevap vermiyordu.** Varsayılan düşünme açık: 9.000 karakter düşünce, çıktı sınırı, boş
   cevap (257 sn). `think: false` (models.toml) ile 44 sn ve 16/16 doğru. Düşünme anahtarı olmayan model reddederse
   anahtarsız yeniden soruluyor.
3. **Boş cevap "hazır" görünüyordu.** Model cevabında alan listesi yoksa (kesik JSON) çıkarım sessizce 0 alanla bitiyor,
   belge "ready" oluyordu (fiş 41, ilk deneme). Artık `UnreadableAnswer`: belge "failed", açıklamalı mesaj, yeniden
   okunabilir. Boş liste (`{"fields": []}`) hâlâ geçerli cevap.
4. **Servis bedeli kural dışıydı.** `receipt` şemasında servis alanı yoktu; "subtotal + tax − discount = total" servis
   bedelli her fişte düşüp dört tutarı incelemeye atıyordu. `service` alanı ve kural terimi eklendi.
5. **Gerekçe metni:** kural hatası "735000 != 105000" yerine "735,000 ≠ 105,000"; çarpım kuralında `×`.

Her biri için düzeltmeden önceki davranışı reddeden test var (`test_providers.py`, `test_extract.py`,
`test_verify.py`).

## Bilinen sınırlar

- `anthropic` sağlayıcısı birim testlerle kapsanıyor, canlı API'ye karşı koşulmadı (Scryne 10-24: API denemesi yok;
  README'de yazıyor). Yayımlanan sayılar Claude Code üzerinden aynı modellerle ölçüldü.
- README'deki doğruluk tabloları `service` alanından önceki `receipt` şemasıyla ölçüldü (Faz 7, 10-24).
- Yerel modelde (qwen3-vl:8b) servis bedelli, çok kalemli fişlerde inceleme oranı yüksek (fiş 41: 37/55). Kurallar
  hataları yakalıyor, otomatik onay oranı düşük.
- Ayarlar sayfası veri dizininin yerel yolunu gösteriyor (tek kullanıcılı yerel uygulama için bilerek); ekran
  görüntüsü paylaşırken bu sayfa kullanılmamalı.

## Dış adımlar (kodla çözülmez, Scryne'da)

1. PyPI: pypi.org'da proje için "trusted publisher" kaydı (repo `Scryne/citefield`, workflow `release.yml`), sonra
   `v0.1.0` etiketi. Etiket push'u yayındır.
2. Lansman gönderileri (Show HN, r/selfhosted vb.): metin hazırlanabilir, göndermek Scryne'ın.
3. Faz 8 bitti kriteri: ≥ 3 dış kişinin kendi belgesiyle çalıştırdığına dair kanıt.
4. İsteğe bağlı: Anthropic anahtarıyla tek canlı deneme (para harcar).

## v2 fikirleri (bu turdan sonra bulunanlar buraya)

- Haiku'nun ayrılmış dilimi (Faz 7'de bellek baskısıyla yarım kaldı).
- SVG kutu katmanında klavyeyle yeniden alıntı (şu an fare gerekiyor).
- Yerel modelde "yalnız satır toplamı basılı" fişler için istem ipucu (birim fiyatı uydurmasın).
- Çok kullanıcı, giriş, kiracı, ödeme, webhook (SaaS, v2 kapsamı).
