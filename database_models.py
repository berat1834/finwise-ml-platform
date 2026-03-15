#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Schema & ORM Models for FinWise-ML
Uses SQLAlchemy for PostgreSQL with Scoped Sessions for Flask request context
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from datetime import datetime
import enum
import os
from pathlib import Path

# Database connection
Path('instance').mkdir(exist_ok=True)
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///instance/finwise_domain.db')

engine_kwargs = {
    'echo': False,
    'pool_pre_ping': True,
    'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE_SEC', '1800') or 1800),
}
if DATABASE_URL.startswith('sqlite'):
    engine_kwargs['connect_args'] = {'check_same_thread': False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine)
# Scoped session for Flask request context management
db_session = scoped_session(SessionLocal)
Base = declarative_base()


class CreditStatusEnum(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    COMPLETED = "completed"
    DEFAULTED = "defaulted"


class InstallmentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    MISSED = "missed"


class Customer(Base):
    """Customer accounts"""
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    full_name = Column(String(255), nullable=False)
    date_of_birth = Column(DateTime)
    national_id = Column(String(50), unique=True)
    
    # Contact
    address = Column(Text)
    city = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100), default='TR')
    
    # Financial
    annual_income = Column(Float)
    employment_status = Column(String(50))  # employed, self-employed, unemployed, etc
    
    # System
    stripe_customer_id = Column(String(255), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    credits = relationship('Credit', back_populates='customer')
    applications = relationship('CreditApplication', back_populates='customer')
    payments = relationship('Payment', back_populates='customer')
    audit_logs = relationship('AuditLog', back_populates='customer')


class CreditApplication(Base):
    """Credit application submissions"""
    __tablename__ = 'credit_applications'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    
    # Application details
    requested_amount = Column(Float, nullable=False)
    requested_term_months = Column(Integer)
    purpose = Column(String(255))  # home, car, education, etc
    
    # Model prediction
    model_prediction = Column(Float)  # 0-1 probability
    model_decision = Column(String(50))  # approved, rejected
    model_threshold = Column(Float)
    di_analysis = Column(Text)  # Fairness analysis JSON
    
    # Final decision
    status = Column(Enum(CreditStatusEnum), default=CreditStatusEnum.PENDING)
    approved_amount = Column(Float)
    approved_rate = Column(Float)
    approved_term_months = Column(Integer)
    
    # Audit
    processed_by = Column(String(255))  # User/admin who made decision
    decision_explanation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime)
    
    # Relationships
    customer = relationship('Customer', back_populates='applications')
    credit = relationship('Credit', uselist=False, back_populates='application')


class Credit(Base):
    """Active credit accounts"""
    __tablename__ = 'credits'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    application_id = Column(Integer, ForeignKey('credit_applications.id'), unique=True)
    
    # Terms
    principal_amount = Column(Float, nullable=False)
    interest_rate_annual = Column(Float)
    term_months = Column(Integer)
    monthly_payment = Column(Float, nullable=False)
    
    # Status
    status = Column(Enum(CreditStatusEnum), default=CreditStatusEnum.ACTIVE)
    disbursed_date = Column(DateTime)
    maturity_date = Column(DateTime)
    
    # Tracking
    total_paid = Column(Float, default=0)
    payments_completed = Column(Integer, default=0)
    days_overdue = Column(Integer, default=0)
    
    # Created
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', back_populates='credits')
    application = relationship('CreditApplication', back_populates='credit')
    installments = relationship('Installment', back_populates='credit', cascade='all, delete-orphan')


class Installment(Base):
    """Monthly installment payments"""
    __tablename__ = 'installments'
    
    id = Column(Integer, primary_key=True)
    credit_id = Column(Integer, ForeignKey('credits.id'), nullable=False)
    
    # Payment details
    installment_number = Column(Integer, nullable=False)
    principal_amount = Column(Float)
    interest_amount = Column(Float)
    total_due = Column(Float, nullable=False)
    
    # Status
    status = Column(Enum(InstallmentStatusEnum), default=InstallmentStatusEnum.PENDING)
    due_date = Column(DateTime, nullable=False)
    paid_date = Column(DateTime)
    paid_amount = Column(Float, default=0)
    
    # Tracking
    days_overdue = Column(Integer, default=0)
    late_fee = Column(Float, default=0)
    
    # Created
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    credit = relationship('Credit', back_populates='installments')
    payment = relationship('Payment', uselist=False, back_populates='installment')


class Payment(Base):
    """Payment transactions"""
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    installment_id = Column(Integer, ForeignKey('installments.id'))
    credit_id = Column(Integer, ForeignKey('credits.id'))
    
    # Payment details
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50))  # card, bank_transfer, cash, etc
    stripe_charge_id = Column(String(255))
    
    # Status
    status = Column(String(50), default='pending')  # pending, succeeded, failed
    transaction_id = Column(String(255), unique=True)
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    receipt_url = Column(Text)
    
    # Relationships
    customer = relationship('Customer', back_populates='payments')
    installment = relationship('Installment', back_populates='payment')


class AuditLog(Base):
    """Complete audit trail for compliance"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    
    # Action
    action = Column(String(100), nullable=False)  # create, approve, reject, payment, etc
    entity_type = Column(String(50))  # customer, application, credit, payment
    entity_id = Column(Integer)
    
    # Details
    changes = Column(Text)  # JSON of what changed
    old_value = Column(Text)
    new_value = Column(Text)
    
    # User
    user_id = Column(String(255))  # Who made the change (system or user)
    reason = Column(Text)
    
    # Compliance
    ip_address = Column(String(50))
    user_agent = Column(Text)
    
    # Created
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', back_populates='audit_logs')


class FairnessAudit(Base):
    """Monthly fairness audit results"""
    __tablename__ = 'fairness_audits'
    
    id = Column(Integer, primary_key=True)
    audit_date = Column(DateTime, default=datetime.utcnow)
    
    # Metrics
    di_ratio = Column(Float)  # Disparate Impact Ratio
    approval_rate_overall = Column(Float)
    approval_rate_q1 = Column(Float)  # Lowest income
    approval_rate_q5 = Column(Float)  # Highest income
    
    # Status
    compliant = Column(Boolean)
    issues = Column(Text)  # Any concerns found
    recommendations = Column(Text)
    
    # Audit details
    total_applications = Column(Integer)
    applications_approved = Column(Integer)
    applications_rejected = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Create all tables
def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(engine)
    print('✓ Database tables created')


# Helper functions
def get_db_session():
    """
    Get database session (scoped to Flask request context)
    
    For Flask applications, this returns a session bound to the current 
    request. Sessions are automatically cleaned up via Flask's teardown_appcontext.
    
    Never manually call session.close() - let Flask handle it.
    """
    return db_session


def get_customer(customer_id):
    """Get customer by ID"""
    session = get_db_session()
    return session.query(Customer).filter(Customer.id == customer_id).first()


def get_customer_by_email(email):
    """Get customer by email"""
    session = get_db_session()
    return session.query(Customer).filter(Customer.email == email).first()


def init_db_with_app(app):
    """
    Initialize database with Flask app context management.
    
    This sets up automatic session cleanup at the end of each request,
    preventing connection leaks in production.
    
    Call this in your Flask app factory:
    
        app = Flask(__name__)
        init_db_with_app(app)
    
    Or in your main.py/app_v2_secure.py initialization.
    """
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Clean up session after request"""
        db_session.remove()


def create_customer(email, full_name, phone=None, annual_income=None):
    """Create new customer"""
    session = get_db_session()
    customer = Customer(
        email=email,
        full_name=full_name,
        phone=phone,
        annual_income=annual_income
    )
    session.add(customer)
    session.commit()
    return customer


if __name__ == '__main__':
    init_db()
    print('✓ FinWise-ML database schema ready')
