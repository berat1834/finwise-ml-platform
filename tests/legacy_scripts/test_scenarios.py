#!/usr/bin/env python3
"""Test iki senaryo"""
import requests
import json
import time

API_URL = "http://localhost:5000"

# Login
login_data = {"username": "admin", "password": "admin123"}
login_res = requests.post(f"{API_URL}/auth/login", json=login_data)
token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("\n" + "="*60)
print("SENARYO 3: SINIRLARDA (ÖNCEKİ GİBİ)")
print("="*60)

scenario3 = {
    "person_age": 35,
    "person_income": 100000,
    "person_emp_length": 5,
    "loan_amnt": 5000,
    "loan_int_rate": 5,
    "loan_percent_income": 0.05,
    "cb_person_cred_hist_length": 5,
    "person_home_ownership": "RENT",
    "loan_intent": "PERSONAL",
    "loan_grade": "A",
    "cb_person_default_on_file": "N"
}

res3 = requests.post(f"{API_URL}/degerlendir", json=scenario3, headers=headers).json()
print(f"✅ Karar: {res3['tahmin']}")
print(f"📊 Onay: {res3['onay_olasiligi']:.1f}%")
print(f"📊 Red: {res3['red_olasiligi']:.1f}%")
print(f"🆔 Başvuru ID: {res3['application_id']}")
print(f"🔍 Beklenen: ONAYLANDI")

print("\n" + "="*60)
print("SENARYO 5: UYARILI - GEÇMIŞ TEMERRÜT")
print("="*60)

scenario5 = {
    "person_age": 40,
    "person_income": 80000,
    "person_emp_length": 8,
    "loan_amnt": 15000,
    "loan_int_rate": 20,
    "loan_percent_income": 0.1875,
    "cb_person_cred_hist_length": 10,
    "person_home_ownership": "RENT",
    "loan_intent": "MEDICAL",
    "loan_grade": "C",
    "cb_person_default_on_file": "Y"
}

res5 = requests.post(f"{API_URL}/degerlendir", json=scenario5, headers=headers).json()
print(f"❌ Karar: {res5['tahmin']}")
print(f"📊 Onay: {res5['onay_olasiligi']:.1f}%")
print(f"📊 Red: {res5['red_olasiligi']:.1f}%")
print(f"🆔 Başvuru ID: {res5['application_id']}")
print(f"🔍 Beklenen: REDDEDİLDİ")

if "adverse_action_notice" in res5 and res5["adverse_action_notice"]:
    print("\n🚫 Red Nedenleri:")
    for reason in res5["adverse_action_notice"]["reasons"]:
        print(f"  • {reason}")
    print("\n💡 Öneriler:")
    for rec in res5["adverse_action_notice"]["recommendations"]:
        print(f"  • {rec}")

print("\n" + "="*60)
print("✅ TEST TAMAMLANDI!")
print("="*60 + "\n")
