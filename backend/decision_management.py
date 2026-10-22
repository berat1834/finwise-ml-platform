"""
Credit Decision System - Manual Override & Appeal Management
Banking-grade decision workflow with human intervention
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Application, ManualOverride, User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create blueprint
decision_bp = Blueprint('decision', __name__, url_prefix='/api/decision')


class CreditDecisionEngine:
    """
    Enhanced credit decision engine with:
    - Manual override capability
    - Approval hierarchy (amount-based)
    - Appeal process
    - Human review queue
    """
    
    # Approval authority levels (amount thresholds in TL)
    APPROVAL_LEVELS = {
        'junior': 50000,      # Junior officers: up to 50K TL
        'senior': 200000,     # Senior officers: up to 200K TL
        'manager': 1000000,   # Managers: up to 1M TL
        'director': float('inf')  # Directors: unlimited
    }
    
    # Override reasons
    OVERRIDE_REASONS = [
        'existing_customer_good_history',
        'additional_collateral_provided',
        'manual_income_verification',
        'credit_bureau_error_corrected',
        'policy_exception_approved',
        'relationship_banking',
        'strategic_customer',
        'other'
    ]
    
    # Appeal reasons
    APPEAL_REASONS = [
        'income_underestimated',
        'credit_report_error',
        'temporary_financial_difficulty',
        'additional_documents_available',
        'collateral_not_considered',
        'other'
    ]
    
    @staticmethod
    def can_override(user_role: str, loan_amount: float) -> bool:
        """Check if user has authority to override for this amount"""
        threshold = CreditDecisionEngine.APPROVAL_LEVELS.get(user_role.lower(), 0)
        return loan_amount <= threshold
    
    @staticmethod
    def requires_higher_approval(loan_amount: float, current_role: str) -> str:
        """Determine if higher approval is needed"""
        current_threshold = CreditDecisionEngine.APPROVAL_LEVELS.get(current_role.lower(), 0)
        
        if loan_amount <= current_threshold:
            return None
        
        # Find next level
        for role, threshold in sorted(CreditDecisionEngine.APPROVAL_LEVELS.items(), 
                                     key=lambda x: x[1]):
            if loan_amount <= threshold and threshold > current_threshold:
                return role
        
        return 'director'
    
    @staticmethod
    def calculate_credit_limit(application_data: dict, base_approval: bool) -> dict:
        """
        Calculate approved credit limit
        
        Banking formula:
        Max Limit = (Monthly Income × 0.4 - Existing Debt) × 36 months
        DSI (Debt Service to Income) should be < 40%
        """
        monthly_income = application_data['person_income'] / 12
        loan_amount = application_data['loan_amnt']
        loan_percent_income = application_data['loan_percent_income']
        
        # Calculate maximum sustainable debt
        max_monthly_debt = monthly_income * 0.40  # 40% DSI limit
        current_monthly_debt = monthly_income * loan_percent_income
        available_capacity = max_monthly_debt - current_monthly_debt
        
        # Maximum loan (assuming 36-month term, simple calculation)
        max_loan = available_capacity * 36
        
        if base_approval:
            # Approve requested amount or maximum, whichever is lower
            approved_limit = min(loan_amount, max_loan)
            decision = 'APPROVED'
            reason = 'Within acceptable risk parameters'
        else:
            # Rejection, but offer lower amount if possible
            if max_loan > 0:
                approved_limit = max_loan
                decision = 'CONDITIONAL_APPROVAL'
                reason = f'Original request too high. Approved up to {approved_limit:,.0f} TL'
            else:
                approved_limit = 0
                decision = 'REJECTED'
                reason = 'Insufficient debt service capacity (DSI > 40%)'
        
        return {
            'decision': decision,
            'requested_amount': loan_amount,
            'approved_limit': round(approved_limit, 2),
            'monthly_income': round(monthly_income, 2),
            'max_monthly_debt': round(max_monthly_debt, 2),
            'dsi_ratio': round((current_monthly_debt / monthly_income) * 100, 2),
            'reason': reason
        }


@decision_bp.route('/override/<int:application_id>', methods=['POST'])
@jwt_required()
def override_decision(application_id):
    """
    Manual override of model decision
    Requires appropriate authority level
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get application
        application = Application.query.get(application_id)
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        # Parse request
        data = request.get_json()
        new_decision = data.get('new_decision')  # 'APPROVED' or 'REJECTED'
        reason = data.get('reason')
        reason_detail = data.get('reason_detail', '')
        new_limit = data.get('approved_limit')
        
        # Validation
        if new_decision not in ['APPROVED', 'REJECTED']:
            return jsonify({'error': 'Invalid decision'}), 400
        
        if reason not in CreditDecisionEngine.OVERRIDE_REASONS:
            return jsonify({'error': 'Invalid override reason'}), 400
        
        if not reason_detail or len(reason_detail) < 20:
            return jsonify({'error': 'Detailed reason required (min 20 characters)'}), 400
        
        # Check authority
        loan_amount = application.loan_amnt
        if not CreditDecisionEngine.can_override(user.role, loan_amount):
            required_role = CreditDecisionEngine.requires_higher_approval(
                loan_amount, user.role
            )
            return jsonify({
                'error': 'Insufficient authority for this amount',
                'loan_amount': loan_amount,
                'your_limit': CreditDecisionEngine.APPROVAL_LEVELS.get(user.role.lower(), 0),
                'required_approval': required_role
            }), 403
        
        # Create override record
        override = ManualOverride(
            application_id=application_id,
            user_id=current_user_id,
            original_decision=application.decision,
            new_decision=new_decision,
            reason=reason,
            reason_detail=reason_detail,
            approved_limit=new_limit,
            override_timestamp=datetime.utcnow()
        )
        
        # Update application
        application.decision = new_decision
        application.final_decision = new_decision
        application.approved_limit = new_limit
        application.decision_timestamp = datetime.utcnow()
        application.reviewed_by_user_id = current_user_id
        
        db.session.add(override)
        db.session.commit()
        
        logger.info(f"Override: Application {application_id} by user {current_user_id}: "
                   f"{application.decision} → {new_decision}")
        
        return jsonify({
            'success': True,
            'message': 'Decision overridden successfully',
            'override_id': override.id,
            'application_id': application_id,
            'original_decision': override.original_decision,
            'new_decision': new_decision,
            'override_by': user.username,
            'timestamp': override.override_timestamp.isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Override error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@decision_bp.route('/appeal/<int:application_id>', methods=['POST'])
def submit_appeal(application_id):
    """
    Customer appeals a rejection
    No JWT required - customer facing
    """
    try:
        # Get application
        application = Application.query.get(application_id)
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        if application.decision != 'REJECTED':
            return jsonify({'error': 'Can only appeal rejected applications'}), 400
        
        # Parse appeal
        data = request.get_json()
        appeal_reason = data.get('reason')
        appeal_detail = data.get('detail', '')
        additional_documents = data.get('documents', [])
        
        # Validation
        if appeal_reason not in CreditDecisionEngine.APPEAL_REASONS:
            return jsonify({'error': 'Invalid appeal reason'}), 400
        
        if not appeal_detail or len(appeal_detail) < 50:
            return jsonify({
                'error': 'Detailed explanation required (min 50 characters)'
            }), 400
        
        # Update application
        application.appeal_submitted = True
        application.appeal_reason = appeal_reason
        application.appeal_detail = appeal_detail
        application.appeal_timestamp = datetime.utcnow()
        application.appeal_status = 'PENDING_REVIEW'
        
        db.session.commit()
        
        logger.info(f"Appeal submitted for application {application_id}")
        
        return jsonify({
            'success': True,
            'message': 'Appeal submitted successfully',
            'application_id': application_id,
            'appeal_status': 'PENDING_REVIEW',
            'review_time_estimate': '3-5 business days',
            'next_steps': [
                'Your appeal will be reviewed by a senior credit officer',
                'You may be contacted for additional documentation',
                'Decision will be communicated via email/SMS'
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Appeal submission error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@decision_bp.route('/review-queue', methods=['GET'])
@jwt_required()
def get_review_queue():
    """
    Get applications requiring manual review
    Used by credit officers
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Filter based on role authority
        user_limit = CreditDecisionEngine.APPROVAL_LEVELS.get(user.role.lower(), 0)
        
        # Get pending appeals
        appeals = Application.query.filter(
            Application.appeal_submitted == True,
            Application.appeal_status == 'PENDING_REVIEW',
            Application.loan_amnt <= user_limit
        ).order_by(Application.appeal_timestamp.asc()).all()
        
        # Get high-risk approvals needing verification
        high_risk = Application.query.filter(
            Application.decision == 'APPROVED',
            Application.risk_score > 0.7,
            Application.reviewed_by_user_id == None,
            Application.loan_amnt <= user_limit
        ).order_by(Application.application_date.desc()).limit(20).all()
        
        review_queue = []
        
        for app in appeals:
            review_queue.append({
                'application_id': app.id,
                'type': 'APPEAL',
                'customer_name': app.applicant_name,
                'loan_amount': app.loan_amnt,
                'original_decision': app.decision,
                'appeal_reason': app.appeal_reason,
                'appeal_date': app.appeal_timestamp.isoformat() if app.appeal_timestamp else None,
                'priority': 'HIGH'
            })
        
        for app in high_risk:
            review_queue.append({
                'application_id': app.id,
                'type': 'HIGH_RISK_VERIFICATION',
                'customer_name': app.applicant_name,
                'loan_amount': app.loan_amnt,
                'risk_score': round(app.risk_score, 3),
                'model_decision': app.decision,
                'application_date': app.application_date.isoformat(),
                'priority': 'MEDIUM'
            })
        
        return jsonify({
            'total_items': len(review_queue),
            'queue': review_queue,
            'your_authority_limit': user_limit,
            'role': user.role
        }), 200
        
    except Exception as e:
        logger.error(f"Review queue error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@decision_bp.route('/calculate-limit', methods=['POST'])
@jwt_required()
def calculate_limit():
    """
    Calculate credit limit based on DSI (Debt Service to Income)
    Banking standard: DSI < 40%
    """
    try:
        data = request.get_json()
        
        result = CreditDecisionEngine.calculate_credit_limit(
            data,
            base_approval=data.get('base_approval', True)
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Limit calculation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Export blueprint
def register_decision_routes(app):
    """Register decision management routes"""
    app.register_blueprint(decision_bp)
