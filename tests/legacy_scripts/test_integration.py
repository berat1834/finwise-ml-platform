#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FinWise-ML Integration Test Suite
Kredi baÅŸvurusu, Ã¶deme ve veritabanÄ± iÅŸlemlerini test et
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = 'http://localhost:5000'
COLORS = {
    'GREEN': '\033[92m',
    'RED': '\033[91m',
    'BLUE': '\033[94m',
    'YELLOW': '\033[93m',
    'END': '\033[0m'
}

def test_header(title):
    """Print test header"""
    print(f"\n{'='*60}")
    print(f"{COLORS['BLUE']}â–¶ {title}{COLORS['END']}")
    print(f"{'='*60}")

def test_pass(message):
    """Print passing test"""
    print(f"{COLORS['GREEN']}âœ“ {message}{COLORS['END']}")

def test_fail(message):
    """Print failing test"""
    print(f"{COLORS['RED']}âœ— {message}{COLORS['END']}")

def test_info(message):
    """Print info"""
    print(f"{COLORS['YELLOW']}â„¹ {message}{COLORS['END']}")

# ========================
# TEST 1: Server Health
# ========================
def test_server_health():
    """Check if Flask server is running"""
    test_header("Test 1: Server Health Check")
    
    try:
        response = requests.get(f'{BASE_URL}/', timeout=2)
        test_pass(f"Server is running (Status: {response.status_code})")
        return True
    except requests.exceptions.ConnectionError:
        test_fail(f"Cannot connect to server at {BASE_URL}")
        test_info("Make sure Flask server is running: python app_v2_secure.py")
        return False
    except Exception as e:
        test_fail(f"Server health check failed: {str(e)}")
        return False

# ========================
# TEST 2: Frontend Accessibility
# ========================
def test_frontend_access():
    """Check if frontend templates are accessible"""
    test_header("Test 2: Frontend Accessibility")
    
    templates = [
        '/templates/application.html',
        '/templates/dashboard.html'
    ]
    
    for template in templates:
        try:
            response = requests.get(f'{BASE_URL}{template}', timeout=5)
            if response.status_code == 200:
                test_pass(f"Frontend accessible: {template}")
            else:
                test_fail(f"Template not found: {template} (Status: {response.status_code})")
        except Exception as e:
            test_fail(f"Cannot access {template}: {str(e)}")

# ========================
# TEST 3: Model Prediction
# ========================
def test_model_prediction():
    """Test if ML model can make predictions"""
    test_header("Test 3: Model Prediction")
    
    try:
        import joblib
        import numpy as np
        import json
        
        # Load model
        model = joblib.load('production_model.joblib')
        test_pass("Model loaded successfully")
        
        # Test prediction
        features = np.array([[150000, 50000, 24, 3]])  # income, amount, months, quintile
        prediction = model.predict_proba(features)
        test_pass(f"Model prediction successful: {prediction[0][1]:.4f}")
        
        # Load threshold from metadata
        with open('production_model_meta.json', 'r', encoding='utf-8') as f:
            threshold = float(json.load(f).get('threshold', 0.5))
        test_pass(f"Decision threshold loaded: {threshold:.4f}")
        
        return True
    except Exception as e:
        test_fail(f"Model prediction failed: {str(e)}")
        return False

# ========================
# TEST 4: Database Connection
# ========================
def test_database():
    """Test PostgreSQL connection"""
    test_header("Test 4: Database Connection")
    
    try:
        from database_models import get_db_session, Customer
        
        session = get_db_session()
        test_pass("Database connection successful")
        
        # Try to query
        count = session.query(Customer).count()
        test_pass(f"Database query successful (Customers: {count})")
        
        session.close()
        return True
    except ImportError:
        test_fail("database_models.py not found")
        return False
    except Exception as e:
        test_fail(f"Database connection failed: {str(e)}")
        test_info("Make sure PostgreSQL is running and DATABASE_URL is set in .env")
        return False

# ========================
# TEST 5: Credit Application API
# ========================
def test_credit_application():
    """Test credit application endpoint"""
    test_header("Test 5: Credit Application API")
    
    application_data = {
        'full_name': 'Ahmet Test YÄ±lmaz',
        'email': f'test_{int(time.time())}@example.com',
        'phone': '+90 555 123 4567',
        'date_of_birth': '1990-05-15',
        'national_id': '12345678901',
        'employment_status': 'employed',
        'annual_income': 150000,
        'requested_amount': 50000,
        'requested_term_months': 24,
        'purpose': 'home'
    }
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/v2/apply',
            json=application_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            test_pass(f"Application submitted successfully")
            test_info(f"Decision: {result.get('decision')}")
            test_info(f"Probability: {result.get('probability', 0):.4f}")
            
            if result.get('decision') == 'approved':
                test_info(f"Approved Amount: â‚º{result.get('approved_amount', 0):,.0f}")
                test_info(f"Monthly Payment: â‚º{result.get('monthly_payment', 0):,.2f}")
            
            return True
        else:
            test_fail(f"Application API returned status {response.status_code}")
            test_info(f"Response: {response.json()}")
            return False
    except Exception as e:
        test_fail(f"Credit application test failed: {str(e)}")
        return False

# ========================
# TEST 6: Model Fairness
# ========================
def test_model_fairness():
    """Test if model meets fairness compliance"""
    test_header("Test 6: Model Fairness Check")
    
    try:
        import json
        
        with open('deployment_config.json', 'r') as f:
            config = json.load(f)
        
        di_ratio = config.get('di_ratio')
        auc = config.get('auc')
        
        test_info(f"DI Ratio: {di_ratio:.4f}")
        test_info(f"AUC-ROC: {auc:.4f}")
        
        if di_ratio >= 0.76:
            test_pass(f"âœ“ Disparate Impact compliance: {di_ratio:.4f} (â‰¥0.76)")
        else:
            test_fail(f"âœ— DI Ratio below threshold: {di_ratio:.4f}")
        
        if auc >= 0.89:
            test_pass(f"âœ“ Model performance: AUC {auc:.4f} (â‰¥0.89)")
        else:
            test_fail(f"âœ— AUC below expected: {auc:.4f}")
        
        return True
    except Exception as e:
        test_fail(f"Fairness check failed: {str(e)}")
        return False

# ========================
# TEST 7: API Response Format
# ========================
def test_api_response_format():
    """Test API response structure"""
    test_header("Test 7: API Response Format")
    
    application_data = {
        'full_name': 'Test User',
        'email': f'format_test_{int(time.time())}@example.com',
        'national_id': '12345678902',
        'annual_income': 100000,
        'requested_amount': 30000,
        'requested_term_months': 12
    }
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/v2/apply',
            json=application_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Check required fields
            required_fields = ['decision', 'probability', 'application_id']
            for field in required_fields:
                if field in result:
                    test_pass(f"Response contains '{field}'")
                else:
                    test_fail(f"Response missing '{field}'")
            
            return True
        else:
            return False
    except Exception as e:
        test_fail(f"Response format test failed: {str(e)}")
        return False

# ========================
# Main Test Runner
# ========================
def main():
    """Run all tests"""
    print(f"\n{COLORS['BLUE']}{'='*60}")
    print(f"FinWise-ML Integration Test Suite")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{COLORS['END']}\n")
    
    results = {
        'Server Health': test_server_health(),
        'Frontend Access': test_frontend_access(),
        'Model Prediction': test_model_prediction(),
        'Database': test_database(),
        'Credit Application API': test_credit_application(),
        'Model Fairness': test_model_fairness(),
        'API Response Format': test_api_response_format()
    }
    
    # Summary
    print(f"\n{COLORS['BLUE']}{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}{COLORS['END']}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{COLORS['GREEN']}âœ“ PASS{COLORS['END']}" if result else f"{COLORS['RED']}âœ— FAIL{COLORS['END']}"
        print(f"{status} - {test_name}")
    
    print(f"\n{COLORS['BLUE']}Total: {passed}/{total} tests passed{COLORS['END']}")
    
    if passed == total:
        print(f"{COLORS['GREEN']}âœ“ All tests passed! Ready for production.{COLORS['END']}\n")
    else:
        print(f"{COLORS['YELLOW']}âš  Some tests failed. Check configuration above.{COLORS['END']}\n")

if __name__ == '__main__':
    main()

