# ⚠️ **Yasal Uyarı / Disclaimer**

Bu proje **sadece eğitim ve araştırma amaçlı** paylaşılmıştır. Gerçek finansal kararlar, kredi başvuruları veya ticari uygulamalar için **kullanılamaz**. Proje kapsamında kullanılan tüm veri setleri anonimleştirilmiş, kamuya açık veya sentetiktir; **kişisel veri** veya gerçek müşteri bilgisi içermez. Proje, herhangi bir kurum veya kuruluşun ticari ürününü temsil etmez. Kullanımdan doğabilecek herhangi bir zarardan yazar(lar) sorumlu değildir.

This project is **for educational and research purposes only**. It must not be used for real financial decisions, credit applications, or commercial deployment. All datasets are anonymized, public, or synthetic; **no personal or customer data** is included. The project does not represent any commercial product. The author(s) are **not liable** for any damages arising from use.

Lisans: MIT — Ayrıntılar için LICENSE dosyasına bakınız.

# 🏦 Kredi Risk Analizi Sistemi

Yapay zeka destekli otomatik kredi başvuru değerlendirme sistemi. Müşterilerin girdiği bilgilere göre kredi onay/red kararı verir.

## 📋 Özellikler

- ✅ Yapay zeka tabanlı kredi risk analizi
- 🎯 %93 doğruluk oranı
- 💻 Modern web arayüzü
- 🔄 Gerçek zamanlı değerlendirme
- 📊 Detaylı performans grafikleri
- 🌐 REST API desteği

## 🚀 Kurulum

### 1. Gerekli Kütüphaneleri Yükleyin

```bash
pip install pandas scikit-learn matplotlib seaborn flask flask-cors pickle-mixin
```

### 2. Modeli Eğitin

```bash
python kredi_basvuru_sistemi.py
```

- Menüden **2** seçeneğini seçin (Modeli yeniden eğit)
- Model otomatik olarak eğitilecek ve kaydedilecektir
- Eğitim sonunda performans grafikleri gösterilecektir

### 3. Web Sunucusunu Başlatın

```bash
python app.py
```

### 4. Tarayıcıdan Erişin

Tarayıcınızda şu adresi açın:
```
http://localhost:5000
```

## 📱 Kullanım

### Web Arayüzü ile

1. Tarayıcıda `http://localhost:5000` adresini açın
2. Formu doldurun:
   - **Kişisel Bilgiler:** Yaş, gelir, iş deneyimi
   - **Kredi Bilgileri:** Kredi miktarı, faiz oranı
   - **Finansal Geçmiş:** Kredi notu, önceki temerrüt
3. "Başvuruyu Değerlendir" butonuna tıklayın
4. Anında sonuç alın!

### Komut Satırı ile

```bash
python kredi_basvuru_sistemi.py
```

- Menüden **1** seçeneğini seçin (Mevcut modeli kullan)
- Müşteri bilgilerini girin
- Sistem kredi değerlendirmesini gösterecektir

### API ile

**Endpoint:** `POST http://localhost:5000/degerlendir`

**Request Body:**
```json
{
    "person_age": 30,
    "person_income": 50000,
    "person_emp_length": 5,
    "loan_amnt": 10000,
    "loan_int_rate": 7.5,
    "loan_percent_income": 0.2,
    "cb_person_cred_hist_length": 8,
    "person_home_ownership": "RENT",
    "loan_intent": "PERSONAL",
    "loan_grade": "B",
    "cb_person_default_on_file": "N"
}
```

**Response:**
```json
{
    "tahmin": "ONAYLANDI",
    "onay_olasiligi": 0.92,
    "red_olasiligi": 0.08
}
```

### AI Risk Assistant (Yeni)

Risk analistleri icin dogal dil aciklama endpoint'leri:

- `POST /api/v2/ai-risk-explanation`
- `POST /api/v2/fairness-summary`
- `POST /api/v2/ai-risk-assistant`

#### Hizli Ortam Ayari

`.env` dosyaniza asagidaki alanlari ekleyin (veya `.env.example` kopyalayin):

```env
AI_ASSISTANT_PROVIDER=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```

Notlar:

- `AI_ASSISTANT_PROVIDER` bos birakilirsa sistem deterministic (yerel) modda calisir.
- `AI_ASSISTANT_PROVIDER=openai` veya `AI_ASSISTANT_PROVIDER=anthropic` secilirse ilgili API key ile LLM modu aktif olur.

#### Ornek Istek (`/api/v2/ai-risk-assistant`)

```json
{
   "question": "Why was this loan rejected?",
   "application_id": 123,
   "fairness_context": {
      "disparate_impact_ratio": 0.79,
      "demographic_parity_difference": 0.09,
      "equal_opportunity_difference": 0.07
   }
}
```

## 📊 Model Detayları

- **Algoritma:** Random Forest Classifier
- **Doğruluk:** %93.03
- **Veri Seti:** Credit Risk Dataset
- **Özellik Sayısı:** 20+
- **Eğitim/Test Oranı:** 70/30

### Değerlendirilen Faktörler

1. **Demografik Bilgiler**
   - Yaş
   - Gelir seviyesi
   - İş deneyimi

2. **Kredi Bilgileri**
   - Talep edilen miktar
   - Faiz oranı
   - Kredi/gelir oranı

3. **Finansal Geçmiş**
   - Kredi notu (A-G)
   - Kredi geçmişi uzunluğu
   - Önceki temerrüt kaydı

4. **Diğer Faktörler**
   - Ev sahipliği durumu
   - Kredi amacı

## 📁 Dosya Yapısı

```
ML Projem/
├── Credit_Risk_Analysis.py          # Orijinal analiz dosyası
├── kredi_basvuru_sistemi.py        # Ana sistem (CLI)
├── app.py                          # Flask web sunucusu
├── index.html                      # Web arayüzü
├── credit_risk_dataset.csv         # Eğitim verisi
├── kredi_risk_model.pkl           # Eğitilmiş model
├── feature_columns.pkl            # Özellik sütunları
└── README.md                       # Bu dosya
```

## 🎯 Örnek Senaryolar

### Senaryo 1: Başarılı Başvuru
- **Yaş:** 35
- **Gelir:** $80,000
- **İş Deneyimi:** 10 yıl
- **Kredi Miktarı:** $15,000
- **Kredi Notu:** A
- **Sonuç:** ✅ ONAYLANDI (%95 olasılık)

### Senaryo 2: Riskli Başvuru
- **Yaş:** 22
- **Gelir:** $25,000
- **İş Deneyimi:** 1 yıl
- **Kredi Miktarı:** $30,000
- **Kredi Notu:** E
- **Geçmiş Temerrüt:** Evet
- **Sonuç:** ❌ REDDEDİLDİ (%78 olasılık)

## 🔧 Teknik Gereksinimler

- Python 3.7+
- 2GB RAM (minimum)
- İnternet bağlantısı (kurulum için)

## 🐛 Sorun Giderme

### Model Bulunamadı Hatası
```bash
python kredi_basvuru_sistemi.py
# Menüden 2'yi seçip modeli eğitin
```

### Flask Kurulu Değil
```bash
pip install flask flask-cors
```

### Grafik Görünmüyor
```bash
pip install matplotlib seaborn
```

### Port Zaten Kullanımda
`app.py` dosyasında port numarasını değiştirin:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

## 📈 Model Performansı

| Metrik | Değer |
|--------|-------|
| Doğruluk | %93.03 |
| Precision (Onaylanan) | %93 |
| Recall (Onaylanan) | %99 |
| F1-Score (Onaylanan) | %96 |
| Precision (Reddedilen) | %96 |
| Recall (Reddedilen) | %72 |
| F1-Score (Reddedilen) | %82 |

## 🔐 Güvenlik Notları

- Bu sistem demo amaçlıdır
- Gerçek üretim ortamında ek güvenlik önlemleri alınmalıdır
- Müşteri verileri şifrelenmeli ve güvenli saklanmalıdır
- GDPR ve yerel veri koruma yasalarına uyulmalıdır

## 📝 Lisans

Bu proje eğitim amaçlıdır.

## 👨‍💻 Geliştirici

Berat - Machine Learning Project

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/yeniOzellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik eklendi'`)
4. Branch'inizi push edin (`git push origin feature/yeniOzellik`)
5. Pull Request oluşturun

## 📞 İletişim

Sorularınız için issue açabilirsiniz.

---

⭐ Projeyi beğendiyseniz yıldız vermeyi unutmayın!
