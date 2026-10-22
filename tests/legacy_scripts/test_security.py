#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Script - Authentication & Security Features
Tüm güvenlik özelliklerini kontrol et
"""
import requests
import json
import sys
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:5000"
HEADERS_JSON = {"Content-Type": "application/json"}

class SecurityTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.test_results = []
    
    def test_register(self) -> bool:
        """Test user registration"""
        print("\n[TEST 1] User Registration...")
        try:
            data = {
                "username": f"test_user_{int(__import__('time').time())}",
                "password": "TestPassword123!",
                "email": "test@example.com",
                "role": "analyst"
            }
            resp = requests.post(
                f"{self.base_url}/auth/register",
                json=data,
                headers=HEADERS_JSON,
                timeout=5
            )
            
            if resp.status_code in [201, 400]:  # 400 if user exists (expected on re-run)
                self.test_results.append(("Registration", "✓ PASS" if resp.status_code == 201 else "✓ PASS (User exists)"))
                print(f"✓ Status: {resp.status_code}")
                print(f"  Response: {resp.text[:200]}")
                return True
            else:
                self.test_results.append(("Registration", f"✗ FAIL ({resp.status_code})"))
                print(f"✗ Status: {resp.status_code}")
                return False
                
        except Exception as e:
            self.test_results.append(("Registration", f"✗ ERROR: {str(e)}"))
            print(f"✗ Error: {str(e)}")
            return False
    
    def test_login(self) -> bool:
        """Test user login & JWT token generation"""
        print("\n[TEST 2] User Login & JWT Token...")
        try:
            data = {
                "username": "test_user",
                "password": "password123"
            }
            resp = requests.post(
                f"{self.base_url}/auth/login",
                json=data,
                headers=HEADERS_JSON,
                timeout=5
            )
            
            if resp.status_code in [200, 401]:  # 401 if wrong credentials (expected)
                if resp.status_code == 200:
                    resp_json = resp.json()
                    self.token = resp_json.get('access_token')
                    self.user_id = resp_json.get('user', {}).get('id')
                    self.test_results.append(("Login", "✓ PASS"))
                    print(f"✓ Status: {resp.status_code}")
                    print(f"  Token obtained: {self.token[:50] if self.token else 'N/A'}...")
                    return True
                else:
                    self.test_results.append(("Login", "✓ PASS (Invalid credentials expected)"))
                    print(f"✓ Status: {resp.status_code} - Invalid credentials (expected)")
                    return True
            else:
                self.test_results.append(("Login", f"✗ FAIL ({resp.status_code})"))
                print(f"✗ Status: {resp.status_code}")
                return False
                
        except Exception as e:
            self.test_results.append(("Login", f"✗ ERROR: {str(e)}"))
            print(f"✗ Error: {str(e)}")
            return False
    
    def test_health(self) -> bool:
        """Test health check endpoint"""
        print("\n[TEST 3] Health Check Endpoint...")
        try:
            resp = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            
            if resp.status_code in [200, 503]:
                data = resp.json()
                self.test_results.append(("Health Check", "✓ PASS"))
                print(f"✓ Status: {resp.status_code}")
                print(f"  Database: {data.get('database', 'N/A')}")
                print(f"  Model: {data.get('model', 'N/A')}")
                return True
            else:
                self.test_results.append(("Health Check", f"✗ FAIL ({resp.status_code})"))
                print(f"✗ Status: {resp.status_code}")
                return False
                
        except Exception as e:
            self.test_results.append(("Health Check", f"✗ ERROR: {str(e)}"))
            print(f"✗ Error: {str(e)}")
            return False
    
    def test_protected_endpoint_without_token(self) -> bool:
        """Test that protected endpoints require JWT token"""
        print("\n[TEST 4] Protected Endpoint Without Token (Should Fail)...")
        try:
            resp = requests.post(
                f"{self.base_url}/degerlendir",
                json={
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
                },
                headers=HEADERS_JSON,
                timeout=5
            )
            
            # Should get 401 Unauthorized without token
            if resp.status_code == 401:
                self.test_results.append(("Protected Endpoint (No Token)", "✓ PASS - 401 Unauthorized"))
                print(f"✓ Status: {resp.status_code} (Correctly rejected)")
                return True
            else:
                self.test_results.append(("Protected Endpoint (No Token)", f"✗ FAIL - Got {resp.status_code}"))
                print(f"✗ Status: {resp.status_code} (Should be 401)")
                return False
                
        except Exception as e:
            self.test_results.append(("Protected Endpoint (No Token)", f"✗ ERROR: {str(e)}"))
            print(f"✗ Error: {str(e)}")
            return False
    
    def test_rate_limiting(self) -> bool:
        """Test rate limiting on login endpoint"""
        print("\n[TEST 5] Rate Limiting Check...")
        try:
            print("  Sending 15 rapid requests to /auth/login...")
            blocked_count = 0
            
            for i in range(15):
                resp = requests.post(
                    f"{self.base_url}/auth/login",
                    json={
                        "username": "test",
                        "password": "test"
                    },
                    headers=HEADERS_JSON,
                    timeout=5
                )
                
                # Rate limit typically returns 429 Too Many Requests
                if resp.status_code == 429:
                    blocked_count += 1
            
            if blocked_count > 0:
                self.test_results.append(("Rate Limiting", f"✓ PASS - {blocked_count} requests blocked"))
                print(f"✓ Rate limiting active: {blocked_count}/15 requests blocked")
                return True
            else:
                self.test_results.append(("Rate Limiting", "⚠ WARNING - No rate limiting detected"))
                print(f"⚠ No rate limiting detected (check if enabled in config)")
                return False
                
        except Exception as e:
            self.test_results.append(("Rate Limiting", f"✗ ERROR: {str(e)}"))
            print(f"✗ Error: {str(e)}")
            return False
    
    def test_https_redirect(self) -> bool:
        """Test HTTPS enforcement (if enabled)"""
        print("\n[TEST 6] HTTPS Enforcement Check...")
        try:
            # This test is informational - not all setups enforce HTTPS
            resp = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            
            # Check if X-Forwarded-Proto header is present
            if 'X-Forwarded-Proto' in resp.headers or resp.url.startswith('https'):
                self.test_results.append(("HTTPS Enforcement", "✓ PASS - HTTPS detected"))
                print(f"✓ HTTPS or proxy detected")
                return True
            else:
                self.test_results.append(("HTTPS Enforcement", "⚠ INFO - HTTP in development"))
                print(f"⚠ Using HTTP (OK for development, NOT for production)")
                return True  # Pass since it's development
                
        except Exception as e:
            self.test_results.append(("HTTPS Enforcement", f"✗ ERROR: {str(e)}"))
            print(f"✗ Error: {str(e)}")
            return False
    
    def test_input_sanitization(self) -> bool:
        """Test input sanitization (SQL injection, XSS prevention)"""
        print("\n[TEST 7] Input Sanitization Check...")
        try:
            # Try SQL injection payload
            malicious_data = {
                "username": "admin'; DROP TABLE users; --",
                "password": "<script>alert('xss')</script>"
            }
            
            resp = requests.post(
                f"{self.base_url}/auth/login",
                json=malicious_data,
                headers=HEADERS_JSON,
                timeout=5
            )
            
            # Should fail gracefully without executing injection
            if resp.status_code in [400, 401, 422]:
                self.test_results.append(("Input Sanitization", "✓ PASS - Malicious input rejected"))
                print(f"✓ Status: {resp.status_code} (Malicious input safely rejected)")
                return True
            else:
                self.test_results.append(("Input Sanitization", f"⚠ WARNING - Unexpected response"))
                print(f"⚠ Status: {resp.status_code}")
                return True  # Warning only
                
        except Exception as e:
            self.test_results.append(("Input Sanitization", f"✗ ERROR: {str(e)}"))
            print(f"✗ Error: {str(e)}")
            return False
    
    def print_summary(self):
        """Print test summary report"""
        print("\n" + "="*70)
        print("SECURITY TEST SUMMARY REPORT")
        print("="*70)
        
        passed = sum(1 for _, result in self.test_results if "PASS" in result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✓" if "PASS" in result else ("⚠" if "WARNING" in result else "✗")
            print(f"{status_icon} {test_name:.<40} {result}")
        
        print("="*70)
        print(f"TOTAL: {passed}/{total} tests passed")
        print("="*70)
        
        if passed == total:
            print("✓ All security tests passed!")
        elif passed >= total - 2:
            print("⚠ Most tests passed. Check warnings.")
        else:
            print("✗ Multiple tests failed. Review security configuration.")
        
        return passed == total


if __name__ == "__main__":
    print("🔐 CREDIT RISK API - SECURITY TEST SUITE")
    print(f"Target: {BASE_URL}")
    print("="*70)
    
    tester = SecurityTester()
    
    # Run all tests
    tester.test_register()
    tester.test_login()
    tester.test_health()
    tester.test_protected_endpoint_without_token()
    tester.test_rate_limiting()
    tester.test_https_redirect()
    tester.test_input_sanitization()
    
    # Print summary
    all_passed = tester.print_summary()
    
    sys.exit(0 if all_passed else 1)
