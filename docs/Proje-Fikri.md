---
proje: Citefield
created: 2026-10-24
type: proje-fikri
status: taslak
---
# Citefield — Proje Fikri

> Çalışma adı "Okur" idi; 2026-10-24 denetiminde "Citefield" seçildi (GitHub, PyPI, npm boş; ad kontrolü `docs/arastirma/rakip-analizi.md` ekinde).

## Problem
Şirketlere her gün PDF, fotoğraf ve tarama olarak fatura, irsaliye, banka ekstresi, form gelir. Biri bunları
elle Excel'e ya da muhasebe programına geçirir: belge başı 3–5 dakika, yazım hatası, sıkıcı iş. Muhasebe büroları,
lojistik, İK ve sigorta aynı derdi yaşar.

Ticari çözümler pahalı (pazarın lideri Rossum'un en ucuz planı ~18.000 $/yıl). Açık kaynak tarafında belgeyi
metne çeviren araçlar var (Docling, Marker), ama **alan bazında güven skoru + belgedeki kaynak konumu + kural
doğrulaması + insan onay kuyruğu** sunan, kurulup kullanılabilir bir ürün bulunamadı (araştırma kolu, 2026-10-24;
en büyük OSS IDP reposu py-idp 297★). Rakip analizi (`docs/arastirma/rakip-analizi.md`) bunu doğruladı: Unstract
(7,3k★) inceleme kuyruğunu ve kaynak vurgusunu ücretli sürüme kilitliyor, alan güveni hiçbir sürümde yok; Docling ve
Marker parser seviyesinde kalıyor; hepsini birleştiren repolar 0★. Ticari tarafta Reducto ($0.02/sf.), Mindee,
Rossum bunu sunuyor.

**Fark:** inceleme kuyruğu + kaynak kutusu açık çekirdekte, doğrulama birinci sınıf, güven kalibre edilip ölçümü
yayımlanır, GPU'suz tek komutla kurulur. Türkiye notu: e-Fatura zaten XML; Türk pazarı (yerli rakip ~0,4 TL/belge)
gelir için zayıf, kitle önce global, Türkiye paketi sonra.

## Ne yapar
Kullanıcı belgeyi atar. Ekranın solunda belge, sağında çıkarılan alanlar durur:
- **Her alanın kaynağı:** alana tıklayınca belgede değerin alındığı yer kutuyla işaretlenir.
- **Güven skoru:** her alanın puanı var; düşük puanlı alan insan onayına gider, yanlış veri sessizce geçmez.
- **Kendini denetler:** satırlar toplamı = genel toplam, KDV oranı, tarih biçimi, VKN/TCKN sağlama hanesi.
- Onaylanan veri API, JSON/CSV/Excel ile dışarı çıkar.

## Model (open-core)
- **Motor (açık kaynak):** okuma, şemaya göre çıkarım, kaynak eşleme, puanlama, doğrulama. Tek komutla kendi
  sunucunda kurulur. GitHub görünürlüğü buradan.
- **Platform (barındırılan SaaS, v2):** kayıt, ekip, onay kuyruğu yönetimi, API anahtarı, webhook, belge sayısına
  göre ücret. Örnek yol: Plausible (solo → 1M $ ARR, 2022), Postiz.

## Hedef Kullanıcı
1. Belge yığınıyla uğraşan küçük işletme ve muhasebe bürosu (barındırılan sürüm).
2. Kendi sisteminde belge çıkarımı isteyen geliştirici/şirket (self-host motor).
3. İlk gerçek kullanıcı: Scryne'ın kendisi; Tezgah'ın PDF→Excel siparişleri bu motorla işlenebilir.

## Neden bu proje (CV/portfolyo)
TenderIQ (Docling, OCR, kaynağa izlenebilir analiz), AEGIS (çok kiracılı, RLS, Celery, belge işleme) ve Tezgah
(PDF→Excel satışı, satır aritmetiği doğrulaması, Claude/docling ölçümü) parçalarını tek, bitmiş, kullanılan bir
üründe birleştirir. Savunulabilir mühendislik çekirdeği: kaynak eşleme, güven kalibrasyonu, doğrulama motoru.

## v1: Kapsam ve "Bitti" Tanımı
- **Süre tavanı:** ~4 hafta. v1 = açık kaynak motor + inceleme arayüzü, tek kullanıcı, self-host. SaaS v2'ye gider.
- **Bitti = kullanıldı:** Scryne'ın elinde gerçek belge yok (10-24 kararı: yalnız açık veri). Bu yüzden v1 iki
  parçada biter: (a) açık fatura/fiş veri setlerinde ölçülen alan doğruluğu ve kalibrasyon ("düşük güven → gerçekten
  yanlış" oranı) README'de yayımlanır; (b) public lansmandan sonra en az 3 dış kişi motoru kendi belgesiyle kurup
  çalıştırır (issue/discussion/geri bildirim kanıtı). (b) olmadan v1 "yayında" sayılır, "bitti" sayılmaz.
- **Temel özellikler:**
  1. Belge alma (PDF, görsel) → sayfa görüntüsü + metin katmanı + koordinatlar
  2. Şema tanımı (JSON tabanlı) + hazır fatura şablonu
  3. Alan çıkarımı + her alan için kaynak konumu (sayfa + kutu)
  4. Alan bazında güven skoru
  5. Doğrulama kuralları (aritmetik, biçim, sağlama hanesi)
  6. İnceleme arayüzü: yan yana belge/alanlar, düşük güven kuyruğu, düzelt-onayla
  7. REST API + JSON/CSV/Excel dışa aktarım, tek komutla kurulum (docker compose)

## Kapsam Dışı (v1)
Çok kiracılı SaaS, ödeme, ekip/rol, webhook (v2) · e-Fatura XML/GİB entegrasyonu · muhasebe programı
entegrasyonları · el yazısı · model eğitimi/ince ayar · mobil uygulama.

## Kararlar (denetim, 2026-10-24)
- **Dil:** İngilizce (README, arayüz, doküman); Türkçe arayüz ikinci dil olarak sonra.
- **Ad:** Citefield ("cite" + "field": kaynağını gösteren alan). Elenen: Tracefield (rakip), Ledgerlens, Provena, Docproof, Sightline (dolu), Fieldtrace (rakibe çok yakın).
- **Repo:** v1'e kadar private GitHub reposu; public'e geçiş lansmanda, `yayin-oncesi` kapısından sonra.
- **Değerlendirme verisi:** yalnız açık veri setleri. Kişisel veri içeren belge repoya girmez.

## Açık Sorular
- ~~**Rakip farkı**~~ → kapandı (2026-10-24, yukarıda "Fark"). Açık kalan: HN talep sinyali doğrulanamadı.
- **Çıkarım yolu:** LLM (Claude / NIM / yerel) mi, kural + yerleşim mi, karma mı? Maliyet ve self-host'ta LLM'siz çalışma.
- **Anlam kararları:** belge türü sınıflandırma ve çıkarılan değerin doğrulanması için TypeSafe (Jev) adayı; spike'la denenecek.
- **Riskli kararlar (spike):** ~~S1 kaynak eşleme~~ ✅ 2026-10-24 (`spikes/s1-kaynak-esleme/SONUC.md`): görsel + kimlikli
  OCR kelimeleri + alıntı doğrulama; konum CORD %97,1, FATURA %100; OCR RapidOCR. ~~S2 güven~~ (`spikes/s2-guven/SONUC.md`):
  CORD'da eşik altı (etiket gürültüsü), sentetikte 1.428'de 4 yanlış → ölçülemedi; tasarıma çevrildi: gerekçeli inceleme
  tetikleri (iki okuma uyuşmazlığı, düşük model güveni, kural, alıntı, alıntı çakışması), "kalibre güven" iddiası yok, ölçüm
  v1 teslimatı. Açık: S3 başka/yerel model, çeşitli ikinci okuma, GPU'suz kalite.
- **Lisans** seçimi (open-core).
- **Değerlendirme seti:** hangi açık veri setleri (alan + kutu etiketli fatura/fiş), erişim ve kullanım koşulları.
