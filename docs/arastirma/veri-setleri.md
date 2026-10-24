---
proje: Citefield
created: 2026-10-24
type: arastirma
---
# Açık değerlendirme veri setleri (2026-10-24)

Kaynak: arastirmaci kolu (SROIE resmî sitesi açılmadı; HF tarihleri HF API'sinden). Koşullar yalnız adıyla.

| Set | İçerik | Etiket | Erişim | Koşul | Bilinen sonuç |
|---|---|---|---|---|---|
| **CORD v2** | Endonezce fiş, 1.000 (800/100/100) | alan, satır kalemi, quad bbox | HF parquet, doğrudan, 2,31 GB | CC BY 4.0 | Donut F1 84,1; LayoutLMv3-L 97,46; GPT-4o 81,26 (CC-OCR) |
| SROIE | İngilizce fiş, ~1.000 | 4 alan + kelime/satır bbox | resmî kayıtlı; HF yansıması ~421 MB | resmî doğrulanamadı | GPT-4o 72,55; Claude-3.5-Sonnet 69,83 (CC-OCR) |
| **DocILE** | İngilizce iş belgesi/fatura, 6.680 etiketli (val 500) | 55 alan sınıfı + bbox, satır kalemi, hazır OCR | **form onayı** + token | "research purposes" | KILE/LIR F1 0,66–0,72 |
| **FATURA** | sentetik fatura, 10.000 (50 şablon) | 24 sınıf, bbox + metin | Zenodo, doğrudan, 690,7 MB | CC BY 4.0 | bilinmeyen şablonda F1 56,3 |
| synthetic-receipts-ocr | sentetik fiş 32.000, en/de/it/fr, temiz + bozulmuş ikiz | kelime bbox, alan, kalem | HF, 4,08 GB | Apache-2.0 | yok |
| turkish-synthetic-documents | **Türkçe** sentetik 200k (fiş, fatura, form…) | metin + `fields` JSON, **bbox yok** | HF, 23,3 GB | CC BY 4.0 | yok |
| FUNSD / XFUND | form, 199 / 7 dil 1.393 | entity + ilişki + kutu | doğrudan | araştırma / CC BY-NC-SA 4.0 | LayoutLMv3 92,08 |
| WildReceipt, VRDU, Kleister, katanaml, InvoicesReceiptsPT, EPHOIE | — | — | — | lisansı yok / bbox yok / onaylı | ikincil |

Gerçek Türkçe fatura/fiş açık seti bulunamadı.

## Seçim (spike'lar için)
- **S1 kaynak eşleme:** FATURA (fatura, bbox + metin, doğrudan) + CORD v2 doğrulama bölümü (gerçek fotoğraf fiş, quad bbox).
- **S2 kalibrasyon:** CORD v2 + synthetic-receipts-ocr'ın bozulmuş ikizleri (aynı belge temiz/bozuk → güven düşüyor mu).
- **Sonra:** DocILE (gerçek fatura) — erişim formu Scryne'ın onayıyla doldurulur; Türkçe metin doğruluğu için turkish-synthetic-documents.
- CC-OCR sayıları 2024-12 tarihli, model sürümleri eski; kıyas için kendi koşumuz esas.
