---
proje: Okur
created: 2026-10-24
type: proje-fikri
status: taslak
---
# Okur — Proje Fikri

> Çalışma adı. Ad çakışması kontrol edilmedi; denetimde kesinleşir.

## Problem
Şirketlere her gün PDF, fotoğraf ve tarama olarak fatura, irsaliye, banka ekstresi, form gelir. Biri bunları
elle Excel'e ya da muhasebe programına geçirir: belge başı 3–5 dakika, yazım hatası, sıkıcı iş. Muhasebe büroları,
lojistik, İK ve sigorta aynı derdi yaşar.

Ticari çözümler pahalı (pazarın lideri Rossum'un en ucuz planı ~18.000 $/yıl). Açık kaynak tarafında belgeyi
metne çeviren araçlar var (Docling, Marker), ama **alan bazında güven skoru + belgedeki kaynak konumu + kural
doğrulaması + insan onay kuyruğu** sunan, kurulup kullanılabilir bir ürün bulunamadı (araştırma kolu, 2026-10-24;
en büyük OSS IDP reposu py-idp 297★). Unstract, Sparrow, Reducto, LlamaExtract henüz kontrol edilmedi.

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
- **Bitti = kullanıldı:** (taslak, denetimde kesinleşir) Scryne gerçek bir Tezgah siparişini ya da gerçek bir fatura
  yığınını (≥20 belge) okur ile işler, onaylı çıktı alıcıya gider; ölçülen alan doğruluğu ve "düşük güven → gerçekten
  yanlış" oranı README'de yayımlanır. Artı en az bir dış kişi motoru kendi belgesiyle kurup çalıştırır.
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

## Açık Sorular
- **Rakip farkı:** Unstract, Sparrow, Docling, Reducto, LlamaExtract, Rossum karşılaştırması (araştırma sürüyor).
- **Çıkarım yolu:** LLM (Claude / NIM / yerel) mi, kural + yerleşim mi, karma mı? Maliyet ve self-host'ta LLM'siz çalışma.
- **Anlam kararları:** belge türü sınıflandırma ve çıkarılan değerin doğrulanması için TypeSafe (Jev) adayı; spike'la denenecek.
- **Riskli kararlar (spike):** S1 LLM çıktısını belgedeki kutuya geri bağlama; S2 güven skoru gerçekten yanlışları
  ayırıyor mu (kalibrasyon); S3 GPU'suz/ucuz çalıştırmada kalite.
- **Ad** ve **lisans** seçimi (open-core).
- Değerlendirme seti: gerçek belgeler nereden (Tezgah örnekleri, açık fatura veri setleri)? Kişisel veri içeren
  belgeler repoya girmez.
