#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compliance Module - GDPR, Basel, BDDK, Model Risk Management
Regulatory compliance utilities and calculations
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from models import (
    db, Application, DataRetentionLog, GDPRRequest, 
    ComplianceReport, ModelValidation, CustomerAppeal
)


class ComplianceManager:
    """Central compliance management system"""
    
    # Data retention periods (days) per GDPR/KVKK
    RETENTION_PERIODS = {
        'application': 7 * 365,  # 7 years for financial records
        'audit_log': 10 * 365,   # 10 years for audit trails
        'user': 5 * 365,          # 5 years after last activity
        'appeal': 3 * 365,        # 3 years after resolution
    }
    
    @staticmethod
    def schedule_data_retention(data_type: str, record_id: int) -> DataRetentionLog:
        """Schedule data retention and automatic deletion"""
        retention_days = ComplianceManager.RETENTION_PERIODS.get(data_type, 365)
        created_date = datetime.utcnow()
        deletion_date = created_date + timedelta(days=retention_days)
        
        retention_log = DataRetentionLog(
            data_type=data_type,
            record_id=record_id,
            created_date=created_date,
            retention_period_days=retention_days,
            scheduled_deletion_date=deletion_date
        )
        
        db.session.add(retention_log)
        db.session.commit()
        
        return retention_log
    
    @staticmethod
    def process_gdpr_request(request_type: str, email: str, user_id: Optional[int] = None) -> GDPRRequest:
        """Process GDPR/KVKK data subject request"""
        request_date = datetime.utcnow()
        due_date = request_date + timedelta(days=30)  # GDPR 30-day requirement
        
        gdpr_request = GDPRRequest(
            user_id=user_id,
            email=email,
            request_type=request_type,
            request_date=request_date,
            due_date=due_date,
            status='PENDING'
        )
        
        db.session.add(gdpr_request)
        db.session.commit()
        
        return gdpr_request
    
    @staticmethod
    def export_user_data(user_id: int) -> Dict:
        """Export all user data (GDPR Right to Data Portability)"""
        from models import User, Application, AuditLog
        
        user = User.query.get(user_id)
        if not user:
            return None
        
        # Collect all user data
        data = {
            'user_info': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'created_at': user.created_at.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None
            },
            'applications': [],
            'audit_logs': []
        }
        
        # Applications
        applications = Application.query.filter_by(analyst_id=user_id).all()
        for app in applications:
            data['applications'].append(app.to_dict())
        
        # Audit logs
        audit_logs = AuditLog.query.filter_by(user_id=user_id).all()
        for log in audit_logs:
            data['audit_logs'].append({
                'event_type': log.event_type,
                'event_detail': log.event_detail,
                'created_at': log.created_at.isoformat()
            })
        
        return data
    
    @staticmethod
    def anonymize_user_data(user_id: int) -> bool:
        """Anonymize user data (GDPR Right to Erasure with retention requirements)"""
        from models import User, Application
        
        user = User.query.get(user_id)
        if not user:
            return False
        
        # Anonymize personal data while keeping records for compliance
        user.username = f"DELETED_USER_{user_id}"
        user.email = f"deleted_{user_id}@anonymized.local"
        user.is_active = False
        
        # Anonymize applications
        applications = Application.query.filter_by(analyst_id=user_id).all()
        for app in applications:
            if app.applicant_name:
                app.applicant_name = "ANONYMIZED"
            if app.applicant_id:
                app.applicant_id = f"ANON_{app.id}"
            if app.phone:
                app.phone = "***"
            if app.email:
                app.email = f"anon_{app.id}@deleted.local"
        
        db.session.commit()
        return True


class BaselCalculator:
    """Basel III/IV Risk-Weighted Assets (RWA) Calculator"""
    
    # Risk weights per Basel standardized approach
    RISK_WEIGHTS = {
        'A': 0.20,  # Excellent credit (AAA-AA)
        'B': 0.50,  # Good credit (A-BBB)
        'C': 0.75,  # Fair credit (BB-B)
        'D': 1.00,  # Poor credit (CCC-CC)
        'E': 1.25,  # Very poor (C)
        'F': 1.50,  # Default risk (D)
        'G': 1.50,  # High default risk
    }
    
    @staticmethod
    def calculate_rwa(loan_amount: float, loan_grade: str) -> float:
        """Calculate Risk-Weighted Assets"""
        risk_weight = BaselCalculator.RISK_WEIGHTS.get(loan_grade, 1.00)
        return loan_amount * risk_weight
    
    @staticmethod
    def calculate_car(total_capital: float, rwa: float) -> float:
        """Calculate Capital Adequacy Ratio (CAR)"""
        if rwa == 0:
            return 0.0
        return (total_capital / rwa) * 100
    
    @staticmethod
    def generate_basel_report(period_start: datetime, period_end: datetime) -> Dict:
        """Generate Basel III compliance report"""
        applications = Application.query.filter(
            Application.decision == 'ONAYLANDI',
            Application.created_at.between(period_start, period_end)
        ).all()
        
        total_exposure = 0
        total_rwa = 0
        
        for app in applications:
            loan_amount = app.approved_limit or app.loan_amnt
            total_exposure += loan_amount
            total_rwa += BaselCalculator.calculate_rwa(loan_amount, app.loan_grade)
        
        # Assuming 15% capital (simplified)
        total_capital = total_exposure * 0.15
        car = BaselCalculator.calculate_car(total_capital, total_rwa)
        
        return {
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'total_credit_exposure': round(total_exposure, 2),
            'risk_weighted_assets': round(total_rwa, 2),
            'total_capital': round(total_capital, 2),
            'capital_adequacy_ratio': round(car, 2),
            'meets_requirement': car >= 8.0,  # Basel III minimum 8%
            'risk_weight_distribution': BaselCalculator._get_risk_distribution(applications)
        }
    
    @staticmethod
    def _get_risk_distribution(applications: List[Application]) -> Dict:
        """Get distribution of loans by risk grade"""
        distribution = {}
        for app in applications:
            grade = app.loan_grade
            if grade not in distribution:
                distribution[grade] = {'count': 0, 'amount': 0}
            distribution[grade]['count'] += 1
            distribution[grade]['amount'] += app.approved_limit or app.loan_amnt
        return distribution


class BDDKClassifier:
    """BDDK (Turkish Banking Regulation) Credit Classification"""
    
    # BDDK loan classification based on days past due
    CLASSIFICATIONS = {
        'STANDARD': {'days_past_due': 0, 'provision_rate': 0.00},
        'WATCH_LIST': {'days_past_due': 30, 'provision_rate': 0.05},
        'SUBSTANDARD': {'days_past_due': 90, 'provision_rate': 0.20},
        'DOUBTFUL': {'days_past_due': 180, 'provision_rate': 0.50},
        'LOSS': {'days_past_due': 365, 'provision_rate': 1.00}
    }
    
    @staticmethod
    def classify_loan(days_past_due: int) -> Dict:
        """Classify loan per BDDK standards"""
        if days_past_due == 0:
            classification = 'STANDARD'
        elif days_past_due < 90:
            classification = 'WATCH_LIST'
        elif days_past_due < 180:
            classification = 'SUBSTANDARD'
        elif days_past_due < 365:
            classification = 'DOUBTFUL'
        else:
            classification = 'LOSS'
        
        return {
            'classification': classification,
            'provision_rate': BDDKClassifier.CLASSIFICATIONS[classification]['provision_rate']
        }
    
    @staticmethod
    def generate_bddk_report(period_start: datetime, period_end: datetime) -> Dict:
        """Generate BDDK compliance report"""
        applications = Application.query.filter(
            Application.decision == 'ONAYLANDI',
            Application.created_at.between(period_start, period_end)
        ).all()
        
        classifications = {
            'STANDARD': 0,
            'WATCH_LIST': 0,
            'SUBSTANDARD': 0,
            'DOUBTFUL': 0,
            'LOSS': 0
        }
        
        total_loans = len(applications)
        total_amount = sum([app.approved_limit or app.loan_amnt for app in applications])
        
        # For demo, classify based on rejection probability
        for app in applications:
            if app.rejection_probability < 0.1:
                classifications['STANDARD'] += app.approved_limit or app.loan_amnt
            elif app.rejection_probability < 0.3:
                classifications['WATCH_LIST'] += app.approved_limit or app.loan_amnt
            elif app.rejection_probability < 0.5:
                classifications['SUBSTANDARD'] += app.approved_limit or app.loan_amnt
            elif app.rejection_probability < 0.7:
                classifications['DOUBTFUL'] += app.approved_limit or app.loan_amnt
            else:
                classifications['LOSS'] += app.approved_limit or app.loan_amnt
        
        return {
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'total_loans': total_loans,
            'total_amount': round(total_amount, 2),
            'classifications': {k: round(v, 2) for k, v in classifications.items()},
            'npl_ratio': round((classifications['SUBSTANDARD'] + classifications['DOUBTFUL'] + classifications['LOSS']) / total_amount * 100 if total_amount > 0 else 0, 2)
        }


class ModelRiskManager:
    """Model Risk Management - Validation and Monitoring"""
    
    @staticmethod
    def create_validation_record(model_version: str, validator_id: int, test_results: Dict) -> ModelValidation:
        """Create model validation record"""
        validation = ModelValidation(
            model_version=model_version,
            validation_date=datetime.utcnow().date(),
            validation_type='periodic',
            validator_id=validator_id,
            test_dataset_size=test_results.get('dataset_size'),
            test_accuracy=test_results.get('accuracy'),
            test_precision=test_results.get('precision'),
            test_recall=test_results.get('recall'),
            test_f1_score=test_results.get('f1_score'),
            test_roc_auc=test_results.get('roc_auc'),
            bias_test_performed=test_results.get('bias_tested', False),
            bias_test_results=test_results.get('bias_results'),
            validation_status='PASSED' if test_results.get('accuracy', 0) > 0.80 else 'FAILED'
        )
        
        db.session.add(validation)
        db.session.commit()
        
        return validation
    
    @staticmethod
    def check_model_performance_drift() -> Dict:
        """Check for model performance drift"""
        from models import ModelPerformance
        
        # Get last 30 days of performance
        recent_performance = ModelPerformance.query.order_by(
            ModelPerformance.date.desc()
        ).limit(30).all()
        
        if len(recent_performance) < 10:
            return {'status': 'insufficient_data'}
        
        # Calculate average metrics
        avg_accuracy = sum([p.accuracy for p in recent_performance if p.accuracy]) / len(recent_performance)
        
        # Check against baseline (e.g., 80%)
        baseline_accuracy = 0.80
        drift_detected = avg_accuracy < baseline_accuracy - 0.05
        
        return {
            'status': 'drift_detected' if drift_detected else 'normal',
            'avg_accuracy': round(avg_accuracy, 4),
            'baseline_accuracy': baseline_accuracy,
            'recommendation': 'Model retraining recommended' if drift_detected else 'No action needed'
        }


class AppealManager:
    """Customer Appeal Management System"""
    
    @staticmethod
    def submit_appeal(application_id: int, reason: str, detail: str, contact_method: str = 'email') -> CustomerAppeal:
        """Submit customer appeal"""
        submission_date = datetime.utcnow()
        response_due = submission_date + timedelta(days=60)  # 60-day response requirement
        
        appeal = CustomerAppeal(
            application_id=application_id,
            appeal_reason=reason,
            appeal_detail=detail,
            contact_method=contact_method,
            submission_date=submission_date,
            response_due_date=response_due,
            status='SUBMITTED'
        )
        
        db.session.add(appeal)
        db.session.commit()
        
        return appeal
    
    @staticmethod
    def process_appeal(appeal_id: int, resolution_type: str, resolution_detail: str, assigned_to: int) -> bool:
        """Process customer appeal"""
        appeal = CustomerAppeal.query.get(appeal_id)
        if not appeal:
            return False
        
        appeal.status = 'UNDER_REVIEW'
        appeal.assigned_to = assigned_to
        appeal.resolution_type = resolution_type
        appeal.resolution_detail = resolution_detail
        appeal.resolution_date = datetime.utcnow()
        
        db.session.commit()
        return True
    
    @staticmethod
    def get_overdue_appeals() -> List[CustomerAppeal]:
        """Get appeals that are overdue"""
        now = datetime.utcnow()
        overdue = CustomerAppeal.query.filter(
            CustomerAppeal.response_due_date < now,
            CustomerAppeal.status.in_(['SUBMITTED', 'UNDER_REVIEW'])
        ).all()
        
        return overdue
