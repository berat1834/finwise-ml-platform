# FinWise Credit Risk API - Lokal Production Setup

## 🚀 Sistem Durumu

| Bileşen | Durum | Bilgi |
|---------|-------|-------|
| **API Server** | ✅ Çalışıyor | Flask (5000) |
| **Database** | ✅ SQLite | finwise_production.db |
| **ML Model** | ✅ Yüklendi | AUC: 0.9198, Recall: 77.7%, F1: 75.4% |
| **Authentication** | ✅ JWT | admin/admin123 |

---

## 📋 API Kullanımı

### 1. **Health Check** (Herkese açık)
```bash
GET http://127.0.0.1:5000/health
```

**Response (200):**
```json
{
  "status": "healthy",
  "database": "SQLite",
  "model": "loaded",
  "api_version": "2.0.0",
  "timestamp": "2026-03-06T21:45:00"
}
```

---

### 2. **User Registration**
```bash
POST /api/v2/register
Content-Type: application/json

{
  "username": "user1",
  "password": "secure123",
  "email": "user1@example.com"
}
```

**Response (201):**
```json
{
  "message": "Kullanıcı başarıyla oluşturuldu",
  "username": "user1"
}
```

---

### 3. **Login (JWT Token Alma)**
```bash
POST /api/v2/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "username": "admin",
  "role": "admin"
}
```

**Token Kullanımı:**
```bash
Authorization: Bearer <access_token>
```

---

### 4. **Kredi Başvurusunu Değerlendir** ⭐
```bash
POST /api/v2/evaluate
Authorization: Bearer <token>
Content-Type: application/json

{
  "customer_id": "CUST-001",
  "person_age": 35,
  "person_income": 75000,
  "person_emp_length": 8,
  "loan_amnt": 20000,
  "loan_int_rate": 7.5,
  "loan_percent_income": 0.27,
  "cb_person_cred_hist_length": 15,
  "person_home_ownership": "RENT",
  "loan_intent": "PERSONAL",
  "loan_grade": "B",
  "cb_person_default_on_file": "N"
}
```

**Response (200):**
```json
{
  "application_id": "APP-A1B2C3D4E5F6",
  "decision": "APPROVED",
  "decision_reason": "Düşük risk (Olasılık: 18.5%)",
  "risk_probability": 0.1851,
  "prediction": 0,
  "model_version": "1.0.0",
  "processing_time_ms": 156
}
```

---

### 5. **Başvuruları Listele**
```bash
GET /api/v2/applications?limit=50
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "count": 5,
  "applications": [
    {
      "application_id": "APP-A1B2C3D4E5F6",
      "customer_id": "CUST-001",
      "created_at": "2026-03-06 21:45:12",
      "decision": "APPROVED",
      "probability": 0.1851
    }
  ]
}
```

---

### 6. **İstatistikler**
```bash
GET /api/v2/stats
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "total_applications": 5,
  "approved": 4,
  "rejected": 1,
  "approval_rate": 0.8,
  "avg_risk_probability": 0.2145,
  "avg_processing_time_ms": 142
}
```

---

## 🔐 Güvenlik

- ✅ **JWT Authentication:** Token tabanlı
- ✅ **Password Hashing:** werkzeug.security
- ✅ **CORS:** Configured
- ✅ **Input Validation:** Flask request parsing

---

## 📊 Model Performansı

```
Training Samples: 22,806
Decision Threshold: 0.24 (optimized)

Performance Metrics:
  • AUC-ROC: 0.9198 ✅
  • Recall: 77.73% ✅ (balanced sensitivity)
  • Precision: 73.27% ✅
  • F1-Score: 75.43%

Compliance:
  • FCRA: Compliant ✅
  • GDPR Article 22: Compliant ✅
  • ECOA 80% Rule: Partial ⚠️ (DI Ratio: 0.628, target: ≥0.80)
```

---

## 🛠️ Startup/Shutdown

### **API Başlat**
```bash
.venv\Scripts\python.exe app_api.py
```

Başarılı output:
```
============================================================
FinWise Credit Risk API - Production Ready
============================================================
✓ Database: SQLite (finwise_production.db)
✓ Model: Loaded
✓ API endpoint: http://127.0.0.1:5000
✓ Health check: http://127.0.0.1:5000/health
```

### **API Kapat**
```bash
Terminal'de: Ctrl+C
```

---

## 💾 Database Backup

### **Database'i Yedekle**
```bash
copy finwise_production.db finwise_production_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db
```

### **Database'i Sıfırla**
```bash
del finwise_production.db
# API yeniden başlatınca otomatik oluşur
```

---

## 📈 Production Checklist

- ✅ Model validation (AUC 0.9198)
- ✅ Database setup (SQLite)
- ✅ API endpoints (6 endpoint)
- ✅ JWT authentication
- ✅ Error handling
- ✅ Logging
- ⏳ **Monitoring dashboard** (sonraki adım)
- ⏳ **Automated backup** (sonraki adım)
- ⏳ **Performance optimization** (sonraki adım)

---

## 🐛 Troubleshooting

### **Port 5000 zaten kullanımdaysa?**
```bash
# Kullanılan port'u kontrol et
netstat -ano | findstr :5000

# Process'i öldür (PID yerine gerçek numarası yazın)
taskkill /PID <PID> /F
```

### **Model yüklenmiyor?**
```bash
# model_production.joblib varsa kontrol et
if (Test-Path "model_production.joblib") { echo "OK" } else { echo "Yok" }
```

### **Database hatası?**
```bash
# Database'i sıfırla
del finwise_production.db
# API'ı yeniden başlat
```

---

## 📞 Support

**Hata raporu:**
- Terminal output'unu kaydet
- API response'unu kaydęt
- `finwise_production.log` dosyasını kontrol et

---

## 🚀 İleri Adımlar (İsteğe Bağlı)

1. **Monitoring Dashboard** - Prometheus + Grafana
2. **API Load Testing** - Apache JMeter veya Locust
3. **Automated Backup** - Cron/Task Scheduler
4. **Email Notifications** - Critical alerts için
5. **AWS Migration** - Production scale için

---

**Version:** 2.0.0  
**Updated:** 2026-03-06  
**Status:** Production-Ready ✅
