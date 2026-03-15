"""
Test Suite for Database Operations
"""
import pytest
from models import User, Application, ManualOverride, AuditLog
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime


class TestUserModel:
    """Test User model"""
    
    def test_create_user(self, app, db_session):
        """Test creating a user"""
        user = User(
            username='newuser',
            email='newuser@example.com',
            password_hash=generate_password_hash('password123'),
            role='analyst'
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.username == 'newuser'
        assert user.email == 'newuser@example.com'
        assert user.role == 'analyst'
    
    def test_user_password_hashing(self, app, db_session):
        """Test password is hashed"""
        password = 'securepassword123'
        user = User(
            username='testuser2',
            email='test2@example.com',
            password_hash=generate_password_hash(password),
            role='analyst'
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.password_hash != password
        assert check_password_hash(user.password_hash, password)
    
    def test_user_unique_username(self, app, db_session):
        """Test username must be unique"""
        user1 = User(
            username='duplicate',
            email='user1@example.com',
            password_hash=generate_password_hash('pass123'),
            role='analyst'
        )
        db_session.add(user1)
        db_session.commit()
        
        user2 = User(
            username='duplicate',
            email='user2@example.com',
            password_hash=generate_password_hash('pass456'),
            role='analyst'
        )
        db_session.add(user2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            db_session.commit()


class TestApplicationModel:
    """Test Application model"""
    
    def test_create_application(self, app, db_session):
        """Test creating an application"""
        # Get test user
        user = db_session.query(User).filter_by(username='testuser').first()
        
        application = Application(
            analyst_id=user.id,
            person_age=30,
            person_income=50000.0,
            person_emp_length=5,
            loan_amnt=10000.0,
            loan_int_rate=8.5,
            loan_percent_income=0.2,
            cb_person_cred_hist_length=10,
            person_home_ownership='RENT',
            loan_intent='PERSONAL',
            loan_grade='B',
            cb_person_default_on_file='N',
            risk_score=0.15,
            decision='ONAYLANDI'
        )
        db_session.add(application)
        db_session.commit()
        
        assert application.id is not None
        assert application.decision == 'ONAYLANDI'
        assert application.risk_score == 0.15
    
    def test_application_relationships(self, app, db_session):
        """Test application-user relationship"""
        user = db_session.query(User).filter_by(username='testuser').first()
        
        application = Application(
            analyst_id=user.id,
            person_age=30,
            person_income=50000.0,
            person_emp_length=5,
            loan_amnt=10000.0,
            loan_int_rate=8.5,
            loan_percent_income=0.2,
            cb_person_cred_hist_length=10,
            person_home_ownership='RENT',
            loan_intent='PERSONAL',
            loan_grade='B',
            cb_person_default_on_file='N',
            risk_score=0.15,
            decision='ONAYLANDI'
        )
        db_session.add(application)
        db_session.commit()
        
        # Test relationship
        assert application.analyst.username == 'testuser'
    
    def test_application_timestamps(self, app, db_session):
        """Test application has timestamps"""
        user = db_session.query(User).filter_by(username='testuser').first()
        
        application = Application(
            analyst_id=user.id,
            person_age=30,
            person_income=50000.0,
            person_emp_length=5,
            loan_amnt=10000.0,
            loan_int_rate=8.5,
            loan_percent_income=0.2,
            cb_person_cred_hist_length=10,
            person_home_ownership='RENT',
            loan_intent='PERSONAL',
            loan_grade='B',
            cb_person_default_on_file='N',
            risk_score=0.15,
            decision='ONAYLANDI'
        )
        db_session.add(application)
        db_session.commit()
        
        assert application.created_at is not None
        assert isinstance(application.created_at, datetime)


class TestManualOverrideModel:
    """Test ManualOverride model"""
    
    def test_create_override(self, app, db_session):
        """Test creating a manual override"""
        user = db_session.query(User).filter_by(username='testuser').first()
        
        # Create application first
        application = Application(
            analyst_id=user.id,
            person_age=30,
            person_income=50000.0,
            person_emp_length=5,
            loan_amnt=10000.0,
            loan_int_rate=8.5,
            loan_percent_income=0.2,
            cb_person_cred_hist_length=10,
            person_home_ownership='RENT',
            loan_intent='PERSONAL',
            loan_grade='B',
            cb_person_default_on_file='N',
            risk_score=0.65,
            decision='REDDEDİLDİ'
        )
        db_session.add(application)
        db_session.commit()
        
        # Create override
        override = ManualOverride(
            application_id=application.id,
            overrider_id=user.id,
            original_decision='REDDEDİLDİ',
            new_decision='ONAYLANDI',
            reason='Special circumstances'
        )
        db_session.add(override)
        db_session.commit()
        
        assert override.id is not None
        assert override.original_decision == 'REDDEDİLDİ'
        assert override.new_decision == 'ONAYLANDI'
    
    def test_override_relationships(self, app, db_session):
        """Test override relationships"""
        user = db_session.query(User).filter_by(username='testuser').first()
        
        application = Application(
            analyst_id=user.id,
            person_age=30,
            person_income=50000.0,
            person_emp_length=5,
            loan_amnt=10000.0,
            loan_int_rate=8.5,
            loan_percent_income=0.2,
            cb_person_cred_hist_length=10,
            person_home_ownership='RENT',
            loan_intent='PERSONAL',
            loan_grade='B',
            cb_person_default_on_file='N',
            risk_score=0.65,
            decision='REDDEDİLDİ'
        )
        db_session.add(application)
        db_session.commit()
        
        override = ManualOverride(
            application_id=application.id,
            overrider_id=user.id,
            original_decision='REDDEDİLDİ',
            new_decision='ONAYLANDI',
            reason='Test'
        )
        db_session.add(override)
        db_session.commit()
        
        # Test relationships
        assert override.application.id == application.id
        assert override.overrider.username == 'testuser'


class TestAuditLogModel:
    """Test AuditLog model"""
    
    def test_create_audit_log(self, app, db_session):
        """Test creating an audit log entry"""
        user = db_session.query(User).filter_by(username='testuser').first()
        
        audit = AuditLog(
            user_id=user.id,
            action='LOGIN',
            endpoint='/auth/login',
            ip_address='127.0.0.1',
            user_agent='pytest'
        )
        db_session.add(audit)
        db_session.commit()
        
        assert audit.id is not None
        assert audit.action == 'LOGIN'
        assert audit.ip_address == '127.0.0.1'
    
    def test_audit_log_timestamps(self, app, db_session):
        """Test audit log has timestamps"""
        user = db_session.query(User).filter_by(username='testuser').first()
        
        audit = AuditLog(
            user_id=user.id,
            action='EVALUATE',
            endpoint='/degerlendir'
        )
        db_session.add(audit)
        db_session.commit()
        
        assert audit.timestamp is not None
        assert isinstance(audit.timestamp, datetime)


class TestDatabaseQueries:
    """Test common database queries"""
    
    def test_get_user_applications(self, app, db_session):
        """Test querying user's applications"""
        user = db_session.query(User).filter_by(username='testuser').first()
        
        # Create multiple applications
        for i in range(3):
            app = Application(
                analyst_id=user.id,
                person_age=30,
                person_income=50000.0,
                person_emp_length=5,
                loan_amnt=10000.0,
                loan_int_rate=8.5,
                loan_percent_income=0.2,
                cb_person_cred_hist_length=10,
                person_home_ownership='RENT',
                loan_intent='PERSONAL',
                loan_grade='B',
                cb_person_default_on_file='N',
                risk_score=0.15,
                decision='ONAYLANDI'
            )
            db_session.add(app)
        db_session.commit()
        
        # Query applications
        applications = db_session.query(Application).filter_by(analyst_id=user.id).all()
        assert len(applications) >= 3
    
    def test_count_decisions(self, app, db_session):
        """Test counting approved/rejected applications"""
        user = db_session.query(User).filter_by(username='testuser').first()
        
        # Create approved and rejected
        for decision in ['ONAYLANDI', 'REDDEDİLDİ', 'ONAYLANDI']:
            app = Application(
                analyst_id=user.id,
                person_age=30,
                person_income=50000.0,
                person_emp_length=5,
                loan_amnt=10000.0,
                loan_int_rate=8.5,
                loan_percent_income=0.2,
                cb_person_cred_hist_length=10,
                person_home_ownership='RENT',
                loan_intent='PERSONAL',
                loan_grade='B',
                cb_person_default_on_file='N',
                risk_score=0.15,
                decision=decision
            )
            db_session.add(app)
        db_session.commit()
        
        approved = db_session.query(Application).filter_by(decision='ONAYLANDI').count()
        rejected = db_session.query(Application).filter_by(decision='REDDEDİLDİ').count()
        
        assert approved >= 2
        assert rejected >= 1
