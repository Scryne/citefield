---
proje: Citefield
created: 2026-10-24
type: arastirma
---
# Rakip analizi (2026-10-24)

Kaynak: arastirmaci kolu; yıldız ve son push GitHub API'den (2026-10-24). HN taraması ve Logo/Mikro yerleşik OCR'ı
doğrulanamadı (arama kotası doldu). Lisanslar yalnız adıyla.

## Özet
Alan güveni + bbox kaynağı + kural doğrulaması + açık sürümde inceleme kuyruğu + API, **tek bakımlı OSS projede yok**.
Parçalar dağınık; ticari tarafta (Reducto, LlamaExtract, Mindee, Rossum) var.

## Açık kaynak
| Ürün | Lisans / ★ / son push | Alan güveni | bbox | İnceleme | Doğrulama | Not |
|---|---|---|---|---|---|---|
| Unstract | AGPL-3.0 / 7,3k / 10-23 | yok | yalnız Cloud | HITL yalnız Cloud/Ent. | LLMChallenge yalnız Cloud | Cloud $499/ay'dan, ≥8 GB RAM |
| Sparrow | GPL-3.0 / 5,2k / 10-08 | yok | opsiyonel | yok | `--validation` | |
| Docling | MIT / 69,5k / 10-23 | parser seviyesi | var | yok | yok | kütüphane; Citefield'un girdi katmanı adayı |
| Marker / Surya | Apache-2.0 kod, ağırlıklar Open Rail-M / 40,6k / 21,5k | Surya satır OCR güveni | polygon | yok | yok | Datalab extraction $6–20/1000 sf. |
| Zerox | MIT / 12,2k / 2025-05 (durgun) | yok | yok | yok | yok | |
| Unstructured | Apache-2.0 / 15,6k | yok | — | yok | yok | $0.015/sf. |
| LangExtract (Google) | Apache-2.0 / 39k | yok | karakter offseti | görselleştirme | yok | |
| Label Studio | Apache-2.0 / 28,5k | — | etiketleme | review akışı Enterprise | — | |
| invoice2data / InvoiceNet | 2,2k / 2,7k (2024-05) | — | — | — | — | şablon/regex, eski |

Hepsini bir arada iddia eden repolar 0★ (ledgerline, extraction-pipeline).

## Ticari fiyat referansı (sayfa başı)
Reducto Extract $0.02 · LlamaExtract $0.01–0.075 · Extend ~$0.05 · Mindee $0.10 · AWS AnalyzeExpense $0.01 ·
Azure invoice ~$0.01 · Google Custom Extractor $0.03 · Unstract Cloud $499/ay · Rossum ~$18k/yıl (doğrulanmadı).
Reducto ve Mindee alan güveni + bbox veriyor; Rossum kalibre güven + eşik (0.975); LlamaExtract skorlarının kalibre
olmadığını kendisi yazıyor.

## Türkiye
- e-Fatura/e-Arşiv zaten yapılandırılmış XML → OCR ihtiyacı kâğıt fiş, yabancı/PDF fatura, e-Dönüşüm dışı belge, ekstre.
- Azure prebuilt invoice Türkçe destekliyor; banka ekstresi modeli yalnız en-US. Google'ın fatura/ekstre parser'larında Türkçe yok.
- Yerli: Rahat Aktarım (mali müşavir; e-Fatura, ekstre, Z raporu, fiş; Luca/Zirve/Logo/Mikro aktarımı; ~0,32–0,49 TL/belge;
  güven skoru ve bbox yok), Mihsap (LLM + kural + insan doğrulama), Paraşüt AI OCR (yalnız mobil fiş).
- Türk belgesine özel açık kaynak proje görülmedi.

## Farklılaşma (Aria'nın önerisi)
1. İnceleme kuyruğu ve bbox vurgusu **açık çekirdekte** (Unstract ve Label Studio bunu ücretliye kilitliyor).
2. Doğrulama birinci sınıf: satır toplamı, KDV × matrah, tarih, VKN/TCKN sağlama; reddet/incele kuralları.
3. Kalibre güven: model güveni + doğrulama sonucu birleşik; kalibrasyonu ölçüp README'de yayımla.
4. Hafif self-host: GPU'suz, tek `docker compose`.
5. Türkiye paketi (sonra): UBL-TR XML ↔ PDF çapraz doğrulama, Türk banka ekstreleri, muhasebe programı aktarımı.
6. Konum: global OSS kitlesi önce; Türkiye fiyat seviyesi düşük (~0,4 TL/belge), SaaS geliri için tek başına zayıf.

Kaynaklar: unstract.com/unstract-editions · github.com/Zipstack/unstract · github.com/katanaml/sparrow ·
docling-project.github.io/docling/concepts/confidence_scores · github.com/datalab-to/marker · docs.reducto.ai/configs/extract/citations ·
developers.llamaindex.ai/llamaparse/extract · docs.mindee.com · knowledge-base.rossum.ai (eşik) · aws.amazon.com/textract/pricing ·
learn.microsoft.com (Document Intelligence dil desteği, 2026-10-19) · rahataktarim.com · mihsap.com/blog/fatura-isleme ·
support.humansignal.com (Label Studio review Enterprise).

## Ek (2026-10-24, ad kontrolünden çıktı): doğrudan rakip
- **tracefield.io** (© 2026, altbilgi "EMINCAN.COM"; ekip/tarih belirtilmemiş): aynı konsept. Değer + kaynak metni + belgede
  konum ("every value proves where it came from"), çözülemeyen değer incelemeye düşer ("unverified never auto-passes"),
  aritmetik çapraz kontrol, onay/düzelt/reddet kuyruğu + denetim izi, tedarikçi listesiyle doğrulama, CSV/JSON + MCP,
  imzalı webhook. Fiyat: $0 (5 belge), $49/ay (500), $199/ay (2.500); hepsi erken erişimde ücretsiz. "Runtime MIT" diyor
  ama GitHub bağlantısı yok; ürünün geri kalanı kapalı. Alan bazında güven skorunun anlamı açıklanmamış.
- **LedgerLens SDK** (npm, 2026-01): "Document Intelligence API with math verification", repo 0xShortx/ledgerlens.
- Etki: konsept doğrulandı ve 2026'da kalabalıklaşıyor. Citefield'un farkı açık kaynak olmasında kalıyor: tüm ürün (inceleme
  kuyruğu dahil) açık, self-host tek komut, kalibrasyon ve doğruluk açık veri setlerinde ölçülüp yayımlanıyor.

## Ad kontrolü (2026-10-24)
Citefield, Fieldtrace, Boxproof: GitHub kullanıcı/org, PyPI, npm boş; belge/AI alanında aynı adlı ürün bulunmadı (web araması
bu üçünde eksik kaldı). Dolu: Tracefield (doğrudan rakip), Ledgerlens (npm "Document Intelligence API with math verification"),
Provena (PyPI + org), Docproof (PyPI + npm), Sightline. Fieldtrace boş ama rakip adına çok yakın → elendi. Seçim: **Citefield**.
