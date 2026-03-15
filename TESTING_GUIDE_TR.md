# 🧪 FinWise-ML TESTING GUIDE

## ⚠️ Ön Koşullar

### 1. Python Kütüphanelerini Yükle
```powershell
pip install -r requirements_full.txt
```

### 2. Environment Variables Ayarla

`.env` dosyası oluştur (proje kök dizininde):
```
# Database (opsiyonel - şimdilik skip edebilirsin)
DATABASE_URL=postgresql://finwise_user:password@localhost:5432/finwise

# Stripe (test key - https://stripe.com/docs/keys#test-live-modes)
STRIPE_API_KEY=sk_test_YOUR_TEST_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_test_YOUR_WEBHOOK_SECRET

# Flask
FLASK_ENV=development
JWT_SECRET_KEY=your_jwt_secret_key_here_for_testing

# API
API_HOST=localhost
API_PORT=5000
```

---

## 🚀 TEST ADIMLAR

### ADIM 1: API Sunucusunu Başlat

**Terminal 1:**
```powershell
cd "c:\Users\berat\OneDrive\Masaüstü\FinWise-ML Projem"
python app_v2_secure.py
```

**Beklenen çıktı:**
```
 * Running on http://127.0.0.1:5000
 * WARNING: This is a development server. Do not use it in production deployment.
```

✅ **Sunucu çalışıyor** - Terminal'i açık bırak

---

### ADIM 2: Test Script'i Çalıştır

**Terminal 2 (yeni açılacak):**
```powershell
cd "c:\Users\berat\OneDrive\Masaüstü\FinWise-ML Projem"
python test_integration.py
```

**Beklenen çıktı:**
```
============================================================
FinWise-ML Integration Test Suite
Started: 2026-01-22 14:30:45
============================================================

============================================================
▶ Test 1: Server Health Check
============================================================
✓ Server is running (Status: 200)

============================================================
▶ Test 2: Frontend Accessibility
============================================================
✓ Frontend accessible: /templates/application.html
✓ Frontend accessible: /templates/dashboard.html

============================================================
▶ Test 3: Model Prediction
============================================================
✓ Model loaded successfully
✓ Model prediction successful: 0.7234

✓ Decision threshold loaded: 0.6320

... (daha fazla test) ...

============================================================
TEST SUMMARY
============================================================
✓ PASS - Server Health
✓ PASS - Frontend Access
✓ PASS - Model Prediction
✓ PASS - Database
✓ PASS - Credit Application API
✓ PASS - Model Fairness
✓ PASS - API Response Format

Total: 7/7 tests passed

✓ All tests passed! Ready for production.
```

---

### ADIM 3: Frontend'i Tarayıcıda Test Et

**Chrome/Firefox'ta aç:**

#### 3.1 Kredi Başvuru Formu
```
http://localhost:5000/templates/application.html
```

**Test Verileri:**
```
Ad Soyad: Ahmet Yılmaz
E-Posta: ahmet@example.com
T.C. Kimlik: 12345678901
Yıllık Gelir: 150000
Kredi Tutarı: 50000
Vade: 24 Ay
Amaç: Ev Alımı
```

**Beklenen Sonuç:**
- Form gönderme sırasında: "⏳ Başvurunuz değerlendiriliyor..."
- 3-5 saniye sonra sonuç gösterilmeli:
  - ✓ **BAŞVURUNUZ ONAYLANDI** (yeşil) veya
  - ✗ **BAŞVURUNUZ REDDEDİLDİ** (kırmızı)

#### 3.2 Dashboard Formu
```
http://localhost:5000/templates/dashboard.html
```

**Beklenen Sonuç:**
- Müşteri paneli yüklenmeli
- "Aktif Krediler", "Toplam Borç" gösterilmeli
- Ödeme takvimi listelenecek

---

## 🔧 Manuel API Test (Postman/curl)

### Test 1: Kredi Başvurusu

**curl komutu:**
```powershell
$body = @{
    full_name = "Test User"
    email = "test@example.com"
    phone = "+90 555 123 4567"
    date_of_birth = "1990-01-15"
    national_id = "12345678901"
    employment_status = "employed"
    annual_income = 150000
    requested_amount = 50000
    requested_term_months = 24
    purpose = "home"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5000/api/v2/apply" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**Beklenen Cevap:**
```json
{
  "application_id": 1,
  "decision": "approved",
  "probability": 0.7234,
  "approved_amount": 50000,
  "approved_rate": 0.12,
  "approved_term_months": 24,
  "monthly_payment": 2283.45
}
```

---

## 📊 Test Sonuçlarını Yorumla

### ✅ Tüm Testler Geçerse
```
✓ All tests passed! Ready for production.
```
- Model çalışıyor ✓
- API çalışıyor ✓
- Frontend erişilebilir ✓
- Başvuru sistemi çalışıyor ✓

### ⚠️ Bazı Testler Başarısız Olursa

**Hata: `Cannot connect to server`**
```powershell
# Çözüm: Flask sunucusunu başlat
python app_v2_secure.py
```

**Hata: `Database connection failed`**
```powershell
# PostgreSQL'i başlat (Windows)
pg_ctl -D "C:\Program Files\PostgreSQL\15\data" start

# Veya services'ten PostgreSQL'i başlat
# Database URL'i .env'de kontrol et
```

**Hata: `Template not found`**
```powershell
# templates/ dizininin olduğundan emin ol
ls templates/

# Dosya oluşturulmuş mu kontrol et
ls templates/application.html
```

**Hata: `Model prediction failed`**
```powershell
# Dosyaların var olduğundan emin ol
ls model_production_optimal.joblib
ls threshold_config_final.pkl
```

---

## 🎯 Entegrasyon Test Checklist

- [ ] API sunucusu başlatılmış (`python app_v2_secure.py` çalışıyor)
- [ ] `test_integration.py` başarıyla çalışıyor
- [ ] Frontend formlar tarayıcıda açılabiliyor
- [ ] Kredi başvurusu formu doldurulabiliyor
- [ ] Başvuru gönderildiğinde sonuç gösteriliyor
- [ ] API `POST /api/v2/apply` çalışıyor
- [ ] Model fairness metrics normal (`DI > 0.76`)
- [ ] Dashboard formu açılabiliyor

---

## 📁 Proje Dosya Yapısı (Test için)

```
FinWise-ML Projem/
├── model_production_optimal.joblib      ✅ (ML Model)
├── threshold_config_final.pkl           ✅ (Decision threshold)
├── deployment_config.json               ✅ (Config)
├── app_v2_secure.py                     ✅ (Flask API)
├── api_routes.py                        ✅ (Yeni endpoints)
├── database_models.py                   ✅ (Database ORM)
├── payment_processor_v2.py              ✅ (Stripe)
├── test_integration.py                  ✅ (TEST SCRIPT)
├── requirements_full.txt                ✅ (Dependencies)
├── .env                                 ⏳ (Gerekli - oluştur)
├── templates/
│   ├── application.html                 ✅ (Başvuru formu)
│   └── dashboard.html                   ✅ (Müşteri paneli)
└── static/
    └── (CSS/JS - opsiyonel)
```

---

## 🚨 Yaygın Sorunlar & Çözümleri

| Sorun | Çözüm |
|-------|-------|
| `Port 5000 zaten kullanılıyor` | `lsof -i :5000` ile process'i bul ve kapat |
| `ImportError: No module named 'flask'` | `pip install -r requirements_full.txt` |
| `FileNotFoundError: model_production_optimal.joblib` | Dosyalar proje dizininde olmalı |
| `CORS error` | `.env` dosyasında `FLASK_ENV=development` kontrol et |
| `Database connection refused` | PostgreSQL çalışıyor mu kontrol et |
| `Stripe error: Invalid API Key` | `.env` dosyasında test key mi var kontrol et |

---

## ✅ QUICK START (3 ADIM)

```powershell
# ADIM 1: Terminal 1'de API sunucusu
cd "c:\Users\berat\OneDrive\Masaüstü\FinWise-ML Projem"
python app_v2_secure.py

# ADIM 2: Terminal 2'de testleri çalıştır
python test_integration.py

# ADIM 3: Tarayıcıda formu test et
# http://localhost:5000/templates/application.html
```

---

**Sorun olursa bana mesaj at! 🚀**
