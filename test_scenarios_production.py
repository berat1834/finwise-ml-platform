#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Multiple Scenarios
"""
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

# Get login token first
print("\n[*] Logging in...")
login_payload = {"username": "admin", "password": "admin123"}
r = requests.post(f"{BASE_URL}/api/v2/login", json=login_payload)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"[✓] Token acquired: {token[:40]}...\n")

# Test scenarios
scenarios = [
    {
        "name": "Young Professional - Low Risk",
        "data": {
            "person_age": 28,
            "person_income": 85000,
            "person_emp_length": 5,
            "loan_amnt": 12000,
            "loan_int_rate": 4.5,
            "loan_percent_income": 0.14,
            "cb_person_cred_hist_length": 8,
            "person_home_ownership": "RENT",
            "loan_intent": "PERSONAL",
            "loan_grade": "A",
            "cb_person_default_on_file": "N"
        }
    },
    {
        "name": "High Income - Low Risk",
        "data": {
            "person_age": 45,
            "person_income": 150000,
            "person_emp_length": 15,
            "loan_amnt": 20000,
            "loan_int_rate": 3.5,
            "loan_percent_income": 0.13,
            "cb_person_cred_hist_length": 18,
            "person_home_ownership": "OWN",
            "loan_intent": "HOMEIMPROVEMENT",
            "loan_grade": "A",
            "cb_person_default_on_file": "N"
        }
    },
    {
        "name": "Risky Profile - High Risk",
        "data": {
            "person_age": 35,
            "person_income": 35000,
            "person_emp_length": 2,
            "loan_amnt": 25000,
            "loan_int_rate": 10.5,
            "loan_percent_income": 0.71,
            "cb_person_cred_hist_length": 3,
            "person_home_ownership": "OTHER",
            "loan_intent": "DEBTCONSOLIDATION",
            "loan_grade": "G",
            "cb_person_default_on_file": "Y"
        }
    },
]

print("=" * 70)
print("FINWISE - TEST SCENARIOS")
print("=" * 70)

for i, scenario in enumerate(scenarios, 1):
    print(f"\n[Scenario {i}] {scenario['name']}")
    print("-" * 70)
    
    try:
        r = requests.post(f"{BASE_URL}/api/v2/evaluate", 
                         json=scenario['data'], 
                         headers=headers)
        
        if r.status_code == 200:
            data = r.json()
            print(f"    Decision:     {data['decision']}")
            print(f"    Risk Score:   {data['risk_probability']:.4f} ({data['risk_probability']*100:.2f}%)")
            print(f"    Reason:       {data['decision_reason']}")
            print(f"    App ID:       {data['application_id']}")
            print(f"    Time:         {data['processing_time_ms']} ms")
        else:
            print(f"    ERROR: {r.text}")
    except Exception as e:
        print(f"    FAILED: {e}")

print("\n" + "=" * 70)
print("[✓] Test Complete")
print("=" * 70)
