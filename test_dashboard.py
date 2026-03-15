#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Dashboard API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def get_token():
    """Login and get JWT token"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json()['access_token']
    return None

def test_dashboard():
    print("=== Testing Dashboard API ===\n")
    
    # Get token
    token = get_token()
    if not token:
        print("❌ Login failed")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test endpoints
    endpoints = [
        ("/dashboard/overview", "Overview Statistics"),
        ("/dashboard/trends", "Daily Trends"),
        ("/dashboard/risk-distribution", "Risk Distribution"),
        ("/dashboard/loan-intent", "Loan Intent Breakdown"),
        ("/dashboard/analysts", "Top Analysts"),
        ("/dashboard/model-performance", "Model Performance"),
        ("/dashboard/appeals", "Appeals Summary"),
        ("/dashboard/financial", "Financial Summary"),
        ("/dashboard/activity", "System Activity")
    ]
    
    for endpoint, name in endpoints:
        print(f"\n📊 Testing: {name}")
        print(f"   Endpoint: {endpoint}")
        
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS")
                print(f"   Data: {json.dumps(data, indent=2)[:500]}...")
            else:
                print(f"   ❌ FAILED: {response.status_code}")
                print(f"   Response: {response.text}")
        
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_dashboard()
