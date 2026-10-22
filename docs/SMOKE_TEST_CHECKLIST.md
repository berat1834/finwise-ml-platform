# FinWise 5 Dakika Smoke Test Checklist (UI + API)

Bu dokuman, lokal ortamda hizli dogrulama icin minimum kontrol adimlarini icerir.

## 1) Hazirlik (30 sn)

- API sunucusu calisiyor olmali:
  - Gorev: Run: app_v2_secure.py (JWT API)
- UI sayfasi tarayicida acik olmali:
  - index_v2.html
- Test kullanicisi:
  - username: admin
  - password: admin123

## 2) UI Smoke Test (2-3 dk)

### 2.1 Login
- Adim: Ustteki auth alanindan admin/admin123 ile giris yap.
- Beklenen:
  - Basarili giris toast'i gorunmeli.
  - Form alani aktif olmali.

### 2.2 Basvuru Degerlendirme
- Adim: Formu ornek verilerle doldur ve degerlendir.
- Ornek veri:
  - person_age: 35
  - person_income: 80000
  - person_emp_length: 10
  - loan_amnt: 15000
  - loan_int_rate: 5.5
  - loan_percent_income: 0.1875
  - cb_person_cred_hist_length: 12
  - person_home_ownership: OWN
  - loan_intent: PERSONAL
  - loan_grade: A
  - cb_person_default_on_file: N
- Beklenen:
  - Sonuc karti acilmali.
  - Application ID gorunmeli.
  - Olasilik barlari 0'dan buyuk deger gostermeli.

### 2.3 AI Chat Soru/Yanit
- Adim: AI Risk Chat bolumunde hazir bir soru tikla veya soru yazip Sor butonuna bas.
- Beklenen:
  - En az 1 chat turn olusmali.
  - Kaynak badge asagidaki tek tip formatlardan biri olmali:
    - Kaynak: Hazir
    - Kaynak: Kural+Model
    - Kaynak: LLM
    - Kaynak: Bilinmiyor

### 2.4 Gecmisi Temizle
- Adim: Gecmisi Temizle butonuna bas.
- Beklenen:
  - Chat listesi temizlenmeli.
  - Placeholder geri gelmeli.
  - Kaynak badge: Kaynak: Hazir

### 2.5 Basvuru Gecis Baglami
- Adim: Yeni bir basvuru degerlendir veya gecmisten farkli bir basvuru ac.
- Beklenen:
  - Sohbet baglami etiketi guncellenmeli.
  - Gecis varsa onceki basvurudan gecis metni gorunmeli.

## 3) API Smoke Test (2 dk)

PowerShell ile proje klasorunde calistir.

### 3.1 Health
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/health" | ConvertTo-Json -Depth 5
```
Beklenen:
- status = up
- version alani dolu

### 3.2 Login ve Token Alma
```powershell
$loginBody = @{ username = "admin"; password = "admin123" } | ConvertTo-Json
$loginRes = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/auth/login" -ContentType "application/json" -Body $loginBody
$token = $loginRes.access_token
$token
```
Beklenen:
- access_token donmeli

### 3.3 /degerlendir
```powershell
$headers = @{ Authorization = "Bearer $token" }
$evalBody = @{
  person_age = 35
  person_income = 80000
  person_emp_length = 10
  loan_amnt = 15000
  loan_int_rate = 5.5
  loan_percent_income = 0.1875
  cb_person_cred_hist_length = 12
  person_home_ownership = "OWN"
  loan_intent = "PERSONAL"
  loan_grade = "A"
  cb_person_default_on_file = "N"
} | ConvertTo-Json

$evalRes = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/degerlendir" -Headers $headers -ContentType "application/json" -Body $evalBody
$evalRes | ConvertTo-Json -Depth 6
```
Beklenen:
- application_id dolu
- tahmin veya decision dolu
- onay_olasiligi ve red_olasiligi alanlari mevcut

### 3.4 /api/v2/ai-risk-assistant
```powershell
$assistantBody = @{
  application_id = $evalRes.application_id
  question = "Why was this decision made?"
  fairness_context = @{
    disparate_impact_ratio = 0.79
    demographic_parity_difference = 0.09
    equal_opportunity_difference = 0.07
  }
} | ConvertTo-Json -Depth 6

$assistantRes = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/v2/ai-risk-assistant" -Headers $headers -ContentType "application/json" -Body $assistantBody
$assistantRes | ConvertTo-Json -Depth 6
```
Beklenen:
- answer dolu
- answer_type dolu
- evidence listesi donmeli (bos olabilir ama alan bulunmali)

## 4) Pass/Fail Kriteri

PASS:
- Tum UI adimlari beklenen sonucla calisir.
- Tum API adimlari 2xx doner ve kritik alanlar doludur.

FAIL:
- Login/token alinamaz.
- /degerlendir veya AI assistant 4xx/5xx doner.
- UI chat temizleme veya baglam etiketi beklenen sekilde guncellenmez.
