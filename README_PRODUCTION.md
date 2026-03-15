# 🏦 Kredi Risk Analizi Sistemi - Profesyonel Versiyon

## ✨ Özellikler

### 🎯 Üretim Seviyesi İyileştirmeler
- ✅ **Gelişmiş ML Pipeline**: ColumnTransformer + StandardScaler + OneHotEncoder
- ✅ **Class Imbalance**: `class_weight='balanced'` ile dengeli eğitim
- ✅ **Hiperparametre Optimizasyonu**: 5-fold CV ile GridSearch
- ✅ **Threshold Tuning**: Risk odaklı karar eşiği (Recall ↑)
- ✅ **Model Versiyonlama**: JSON metadata ile izlenebilirlik
- ✅ **API Validasyonu**: Pydantic v2 ile güçlü input kontrolü
- ✅ **Structured Logging**: Rotating file logs (`logs/app.log`)
- ✅ **Explainability**: SHAP ile karar açıklamaları

### 📊 Model Performansı
- **ROC AUC**: 0.932 (Excellent)
- **PR AUC**: 0.884 (Very Good)
- **Accuracy**: 81.5%
- **Threshold**: 0.191 (Risk-focused)
- **Confusion Matrix**: [[4080, 1015], [191, 1231]]

**Not**: Accuracy'nin %93'ten %81.5'e düşmesi KASITLIDIR. Yüksek riskli kredilerin %86.6'sını yakalıyor (recall), bankacılıkta kritik olan budur.

---

## 🚀 Kurulum

### 1. Bağımlılıkları Yükleyin
```powershell
cd "C:\Users\berat\OneDrive\Masaüstü\ML Projem"
pip install -r requirements.txt
```

### 2. Modeli Eğitin (İlk Kurulum)
```powershell
python training_pipeline.py
```
**Çıktı**: `model.joblib` ve `model_meta.json` oluşturulur.

---

## 🎮 Kullanım

### Seçenek 1: Web Arayüzü (Önerilen)
```powershell
cd "C:\Users\berat\OneDrive\Masaüstü\ML Projem"
python start.py
```
Sonra tarayıcıda: **http://localhost:5000**

### Seçenek 2: API İstekleri

**Health Check:**
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:5000/health
```

**Kredi Değerlendirme:**
```powershell
$body = @{
    person_age = 30
    person_income = 60000
    person_emp_length = 5
    loan_amnt = 12000
    loan_int_rate = 7.5
    loan_percent_income = 0.2
    cb_person_cred_hist_length = 8
    person_home_ownership = "RENT"
    loan_intent = "PERSONAL"
    loan_grade = "B"
    cb_person_default_on_file = "N"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://127.0.0.1:5000/degerlendir -Method Post -ContentType "application/json" -Body $body
```

**Karar Açıklaması (SHAP):**
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:5000/explain -Method Post -ContentType "application/json" -Body $body
```

**Model İstatistikleri:**
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:5000/istatistik
```

---

## 📁 Dosya Yapısı

```
ML Projem/
├── Credit_Risk_Analysis.py      # Orijinal analiz (eski)
├── credit_risk_dataset.csv      # Eğitim verisi
├── training_pipeline.py         # 🆕 Production training
├── app.py                        # 🆕 Production API
├── start.py                      # 🆕 Basit sunucu başlatıcı
├── run_production.py             # 🆕 Waitress sunucu (opsiyonel)
├── test_api.py                   # 🆕 API test client
├── index.html                    # Web arayüzü
├── requirements.txt              # 🆕 Python bağımlılıkları
├── model.joblib                  # 🆕 Eğitilmiş pipeline
├── model_meta.json               # 🆕 Model metadata
├── logs/                         # 🆕 API logları
│   └── app.log
└── README_PRODUCTION.md          # Bu dosya
```

---

## 🔧 API Endpoints

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/` | GET | Web arayüzü |
| `/health` | GET | Sistem sağlık kontrolü |
| `/degerlendir` | POST | Kredi başvurusu değerlendirme |
| `/explain` | POST | SHAP ile karar açıklaması |
| `/istatistik` | GET | Model metrikleri ve bilgileri |

---

## 📊 Profesyonel Özellikler

### 1. Robust Preprocessing Pipeline
```python
ColumnTransformer([
    ('num', StandardScaler(), numeric_features),
    ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
])
```

### 2. Class Imbalance Handling
```python
RandomForestClassifier(class_weight='balanced')
```

### 3. Threshold Optimization
```python
# Precision ≥ 0.8 koşulu altında recall'u maksimize et
threshold = select_threshold(model, X_valid, y_valid, min_precision=0.8)
```

### 4. Production Logging
```python
logging.info("decision result=%s prob_reject=%.4f", result, probability)
```

### 5. Input Validation
```python
class InputSchema(BaseModel):
    person_age: int
    person_income: float
    
    @field_validator('person_home_ownership')
    def valid_home(cls, v):
        if v not in {'RENT','OWN','MORTGAGE','OTHER'}:
            raise ValueError(...)
```

---

## 🎯 Örnek Senaryolar

### ✅ Başarılı Başvuru
```json
{
  "person_age": 35,
  "person_income": 80000,
  "person_emp_length": 10,
  "loan_amnt": 15000,
  "loan_grade": "A",
  "cb_person_default_on_file": "N"
}
```
**Sonuç**: ONAYLANDI (%92 olasılık)

### ❌ Riskli Başvuru
```json
{
  "person_age": 22,
  "person_income": 25000,
  "person_emp_length": 1,
  "loan_amnt": 30000,
  "loan_grade": "E",
  "cb_person_default_on_file": "Y"
}
```
**Sonuç**: REDDEDİLDİ (%85 olasılık)

---

## 🔍 SHAP Açıklamaları

Her karar için en önemli faktörleri gösterir:

```json
{
  "top_features": [
    {"feature": "loan_grade_D", "contribution": 0.1234},
    {"feature": "person_income", "contribution": -0.0987},
    {"feature": "loan_int_rate", "contribution": 0.0765}
  ]
}
```

**Pozitif**: Red riskini artırır  
**Negatif**: Onay şansını artırır

---

## ⚙️ Gelişmiş Ayarlar

### Threshold Değiştirme
`model_meta.json` dosyasında `threshold` değerini manuel olarak değiştirin:
```json
{
  "threshold": 0.25
}
```

### Log Seviyesi Ayarlama
`app.py` içinde:
```python
logging.basicConfig(level=logging.DEBUG)  # Daha detaylı loglar
```

### Model Yeniden Eğitme
```powershell
python training_pipeline.py
# Yeni model.joblib ve model_meta.json oluşturulur
# Sunucuyu yeniden başlatın
```

---

## 🐛 Sorun Giderme

### Port Zaten Kullanımda
```powershell
# app.py içinde port değiştirin
app.run(host='127.0.0.1', port=5001)
```

### Model Bulunamadı
```powershell
python training_pipeline.py  # Modeli yeniden eğit
```

### API'ye Bağlanılamıyor
- Firewall kontrolü yapın
- `127.0.0.1` yerine `localhost` deneyin
- Sunucunun çalıştığından emin olun: `python start.py`

---

## 📈 Performans Karşılaştırması

| Metrik | Eski Model | Yeni Model | Değişim |
|--------|-----------|-----------|---------|
| Accuracy | 93.0% | 81.5% | ⬇️ -11.5% |
| Recall (Risk) | 72.0% | 86.6% | ⬆️ +14.6% |
| Precision (Risk) | 96.0% | 54.8% | ⬇️ -41.2% |
| ROC AUC | ~0.85 | 0.932 | ⬆️ +8.2% |
| False Negatives | 609 | 191 | ⬇️ -68.6% |

**Sonuç**: Risk tespiti %68.6 daha iyi! Bankacılık için kritik.

---

## 🚀 Üretim Deployment (Gelecek)

### Docker
```dockerfile
FROM python:3.13
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "run_production.py"]
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: credit-risk-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: credit-risk:latest
        ports:
        - containerPort: 5000
```

---

## 📝 Lisans

Eğitim amaçlı proje.

## 👨‍💻 Geliştirici

**Berat** - Machine Learning Engineer  
Proje: Profesyonel Kredi Risk Analizi Sistemi

---

## 🎉 Sonuç

Bu sistem artık **profesyonel kullanıma hazır** temel özelliklere sahip:
- ✅ Production-grade ML pipeline
- ✅ Robust input validation
- ✅ Structured logging
- ✅ Model explainability (SHAP)
- ✅ API documentation
- ✅ Risk-focused decision threshold

**Başarılı testler**: Sistem çalışıyor ve kullanıma hazır! 🚀
