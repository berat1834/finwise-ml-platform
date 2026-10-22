# VTYS Teslim Kontrol Matrisi

## Proje Konusu

FinWise: Yapay Zeka Destekli Kredi Risk Analizi ve Karar Destek Sistemi

## Gereksinim Karsiliklari

| Gereksinim | Karsilik | Dosya |
| --- | --- | --- |
| En az 8 tablo | `applications`, `decisions`, `users`, `manual_overrides`, `sla_violations`, `customer_subscriptions`, `drift_metrics`, `fairness_audit_log`, `application_analyst_assignments`, `daily_decision_reports` | [VTYS_EK_SQL.sql](VTYS_EK_SQL.sql), [init_postgres.sql](init_postgres.sql) |
| En az 1 adet N-N iliski | `applications` <-> `users` iliskisi `application_analyst_assignments` uzerinden | [VTYS_PROJE_RAPORU.md](VTYS_PROJE_RAPORU.md), [VTYS_EK_SQL.sql](VTYS_EK_SQL.sql) |
| En az 10 analiz sorgusu | 10 adet sorgu hazirlandi | [VTYS_ANALIZ_SORGULARI.sql](VTYS_ANALIZ_SORGULARI.sql) |
| En az 1 VIEW | `vw_application_decision_summary` | [VTYS_EK_SQL.sql](VTYS_EK_SQL.sql) |
| En az 1 TRIGGER | `trg_set_applications_updated_at`, `trg_log_manual_override` | [VTYS_EK_SQL.sql](VTYS_EK_SQL.sql) |
| En az 1 STORED PROCEDURE | `sp_generate_daily_decision_report` | [VTYS_EK_SQL.sql](VTYS_EK_SQL.sql) |
| ER diyagrami | Mermaid tabanli mantiksal ER gosterimi | [VTYS_PROJE_RAPORU.md](VTYS_PROJE_RAPORU.md) |
| 1NF-3NF aciklamasi | Ayri normalizasyon bolumu | [VTYS_PROJE_RAPORU.md](VTYS_PROJE_RAPORU.md) |

## Teslimde Kullanilabilecek Dosya Sirasi

1. Ana rapor: [VTYS_PROJE_RAPORU.md](VTYS_PROJE_RAPORU.md)
2. SQL ekleri: [VTYS_EK_SQL.sql](VTYS_EK_SQL.sql)
3. Analiz sorgulari: [VTYS_ANALIZ_SORGULARI.sql](VTYS_ANALIZ_SORGULARI.sql)
4. Gereksinim ozeti: [VTYS_TESLIM_KONTROL_MATRISI.md](VTYS_TESLIM_KONTROL_MATRISI.md)

## Sozlu Sunumda Vurgulanabilecek Noktalar

1. Proje klasik otomasyon degil, karar destek ve veri analizi odaklidir.
2. Veri modeli operasyonel ve analitik tablolari birlikte tasir.
3. N-N iliski ve raporlama nesneleri teslim gereksinimi icin acik sekilde gosterilmistir.
4. SQL sorgulari yonetsel karar destek amacina yoneliktir.