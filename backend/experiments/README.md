# Deneysel & Alternative Model Scripts

Bu klasör, projenin ana pipeline'ına entegre olmayan deneysel veya alternative model implementasyonlarını içerir.

## İçerik

- **MLProje.py** — ARIMA zaman serisi modeli (alternatif yaklaşım)
- **MLProje2.py** — ARIMA model varyasyonu  
- **Credit_Risk_Analysis.py** — Tekil risk analizi scripti (archival)
- **daily_fairness_report.py** — Historik fairness raporlama araçı

## Kullanım

Bu dosyalar **araştırma ve geliştirme amaçlı** tutulmuştur. 

Production pipeline için bkz: `../training_pipeline.py`

### Deneysel Çalıştırma

```bash
cd experiments
python MLProje.py
```

## Production'a Promotasyon

Bir deneysel model production'a alınmak istenirse:

1. **Core pipeline'a entegre edin**: `training_pipeline.py`'ye fairness strategy olarak ekleyin
2. **Metadataile güncelle**: Modeli `production_model.joblib` olarak serialize edin
3. **Tests ekleyin**: Fairness ve leakage testleri ekleyin
4. **Dokumentasyon güncelleyin**: `PROJE_RAPORU.md` ve `API_DOCUMENTATION.md`'ü güncelleyin

---

**Son Güncellenme**: 12 Mart 2026
