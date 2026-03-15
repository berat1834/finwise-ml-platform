#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple API Test - No Unicode Issues
"""
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

print("\n" + "="*60)
print("FinWise API Test - Simple Version")
print("="*60 + "\n")

# Test 1: Health
print("[1] Testing /health endpoint...")
try:
    r = requests.get(f"{BASE_URL}/health")
    print(f"    Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"    Model: {data.get('model')}")
        print(f"    Database: {data.get('database')}")
        print(f"    OK\n")
    else:
        print(f"    ERROR: {r.text}\n")
except Exception as e:
    print(f"    FAILED: {e}\n")

# Test 2: Register
print("[2] Testing /api/v2/register...")
try:
    payload = {
        "username": "testuser",
        "password": "testpass123",
        "email": "test@finwise.local"
    }
    r = requests.post(f"{BASE_URL}/api/v2/register", json=payload)
    print(f"    Status: {r.status_code}")
    if r.status_code in [201, 200]:
        print(f"    OK - User registered\n")
    else:
        print(f"    Response: {r.text}\n")
except Exception as e:
    print(f"    FAILED: {e}\n")

# Test 3: Login
print("[3] Testing /api/v2/login...")
try:
    payload = {
        "username": "admin",
        "password": "admin123"
    }
    r = requests.post(f"{BASE_URL}/api/v2/login", json=payload)
    print(f"    Status: {r.status_code}")
    if r.status_code == 200:
        token = r.json().get('access_token')
        print(f"    Token: {token[:20]}...")
        print(f"    OK\n")
    else:
        print(f"    ERROR: {r.text}\n")
        token = None
except Exception as e:
    print(f"    FAILED: {e}\n")
    token = None

# Test 4: Evaluate (with preprocessing)
print("[4] Testing /api/v2/evaluate (WITH PREPROCESSING)...")
if token:
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
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
        }
        r = requests.post(f"{BASE_URL}/api/v2/evaluate", json=payload, headers=headers)
        print(f"    Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"    Decision: {data.get('decision')}")
            print(f"    Risk Probability: {data.get('risk_probability'):.4f}")
            print(f"    Processing Time: {data.get('processing_time_ms')} ms")
            print(f"    OK\n")
        else:
            print(f"    ERROR: {r.text}\n")
    except Exception as e:
        print(f"    FAILED: {e}\n")
        import traceback
        traceback.print_exc()
else:
    print("    SKIPPED: No token available\n")

# Test 5: Get Applications
print("[5] Testing /api/v2/applications...")
if token:
    try:
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(f"{BASE_URL}/api/v2/applications", headers=headers)
        print(f"    Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"    Total: {data.get('count')} applications")
            print(f"    OK\n")
        else:
            print(f"    ERROR: {r.text}\n")
    except Exception as e:
        print(f"    FAILED: {e}\n")
else:
    print("    SKIPPED: No token available\n")

# Test 6: Stats
print("[6] Testing /api/v2/stats...")
if token:
    try:
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(f"{BASE_URL}/api/v2/stats", headers=headers)
        print(f"    Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"    Total processed: {data.get('stats', {}).get('total', 0)}")
            print(f"    OK\n")
        else:
            print(f"    ERROR: {r.text}\n")
    except Exception as e:
        print(f"    FAILED: {e}\n")
else:
    print("    SKIPPED: No token available\n")

print("="*60)
print("Test Complete")
print("="*60)
