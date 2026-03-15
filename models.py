#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database models for Credit Risk Analysis System
SQLAlchemy ORM models
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()


class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='analyst')  # analyst, manager, admin
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships - specify foreign_keys to avoid ambiguity
    applications = db.relationship('Application', foreign_keys='Application.analyst_id', backref='analyst', lazy='dynamic')
    reviewed_applications = db.relationship('Application', foreign_keys='Application.reviewed_by_user_id', backref='reviewer', lazy='dynamic')
    appeal_decisions = db.relationship('Application', foreign_keys='Application.appeal_decision_by', backref='appeal_reviewer', lazy='dynamic')
    overrides = db.relationship('ManualOverride', foreign_keys='ManualOverride.user_id', backref='override_by', lazy='dynamic')
    manager_approvals = db.relationship('ManualOverride', foreign_keys='ManualOverride.manager_id', backref='approved_by_manager', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'


class Application(db.Model):
    """Credit application model"""
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Customer Information
    person_age = db.Column(db.Integer, nullable=False)
    person_income = db.Column(db.Float, nullable=False)
    person_emp_length = db.Column(db.Integer, nullable=False)
    person_home_ownership = db.Column(db.String(20), nullable=False)
    cb_person_cred_hist_length = db.Column(db.Integer, nullable=False)
    cb_person_default_on_file = db.Column(db.String(1), nullable=False)
    
    # Loan Information
    loan_amnt = db.Column(db.Float, nullable=False)
    loan_intent = db.Column(db.String(20), nullable=False)
    loan_grade = db.Column(db.String(1), nullable=False)
    loan_int_rate = db.Column(db.Float, nullable=False)
    loan_percent_income = db.Column(db.Float, nullable=False)
    
    # Decision Information
    decision = db.Column(db.String(20), nullable=False)  # ONAYLANDI, REDDEDİLDİ
    approval_probability = db.Column(db.Float, nullable=False)
    rejection_probability = db.Column(db.Float, nullable=False)
    threshold_used = db.Column(db.Float, nullable=False)
    model_version = db.Column(db.String(50))
    risk_score = db.Column(db.Float)  # Overall risk score
    
    # Credit Limit & Pricing (NEW - Banking features)
    approved_limit = db.Column(db.Float)  # Approved credit limit
    interest_rate_offered = db.Column(db.Float)  # Risk-based pricing
    dsi_ratio = db.Column(db.Float)  # Debt Service to Income ratio
    
    # Customer Information (NEW - Banking requirements)
    applicant_name = db.Column(db.String(200))
    applicant_id = db.Column(db.String(50))  # National ID or customer number
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    
    # SHAP Explanation
    shap_values = db.Column(JSON)  # Top features and contributions
    adverse_action_reasons = db.Column(JSON)  # Reasons for rejection
    
    # Metadata
    analyst_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    application_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    decision_timestamp = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    
    # Manual Override (NEW - Enhanced)
    is_overridden = db.Column(db.Boolean, default=False)
    final_decision = db.Column(db.String(20))  # If overridden
    reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    review_notes = db.Column(db.Text)
    
    # Appeal Process (NEW - Banking requirement)
    appeal_submitted = db.Column(db.Boolean, default=False)
    appeal_reason = db.Column(db.String(100))
    appeal_detail = db.Column(db.Text)
    appeal_timestamp = db.Column(db.DateTime)
    appeal_status = db.Column(db.String(20))  # PENDING_REVIEW, APPROVED, DENIED
    appeal_decision_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    appeal_decision_date = db.Column(db.DateTime)
    
    # Relationships
    override = db.relationship('ManualOverride', backref='application', uselist=False)
    audit_logs = db.relationship('AuditLog', backref='application', lazy='dynamic')
    
    def __repr__(self):
        return f'<Application {self.id} - {self.decision}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'person_age': self.person_age,
            'person_income': self.person_income,
            'person_emp_length': self.person_emp_length,
            'loan_amnt': self.loan_amnt,
            'loan_int_rate': self.loan_int_rate,
            'loan_percent_income': self.loan_percent_income,
            'cb_person_cred_hist_length': self.cb_person_cred_hist_length,
            'person_home_ownership': self.person_home_ownership,
            'loan_intent': self.loan_intent,
            'loan_grade': self.loan_grade,
            'cb_person_default_on_file': self.cb_person_default_on_file,
            'decision': self.final_decision if self.is_overridden else self.decision,
            'approval_probability': self.approval_probability,
            'rejection_probability': self.rejection_probability,
            'is_overridden': self.is_overridden,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ManualOverride(db.Model):
    """Manual override of model decision by analyst"""
    __tablename__ = 'manual_overrides'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False, unique=True)
    
    # Override Information
    original_decision = db.Column(db.String(20), nullable=False)
    new_decision = db.Column(db.String(20), nullable=False)
    
    # Justification (Banking requirement - detailed reasoning)
    reason = db.Column(db.String(100), nullable=False)  # Coded reason
    reason_detail = db.Column(db.Text, nullable=False)  # Detailed explanation
    supporting_docs = db.Column(JSON)  # Document references
    
    # Credit Limit Override
    approved_limit = db.Column(db.Float)  # Override approved amount
    
    # Approval workflow (Banking hierarchy)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_role = db.Column(db.String(20))  # Role at time of override
    manager_approval_required = db.Column(db.Boolean, default=False)
    manager_approved = db.Column(db.Boolean, default=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    manager_approval_date = db.Column(db.DateTime)
    
    # Metadata
    override_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Audit trail
    ip_address = db.Column(db.String(45))
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ManualOverride App:{self.application_id} {self.original_decision}->{self.new_decision}>'


class AuditLog(db.Model):
    """Comprehensive audit trail"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Event Information
    event_type = db.Column(db.String(50), nullable=False, index=True)  # login, prediction, override, etc.
    event_detail = db.Column(db.Text)
    
    # Related Entities
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'))
    
    # Request Information
    endpoint = db.Column(db.String(100))
    method = db.Column(db.String(10))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    
    # Response Information
    status_code = db.Column(db.Integer)
    response_time_ms = db.Column(db.Float)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.event_type} at {self.created_at}>'


class ModelPerformance(db.Model):
    """Model performance tracking over time"""
    __tablename__ = 'model_performance'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Time period
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    
    # Volume metrics
    total_applications = db.Column(db.Integer, default=0)
    approved_count = db.Column(db.Integer, default=0)
    rejected_count = db.Column(db.Integer, default=0)
    override_count = db.Column(db.Integer, default=0)
    
    # Performance metrics (if ground truth available)
    true_positives = db.Column(db.Integer)
    true_negatives = db.Column(db.Integer)
    false_positives = db.Column(db.Integer)
    false_negatives = db.Column(db.Integer)
    
    # Calculated metrics
    approval_rate = db.Column(db.Float)
    override_rate = db.Column(db.Float)
    accuracy = db.Column(db.Float)
    precision = db.Column(db.Float)
    recall = db.Column(db.Float)
    
    # Distribution metrics (for drift detection)
    avg_person_age = db.Column(db.Float)
    avg_person_income = db.Column(db.Float)
    avg_loan_amnt = db.Column(db.Float)
    avg_loan_int_rate = db.Column(db.Float)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ModelPerformance {self.date}>'


# ============================================================================
# COMPLIANCE & REGULATORY MODELS
# ============================================================================

class DataRetentionLog(db.Model):
    """GDPR/KVKK - Data retention and deletion tracking"""
    __tablename__ = 'data_retention_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Data subject
    data_type = db.Column(db.String(50), nullable=False)  # application, user, audit
    record_id = db.Column(db.Integer, nullable=False)
    
    # Retention policy
    created_date = db.Column(db.DateTime, nullable=False)
    retention_period_days = db.Column(db.Integer, nullable=False)  # Legal requirement
    scheduled_deletion_date = db.Column(db.DateTime, nullable=False, index=True)
    
    # Deletion tracking
    is_deleted = db.Column(db.Boolean, default=False)
    deletion_date = db.Column(db.DateTime)
    deleted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    deletion_reason = db.Column(db.String(100))  # policy_expiry, user_request, legal_hold
    
    # Legal hold (prevent deletion)
    legal_hold = db.Column(db.Boolean, default=False)
    legal_hold_reason = db.Column(db.Text)
    legal_hold_until = db.Column(db.DateTime)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DataRetentionLog {self.data_type}:{self.record_id}>'


class GDPRRequest(db.Model):
    """GDPR/KVKK - User data rights requests"""
    __tablename__ = 'gdpr_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Requestor
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    applicant_id = db.Column(db.String(50))  # For non-users
    email = db.Column(db.String(120), nullable=False)
    
    # Request details
    request_type = db.Column(db.String(30), nullable=False)  # access, rectification, erasure, portability, restriction
    request_detail = db.Column(db.Text)
    
    # Processing
    status = db.Column(db.String(20), default='PENDING')  # PENDING, IN_PROGRESS, COMPLETED, REJECTED
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timeline (GDPR requires response within 30 days)
    request_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)  # request_date + 30 days
    completed_date = db.Column(db.DateTime)
    
    # Response
    response_detail = db.Column(db.Text)
    data_export_path = db.Column(db.String(255))  # For portability requests
    
    # Verification (identity verification required)
    identity_verified = db.Column(db.Boolean, default=False)
    verification_method = db.Column(db.String(50))
    verification_date = db.Column(db.DateTime)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<GDPRRequest {self.id} - {self.request_type}>'


class ComplianceReport(db.Model):
    """Regulatory compliance reports (Basel, BDDK, etc.)"""
    __tablename__ = 'compliance_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Report details
    report_type = db.Column(db.String(50), nullable=False)  # basel_car, bddk_monthly, model_validation
    report_period_start = db.Column(db.Date, nullable=False)
    report_period_end = db.Column(db.Date, nullable=False)
    
    # Basel III/IV metrics
    total_credit_exposure = db.Column(db.Float)  # Total credit amount
    risk_weighted_assets = db.Column(db.Float)  # RWA
    capital_adequacy_ratio = db.Column(db.Float)  # CAR %
    
    # Credit risk classification (BDDK)
    standard_loans = db.Column(db.Float)  # 0% provision
    watch_list = db.Column(db.Float)  # Yakından İzlenenler - 0-5%
    substandard = db.Column(db.Float)  # Tahsili Gecikmiş - 20%
    doubtful = db.Column(db.Float)  # Tahsili Şüpheli - 50%
    loss = db.Column(db.Float)  # Zarar Niteliğinde - 100%
    
    # Model performance metrics
    model_accuracy = db.Column(db.Float)
    model_precision = db.Column(db.Float)
    model_recall = db.Column(db.Float)
    model_f1_score = db.Column(db.Float)
    
    # Bias and fairness metrics
    demographic_parity_diff = db.Column(db.Float)
    equal_opportunity_diff = db.Column(db.Float)
    disparate_impact_ratio = db.Column(db.Float)
    
    # Report metadata
    report_data = db.Column(JSON)  # Full report data
    generated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Submission tracking
    submitted_to_regulator = db.Column(db.Boolean, default=False)
    submission_date = db.Column(db.DateTime)
    submission_reference = db.Column(db.String(100))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ComplianceReport {self.report_type} {self.report_period_start}>'


class ModelValidation(db.Model):
    """Model risk management - validation records"""
    __tablename__ = 'model_validations'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Model information
    model_version = db.Column(db.String(50), nullable=False)
    model_file = db.Column(db.String(255))
    validation_date = db.Column(db.Date, nullable=False)
    
    # Validation type
    validation_type = db.Column(db.String(30))  # initial, periodic, ad_hoc, regulatory
    validator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    validator_role = db.Column(db.String(50))  # Must be independent
    
    # Test results
    test_dataset_size = db.Column(db.Integer)
    test_accuracy = db.Column(db.Float)
    test_precision = db.Column(db.Float)
    test_recall = db.Column(db.Float)
    test_f1_score = db.Column(db.Float)
    test_roc_auc = db.Column(db.Float)
    
    # Bias testing
    bias_test_performed = db.Column(db.Boolean, default=False)
    bias_test_results = db.Column(JSON)
    
    # Stress testing
    stress_test_performed = db.Column(db.Boolean, default=False)
    stress_test_results = db.Column(JSON)
    
    # Validation outcome
    validation_status = db.Column(db.String(20))  # PASSED, FAILED, CONDITIONAL
    findings = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    
    # Approval
    approved = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_date = db.Column(db.DateTime)
    
    # Next validation
    next_validation_due = db.Column(db.Date)  # Annual requirement
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ModelValidation {self.model_version} - {self.validation_status}>'


class CustomerAppeal(db.Model):
    """Customer appeal/complaint system - ECOA requirement"""
    __tablename__ = 'customer_appeals'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Related application
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    
    # Appeal details
    appeal_reason = db.Column(db.String(100), nullable=False)
    appeal_detail = db.Column(db.Text, nullable=False)
    supporting_documents = db.Column(JSON)  # Document references
    
    # Customer contact
    contact_method = db.Column(db.String(20))  # email, phone, in_person
    preferred_language = db.Column(db.String(10), default='tr')
    
    # Processing (60-day response requirement)
    status = db.Column(db.String(20), default='SUBMITTED')  # SUBMITTED, UNDER_REVIEW, RESOLVED, CLOSED
    priority = db.Column(db.String(10), default='NORMAL')  # HIGH, NORMAL, LOW
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timeline
    submission_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    acknowledgement_sent = db.Column(db.Boolean, default=False)
    acknowledgement_date = db.Column(db.DateTime)
    response_due_date = db.Column(db.DateTime, nullable=False)  # 60 days from submission
    resolution_date = db.Column(db.DateTime)
    
    # Resolution
    resolution_type = db.Column(db.String(30))  # APPROVED, PARTIAL, DENIED, REFERRED
    resolution_detail = db.Column(db.Text)
    new_decision = db.Column(db.String(20))  # If decision changed
    compensation_offered = db.Column(db.Float)  # If applicable
    
    # Customer satisfaction
    customer_notified = db.Column(db.Boolean, default=False)
    notification_date = db.Column(db.DateTime)
    customer_satisfied = db.Column(db.Boolean)
    satisfaction_notes = db.Column(db.Text)
    
    # Escalation
    escalated = db.Column(db.Boolean, default=False)
    escalated_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    escalation_reason = db.Column(db.String(100))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<CustomerAppeal {self.id} App:{self.application_id} - {self.status}>'
