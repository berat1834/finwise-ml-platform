import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'services'))
sys.path.insert(0, os.path.dirname(__file__))

from app.services.fraud_service import FraudService
import json
import requests

base_url = "http://localhost:8000"

# 1. Login to get token
login_res = requests.post(f"{base_url}/auth/login", json={
    "username": "admin",
    "password": "admin"
})
print("Login Response:", login_res.text)

payload = {
    "person_age": 20,
    "person_income": 50000,
    "person_emp_length": 5,
    "loan_amnt": 10000,
    "loan_int_rate": 10,
    "loan_percent_income": 0.2,
    "cb_person_cred_hist_length": 2,
    "person_home_ownership": "RENT",
    "loan_intent": "EDUCATION",
    "loan_grade": "A",
    "cb_person_default_on_file": "N"
}

fraud_analysis = FraudService.evaluate(payload)
print("Fraud Analysis:", json.dumps(fraud_analysis, indent=2))
