# DURUM — Citefield — kaynak kutulu belge çıkarımı ve inceleme

> **Ne bu dosya:** sertifika değil **envanter**. Ölçülen gerçek durum; "yok" yazan satır kusur değil, kayıt.
> Faz durumu `docs/Roadmap.md`'de; bu dosya son ölçümü tutar.

**Ölçüm tarihi:** 2026-11-13
**Tek cümle:** Fatura/fiş gibi belgelerden değer çıkaran, her değeri belgedeki kutusuna bağlayan, kurallardan ya da
ikinci okumadan geçemeyeni insana inceleme kuyruğuna koyan yerel uygulama (Python API + React arayüz). Faz 1–7.5
tamam; Faz 8 (PyPI yayını, gerçek kullanım) Scryne'ın onayını bekliyor.

## Ne çalışıyor (2026-11-13'te ölçüldü)

- **Python:** `ruff` + `ruff format --check` + `mypy` temiz, pytest 89/89.
- **Arayüz:** `oxlint` 0, `tsc -b` 0, `vite build` 0; `npm audit` 0. Sayfa başına kod bölme (`27df0f9`): tek
  565 kB parça yerine en büyüğü 248 kB, Vite boyut uyarısı yok.
- **Playwright:** 6/6 (gerçek uygulama, sahte model; `E2E_PORT` ile port seçilebilir, `20f4a1b`).
- **Dependabot:** PR #5 (ui grubu, 8) ve #6 (python grubu, 8) yerelde birleştirildi, testler yeşil.
- **Gezi:** `tests/e2e_server.py` demo verisiyle 7 rota (genel bakış, belgeler, inceleme kuyruğu, belge inceleme,
  şemalar, ayarlar, bilinmeyen adres) × 390/1440 × açık/koyu = 28 kare: taşma 0, konsol 0.
- **Uçtan uca:** fişte ikinci okuma toplamda anlaşmıyor → "1 of 6 values needs review" → Approve → genel bakışta
  "Nothing waits for you", Approved 1, Needs review 0; API'de `to_review: 0`.

## Bilinen sınırlar

- `anthropic` sağlayıcısı birim testlerle kapsanıyor, canlı API'ye karşı koşulmadı (README'de de yazıyor).
- Ayarlar sayfası veri dizininin yerel yolunu gösteriyor (tek kullanıcılı yerel uygulama için bilerek); ekran
  görüntüsü paylaşırken bu sayfa kullanılmamalı.
