#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard Analytics Module
Real-time statistics and business intelligence
"""
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy import func, and_, or_
from models import db, Application, User, AuditLog, ModelPerformance, ManualOverride, CustomerAppeal


class DashboardAnalytics:
    """Dashboard analytics and statistics"""
    
    @staticmethod
    def get_overview_stats(days: int = 30) -> Dict:
        """Get overview statistics for dashboard"""
        period_start = datetime.utcnow() - timedelta(days=days)
        
        # Total applications
        total_apps = Application.query.filter(
            Application.created_at >= period_start
        ).count()
        
        # Approved/Rejected counts
        approved = Application.query.filter(
            Application.created_at >= period_start,
            Application.decision == 'ONAYLANDI'
        ).count()
        
        rejected = Application.query.filter(
            Application.created_at >= period_start,
            Application.decision == 'REDDEDİLDİ'
        ).count()
        
        # Override rate
        overridden = Application.query.filter(
            Application.created_at >= period_start,
            Application.is_overridden == True
        ).count()
        
        # Average processing time (in minutes)
        apps_with_timestamp = Application.query.filter(
            Application.created_at >= period_start,
            Application.decision_timestamp.isnot(None)
        ).all()
        
        avg_processing_time = 0
        if apps_with_timestamp:
            total_time = sum([
                (app.decision_timestamp - app.created_at).total_seconds() / 60
                for app in apps_with_timestamp
            ])
            avg_processing_time = total_time / len(apps_with_timestamp)
        
        # Approval rate
        approval_rate = (approved / total_apps * 100) if total_apps > 0 else 0
        override_rate = (overridden / total_apps * 100) if total_apps > 0 else 0
        
        return {
            'period_days': days,
            'period_start': period_start.isoformat(),
            'period_end': datetime.utcnow().isoformat(),
            'total_applications': total_apps,
            'approved': approved,
            'rejected': rejected,
            'approval_rate': round(approval_rate, 2),
            'override_count': overridden,
            'override_rate': round(override_rate, 2),
            'avg_processing_time_minutes': round(avg_processing_time, 2)
        }
    
    @staticmethod
    def get_daily_trends(days: int = 30) -> List[Dict]:
        """Get daily application trends"""
        period_start = datetime.utcnow() - timedelta(days=days)
        
        # Group by date
        daily_stats = db.session.query(
            func.date(Application.created_at).label('date'),
            func.count(Application.id).label('total'),
            func.sum(func.case([(Application.decision == 'ONAYLANDI', 1)], else_=0)).label('approved'),
            func.sum(func.case([(Application.decision == 'REDDEDİLDİ', 1)], else_=0)).label('rejected')
        ).filter(
            Application.created_at >= period_start
        ).group_by(
            func.date(Application.created_at)
        ).order_by(
            func.date(Application.created_at)
        ).all()
        
        trends = []
        for stat in daily_stats:
            approval_rate = (stat.approved / stat.total * 100) if stat.total > 0 else 0
            trends.append({
                'date': stat.date.isoformat(),
                'total': stat.total,
                'approved': stat.approved,
                'rejected': stat.rejected,
                'approval_rate': round(approval_rate, 2)
            })
        
        return trends
    
    @staticmethod
    def get_risk_distribution() -> Dict:
        """Get loan grade risk distribution"""
        # Last 30 days
        period_start = datetime.utcnow() - timedelta(days=30)
        
        distribution = db.session.query(
            Application.loan_grade,
            func.count(Application.id).label('count'),
            func.sum(Application.loan_amnt).label('total_amount'),
            func.avg(Application.approval_probability).label('avg_approval_prob')
        ).filter(
            Application.created_at >= period_start
        ).group_by(
            Application.loan_grade
        ).order_by(
            Application.loan_grade
        ).all()
        
        result = {}
        for item in distribution:
            result[item.loan_grade] = {
                'count': item.count,
                'total_amount': round(float(item.total_amount), 2),
                'avg_approval_probability': round(float(item.avg_approval_prob), 4)
            }
        
        return result
    
    @staticmethod
    def get_loan_intent_breakdown() -> Dict:
        """Get loan purpose breakdown"""
        period_start = datetime.utcnow() - timedelta(days=30)
        
        breakdown = db.session.query(
            Application.loan_intent,
            func.count(Application.id).label('count'),
            func.sum(Application.loan_amnt).label('total_amount'),
            func.sum(func.case([(Application.decision == 'ONAYLANDI', 1)], else_=0)).label('approved')
        ).filter(
            Application.created_at >= period_start
        ).group_by(
            Application.loan_intent
        ).all()
        
        result = {}
        for item in breakdown:
            approval_rate = (item.approved / item.count * 100) if item.count > 0 else 0
            result[item.loan_intent] = {
                'count': item.count,
                'total_amount': round(float(item.total_amount), 2),
                'approved': item.approved,
                'approval_rate': round(approval_rate, 2)
            }
        
        return result
    
    @staticmethod
    def get_top_analysts(limit: int = 10) -> List[Dict]:
        """Get top performing analysts"""
        period_start = datetime.utcnow() - timedelta(days=30)
        
        analyst_stats = db.session.query(
            User.id,
            User.username,
            func.count(Application.id).label('total_apps'),
            func.sum(func.case([(Application.decision == 'ONAYLANDI', 1)], else_=0)).label('approved'),
            func.count(ManualOverride.id).label('overrides')
        ).join(
            Application, Application.analyst_id == User.id
        ).outerjoin(
            ManualOverride, and_(
                ManualOverride.application_id == Application.id,
                ManualOverride.user_id == User.id
            )
        ).filter(
            Application.created_at >= period_start
        ).group_by(
            User.id, User.username
        ).order_by(
            func.count(Application.id).desc()
        ).limit(limit).all()
        
        analysts = []
        for stat in analyst_stats:
            approval_rate = (stat.approved / stat.total_apps * 100) if stat.total_apps > 0 else 0
            analysts.append({
                'user_id': stat.id,
                'username': stat.username,
                'total_applications': stat.total_apps,
                'approved': stat.approved,
                'approval_rate': round(approval_rate, 2),
                'overrides': stat.overrides or 0
            })
        
        return analysts
    
    @staticmethod
    def get_model_performance_summary() -> Dict:
        """Get model performance summary"""
        # Last 7 days
        period_start = datetime.utcnow() - timedelta(days=7)
        
        recent_apps = Application.query.filter(
            Application.created_at >= period_start
        ).all()
        
        if not recent_apps:
            return {
                'status': 'no_data',
                'message': 'Insufficient data for analysis'
            }
        
        # Calculate metrics
        total = len(recent_apps)
        avg_approval_prob = sum([app.approval_probability for app in recent_apps]) / total
        avg_rejection_prob = sum([app.rejection_probability for app in recent_apps]) / total
        
        # High confidence predictions (> 80%)
        high_confidence = len([
            app for app in recent_apps 
            if max(app.approval_probability, app.rejection_probability) > 0.8
        ])
        
        high_confidence_rate = (high_confidence / total * 100) if total > 0 else 0
        
        return {
            'period': 'Last 7 days',
            'total_predictions': total,
            'avg_approval_probability': round(avg_approval_prob, 4),
            'avg_rejection_probability': round(avg_rejection_prob, 4),
            'high_confidence_predictions': high_confidence,
            'high_confidence_rate': round(high_confidence_rate, 2),
            'model_health': 'good' if high_confidence_rate > 70 else 'warning' if high_confidence_rate > 50 else 'poor'
        }
    
    @staticmethod
    def get_appeals_summary() -> Dict:
        """Get customer appeals summary"""
        period_start = datetime.utcnow() - timedelta(days=30)
        
        total_appeals = CustomerAppeal.query.filter(
            CustomerAppeal.submission_date >= period_start
        ).count()
        
        resolved = CustomerAppeal.query.filter(
            CustomerAppeal.submission_date >= period_start,
            CustomerAppeal.status == 'RESOLVED'
        ).count()
        
        pending = CustomerAppeal.query.filter(
            CustomerAppeal.submission_date >= period_start,
            CustomerAppeal.status.in_(['SUBMITTED', 'UNDER_REVIEW'])
        ).count()
        
        # Overdue appeals
        overdue = CustomerAppeal.query.filter(
            CustomerAppeal.response_due_date < datetime.utcnow(),
            CustomerAppeal.status.in_(['SUBMITTED', 'UNDER_REVIEW'])
        ).count()
        
        # Average resolution time
        resolved_appeals = CustomerAppeal.query.filter(
            CustomerAppeal.submission_date >= period_start,
            CustomerAppeal.status == 'RESOLVED',
            CustomerAppeal.resolution_date.isnot(None)
        ).all()
        
        avg_resolution_days = 0
        if resolved_appeals:
            total_days = sum([
                (appeal.resolution_date - appeal.submission_date).days
                for appeal in resolved_appeals
            ])
            avg_resolution_days = total_days / len(resolved_appeals)
        
        return {
            'period_days': 30,
            'total_appeals': total_appeals,
            'resolved': resolved,
            'pending': pending,
            'overdue': overdue,
            'avg_resolution_days': round(avg_resolution_days, 1),
            'resolution_rate': round((resolved / total_appeals * 100) if total_appeals > 0 else 0, 2)
        }
    
    @staticmethod
    def get_financial_summary(days: int = 30) -> Dict:
        """Get financial summary"""
        period_start = datetime.utcnow() - timedelta(days=days)
        
        approved_apps = Application.query.filter(
            Application.created_at >= period_start,
            Application.decision == 'ONAYLANDI'
        ).all()
        
        total_exposure = sum([app.approved_limit or app.loan_amnt for app in approved_apps])
        total_approved = len(approved_apps)
        
        # Average loan amount
        avg_loan = total_exposure / total_approved if total_approved > 0 else 0
        
        # Risk-weighted assets (simplified Basel calculation)
        from compliance import BaselCalculator
        total_rwa = sum([
            BaselCalculator.calculate_rwa(app.approved_limit or app.loan_amnt, app.loan_grade)
            for app in approved_apps
        ])
        
        # Grade distribution
        grade_breakdown = {}
        for app in approved_apps:
            grade = app.loan_grade
            if grade not in grade_breakdown:
                grade_breakdown[grade] = {'count': 0, 'amount': 0}
            grade_breakdown[grade]['count'] += 1
            grade_breakdown[grade]['amount'] += app.approved_limit or app.loan_amnt
        
        return {
            'period_days': days,
            'total_approved_loans': total_approved,
            'total_credit_exposure': round(total_exposure, 2),
            'avg_loan_amount': round(avg_loan, 2),
            'total_risk_weighted_assets': round(total_rwa, 2),
            'grade_breakdown': {k: {**v, 'amount': round(v['amount'], 2)} for k, v in grade_breakdown.items()}
        }
    
    @staticmethod
    def get_system_activity() -> Dict:
        """Get recent system activity"""
        # Last 24 hours
        period_start = datetime.utcnow() - timedelta(hours=24)
        
        # API calls
        api_calls = AuditLog.query.filter(
            AuditLog.created_at >= period_start
        ).count()
        
        # Unique users
        unique_users = db.session.query(
            func.count(func.distinct(AuditLog.user_id))
        ).filter(
            AuditLog.created_at >= period_start
        ).scalar()
        
        # Login attempts
        logins = AuditLog.query.filter(
            AuditLog.created_at >= period_start,
            AuditLog.event_type.in_(['login_success', 'login_failed'])
        ).count()
        
        # Failed logins
        failed_logins = AuditLog.query.filter(
            AuditLog.created_at >= period_start,
            AuditLog.event_type == 'login_failed'
        ).count()
        
        return {
            'period': 'Last 24 hours',
            'total_api_calls': api_calls,
            'unique_users': unique_users or 0,
            'total_logins': logins,
            'failed_logins': failed_logins,
            'system_health': 'healthy' if failed_logins < 10 else 'warning'
        }
