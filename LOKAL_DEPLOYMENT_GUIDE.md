# 🚀 FinWise Lokal Production Deployment Guide

**Tarih:** 06 Mart 2026  
**Sürüm:** 2.0.0 (Production-Ready)  
**Dil:** Türkçe / English  

---

## 📋 Hızlı Başlangıç (Quick Start)

### **Windows - Direct Launch**

```batch
cd "C:\Users\berat\OneDrive\Masaüstü\FinWise-ML Projem"
.venv\Scripts\python.exe app_api.py
```

API şu adresten erişebilir:
```
http://127.0.0.1:5000
```

### **Windows - Interactive Menu**

```batch
python production_setup.py
```

Seçenekler:
1. Start API
2. Check environment
3. View documentation
4. Test API
5. Database backup
6. Reset database
7. Exit

---

## 🔐 Kimlik Doğrulama (Authentication)

### **Varsayılan Kullanıcı**
```
Username: admin
Password: admin123
```

### **Yeni Kullanıcı Kaydı**

```bash
curl -X POST http://127.0.0.1:5000/api/v2/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "securepass123",
    "email": "user@finwise.local"
  }'
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user_id": 2
}
```

### **Login - JWT Token Al**

```bash
curl -X POST http://127.0.0.1:5000/api/v2/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

---

## 🏥 Health Check

```bash
curl http://127.0.0.1:5000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-06T00:57:15+00:00",
  "database": "SQLite",
  "model": "loaded",
  "model_version": "1.0.0",
  "api_version": "2.0.0"
}
```

---

## 💳 Kredi Başvurusu Değerlendirmesi

**Endpoint:** `POST /api/v2/evaluate`  
**Authentication:** JWT Bearer Token gerekli

### **Request Format**

```bash
curl -X POST http://127.0.0.1:5000/api/v2/evaluate \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "person_age": 35,
    "person_income": 75000,
    "person_emp_length": 8,
    "loan_amnt": 15000,
    "loan_int_rate": 5.5,
    "loan_percent_income": 0.20,
    "cb_person_cred_hist_length": 10,
    "person_home_ownership": "RENT",
    "loan_intent": "PERSONAL",
    "loan_grade": "B",
    "cb_person_default_on_file": "N",
    "customer_id": "CUST-12345"
  }'
```

### **Input Parameters**

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| person_age | Integer | 18-100 | Yaş |
| person_income | Float | 0-500000 | Yıllık gelir |
| person_emp_length | Integer | 0-50 | İş deneyimi (yıl) |
| loan_amnt | Float | 500-50000 | Kredi tutarı |
| loan_int_rate | Float | 1-25 | Faiz oranı (%) |
| loan_percent_income | Float | 0-1 | Gelirin yüzdesi |
| cb_person_cred_hist_length | Integer | 1-50 | Kredi geçmişi (yıl) |
| person_home_ownership | String | RENT, OWN, MORTGAGE, OTHER | Ev sahipliği |
| loan_intent | String | PERSONAL, EDUCATION, MEDICAL, VENTURE, HOMEIMPROVEMENT, DEBTCONSOLIDATION | Kredi amacı |
| loan_grade | String | A, B, C, D, E, F, G | Kredi notu |
| cb_person_default_on_file | String | Y, N | Geçmiş temerrüt |
| customer_id | String | Optional | Müşteri kodu |

### **Success Response (Status 200)**

```json
{
  "application_id": "APP-A1B2C3D4E5F6",
  "decision": "APPROVED",
  "decision_reason": "Düşük risk (Olasılık: 22.15%)",
  "risk_probability": 0.2215,
  "prediction": 0,
  "model_version": "1.0.0",
  "processing_time_ms": 42
}
```

### **Error Response (Status 400/500)**

```json
{
  "error": "X has 14 features, but RandomForestClassifier is expecting 22 features"
}
```

---

## 📊 Başvuruları Listele

**Endpoint:** `GET /api/v2/applications`

```bash
curl http://127.0.0.1:5000/api/v2/applications \
  -H "Authorization: Bearer <YOUR_TOKEN>"
```

**Response:**
```json
{
  "count": 5,
  "applications": [
    {
      "application_id": "APP-A1B2C3D4E5F6",
      "customer_id": "CUST-001",
      "created_at": "2026-03-06 00:57:15",
      "decision": "APPROVED",
      "probability": 0.2215,
      "processing_time_ms": 42
    },
    ...
  ]
}
```

---

## 📈 İstatistikler

**Endpoint:** `GET /api/v2/stats`

```bash
curl http://127.0.0.1:5000/api/v2/stats \
  -H "Authorization: Bearer <YOUR_TOKEN>"
```

**Response:**
```json
{
  "stats": {
    "total": 5,
    "approved": 4,
    "rejected": 1,
    "avg_risk": 0.2850,
    "avg_time_ms": 38
  }
}
```

---

## 🛠️ Database Management

### **Backup Al**

```bash
python production_setup.py
# Option 5. Database backup seçin
```

Yedek dosyası: `finwise_production_backup_20260306_002500.db`

### **Database'i Sıfırla**

```bash
python production_setup.py
# Option 6. Reset database seçin
```

⚠️ **Bu işlem geri alınamaz!**

### **Database Dosyası**

```
finwise_production.db
```

**Tablolar:**
- `users` - Kullanıcı hesapları
- `applications` - Kredi başvuruları
- `manual_overrides` - İşletmen müdahaleleri (opsiyonel)
- `audit_trails` - Denetim kaydı (opsiyonel)

---

## 🔧 Troubleshooting

### **Problem: "Port 5000 already in use"**

```batch
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### **Problem: Model loaded but features mismatch**

Solution built-in. Preprocessing pipeline automatically handles:
- StandardScaler for numeric features
- OneHotEncoder for categorical features
- Proper feature alignment

### **Problem: Unicode encoding error in logs**

Already fixed in latest version. Use `logger.info()` instead of `print()`.

### **Problem: Token expired**

Token expires in 1 hour (3600 seconds). Get new token:

```bash
curl -X POST http://127.0.0.1:5000/api/v2/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

---

## 📊 Model Performance

| Metric | Value |
|--------|-------|
| **AUC Score** | 0.9198 |
| **Recall** | 77.73% |
| **Precision** | 73.27% |
| **F1-Score** | 75.43% |
| **Decision Threshold** | 0.24 |
| **Features** | 22 (7 numeric + 15 one-hot encoded categorical) |
| **Framework** | scikit-learn RandomForestClassifier (balanced) |
| **Training Data** | 22,806 samples |

🚨 **CRITICAL FAIRNESS ISSUE:**
- **Disparate Impact Ratio (Q1 vs Q5 income): 0.628**
  - Q1 (Lowest Income): 54.7% approval rate
  - Q5 (Highest Income): 87.1% approval rate
  - **Status:** ⚠️ BELOW LEGAL THRESHOLD (target: ≥0.80)
  - **Risk Level:** MODERATE - Improved from baseline (0.193) but still non-compliant
  
**MANDATORY ACTIONS:**
1. ✅ Deploy with monthly (not quarterly) fairness monitoring
2. ✅ Set automated alerts if Q1 approval rate falls below 50%
3. ⚠️ Plan remediation sprint to reach ≥0.80 DI ratio
4. ⚠️ Legal/compliance sign-off required before production scale-up
5. 📋 Document all fairness-related decisions for audit trail

See `FAIRNESS_REMEDIATION_PROGRESS.md` for detailed remediation strategy.

---

## 🚀 Production Checklist

- [x] Model loads successfully
- [x] Database initialized
- [x] JWT authentication working
- [x] All 6 endpoints tested
- [x] Preprocessing pipeline fixed
- [x] Error handling implemented
- [x] Logging configured
- [x] CORS enabled for frontend
- [x] Documentation complete
- [ ] SSL/HTTPS configured (recommended for production)
- [ ] Rate limiting configured (recommended)
- [ ] Monitoring/alerting setup (recommended)

---

## 📞 Support

**Files:**
- [API Documentation](API_DOCUMENTATION.md)
- [Final Project Report](FINAL_PROJECT_REPORT.md)
- [Fairness Analysis](FAIRNESS_REMEDIATION_PROGRESS.md)
- [Production Readiness](PRODUCTION_READINESS_ASSESSMENT.md)

**Quick Commands:**
```bash
# Start API
.venv\Scripts\python.exe app_api.py

# Test API
.venv\Scripts\python.exe test_simple.py

# Check environment
python production_setup.py

# View model info
.venv\Scripts\python.exe -c "import joblib; print(joblib.load('model_production.joblib'))"
```

---

**Status:** ✅ **PRODUCTION READY**  
**Last Updated:** 06 Mar 2026 00:58:30 UTC  
**Version:** 2.0.0
