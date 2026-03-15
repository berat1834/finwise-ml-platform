#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compliance Features Test Script
Tests GDPR, Basel, BDDK, Appeals functionality
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def login():
    """Login and get JWT token"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    return response.json()['access_token']

def test_basel_report(token):
    """Test Basel III report generation"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/compliance/reports/basel?days=30", headers=headers)
    print("\n📊 Basel III Report:")
    print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

def test_bddk_report(token):
    """Test BDDK report generation"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/compliance/reports/bddk?days=30", headers=headers)
    print("\n🏦 BDDK Report:")
    print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

def test_gdpr_export(token, user_id=1):
    """Test GDPR data export"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/compliance/gdpr/export/{user_id}", headers=headers)
    print("\n📦 GDPR Data Export:")
    result = response.json()
    print(f"Status: {result.get('status')}")
    print(f"Exported at: {result.get('exported_at')}")
    return response.status_code == 200

def test_gdpr_request(token):
    """Test GDPR request submission"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/compliance/gdpr/request", 
                            headers=headers,
                            json={"request_type": "portability"})
    print("\n📋 GDPR Request:")
    print(json.dumps(response.json(), indent=2))
    return response.status_code == 201

def main():
    print("=" * 60)
    print("COMPLIANCE FEATURES TEST")
    print("=" * 60)
    
    try:
        # Login
        print("\n🔐 Logging in...")
        token = login()
        print("✓ Login successful")
        
        # Test Basel Report
        print("\n" + "=" * 60)
        if test_basel_report(token):
            print("✅ Basel III Report: PASSED")
        else:
            print("❌ Basel III Report: FAILED")
        
        # Test BDDK Report
        print("\n" + "=" * 60)
        if test_bddk_report(token):
            print("✅ BDDK Report: PASSED")
        else:
            print("❌ BDDK Report: FAILED")
        
        # Test GDPR Export
        print("\n" + "=" * 60)
        if test_gdpr_export(token):
            print("✅ GDPR Data Export: PASSED")
        else:
            print("❌ GDPR Data Export: FAILED")
        
        # Test GDPR Request
        print("\n" + "=" * 60)
        if test_gdpr_request(token):
            print("✅ GDPR Request: PASSED")
        else:
            print("❌ GDPR Request: FAILED")
        
        print("\n" + "=" * 60)
        print("✅ ALL COMPLIANCE TESTS COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
