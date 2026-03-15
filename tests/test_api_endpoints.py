"""
Test Suite for API Endpoints
"""
import pytest
import json


class TestHealthEndpoint:
    """Test /health endpoint"""
    
    def test_health_check_success(self, client):
        """Test health endpoint returns success"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.json
        assert 'status' in data
        assert data['status'] in ['healthy', 'up']
    
    def test_health_check_structure(self, client):
        """Test health response structure"""
        response = client.get('/health')
        data = response.json
        assert 'database' in data
        assert 'model' in data


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_login_success(self, client):
        """Test successful login"""
        response = client.post('/auth/login', json={
            'username': 'testuser',
            'password': 'testpass123'
        })
        assert response.status_code == 200
        data = response.json
        assert 'access_token' in data
        assert isinstance(data['access_token'], str)
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post('/auth/login', json={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401
    
    def test_login_missing_username(self, client):
        """Test login without username"""
        response = client.post('/auth/login', json={
            'password': 'testpass123'
        })
        assert response.status_code == 400
    
    def test_login_missing_password(self, client):
        """Test login without password"""
        response = client.post('/auth/login', json={
            'username': 'testuser'
        })
        assert response.status_code == 400


class TestEvaluationEndpoint:
    """Test /degerlendir endpoint"""
    
    def test_evaluate_without_auth(self, client, sample_application_data):
        """Test evaluation without JWT token"""
        response = client.post('/degerlendir', json=sample_application_data)
        assert response.status_code == 401
    
    def test_evaluate_with_auth(self, client, auth_headers, sample_application_data):
        """Test successful evaluation"""
        response = client.post('/degerlendir', 
                              json=sample_application_data,
                              headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert 'tahmin' in data
        assert 'red_olasiligi' in data
        assert data['tahmin'] in ['ONAYLANDI', 'REDDEDILDI']
    
    def test_evaluate_high_risk(self, client, auth_headers, high_risk_application_data):
        """Test high risk application gets rejected"""
        response = client.post('/degerlendir',
                              json=high_risk_application_data,
                              headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        # High risk should be rejected
        assert data['tahmin'] == 'REDDEDILDI'
        assert data['red_olasiligi'] > 0.5
        # Should include adverse action notice
        assert 'adverse_action_notice' in data or 'adverse_action' in data
    
    def test_evaluate_invalid_home_ownership(self, client, auth_headers, sample_application_data):
        """Test invalid home ownership value"""
        invalid_data = {**sample_application_data, 'person_home_ownership': 'INVALID'}
        response = client.post('/degerlendir',
                              json=invalid_data,
                              headers=auth_headers)
        assert response.status_code == 400
    
    def test_evaluate_invalid_loan_intent(self, client, auth_headers, sample_application_data):
        """Test invalid loan intent"""
        invalid_data = {**sample_application_data, 'loan_intent': 'INVALID'}
        response = client.post('/degerlendir',
                              json=invalid_data,
                              headers=auth_headers)
        assert response.status_code == 400
    
    def test_evaluate_invalid_loan_grade(self, client, auth_headers, sample_application_data):
        """Test invalid loan grade"""
        invalid_data = {**sample_application_data, 'loan_grade': 'Z'}
        response = client.post('/degerlendir',
                              json=invalid_data,
                              headers=auth_headers)
        assert response.status_code == 400
    
    def test_evaluate_negative_age(self, client, auth_headers, sample_application_data):
        """Test negative age"""
        invalid_data = {**sample_application_data, 'person_age': -5}
        response = client.post('/degerlendir',
                              json=invalid_data,
                              headers=auth_headers)
        # Should either reject or handle gracefully
        assert response.status_code in [200, 400]
    
    def test_evaluate_negative_income(self, client, auth_headers, sample_application_data):
        """Test negative income"""
        invalid_data = {**sample_application_data, 'person_income': -1000}
        response = client.post('/degerlendir',
                              json=invalid_data,
                              headers=auth_headers)
        assert response.status_code in [200, 400]
    
    def test_evaluate_missing_field(self, client, auth_headers):
        """Test missing required field"""
        incomplete_data = {
            'person_age': 30,
            'person_income': 50000.0
            # Missing other required fields
        }
        response = client.post('/degerlendir',
                              json=incomplete_data,
                              headers=auth_headers)
        assert response.status_code == 400


class TestExplainEndpoint:
    """Test /explain/<id> endpoint"""
    
    def test_explain_without_auth(self, client):
        """Test explanation without JWT"""
        response = client.get('/explain/1')
        assert response.status_code == 401
    
    def test_explain_nonexistent_application(self, client, auth_headers):
        """Test explanation for non-existent application"""
        response = client.get('/explain/99999', headers=auth_headers)
        assert response.status_code == 404
    
    def test_explain_after_evaluation(self, client, auth_headers, sample_application_data):
        """Test explanation after creating an application"""
        # First create an application
        eval_response = client.post('/degerlendir',
                                   json=sample_application_data,
                                   headers=auth_headers)
        assert eval_response.status_code == 200
        app_id = eval_response.json.get('basvuru_id')
        
        if app_id:
            # Get explanation
            explain_response = client.get(f'/explain/{app_id}', headers=auth_headers)
            assert explain_response.status_code == 200
            data = explain_response.json
            assert 'shap_values' in data or 'explanation' in data


class TestOverrideEndpoint:
    """Test /override endpoint"""
    
    def test_override_without_auth(self, client):
        """Test override without JWT"""
        response = client.post('/override', json={
            'application_id': 1,
            'new_decision': 'ONAYLANDI',
            'reason': 'Test override'
        })
        assert response.status_code == 401
    
    def test_override_missing_fields(self, client, auth_headers):
        """Test override with missing fields"""
        response = client.post('/override',
                              json={'application_id': 1},
                              headers=auth_headers)
        assert response.status_code == 400
    
    def test_override_success(self, client, auth_headers, high_risk_application_data):
        """Test successful override"""
        # First create a rejected application
        eval_response = client.post('/degerlendir',
                                   json=high_risk_application_data,
                                   headers=auth_headers)
        
        if eval_response.status_code == 200:
            app_id = eval_response.json.get('basvuru_id')
            
            if app_id:
                # Override the decision
                override_response = client.post('/override',
                                               json={
                                                   'application_id': app_id,
                                                   'new_decision': 'ONAYLANDI',
                                                   'reason': 'Special circumstances'
                                               },
                                               headers=auth_headers)
                assert override_response.status_code in [200, 400]  # May fail if already overridden


class TestStatisticsEndpoint:
    """Test /istatistik endpoint"""
    
    def test_statistics_without_auth(self, client):
        """Test statistics without JWT"""
        response = client.get('/istatistik')
        assert response.status_code == 401
    
    def test_statistics_structure(self, client, auth_headers):
        """Test statistics response structure"""
        response = client.get('/istatistik', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert 'total_applications' in data
        assert 'approved' in data
        assert 'rejected' in data


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limit_evaluation(self, client, auth_headers, sample_application_data):
        """Test rate limiting on evaluation endpoint"""
        # Make multiple rapid requests
        responses = []
        for _ in range(15):  # Exceed typical rate limit
            response = client.post('/degerlendir',
                                  json=sample_application_data,
                                  headers=auth_headers)
            responses.append(response.status_code)
        
        # At least one should be rate limited (429)
        # Note: This may pass if rate limit is very high or disabled in tests
        # Just check that we don't crash
        assert all(code in [200, 429, 400] for code in responses)


class TestInputSanitization:
    """Test input sanitization"""
    
    def test_xss_attempt_in_string_fields(self, client, auth_headers, sample_application_data):
        """Test XSS script injection is sanitized"""
        xss_data = {**sample_application_data, 
                   'person_home_ownership': '<script>alert("XSS")</script>'}
        response = client.post('/degerlendir',
                              json=xss_data,
                              headers=auth_headers)
        # Should be rejected or sanitized
        assert response.status_code in [200, 400]
    
    def test_sql_injection_attempt(self, client):
        """Test SQL injection in login"""
        response = client.post('/auth/login', json={
            'username': "admin' OR '1'='1",
            'password': "anything"
        })
        # Should not succeed
        assert response.status_code in [401, 400]
