from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Application, User
from app.models.models import CreditApplication, Customer, AuditLog
from datetime import datetime, timedelta
import random
import json
import logging
import traceback
import binascii

logger = logging.getLogger(__name__)

v2_bp = Blueprint('v2_bp', __name__)

def get_db_session():
    return db.session

def utcnow():
    return datetime.utcnow()


    @v2_bp.route('/api/v2/ai-risk-assistant', methods=['POST'])
    @jwt_required()
    def ai_risk_assistant():
        """
        Analyst-facing Q&A endpoint for risk and fairness context.

        Request JSON:
        {
            "question": "Why was this loan rejected?",
            "application_id": 123,  # optional
            "model_prediction": 0.72,
            "customer_data": { ... },
            "fairness_context": {
                "disparate_impact_ratio": 0.81,
                "demographic_parity_difference": 0.08,
                "equal_opportunity_difference": 0.06
            }
        }
        """
        try:
            customer_id = get_jwt_identity()
            payload = request.get_json() or {}

            question = str(payload.get('question', '') or '').strip()
            if not question:
                return {'error': 'question is required'}, 400

            application_id = payload.get('application_id')
            model_prediction = payload.get('model_prediction')
            customer_data = payload.get('customer_data') or {}
            fairness_context = payload.get('fairness_context') or {}

            if application_id is not None:
                session = get_db_session()
                app_row = session.query(CreditApplication).filter_by(
                    id=application_id,
                    customer_id=customer_id
                ).first()

                if app_row:
                    model_prediction = float(app_row.model_prediction or 0.0)
                    customer = session.query(Customer).filter_by(id=app_row.customer_id).first()
                    customer_data = {
                        'annual_income': float(customer.annual_income or 0.0) if customer else 0.0,
                        'requested_amount': float(app_row.requested_amount or 0.0),
                        'requested_term_months': int(app_row.requested_term_months or 0),
                        'employment_status': customer.employment_status if customer else 'unknown',
                    }
                else:
                    from models import Application, User

                    user = User.query.filter_by(username=customer_id).first()
                    app_model = Application.query.filter_by(id=application_id).first()
                    if not app_model:
                        return {'error': 'Application not found'}, 404
                    if user and app_model.analyst_id and app_model.analyst_id != user.id:
                        return {'error': 'Application not found'}, 404

                    model_prediction = float(app_model.rejection_probability or 0.0)
                    customer_data = {
                        'annual_income': float(app_model.person_income or 0.0),
                        'requested_amount': float(app_model.loan_amnt or 0.0),
                        'requested_term_months': 0,
                        'employment_status': 'unknown',
                        'cb_person_cred_hist_length': int(app_model.cb_person_cred_hist_length or 0),
                    }

            if model_prediction is None:
                return {'error': 'model_prediction is required when application_id is not provided'}, 400

            try:
                model_prediction = float(model_prediction)
            except (TypeError, ValueError):
                return {'error': 'model_prediction must be numeric'}, 400

            if model_prediction < 0.0 or model_prediction > 1.0:
                return {'error': 'model_prediction must be between 0 and 1'}, 400

            result = build_ai_assistant_response(
                question=question,
                model_prediction=model_prediction,
                customer_data=customer_data,
                fairness_context=fairness_context
            )

            llm_answer = maybe_generate_llm_assistant_answer(
                question=question,
                model_prediction=model_prediction,
                customer_data=customer_data,
                fairness_context=fairness_context,
                deterministic_result=result
            )
            response_source = 'deterministic'
            if llm_answer:
                result['answer'] = llm_answer
                result['confidence'] = 'medium-high'
                response_source = f'llm:{AI_ASSISTANT_PROVIDER}'

            return {
                'application_id': application_id,
                'question': question,
                'answer': result['answer'],
                'answer_type': result['answer_type'],
                'confidence': result['confidence'],
                'evidence': result['evidence'],
                'next_actions': result['next_actions'],
                'response_source': response_source,
            }, 200
        except Exception as e:
            logger.error(f'AI risk assistant error: {str(e)}')
            return {'error': str(e)}, 500
    
    
    # ========================
    # 2. PAYMENT ENDPOINTS
    # ========================
    
    @v2_bp.route('/api/v2/payments/plan', methods=['POST'])
    @jwt_required()
    def create_payment_plan():
        """Create payment plan for approved credit"""
        try:
            customer_id = get_jwt_identity()
            data = request.get_json()
            
            required = ['credit_id', 'amount', 'monthly_rate', 'months']
            if not all(f in data for f in required):
                return {'error': 'Missing required fields'}, 400

    @v2_bp.route('/api/v2/offers/mock', methods=['GET'])
    @jwt_required()
    def get_mock_offers():
        """Return partner offers with fallback to deterministic mock offers."""
        try:
            application_id = request.args.get('application_id', '').strip()
            loan_amount = float(request.args.get('loan_amount', 0) or 0)
            term_months = int(request.args.get('term_months', 36) or 36)
            currency = str(request.args.get('currency', 'USD') or 'USD').upper()

            if loan_amount <= 0:
                return {'error': 'Invalid loan_amount'}, 400
            if term_months <= 0 or term_months > 120:
                return {'error': 'Invalid term_months'}, 400
            if currency not in ('USD', 'TRY'):
                currency = 'USD'
            allow_mock_fallback_raw = str(request.args.get('allow_mock_fallback', 'true')).strip().lower()
            allow_mock_fallback = allow_mock_fallback_raw in ('1', 'true', 'yes', 'y', 'on')

            # A/B variant: explicit param overrides deterministic assignment
            ab_variant_raw = str(request.args.get('ab_variant', '')).strip().upper()
            if ab_variant_raw not in ('A', 'B'):
                identity_for_ab = get_jwt_identity()
                ab_split = max(0, min(100, int(os.getenv('OFFERS_AB_SPLIT_PERCENT', '50') or 50)))
                bucket = binascii.crc32(str(identity_for_ab).encode()) % 100
                ab_variant_raw = 'B' if bucket < ab_split else 'A'

            req_payload = {
                'application_id': application_id,
                'loan_amount': loan_amount,
                'term_months': term_months,
                'currency': currency,
            }
            offers, meta = fetch_partner_offers(req_payload, allow_mock_fallback=allow_mock_fallback)

            if offers and ab_variant_raw == 'B':
                # Variant B: rank by confidence_score descending, then monthly_payment ascending
                offers.sort(key=lambda x: (-x.get('confidence_score', 0), x.get('monthly_payment', 10**9)))
                meta['ranking_rule'] = 'Variant B: Sorted by confidence_score desc, then monthly_payment asc'

            if not offers:
                return {
                    'application_id': application_id,
                    'currency': currency,
                    'offers': [],
                    'meta': {
                        'is_mock': bool(meta.get('is_mock', True)),
                        'fallback_used': bool(meta.get('fallback_used', True)),
                        'lead_fallback': True,
                        'lead_message': 'No live partner offers available. Please proceed with callback lead flow.'
                    },
                    'lead_fallback': {
                        'enabled': True,
                        'reason': 'NO_OFFERS_AVAILABLE',
                        'next_action': 'callback_form'
                    }
                }, 200

            return {
                'application_id': application_id,
                'currency': currency,
                'offers': offers,
                'meta': meta,
                'ab_variant': ab_variant_raw,
            }, 200
        except Exception as e:
            logger.error(f'Mock offers error: {str(e)}')
            return {'error': str(e)}, 500


@v2_bp.route("/api/v2/simulate/approval", methods=["POST"])
@jwt_required()
@limiter.limit("60 per hour")
def simulate_approval():
    """
    Re-evaluate what the model would predict if specific features were different.
    Does NOT write to DB — read-only simulation.

    POST /api/v2/simulate/approval
    {
        "base_application_id": 123,     # optional – load feature baseline from existing application
        "overrides": {                   # feature overrides to apply on top of baseline
            "person_income": 80000,
            "loan_amnt": 20000,
            "loan_int_rate": 12.5,
            "loan_percent_income": 0.25,
            "person_age": 35,
            "person_emp_length": 5,
            "cb_person_cred_hist_length": 4,
            "person_home_ownership": "RENT",
            "loan_intent": "PERSONAL",
            "loan_grade": "B",
            "cb_person_default_on_file": "N"
        }
    }
    """
    if PRIMARY_MODEL is None:
        return jsonify({"error": "Model not loaded"}), 503

    data = request.get_json(silent=True) or {}
    overrides = data.get("overrides")
    if not isinstance(overrides, dict) or not overrides:
        return jsonify({"error": "overrides dict is required"}), 400
    base_application_id = data.get("base_application_id")
    try:
        base_row, original_prediction = _load_simulation_context(base_application_id)
        base_row = _apply_simulation_overrides(base_row, overrides)
    except Exception as exc:
        return jsonify({"error": f"Invalid override value: {exc}"}), 400

    simulated = _simulate_from_base_row(base_row, route_key="simulate")

    delta = None
    if original_prediction:
        delta = round(simulated["onay_olasiligi"] - original_prediction["onay_olasiligi"], 4)

    return jsonify({
        "simulated": simulated,
        "original": original_prediction,
        "approval_probability_delta": delta,
        "features_used": base_row,
        "overrides_applied": list(overrides.keys()),
        "base_application_id": base_application_id,
        "note": "Simulation only — no data was written to the database.",
    })



@v2_bp.route("/api/v2/simulate/improvement-options", methods=["POST"])
@jwt_required()
@limiter.limit("60 per hour")
def simulate_improvement_options():
    """Return ranked scenario suggestions that may improve approval probability."""
    if PRIMARY_MODEL is None:
        return jsonify({"error": "Model not loaded"}), 503

    data = request.get_json(silent=True) or {}
    base_application_id = data.get("base_application_id")
    base_overrides = data.get("overrides") if isinstance(data.get("overrides"), dict) else {}

    base_row, original_prediction = _load_simulation_context(base_application_id)
    base_row = _apply_simulation_overrides(base_row, base_overrides)
    original_sim = original_prediction or _simulate_from_base_row(base_row, route_key="simulate_improve_base")

    grade_order = ["A", "B", "C", "D", "E", "F", "G"]
    current_grade = str(base_row.get("loan_grade", "C") or "C").upper()
    improved_grade = current_grade
    if current_grade in grade_order:
        idx = grade_order.index(current_grade)
        improved_grade = grade_order[max(0, idx - 1)]

    candidate_scenarios = [
        {
            "code": "lower_loan_10",
            "title": "Kredi tutarini %10 azalt",
            "description": "Talep edilen kredi miktarini %10 dusurmek risk oranini iyilestirebilir.",
            "overrides": {
                "loan_amnt": round(float(base_row["loan_amnt"]) * 0.90, 2),
                "loan_percent_income": round(max(0.001, float(base_row["loan_percent_income"]) * 0.90), 4),
            },
        },
        {
            "code": "increase_income_15",
            "title": "Geliri %15 artirilmis senaryo",
            "description": "Ek gelir veya ortak gelir ile onay olasiligi yukselebilir.",
            "overrides": {
                "person_income": round(float(base_row["person_income"]) * 1.15, 2),
                "loan_percent_income": round(max(0.001, float(base_row["loan_percent_income"]) * 0.87), 4),
            },
        },
        {
            "code": "better_grade",
            "title": "Bir kademe daha iyi kredi notu",
            "description": "Kredi notunun bir seviye iyilesmesi durumunda ortaya cikacak sonuc.",
            "overrides": {
                "loan_grade": improved_grade,
            },
        },
        {
            "code": "lower_rate_2pt",
            "title": "Faizi 2 puan dusur",
            "description": "Daha dusuk faiz teklifi ile geri odeme yuku azalir.",
            "overrides": {
                "loan_int_rate": round(max(0.1, float(base_row["loan_int_rate"]) - 2.0), 2),
            },
        },
    ]

    evaluated = []
    for scenario in candidate_scenarios:
        scenario_row = _apply_simulation_overrides(base_row, scenario["overrides"])
        simulated = _simulate_from_base_row(scenario_row, route_key=f"simulate_{scenario['code']}")
        delta = round(simulated["onay_olasiligi"] - original_sim["onay_olasiligi"], 4)
        evaluated.append({
            "code": scenario["code"],
            "title": scenario["title"],
            "description": scenario["description"],
            "overrides": scenario["overrides"],
            "simulated": simulated,
            "approval_probability_delta": delta,
        })

    evaluated.sort(key=lambda item: (item["approval_probability_delta"], item["simulated"]["onay_olasiligi"]), reverse=True)

    return jsonify({
        "status": "ok",
        "base_application_id": base_application_id,
        "original": original_sim,
        "suggestions": evaluated[:3],
        "note": "Suggestions are heuristic scenario simulations only.",
    })



@v2_bp.route("/api/v2/applications/history", methods=["GET"])
@jwt_required()
@limiter.limit("120 per hour")
def applications_history():
    """Return recent applications for current user (or all for admin)."""
    identity = get_jwt_identity()
    user = User.query.filter_by(username=identity).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        limit = int(request.args.get("limit", 20))
    except Exception:
        limit = 20
    limit = max(1, min(limit, 100))

    q = Application.query
    if user.role != "admin":
        q = q.filter_by(analyst_id=user.id)

    rows = q.order_by(Application.created_at.desc()).limit(limit).all()
    items = []
    for row in rows:
        items.append({
            "id": row.id,
            "applicant_name": row.applicant_name,
            "customer_id": row.applicant_name or row.applicant_id,
            "loan_amnt": row.loan_amnt,
            "decision": row.final_decision or row.decision,
            "approval_probability": row.approval_probability,
            "rejection_probability": row.rejection_probability,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "currency": "TRY",
            "form_data": {
                "customer_id": row.applicant_name or row.applicant_id,
                "person_age": row.person_age,
                "person_income": row.person_income,
                "person_emp_length": row.person_emp_length,
                "loan_amnt": row.loan_amnt,
                "loan_int_rate": row.loan_int_rate,
                "loan_percent_income": row.loan_percent_income,
                "cb_person_cred_hist_length": row.cb_person_cred_hist_length,
                "person_home_ownership": row.person_home_ownership,
                "loan_intent": row.loan_intent,
                "loan_grade": row.loan_grade,
                "cb_person_default_on_file": row.cb_person_default_on_file,
            },
        })

    return jsonify({
        "status": "ok",
        "applications": items,
        "count": len(items),
    })



@v2_bp.route("/api/v2/applications/history/<int:application_id>", methods=["DELETE"])
@jwt_required()
@limiter.limit("120 per hour")
def applications_history_delete(application_id: int):
    identity = get_jwt_identity()
    user = User.query.filter_by(username=identity).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    q = Application.query.filter_by(id=application_id)
    if user.role != "admin":
        q = q.filter_by(analyst_id=user.id)

    row = q.first()
    if not row:
        return jsonify({"error": "Application not found"}), 404

    db.session.delete(row)
    db.session.add(AuditLog(
        user_id=user.id,
        event_type="history_delete",
        event_detail=json.dumps({"deleted_id": application_id}),
        application_id=application_id,
        endpoint=request.path,
        method=request.method,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:255] if request.user_agent else None,
        status_code=200,
    ))
    db.session.commit()
    logger.info("History record deleted user=%s application_id=%s", identity, application_id)
    return jsonify({"status": "ok", "deleted_id": application_id})



@v2_bp.route("/api/v2/applications/history/clear", methods=["DELETE"])
@jwt_required()
@limiter.limit("60 per hour")
def applications_history_clear():
    identity = get_jwt_identity()
    user = User.query.filter_by(username=identity).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    q = Application.query
    if user.role != "admin":
        q = q.filter_by(analyst_id=user.id)

    rows = q.all()
    deleted = len(rows)
    for row in rows:
        db.session.delete(row)
    db.session.add(AuditLog(
        user_id=user.id,
        event_type="history_clear",
        event_detail=json.dumps({"deleted_count": deleted}),
        endpoint=request.path,
        method=request.method,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:255] if request.user_agent else None,
        status_code=200,
    ))
    db.session.commit()
    logger.info("History cleared user=%s deleted_count=%s", identity, deleted)

    return jsonify({"status": "ok", "deleted_count": deleted})

@v2_bp.route("/api/v2/offers/fraud-stats", methods=["GET"])
@jwt_required()
#@require_roles("admin")
def fraud_stats():
    try:
        total = Application.query.count()
        approved = Application.query.filter_by(decision="ONAYLANDI").count()
        rejected = Application.query.filter_by(decision="REDDEDİLDİ").count()
        overridden = Application.query.filter_by(is_overridden=True).count()
    except Exception:
        total = _stats["total"]
        approved = _stats["approved"]
        rejected = _stats["rejected"]
        overridden = _stats["overridden"]

    override_ratio = (overridden / total) if total > 0 else 0.0
    rejection_ratio = (rejected / total) if total > 0 else 0.0
    approval_ratio = (approved / total) if total > 0 else 0.0

    signals = [
        {
            "signal_type": "Override Rate",
            "ratio": round(override_ratio, 4),
            "description": f"{overridden} başvuru manuel override edildi. Toplam başvuru: {total}",
            "count": overridden,
        },
        {
            "signal_type": "Rejection Rate",
            "ratio": round(rejection_ratio, 4),
            "description": f"{rejected} başvuru reddedildi. Onay oranı: {approval_ratio*100:.1f}%",
            "count": rejected,
        },
        {
            "signal_type": "Model Routing",
            "ratio": round(router.canary_percent / 100.0, 4) if router.canary_percent else 0.0,
            "description": f"Routing mode: {router.mode}. Canary yüklü: {'Evet' if CANARY_MODEL is not None else 'Hayır'}",
            "count": 0,
        },
    ]

    return jsonify({
        "status": "active",
        "summary": {
            "total_applications": total,
            "approved": approved,
            "rejected": rejected,
            "overridden": overridden,
            "approval_rate": f"{approval_ratio*100:.1f}%",
            "override_rate": f"{override_ratio*100:.1f}%",
        },
        "fraud_signals": signals,
        "timestamp": utcnow().isoformat(),
    })

