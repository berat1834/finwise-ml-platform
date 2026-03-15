#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FinWise API Test Suite - Comprehensive API Testing
Tüm endpoints'i test et ve raporla
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    END = '\033[0m'

def log_test(name, status, details=""):
    """Test sonuçlarını yazdır."""
    symbol = f"{Colors.GREEN}✓{Colors.END}" if status else f"{Colors.RED}✗{Colors.END}"
    print(f"{symbol} {name}")
    if details:
        print(f"  └─ {details}")

def test_health_check():
    """Health check endpoint test."""
    print(f"\n{Colors.CYAN}=== 1. HEALTH CHECK ==={Colors.END}")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        success = response.status_code == 200
        log_test("Health endpoint", success, f"Status: {response.status_code}")
        if success:
            data = response.json()
            print(f"  └─ Database: {data.get('database')}")
            print(f"  └─ Model: {data.get('model')}")
            print(f"  └─ API Version: {data.get('api_version')}")
        return success
    except Exception as e:
        log_test("Health check", False, str(e))
        return False

def test_registration():
    """User registration test."""
    print(f"\n{Colors.CYAN}=== 2. USER REGISTRATION ==={Colors.END}")
    try:
        test_user = f"testuser_{int(time.time())}"
        payload = {
            "username": test_user,
            "password": "testpass123",
            "email": f"{test_user}@test.com"
        }
        response = requests.post(
            f"{BASE_URL}/api/v2/register",
            json=payload,
            timeout=5
        )
        success = response.status_code == 201
        log_test("User registration", success, f"Status: {response.status_code}")
        if success:
            print(f"  └─ Username: {test_user}")
        return success, test_user
    except Exception as e:
        log_test("Registration", False, str(e))
        return False, None

def test_login(username=None, password=None):
    """Login and get JWT token."""
    print(f"\n{Colors.CYAN}=== 3. LOGIN & JWT TOKEN ==={Colors.END}")
    try:
        user = username or ADMIN_USER
        pwd = password or ADMIN_PASS
        
        payload = {
            "username": user,
            "password": pwd
        }
        response = requests.post(
            f"{BASE_URL}/api/v2/login",
            json=payload,
            timeout=5
        )
        success = response.status_code == 200
        log_test("Login", success, f"Status: {response.status_code}")
        
        if success:
            data = response.json()
            token = data.get('access_token')
            print(f"  └─ Token (first 30 chars): {token[:30]}...")
            print(f"  └─ Role: {data.get('role')}")
            return True, token
        return False, None
    except Exception as e:
        log_test("Login", False, str(e))
        return False, None

def test_credit_evaluation(token):
    """Credit risk evaluation test."""
    print(f"\n{Colors.CYAN}=== 4. CREDIT EVALUATION ==={Colors.END}")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        test_cases = [
            {
                "name": "Low Risk (Young, High Income)",
                "data": {
                    "customer_id": "CUST-LOW-001",
                    "person_age": 28,
                    "person_income": 100000,
                    "person_emp_length": 10,
                    "loan_amnt": 15000,
                    "loan_int_rate": 5.5,
                    "loan_percent_income": 0.15,
                    "cb_person_cred_hist_length": 20,
                    "person_home_ownership": "OWN",
                    "loan_intent": "PERSONAL",
                    "loan_grade": "A",
                    "cb_person_default_on_file": "N"
                }
            },
            {
                "name": "High Risk (Older, Low Income)",
                "data": {
                    "customer_id": "CUST-HIGH-001",
                    "person_age": 65,
                    "person_income": 30000,
                    "person_emp_length": 2,
                    "loan_amnt": 25000,
                    "loan_int_rate": 12.0,
                    "loan_percent_income": 0.83,
                    "cb_person_cred_hist_length": 5,
                    "person_home_ownership": "RENT",
                    "loan_intent": "DEBT_CONSOLIDATION",
                    "loan_grade": "D",
                    "cb_person_default_on_file": "Y"
                }
            }
        ]
        
        for test_case in test_cases:
            response = requests.post(
                f"{BASE_URL}/api/v2/evaluate",
                json=test_case["data"],
                headers=headers,
                timeout=5
            )
            success = response.status_code == 200
            log_test(f"Evaluation: {test_case['name']}", success)
            
            if success:
                data = response.json()
                print(f"  ├─ Application ID: {data.get('application_id')}")
                print(f"  ├─ Decision: {data.get('decision')}")
                print(f"  ├─ Risk Probability: {data.get('risk_probability'):.2%}")
                print(f"  └─ Processing Time: {data.get('processing_time_ms')}ms")
        
        return True
    except Exception as e:
        log_test("Credit evaluation", False, str(e))
        return False

def test_get_applications(token):
    """Get applications list."""
    print(f"\n{Colors.CYAN}=== 5. GET APPLICATIONS ==={Colors.END}")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/api/v2/applications?limit=10",
            headers=headers,
            timeout=5
        )
        success = response.status_code == 200
        log_test("Get applications", success, f"Status: {response.status_code}")
        
        if success:
            data = response.json()
            print(f"  └─ Total applications: {data.get('count')}")
            if data.get('applications'):
                print(f"  └─ Latest app: {data['applications'][0]['application_id']}")
        
        return success
    except Exception as e:
        log_test("Get applications", False, str(e))
        return False

def test_stats(token):
    """Get statistics."""
    print(f"\n{Colors.CYAN}=== 6. STATISTICS ==={Colors.END}")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/api/v2/stats",
            headers=headers,
            timeout=5
        )
        success = response.status_code == 200
        log_test("Get stats", success, f"Status: {response.status_code}")
        
        if success:
            data = response.json()
            print(f"  ├─ Total applications: {data.get('total_applications')}")
            print(f"  ├─ Approved: {data.get('approved')}")
            print(f"  ├─ Rejected: {data.get('rejected')}")
            print(f"  ├─ Approval rate: {data.get('approval_rate'):.2%}")
            print(f"  └─ Avg processing time: {data.get('avg_processing_time_ms'):.0f}ms")
        
        return success
    except Exception as e:
        log_test("Get stats", False, str(e))
        return False

def test_unauthorized_access():
    """Test unauthorized access without token."""
    print(f"\n{Colors.CYAN}=== 7. UNAUTHORIZED ACCESS ==={Colors.END}")
    try:
        # Try to access protected endpoint without token
        response = requests.get(
            f"{BASE_URL}/api/v2/applications",
            timeout=5
        )
        success = response.status_code == 401  # Should be unauthorized
        log_test("Unauthorized access blocked", success, f"Status: {response.status_code}")
        
        return success
    except Exception as e:
        log_test("Unauthorized test", False, str(e))
        return False

def run_all_tests():
    """Run all tests."""
    print(f"\n{Colors.YELLOW}{'='*60}")
    print(f"FinWise API Test Suite - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{Colors.END}\n")
    
    results = {}
    
    # Test 1: Health
    results['health'] = test_health_check()
    
    if not results['health']:
        print(f"\n{Colors.RED}API is not running. Exiting tests.{Colors.END}")
        return
    
    # Test 2: Registration
    results['registration'], test_user = test_registration()
    
    # Test 3: Login (Admin)
    results['login_admin'], admin_token = test_login()
    
    # Test 4: Credit Evaluation
    if admin_token:
        results['evaluation'] = test_credit_evaluation(admin_token)
    
    # Test 5: Get Applications
    if admin_token:
        results['get_apps'] = test_get_applications(admin_token)
    
    # Test 6: Statistics
    if admin_token:
        results['stats'] = test_stats(admin_token)
    
    # Test 7: Unauthorized Access
    results['unauthorized'] = test_unauthorized_access()
    
    # Summary
    print(f"\n{Colors.YELLOW}{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}{Colors.END}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"{test_name.upper():.<40} {status}")
    
    print(f"\n{Colors.CYAN}Total: {passed}/{total} tests passed{Colors.END}\n")
    
    if passed == total:
        print(f"{Colors.GREEN}✓ All tests passed! API is production-ready.{Colors.END}\n")
    else:
        print(f"{Colors.YELLOW}⚠ Some tests failed. Check the output above.{Colors.END}\n")

if __name__ == "__main__":
    run_all_tests()
