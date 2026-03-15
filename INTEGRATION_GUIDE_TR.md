# ÖDEME, UI VE VERİTABANI ENTEGRASYON REHBERİ

## 📋 Proje Yapısı (YENİ DOSYALAR)

```
FinWise-ML Projem/
├── database_models.py          ✅ PostgreSQL ORM Schema
├── payment_processor_v2.py     ✅ Stripe Payment Integration
├── api_routes.py               ✅ Flask API Endpoints
├── templates/
│   ├── application.html        ✅ Kredi Başvuru Formu
│   ├── dashboard.html          ✅ Müşteri Paneli
│   └── login.html              (Oluşturulması gerekli)
├── static/
│   ├── css/
│   │   └── style.css           (Opsiyonel - centralize CSS)
│   └── js/
│       └── utils.js            (Opsiyonel - shared JavaScript)
└── requirements_full.txt       ✅ Tüm dependencies
```

---

## 🗄️ 1. VERİTABANI KURULUMU

### 1.1 PostgreSQL Yükleme

**Windows:**
```powershell
# Chocolatey ile
choco install postgresql

# veya postgresql.org'dan indirin
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 1.2 Database Oluşturma

```bash
# PostgreSQL'e bağlan
psql -U postgres

# Database ve user oluştur
CREATE DATABASE finwise;
CREATE USER finwise_user WITH PASSWORD 'secure_password_123';
ALTER ROLE finwise_user SET client_encoding TO 'utf8';
ALTER ROLE finwise_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE finwise_user SET default_transaction_deferrable TO on;
ALTER ROLE finwise_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE finwise TO finwise_user;
\q
```

### 1.3 Tables Oluşturma

```bash
# Python ortamında
python -c "
from database_models import init_db
init_db()
"
```

### 1.4 Environment Variables

`.env` dosyası oluşturun:
```
DATABASE_URL=postgresql://finwise_user:secure_password_123@localhost:5432/finwise
STRIPE_API_KEY=sk_test_YOUR_STRIPE_TEST_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE
FLASK_ENV=development
JWT_SECRET_KEY=your_jwt_secret_key_here
```

---

## 💳 2. STRIPE KURULUMU

### 2.1 Stripe Hesabı Oluşturma

1. https://stripe.com/en-tr adresine git
2. "Get started" butonuna tıkla
3. Email ile kayıt ol
4. Dashboard'a git

### 2.2 API Keys Alma

1. Developer → API keys bölümüne git
2. **Test keys** seçeneğini tıkla
3. Secret Key'i kopyala ve `.env` dosyasına ekle
4. Publishable Key ise frontend'de kullanılır

### 2.3 Webhook Setup (Production için)

```bash
# Stripe CLI yükleme (Windows)
choco install stripe-cli

# Webhook listen etme
stripe listen --forward-to localhost:5000/webhooks/stripe

# Webhook signing secret al ve .env'ye ekle
```

---

## 🎨 3. FRONTEND SETUP

### 3.1 Templates Dizini Oluşturma

```bash
mkdir -p templates
mkdir -p static/css
mkdir -p static/js
```

### 3.2 Dosyaları Yerleri Yerleştirme

```bash
# Zaten oluşturduğumuz dosyalar:
# - templates/application.html ✅
# - templates/dashboard.html ✅

# Login sayfası oluştur:
touch templates/login.html
```

### 3.3 HTML Dosyasının Test Edilmesi

```bash
# Flask geliştirme sunucusunda test et
python app_v2_secure.py

# Tarayıcıda
http://localhost:5000/application.html
```

---

## 🚀 4. API ENTEGRASYON ADIMLAR

### 4.1 API Routes'ları Flask'a Ekleme

`app_v2_secure.py` dosyasında aşağıdakileri ekle:

```python
# Dosyasının başında
from api_routes import register_application_endpoints

# Flask app oluşturduktan sonra
app = Flask(__name__)
# ... diğer ayarlamalar ...

# Register new routes
register_application_endpoints(app)
```

### 4.2 Database Import Ekleme

```python
# app_v2_secure.py'ye ekle
from database_models import get_db_session, Customer, Credit, Installment
```

### 4.3 Requirements Güncelleme

```bash
pip install stripe sqlalchemy psycopg2-binary
pip freeze > requirements_full.txt
```

---

## 🧪 5. ENTEGRASYON TESTİ

### 5.1 Kredi Başvurusu Testi

```python
# test_integration.py oluştur
import requests
import json

BASE_URL = 'http://localhost:5000'

# Test 1: Kredi başvurusu
application_data = {
    'full_name': 'Ahmet Yılmaz',
    'email': 'ahmet@example.com',
    'phone': '+90 555 123 4567',
    'date_of_birth': '1990-05-15',
    'national_id': '12345678901',
    'employment_status': 'employed',
    'annual_income': 150000,
    'requested_amount': 50000,
    'requested_term_months': 24,
    'purpose': 'home'
}

response = requests.post(
    f'{BASE_URL}/api/v2/apply',
    json=application_data
)

print('Application Response:')
print(json.dumps(response.json(), indent=2))
```

### 5.2 Dashboard Testi

```bash
# Müşteri panelini test et
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:5000/api/v2/customer/dashboard
```

### 5.3 Ödeme Testi

```python
# Stripe test kartı kullan
test_card_visa = '4242 4242 4242 4242'  # Always succeeds
test_card_declined = '4000 0000 0000 0002'  # Always fails
```

---

## 📊 6. VERITABANI YÖNETİMİ

### 6.1 Backup Alma

```bash
# PostgreSQL backup
pg_dump -U finwise_user finwise > finwise_backup.sql

# Restore
psql -U finwise_user finwise < finwise_backup.sql
```

### 6.2 Veritabanı Temizleme (Test Ortamı)

```bash
# Python'da
from database_models import Base, engine
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
```

### 6.3 Sorguları İnceleme (psql)

```sql
-- Tüm müşterileri listele
SELECT * FROM customers;

-- Başvuruları göster
SELECT id, customer_id, status, model_decision FROM credit_applications;

-- Ödeme geçmişi
SELECT * FROM payments ORDER BY created_at DESC;

-- Audit log
SELECT action, entity_type FROM audit_logs ORDER BY created_at DESC;
```

---

## 🔐 7. GÜVENLIK BEST PRACTICES

### 7.1 Environment Variables

```bash
# .gitignore'a ekle
.env
.env.local
*.db
*.pkl
```

### 7.2 CORS Konfigürasyonu

```python
# app_v2_secure.py'ye ekle
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "https://yourapp.com"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

### 7.3 HTTPS (Production)

```bash
# SSL sertifikası oluştur
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Flask'ta kullan
app.run(ssl_context=('cert.pem', 'key.pem'))
```

---

## 📈 8. MONITORING & LOGGING

### 8.1 Log Dosyası Ayarı

```python
# app_v2_secure.py'ye ekle
import logging

logging.basicConfig(
    filename='finwise.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 8.2 Stripe Webhook Handling

```python
@app.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError:
        return {}, 400
    except stripe.error.SignatureVerificationError:
        return {}, 400
    
    # Handle event
    if event['type'] == 'charge.succeeded':
        # Process successful charge
        pass
    elif event['type'] == 'charge.failed':
        # Process failed charge
        pass
    
    return {'status': 'success'}, 200
```

---

## 🚀 9. DEPLOYMENT KONTROL LİSTESİ

- [ ] PostgreSQL kurulmuş ve çalışıyor
- [ ] Database oluşturulmuş ve tables başlatılmış
- [ ] Stripe hesabı oluşturulmuş
- [ ] API Keys `.env` dosyasına eklemiş
- [ ] API routes Flask'a entegre edilmiş
- [ ] Frontend templates `templates/` dizininde
- [ ] CORS ayarları yapılmış
- [ ] SSL sertifikası oluşturulmuş (production)
- [ ] Logging konfigürasyonu tamamlanmış
- [ ] Webhook testi başarılı
- [ ] End-to-end test yapılmış
- [ ] Database backup prosedürü tanımlanmış

---

## 📞 QUICK START COMMANDS

```bash
# 1. Dependencies yükle
pip install -r requirements_full.txt

# 2. Environment ayarla
echo "DATABASE_URL=postgresql://finwise_user:password@localhost/finwise" > .env
echo "STRIPE_API_KEY=sk_test_..." >> .env

# 3. Database başlat
python -c "from database_models import init_db; init_db()"

# 4. Flask sunucusu başlat
python app_v2_secure.py

# 5. Tarayıcıda aç
# http://localhost:5000/templates/application.html
```

---

## ✅ İŞLEM ÖZETİ

| Bileşen | Dosya | Durum | Açıklama |
|---------|-------|-------|----------|
| **Veritabanı** | `database_models.py` | ✅ Tamamlandı | PostgreSQL ORM, 8 tablo |
| **Ödeme** | `payment_processor_v2.py` | ✅ Tamamlandı | Stripe entegrasyonu |
| **API** | `api_routes.py` | ✅ Tamamlandı | 9 yeni endpoint |
| **Frontend** | `templates/application.html` | ✅ Tamamlandı | Kredi başvuru formu |
| **Frontend** | `templates/dashboard.html` | ✅ Tamamlandı | Müşteri paneli |
| **Config** | `.env` | ⏳ Gerekli | Environment variables |
| **Integration** | `app_v2_secure.py` | 🔄 Güncellenecek | Routes eklenecek |

---

**Sonraki Adımlar:**
1. ✅ PostgreSQL & Stripe kurup `.env` dosyasını doldur
2. ✅ API routes'larını Flask'a entegre et
3. ✅ Frontend'i test et (http://localhost:5000/templates/application.html)
4. ✅ End-to-end test yap (başvuru → onay → ödeme planı → ödeme)
5. ✅ Production deployment'a hazırla
