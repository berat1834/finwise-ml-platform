# ⚡ FinWise API - Quick Reference Card

**Valid from:** 06 Mar 2026  
**Status:** ✅ Production Ready v2.0.0

---

## 🚀 START API

```bash
cd "C:\Users\berat\OneDrive\Masaüstü\FinWise-ML Projem"
.venv\Scripts\python.exe app_api.py
```

**Base URL:** `http://127.0.0.1:5000`

---

## 🔐 QUICK LOGIN

```bash
curl -X POST http://127.0.0.1:5000/api/v2/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**Copy the `access_token` value** for next requests

---

## 💳 EVALUATE CREDIT APPLICATION

```bash
curl -X POST http://127.0.0.1:5000/api/v2/evaluate \
  -H "Authorization: Bearer <TOKEN>" \
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
    "cb_person_default_on_file": "N"
  }'
```

**Response:**
```json
{
  "application_id": "APP-xxx",
  "decision": "APPROVED",
  "risk_probability": 0.2215,
  "decision_reason": "Low risk..."
}
```

---

## 📊 CHECK STATUS

### Health Check
```bash
curl http://127.0.0.1:5000/health
```

### Get Applications
```bash
curl http://127.0.0.1:5000/api/v2/applications \
  -H "Authorization: Bearer <TOKEN>"
```

### Get Stats
```bash
curl http://127.0.0.1:5000/api/v2/stats \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 📁 IMPORTANT FILES

| File | Purpose |
|------|---------|
| `app_api.py` | Main API server |
| `finwise_production.db` | SQLite database |
| `model_production.joblib` | ML Model |
| `API_DOCUMENTATION.md` | Full API docs |
| `LOKAL_DEPLOYMENT_GUIDE.md` | Deployment guide |
| `test_simple.py` | Simple test |
| `test_scenarios_production.py` | Scenario tests |

---

## 🔧 TROUBLESHOOT

| Issue | Solution |
|-------|----------|
| Port 5000 in use | `taskkill /PID <ID> /F` |
| Token expired | Get new token with login |
| Feature mismatch error | Use `test_simple.py` to verify |
| Database error | Delete `finwise_production.db` and restart |

---

## ✅ ENDPOINTS

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/health` | GET | No | Health check |
| `/api/v2/register` | POST | No | Register user |
| `/api/v2/login` | POST | No | Get JWT token |
| `/api/v2/evaluate` | POST | Yes | Evaluate credit risk |
| `/api/v2/applications` | GET | Yes | List applications |
| `/api/v2/stats` | GET | Yes | Get statistics |

---

## 📈 MODEL INFO

- **Type:** RandomForestClassifier (balanced, fairness-aware)
- **AUC Score:** 0.9198
- **Recall:** 77.73%, **Precision:** 73.27%, **F1:** 75.43%
- **Decision Threshold:** 0.24
- **Input Features:** 22 (7 numeric + 15 one-hot categorical)
- **Training Samples:** 22,806

---

## 💡 TIPS

1. Always copy full token from login response
2. Change default password after first use
3. Backup database regularly with `production_setup.py`
4. Monitor fairness metrics (see `FAIRNESS_REMEDIATION_PROGRESS.md`)
5. Set up SSL/HTTPS for production

---

**Need help?** Check `LOKAL_DEPLOYMENT_GUIDE.md` for detailed instructions.

**Test different scenarios:** 
```bash
.venv\Scripts\python.exe test_scenarios_production.py
```
