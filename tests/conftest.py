"""
Pytest Configuration and Shared Fixtures
"""
import pytest
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app_v2_secure import app as flask_app, db
from models import User, Application, ManualOverride, AuditLog
from werkzeug.security import generate_password_hash
import tempfile


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    # Use in-memory SQLite for tests
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['JWT_SECRET_KEY'] = 'test-secret-key'
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['RATELIMIT_ENABLED'] = False
    
    # Create tables
    with flask_app.app_context():
        db.create_all()
        
        # Create test user
        test_user = User(
            username='testuser',
            email='test@example.com',
            password_hash=generate_password_hash('testpass123'),
            role='analyst'
        )
        admin_user = User(
            username='admin_test',
            email='admin_test@example.com',
            password_hash=generate_password_hash('AdminPass123'),
            role='admin'
        )
        db.session.add(test_user)
        db.session.add(admin_user)
        db.session.commit()
    
    yield flask_app
    
    # Cleanup
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()


@pytest.fixture
def auth_token(client):
    """Get JWT token for authenticated requests"""
    response = client.post('/auth/login', json={
        'username': 'testuser',
        'password': 'testpass123'
    })
    data = response.get_json()
    return data['access_token']


@pytest.fixture
def auth_headers(auth_token):
    """Headers with JWT token"""
    return {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def admin_auth_token(client):
    """Get JWT token for admin user."""
    response = client.post('/auth/login', json={
        'username': 'admin_test',
        'password': 'AdminPass123'
    })
    data = response.get_json()
    return data['access_token']


@pytest.fixture
def admin_auth_headers(admin_auth_token):
    """Headers with admin JWT token."""
    return {
        'Authorization': f'Bearer {admin_auth_token}',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def sample_application_data():
    """Sample credit application data"""
    return {
        'person_age': 30,
        'person_income': 50000.0,
        'person_emp_length': 5,
        'loan_amnt': 10000.0,
        'loan_int_rate': 8.5,
        'loan_percent_income': 0.2,
        'cb_person_cred_hist_length': 10,
        'person_home_ownership': 'RENT',
        'loan_intent': 'PERSONAL',
        'loan_grade': 'B',
        'cb_person_default_on_file': 'N'
    }


@pytest.fixture
def high_risk_application_data():
    """High risk application data"""
    return {
        'person_age': 22,
        'person_income': 25000.0,
        'person_emp_length': 1,
        'loan_amnt': 35000.0,
        'loan_int_rate': 15.5,
        'loan_percent_income': 0.65,
        'cb_person_cred_hist_length': 2,
        'person_home_ownership': 'RENT',
        'loan_intent': 'DEBTCONSOLIDATION',
        'loan_grade': 'F',
        'cb_person_default_on_file': 'Y'
    }


@pytest.fixture
def db_session(app):
    """Database session for testing"""
    with app.app_context():
        yield db.session
        db.session.rollback()
