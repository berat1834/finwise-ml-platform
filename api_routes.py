#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Additional Flask API Routes for Payment, Application, and Customer Management
Add these to app_v2_secure.py
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from threading import Lock
import joblib
import json
import logging
import os
import requests
import time
from payment_processor import PaymentProcessor
from fairness_monitor import FairnessMonitor
from bank_offer_adapters import (
    fetch_partner_offers, get_offer_adapter_stats,
    AlfaBankAdapter, NovaFinanceAdapter, HorizonCreditAdapter,
)
import binascii
from model_constants import PRODUCTION_MODEL_PATH, PRODUCTION_META_PATH
from database_models import (
    Customer, CreditApplication, Credit, Installment, Payment, 
    AuditLog, get_db_session, CreditStatusEnum, InstallmentStatusEnum
)
from bleach import clean
import numpy as np

logger = logging.getLogger(__name__)
payment_processor = PaymentProcessor()
fairness_monitor = FairnessMonitor()
AI_ASSISTANT_PROVIDER = os.getenv('AI_ASSISTANT_PROVIDER', '').strip().lower()

# ========================
# 1. CREDIT APPLICATION
# ========================

def register_application_endpoints(app):
    """Register credit application endpoints"""

    offer_event_limit = int(os.getenv('OFFERS_EVENT_RATE_LIMIT_PER_MIN', '60') or 60)
    offer_event_window_sec = int(os.getenv('OFFERS_EVENT_RATE_WINDOW_SEC', '60') or 60)
    offer_event_hits = {}
    offer_event_hits_lock = Lock()

    # --- Anti-fraud in-memory state ---
    _fraud_ip_hits = {}          # ip -> [timestamp, ...]
    _fraud_lead_hits = {}        # identity -> [timestamp, ...]
    _fraud_session_seen = {}     # (session_id, event_type) -> last_ts
    _fraud_signals = []          # list of recent signal dicts (capped at 500)
    _fraud_lock = Lock()

    _FRAUD_IP_LIMIT    = int(os.getenv('FRAUD_IP_BURST_LIMIT',      '100') or 100)
    _FRAUD_IP_WINDOW   = int(os.getenv('FRAUD_IP_BURST_WINDOW_SEC', '300') or 300)
    _FRAUD_LEAD_LIMIT  = int(os.getenv('FRAUD_LEAD_BURST_LIMIT',     '5')  or 5)
    _FRAUD_LEAD_WINDOW = int(os.getenv('FRAUD_LEAD_BURST_WINDOW_SEC','600') or 600)
    _FRAUD_DEDUP_WIN   = int(os.getenv('FRAUD_SESSION_DEDUP_SEC',    '30')  or 30)

    def _fraud_signal(kind: str, key: str, detail: str):
        with _fraud_lock:
            _fraud_signals.append({
                'kind': kind, 'key': key, 'detail': detail,
                'ts': datetime.utcnow().isoformat()
            })
            if len(_fraud_signals) > 500:
                _fraud_signals.pop(0)

    def _check_ip_burst(ip: str):
        """Return True if IP is bursting too many events."""
        now = int(time.time())
        with _fraud_lock:
            hits = [t for t in _fraud_ip_hits.get(ip, []) if now - t < _FRAUD_IP_WINDOW]
            hits.append(now)
            _fraud_ip_hits[ip] = hits
            if len(hits) > _FRAUD_IP_LIMIT:
                return True
        return False

    def _check_lead_burst(identity: str):
        """Return True if user is submitting too many leads too quickly."""
        now = int(time.time())
        with _fraud_lock:
            hits = [t for t in _fraud_lead_hits.get(identity, []) if now - t < _FRAUD_LEAD_WINDOW]
            hits.append(now)
            _fraud_lead_hits[identity] = hits
            if len(hits) > _FRAUD_LEAD_LIMIT:
                return True
        return False

    def _check_session_dedup(session_id: str, event_type: str):
        """Return True if this (session_id, event_type) was already seen within dedup window (drop duplicate)."""
        if not session_id:
            return False
        now = int(time.time())
        key = f"{session_id}|{event_type}"
        with _fraud_lock:
            last = _fraud_session_seen.get(key, 0)
            if now - last < _FRAUD_DEDUP_WIN:
                return True
            _fraud_session_seen[key] = now
        return False

    def _get_fraud_stats():
        now = int(time.time())
        with _fraud_lock:
            ip_bursts = {
                ip: len([t for t in ts if now - t < _FRAUD_IP_WINDOW])
                for ip, ts in _fraud_ip_hits.items()
                if len([t for t in ts if now - t < _FRAUD_IP_WINDOW]) > 0
            }
            lead_bursts = {
                uid: len([t for t in ts if now - t < _FRAUD_LEAD_WINDOW])
                for uid, ts in _fraud_lead_hits.items()
                if len([t for t in ts if now - t < _FRAUD_LEAD_WINDOW]) > 0
            }
            recent_signals = list(_fraud_signals[-50:])

        return {
            'ip_events_active_window': ip_bursts,
            'lead_submits_active_window': lead_bursts,
            'dedup_session_keys_tracked': len(_fraud_session_seen),
            'recent_fraud_signals': recent_signals,
            'thresholds': {
                'ip_burst_limit': _FRAUD_IP_LIMIT,
                'ip_burst_window_sec': _FRAUD_IP_WINDOW,
                'lead_burst_limit': _FRAUD_LEAD_LIMIT,
                'lead_burst_window_sec': _FRAUD_LEAD_WINDOW,
                'session_dedup_window_sec': _FRAUD_DEDUP_WIN,
            },
        }

    def _is_offer_event_rate_limited(identity):
        now = int(time.time())
        key = f"{identity}|{request.remote_addr or ''}"
        with offer_event_hits_lock:
            hits = offer_event_hits.get(key, [])
            valid_hits = [ts for ts in hits if now - ts < offer_event_window_sec]
            if len(valid_hits) >= offer_event_limit:
                offer_event_hits[key] = valid_hits
                return True, max(1, offer_event_window_sec - (now - valid_hits[0]))

            valid_hits.append(now)
            offer_event_hits[key] = valid_hits
            return False, 0

    def _safe_json_object(raw_value):
        if not raw_value:
            return {}
        try:
            parsed = json.loads(raw_value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _write_offer_audit(identity, event_type, application_id, bank_code, redirect_url, consent_accepted, extra=None):
        """Write offer-funnel events to main audit log table."""
        try:
            from models import db as main_db, AuditLog as MainAuditLog, User as MainUser

            main_user = MainUser.query.filter_by(username=str(identity)).first()
            detail = {
                'application_id': application_id,
                'bank_code': bank_code,
                'redirect_url': redirect_url,
                'consent_accepted': consent_accepted,
            }
            if isinstance(extra, dict):
                detail.update(extra)

            audit_row = MainAuditLog(
                event_type=event_type,
                event_detail=json.dumps(detail, ensure_ascii=False),
                user_id=main_user.id if main_user else None,
                application_id=int(application_id) if str(application_id).isdigit() else None,
                endpoint='/api/v2/offers/event',
                method='POST',
                ip_address=request.remote_addr,
                user_agent=(request.headers.get('User-Agent') or '')[:255],
                status_code=200,
                response_time_ms=0.0,
            )
            main_db.session.add(audit_row)
            main_db.session.commit()
        except Exception as audit_exc:
            logger.warning('Offer audit write skipped: %s', audit_exc)
    
    @app.route('/api/v2/apply', methods=['POST'])
    def apply_for_credit():
        """
        Apply for credit
        POST /api/v2/apply
        {
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "+90 5XX XXX XXXX",
            "date_of_birth": "1990-01-15",
            "national_id": "12345678901",
            "employment_status": "employed",
            "annual_income": 150000,
            "requested_amount": 50000,
            "requested_term_months": 24,
            "purpose": "home"
        }
        """
        try:
            data = request.get_json()
            
            # Validate input
            required_fields = ['full_name', 'email', 'national_id', 'annual_income', 
                             'requested_amount', 'requested_term_months']
            for field in required_fields:
                if field not in data or not data[field]:
                    return {'error': f'Missing field: {field}'}, 400
            
            # Sanitize inputs
            data['full_name'] = clean(data['full_name'][:255], strip=True)
            data['email'] = clean(data['email'][:255], strip=True)
            data['national_id'] = clean(data['national_id'][:50], strip=True)
            
            # Validation
            if data['annual_income'] < 0 or data['annual_income'] > 1e9:
                return {'error': 'Invalid income amount'}, 400
            
            if data['requested_amount'] < 5000 or data['requested_amount'] > 500000:
                return {'error': 'Requested amount must be between 5000 and 500000'}, 400
            
            # Check if customer exists
            session = get_db_session()
            customer = session.query(Customer).filter_by(email=data['email']).first()
            
            if not customer:
                # Create customer
                customer = Customer(
                    email=data['email'],
                    full_name=data['full_name'],
                    phone=data.get('phone', ''),
                    date_of_birth=data.get('date_of_birth'),
                    national_id=data['national_id'],
                    annual_income=data['annual_income'],
                    employment_status=data.get('employment_status', 'employed')
                )
                session.add(customer)
                session.flush()
            
            # Load model and use metadata threshold as the single source of truth.
            model = joblib.load(PRODUCTION_MODEL_PATH)
            threshold = 0.5
            try:
                with open(PRODUCTION_META_PATH, 'r', encoding='utf-8') as f:
                    threshold = float(json.load(f).get('threshold', 0.5))
            except Exception:
                threshold = 0.5
            
            # Prepare features for model
            features = prepare_features_for_model({
                'annual_income': data['annual_income'],
                'requested_amount': data['requested_amount'],
                'requested_term_months': data['requested_term_months']
            })
            
            # Make prediction
            prediction_prob = model.predict_proba(features)[0][1]
            
            # Get income quintile for fairness tracking
            quintile = get_income_quintile(data['annual_income'])
            
            # Decision
            decision = 'approved' if prediction_prob >= threshold else 'rejected'
            
            # Create application
            application = CreditApplication(
                customer_id=customer.id,
                requested_amount=data['requested_amount'],
                requested_term_months=data['requested_term_months'],
                purpose=data.get('purpose', 'other'),
                model_prediction=float(prediction_prob),
                model_decision=decision,
                model_threshold=threshold,
                di_analysis=json.dumps({'quintile': quintile}),
                status=CreditStatusEnum.PENDING
            )
            
            if decision == 'approved':
                # Calculate terms
                approved_rate = calculate_interest_rate(
                    data['annual_income'],
                    data['requested_amount']
                )
                monthly_payment = calculate_monthly_payment(
                    data['requested_amount'],
                    approved_rate,
                    data['requested_term_months']
                )
                
                application.approved_amount = data['requested_amount']
                application.approved_rate = approved_rate
                application.approved_term_months = data['requested_term_months']
                application.status = CreditStatusEnum.APPROVED
            else:
                application.status = CreditStatusEnum.REJECTED
            
            application.decided_at = datetime.utcnow()
            
            session.add(application)
            session.commit()
            
            # Log audit
            audit = AuditLog(
                customer_id=customer.id,
                action='credit_application',
                entity_type='application',
                entity_id=application.id,
                changes=json.dumps({
                    'decision': decision,
                    'probability': float(prediction_prob)
                })
            )
            session.add(audit)
            session.commit()
            
            # Prepare response
            response = {
                'application_id': application.id,
                'decision': decision,
                'probability': float(prediction_prob),
                'message': 'BaÅŸvurunuz baÅŸarÄ±yla kaydedilmiÅŸtir'
            }
            
            if decision == 'approved':
                response.update({
                    'approved_amount': float(application.approved_amount),
                    'approved_rate': float(application.approved_rate),
                    'approved_term_months': application.approved_term_months,
                    'monthly_payment': monthly_payment
                })
            else:
                response['reason'] = 'Kredi ÅŸartlarÄ±na uygun deÄŸilsiniz'
            
            return response, 200
            
        except Exception as e:
            logger.error(f'Application error: {str(e)}')
            return {'error': str(e)}, 500
    
    
    @app.route('/api/v2/applications', methods=['GET'])
    @jwt_required()
    def get_applications():
        """Get customer's applications"""
        try:
            customer_id = get_jwt_identity()
            session = get_db_session()
            
            applications = session.query(CreditApplication)\
                .filter_by(customer_id=customer_id)\
                .order_by(CreditApplication.created_at.desc())\
                .all()
            
            return {
                'applications': [{
                    'id': app.id,
                    'requested_amount': float(app.requested_amount),
                    'status': app.status.value,
                    'created_at': app.created_at.isoformat(),
                    'approved_amount': float(app.approved_amount) if app.approved_amount else None,
                    'approved_rate': float(app.approved_rate) if app.approved_rate else None
                } for app in applications]
            }, 200
        except Exception as e:
            return {'error': str(e)}, 500


    @app.route('/api/v2/offers/mock', methods=['GET'])
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


    @app.route('/api/v2/offers/lead', methods=['POST'])
    @jwt_required()
    def submit_offer_lead():
        """Capture callback lead when no partner offers are available."""
        try:
            payload = request.get_json() or {}
            application_id = payload.get('application_id')
            full_name = clean(str(payload.get('full_name', '')).strip()[:120], strip=True)
            phone = clean(str(payload.get('phone', '')).strip()[:40], strip=True)
            email = clean(str(payload.get('email', '')).strip()[:120], strip=True)
            consent_accepted = bool(payload.get('consent_accepted', False))
            ui_language = clean(str(payload.get('ui_language', '')).strip()[:8], strip=True)

            if not consent_accepted:
                return {'error': 'consent_accepted is required'}, 400
            if not phone and not email:
                return {'error': 'phone or email is required'}, 400

            identity = get_jwt_identity()

            if _check_lead_burst(str(identity)):
                _fraud_signal('lead_burst', str(identity), f'phone={phone}')
                return {'error': 'Too many lead submissions. Please wait before trying again.', 'code': 'LEAD_BURST'}, 429

            _write_offer_audit(
                identity=identity,
                event_type='offer_lead_submit',
                application_id=application_id,
                bank_code='LEAD_FALLBACK',
                redirect_url='',
                consent_accepted=consent_accepted,
                extra={
                    'full_name': full_name,
                    'phone': phone,
                    'email': email,
                    'ui_language': ui_language,
                },
            )

            return {
                'status': 'ok',
                'message': 'Lead received. We will contact you shortly.',
                'application_id': application_id,
            }, 200
        except Exception as e:
            logger.error(f'Offer lead submit error: {str(e)}')
            return {'error': str(e)}, 500


    @app.route('/api/v2/offers/adapter-health', methods=['GET'])
    @jwt_required()
    def get_adapter_health():
        """Return reachability and configuration status for each bank adapter."""
        try:
            adapters = [AlfaBankAdapter(), NovaFinanceAdapter(), HorizonCreditAdapter()]
            results = {}

            for adapter in adapters:
                endpoint = os.getenv(adapter.endpoint_env_var, '').strip()
                if not endpoint:
                    results[adapter.bank_code] = {
                        'bank_name': adapter.bank_name,
                        'configured': False,
                        'status': 'not_configured',
                        'latency_ms': None,
                    }
                    continue

                t0 = time.time()
                try:
                    r = requests.head(endpoint, timeout=2.0)
                    latency_ms = round((time.time() - t0) * 1000, 1)
                    # 405 Method Not Allowed still means reachable
                    if r.status_code < 500 or r.status_code == 405:
                        status = 'ok'
                    else:
                        status = 'degraded'
                except Exception as exc:
                    latency_ms = round((time.time() - t0) * 1000, 1)
                    status = 'unreachable'
                    logger.warning('Adapter health check failed for %s: %s', adapter.bank_code, exc)

                results[adapter.bank_code] = {
                    'bank_name': adapter.bank_name,
                    'configured': True,
                    'status': status,
                    'latency_ms': latency_ms,
                }

            configured = [v for v in results.values() if v['configured']]
            if not configured:
                overall = 'mock_only'
            elif all(v['status'] == 'unreachable' for v in configured):
                overall = 'degraded'
            elif any(v['status'] == 'unreachable' for v in configured):
                overall = 'partial'
            else:
                overall = 'healthy'

            return {
                'overall': overall,
                'mock_fallback_active': len(configured) == 0,
                'adapters': results,
                'timestamp': datetime.utcnow().isoformat(),
            }, 200
        except Exception as e:
            logger.error(f'Adapter health check error: {str(e)}')
            return {'error': str(e)}, 500


    @app.route('/api/v2/offers/ab-variant', methods=['GET'])
    @jwt_required()
    def get_ab_variant():
        """Return deterministic A/B test variant for the authenticated user."""
        try:
            identity = get_jwt_identity()
            ab_split = max(0, min(100, int(os.getenv('OFFERS_AB_SPLIT_PERCENT', '50') or 50)))
            bucket = binascii.crc32(str(identity).encode()) % 100
            variant = 'B' if bucket < ab_split else 'A'

            return {
                'variant': variant,
                'bucket': bucket,
                'ab_split_percent': ab_split,
                'variant_a_description': 'Default: sorted by lowest monthly payment',
                'variant_b_description': 'Confidence-first: sorted by confidence_score desc, then monthly payment asc',
            }, 200
        except Exception as e:
            logger.error(f'A/B variant error: {str(e)}')
            return {'error': str(e)}, 500


    @app.route('/api/v2/offers/fraud-stats', methods=['GET'])
    @jwt_required()
    def get_offer_fraud_stats():
        """Return current anti-fraud signal state. Intended for admin/ops use."""
        try:
            claims = get_jwt() or {}
            if str(claims.get('role', '')).lower() != 'admin':
                return {'error': 'Admin role required'}, 403

            return {
                'status': 'ok',
                'fraud_guard': _get_fraud_stats(),
                'timestamp': datetime.utcnow().isoformat(),
            }, 200
        except Exception as e:
            logger.error(f'Fraud stats error: {str(e)}')
            return {'error': str(e)}, 500


    @app.route('/api/v2/offers/click', methods=['POST'])
    @jwt_required()
    def track_offer_click():
        """Track offer click events for funnel analytics."""
        try:
            payload = request.get_json() or {}
            application_id = payload.get('application_id')
            bank_code = str(payload.get('bank_code', '')).strip()
            redirect_url = str(payload.get('redirect_url', '')).strip()
            consent_accepted = bool(payload.get('consent_accepted', False))

            if not bank_code:
                return {'error': 'bank_code is required'}, 400
            if not redirect_url:
                return {'error': 'redirect_url is required'}, 400

            identity = get_jwt_identity()

            _write_offer_audit(
                identity=identity,
                event_type='offer_click',
                application_id=application_id,
                bank_code=bank_code,
                redirect_url=redirect_url,
                consent_accepted=consent_accepted,
            )

            return {
                'status': 'ok',
                'tracked': True,
                'application_id': application_id,
                'bank_code': bank_code
            }, 200
        except Exception as e:
            logger.error(f'Offer click tracking error: {str(e)}')
            return {'error': str(e)}, 500


    @app.route('/api/v2/offers/event', methods=['POST'])
    @jwt_required()
    def track_offer_event():
        """Track offer funnel events: offers_view, offers_redirect_start, offer_click."""
        try:
            identity = get_jwt_identity()
            blocked, retry_after = _is_offer_event_rate_limited(identity)
            if blocked:
                return {
                    'error': 'Rate limit exceeded for offers events',
                    'retry_after_sec': retry_after
                }, 429

            ip = request.remote_addr or ''
            if _check_ip_burst(ip):
                _fraud_signal('ip_burst', ip, f'user={identity}')
                return {'error': 'Too many requests from this IP', 'code': 'IP_BURST'}, 429

            payload = request.get_json() or {}
            event_type = str(payload.get('event_type', '')).strip().lower()
            allowed = {'offers_view', 'offers_redirect_start', 'offer_click'}
            if event_type not in allowed:
                return {'error': 'Invalid event_type'}, 400

            application_id = payload.get('application_id')
            bank_code = str(payload.get('bank_code', '')).strip()
            redirect_url = str(payload.get('redirect_url', '')).strip()
            consent_accepted = bool(payload.get('consent_accepted', False))
            extra = payload.get('extra') if isinstance(payload.get('extra'), dict) else {}

            # Session dedup: silently drop same (session_id, event_type) within dedup window
            session_id = str(extra.get('session_id', '') or payload.get('session_id', '') or '')
            if session_id and _check_session_dedup(session_id, event_type):
                return {
                    'status': 'ok',
                    'tracked': False,
                    'deduped': True,
                    'event_type': event_type,
                    'application_id': application_id,
                }, 200

            if session_id:
                extra['session_id'] = session_id

            _write_offer_audit(
                identity=identity,
                event_type=event_type,
                application_id=application_id,
                bank_code=bank_code,
                redirect_url=redirect_url,
                consent_accepted=consent_accepted,
                extra=extra,
            )

            return {
                'status': 'ok',
                'tracked': True,
                'event_type': event_type,
                'application_id': application_id,
            }, 200
        except Exception as e:
            logger.error(f'Offer event tracking error: {str(e)}')
            return {'error': str(e)}, 500


    @app.route('/api/v2/offers/funnel-report', methods=['GET'])
    @jwt_required()
    def get_offer_funnel_report():
        """Return compact funnel metrics from audit events."""
        try:
            days = int(request.args.get('days', 7) or 7)
            days = max(1, min(days, 90))
            include_legacy_raw = str(request.args.get('include_legacy', 'true')).strip().lower()
            include_legacy = include_legacy_raw in ('1', 'true', 'yes', 'y', 'on')

            application_id_raw = str(request.args.get('application_id', '')).strip()
            application_id = int(application_id_raw) if application_id_raw.isdigit() else None

            since = datetime.utcnow() - timedelta(days=days)
            allowed = ('offers_view', 'offers_redirect_start', 'offer_click')

            from models import AuditLog as MainAuditLog

            query = MainAuditLog.query.filter(
                MainAuditLog.event_type.in_(allowed),
                MainAuditLog.created_at >= since,
            )
            if application_id is not None:
                query = query.filter(MainAuditLog.application_id == application_id)

            rows = query.order_by(MainAuditLog.created_at.asc()).all()

            counts = {
                'offers_view': 0,
                'offers_redirect_start': 0,
                'offer_click': 0,
            }
            unique_sessions = set()
            session_event_flags = {}
            events_without_session = 0
            bank_clicks = {}

            for row in rows:
                detail = {}
                if row.event_detail:
                    try:
                        detail = json.loads(row.event_detail)
                    except Exception:
                        detail = {}

                session_id = detail.get('session_id')
                if session_id:
                    session_key = str(session_id)
                    unique_sessions.add(session_key)
                    if session_key not in session_event_flags:
                        session_event_flags[session_key] = set()
                    session_event_flags[session_key].add(row.event_type)
                else:
                    events_without_session += 1
                    if not include_legacy:
                        continue

                if row.event_type in counts:
                    counts[row.event_type] += 1

                if row.event_type == 'offer_click':
                    bank_code = str(detail.get('bank_code', '')).strip()
                    if bank_code:
                        bank_clicks[bank_code] = bank_clicks.get(bank_code, 0) + 1

            session_counts = {
                'offers_view': sum(1 for flags in session_event_flags.values() if 'offers_view' in flags),
                'offers_redirect_start': sum(1 for flags in session_event_flags.values() if 'offers_redirect_start' in flags),
                'offer_click': sum(1 for flags in session_event_flags.values() if 'offer_click' in flags),
            }

            raw_views = counts['offers_view']
            raw_starts = counts['offers_redirect_start']
            raw_clicks = counts['offer_click']

            session_views = session_counts['offers_view']
            session_starts = session_counts['offers_redirect_start']
            session_clicks = session_counts['offer_click']

            use_session_dedup = session_views > 0
            views = session_views if use_session_dedup else raw_views
            starts = session_starts if use_session_dedup else raw_starts
            clicks = session_clicks if use_session_dedup else raw_clicks

            view_to_start = round((starts / views) * 100, 2) if views else None
            start_to_click = round((clicks / starts) * 100, 2) if starts else None
            view_to_click = round((clicks / views) * 100, 2) if views else None

            top_banks = sorted(
                [{'bank_code': k, 'click_count': v} for k, v in bank_clicks.items()],
                key=lambda x: x['click_count'],
                reverse=True,
            )[:10]
            adapter_stats = get_offer_adapter_stats()

            return {
                'status': 'ok',
                'period_days': days,
                'since_utc': since.isoformat(),
                'application_id': application_id,
                'include_legacy': include_legacy,
                'counts': counts,
                'session_counts': session_counts,
                'unique_sessions': len(unique_sessions),
                'events_without_session': events_without_session,
                'conversion_rates_percent': {
                    'view_to_redirect_start': view_to_start,
                    'redirect_start_to_click': start_to_click,
                    'view_to_click': view_to_click,
                },
                'conversion_source': 'session_dedup' if use_session_dedup else 'raw_events',
                'top_banks_by_clicks': top_banks,
            }, 200
        except Exception as e:
            logger.error(f'Offer funnel report error: {str(e)}')
            return {'error': str(e)}, 500


    @app.route('/api/v2/offers/funnel-dashboard', methods=['GET'])
    @jwt_required()
    def get_offer_funnel_dashboard():
        """Return dashboard-friendly funnel analytics with trend and breakdowns."""
        try:
            days = int(request.args.get('days', 14) or 14)
            days = max(1, min(days, 90))
            include_legacy_raw = str(request.args.get('include_legacy', 'true')).strip().lower()
            include_legacy = include_legacy_raw in ('1', 'true', 'yes', 'y', 'on')

            application_id_raw = str(request.args.get('application_id', '')).strip()
            application_id = int(application_id_raw) if application_id_raw.isdigit() else None

            since = datetime.utcnow() - timedelta(days=days)
            allowed = ('offers_view', 'offers_redirect_start', 'offer_click')

            from models import AuditLog as MainAuditLog

            query = MainAuditLog.query.filter(
                MainAuditLog.event_type.in_(allowed),
                MainAuditLog.created_at >= since,
            )
            if application_id is not None:
                query = query.filter(MainAuditLog.application_id == application_id)

            rows = query.order_by(MainAuditLog.created_at.asc()).all()

            day_counts = {}
            lang_counts = {}
            bank_clicks = {}
            unique_sessions = set()
            session_event_flags = {}
            events_without_session = 0

            for row in rows:
                detail = _safe_json_object(row.event_detail)

                session_id = detail.get('session_id')
                if session_id:
                    session_key = str(session_id)
                    unique_sessions.add(session_key)
                    if session_key not in session_event_flags:
                        session_event_flags[session_key] = set()
                    session_event_flags[session_key].add(row.event_type)
                else:
                    events_without_session += 1
                    if not include_legacy:
                        continue

                day_key = row.created_at.strftime('%Y-%m-%d') if row.created_at else 'unknown'
                if day_key not in day_counts:
                    day_counts[day_key] = {
                        'offers_view': 0,
                        'offers_redirect_start': 0,
                        'offer_click': 0,
                    }
                if row.event_type in day_counts[day_key]:
                    day_counts[day_key][row.event_type] += 1

                ui_lang = str(detail.get('ui_language', 'unknown') or 'unknown').lower()
                lang_counts[ui_lang] = lang_counts.get(ui_lang, 0) + 1

                if row.event_type == 'offer_click':
                    bank_code = str(detail.get('bank_code', '')).strip() or 'UNKNOWN_BANK'
                    bank_clicks[bank_code] = bank_clicks.get(bank_code, 0) + 1

            trend = []
            for day_key in sorted(day_counts.keys()):
                views = day_counts[day_key]['offers_view']
                starts = day_counts[day_key]['offers_redirect_start']
                clicks = day_counts[day_key]['offer_click']
                trend.append({
                    'date': day_key,
                    'offers_view': views,
                    'offers_redirect_start': starts,
                    'offer_click': clicks,
                    'view_to_click_percent': round((clicks / views) * 100, 2) if views else None,
                })

            session_counts = {
                'offers_view': sum(1 for flags in session_event_flags.values() if 'offers_view' in flags),
                'offers_redirect_start': sum(1 for flags in session_event_flags.values() if 'offers_redirect_start' in flags),
                'offer_click': sum(1 for flags in session_event_flags.values() if 'offer_click' in flags),
            }

            top_languages = sorted(
                [{'ui_language': k, 'event_count': v} for k, v in lang_counts.items()],
                key=lambda x: x['event_count'],
                reverse=True,
            )[:10]
            top_banks = sorted(
                [{'bank_code': k, 'click_count': v} for k, v in bank_clicks.items()],
                key=lambda x: x['click_count'],
                reverse=True,
            )[:10]
            adapter_stats = get_offer_adapter_stats()

            return {
                'status': 'ok',
                'period_days': days,
                'since_utc': since.isoformat(),
                'application_id': application_id,
                'include_legacy': include_legacy,
                'events_without_session': events_without_session,
                'unique_sessions': len(unique_sessions),
                'session_counts': session_counts,
                'trend_daily': trend,
                'top_languages_by_events': top_languages,
                'top_banks_by_clicks': top_banks,
                'adapter_stats': adapter_stats,
            }, 200
        except Exception as e:
            logger.error(f'Offer funnel dashboard error: {str(e)}')
            return {'error': str(e)}, 500


    @app.route('/api/v2/ai-risk-explanation', methods=['POST'])
    @jwt_required()
    def ai_risk_explanation():
        """
        Generate natural-language risk explanation for analysts.

        Request JSON:
        {
            "application_id": 123,                  # optional
            "model_prediction": 0.72,               # required if application_id not provided
            "customer_data": {                      # optional
                "annual_income": 65000,
                "requested_amount": 45000,
                "requested_term_months": 24,
                "employment_status": "employed",
                "cb_person_cred_hist_length": 3
            }
        }
        """
        try:
            customer_id = get_jwt_identity()
            payload = request.get_json() or {}
            session = get_db_session()

            model_prediction = payload.get('model_prediction')
            customer_data = payload.get('customer_data') or {}
            application_id = payload.get('application_id')

            if application_id is not None:
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
                    # Fallback to main Flask-SQLAlchemy application records.
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
                return {'error': 'model_prediction must be a numeric value'}, 400

            if model_prediction < 0.0 or model_prediction > 1.0:
                return {'error': 'model_prediction must be between 0 and 1'}, 400

            explanation_payload = build_ai_risk_explanation(model_prediction, customer_data)

            return {
                'application_id': application_id,
                'model_prediction': model_prediction,
                'risk_level': explanation_payload['risk_level'],
                'ai_risk_explanation': explanation_payload['explanation'],
                'key_factors': explanation_payload['key_factors'],
                'recommendation': explanation_payload['recommendation']
            }, 200
        except Exception as e:
            logger.error(f'AI risk explanation error: {str(e)}')
            return {'error': str(e)}, 500


    @app.route('/api/v2/fairness-summary', methods=['POST'])
    @jwt_required()
    def fairness_summary():
        """
        Summarize fairness metrics in analyst-friendly language.

        Request JSON:
        {
            "approval_rates": {"Q1": 54.7, "Q2": 60.1, "Q3": 68.2, "Q4": 74.3, "Q5": 87.1},
            "demographic_parity_difference": 0.07,   # optional
            "equal_opportunity_difference": 0.05     # optional
        }
        """
        try:
            payload = request.get_json() or {}
            approval_rates = payload.get('approval_rates')

            if not isinstance(approval_rates, dict):
                return {'error': 'approval_rates is required and must be a JSON object'}, 400

            required_quintiles = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']
            missing = [q for q in required_quintiles if q not in approval_rates]
            if missing:
                return {'error': f'Missing approval rate(s): {", ".join(missing)}'}, 400

            normalized_rates = {}
            for q in required_quintiles:
                try:
                    normalized_rates[q] = float(approval_rates[q])
                except (TypeError, ValueError):
                    return {'error': f'approval_rates.{q} must be numeric'}, 400

            check = fairness_monitor.check_fairness(normalized_rates)
            interpretation = build_fairness_interpretation(
                check.q1_vs_q5_ratio,
                payload.get('demographic_parity_difference'),
                payload.get('equal_opportunity_difference'),
                check.passes_80_rule,
                check.alert_triggered
            )

            response = {
                'summary': {
                    'status': 'compliant' if check.passes_80_rule else 'non_compliant',
                    'risk_level': interpretation['risk_level'],
                    'passes_80_percent_rule': check.passes_80_rule,
                    'alert_triggered': check.alert_triggered,
                },
                'metrics': {
                    'approval_rates': normalized_rates,
                    'disparate_impact_ratio': check.q1_vs_q5_ratio,
                    'q1_vs_q5_ratio': check.q1_vs_q5_ratio,
                    'demographic_parity_difference': payload.get('demographic_parity_difference'),
                    'equal_opportunity_difference': payload.get('equal_opportunity_difference'),
                },
                'interpretation': interpretation['text'],
                'compliance_notes': interpretation['compliance_notes'],
                'recommended_actions': interpretation['recommended_actions'],
            }

            if check.recommendation:
                response['recommended_actions'].append(check.recommendation)
            if check.alert_reason:
                response['alert_reason'] = check.alert_reason

            return response, 200
        except Exception as e:
            logger.error(f'Fairness summary error: {str(e)}')
            return {'error': str(e)}, 500


    @app.route('/api/v2/ai-risk-assistant', methods=['POST'])
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
    
    @app.route('/api/v2/payments/plan', methods=['POST'])
    @jwt_required()
    def create_payment_plan():
        """Create payment plan for approved credit"""
        try:
            customer_id = get_jwt_identity()
            data = request.get_json()
            
            required = ['credit_id', 'amount', 'monthly_rate', 'months']
            if not all(f in data for f in required):
                return {'error': 'Missing required fields'}, 400
            
            session = get_db_session()
            
            # Get credit
            credit = session.query(Credit)\
                .filter_by(id=data['credit_id'], customer_id=customer_id)\
                .first()
            
            if not credit:
                return {'error': 'Credit not found'}, 404
            
            # Create Stripe customer if needed
            customer = session.query(Customer).get(customer_id)
            if not customer.stripe_customer_id:
                stripe_customer = payment_processor.create_customer(
                    email=customer.email,
                    name=customer.full_name
                )
                customer.stripe_customer_id = stripe_customer['id']
                session.commit()
            
            # Calculate installments
            monthly_payment = payment_processor.calculate_installment(
                principal=data['amount'],
                annual_rate=data['monthly_rate'],
                months=data['months']
            )
            
            # Create Stripe subscription
            subscription = payment_processor.create_installment_plan(
                customer_id=customer.stripe_customer_id,
                amount=monthly_payment,
                months=data['months']
            )
            
            # Create installment records
            start_date = datetime.utcnow()
            for i in range(1, data['months'] + 1):
                due_date = start_date + timedelta(days=30*i)
                installment = Installment(
                    credit_id=credit.id,
                    installment_number=i,
                    total_due=monthly_payment,
                    due_date=due_date,
                    status=InstallmentStatusEnum.PENDING
                )
                session.add(installment)
            
            session.commit()
            
            return {
                'subscription_id': subscription['id'],
                'monthly_payment': monthly_payment,
                'total_months': data['months'],
                'total_amount': monthly_payment * data['months']
            }, 201
            
        except Exception as e:
            logger.error(f'Payment plan error: {str(e)}')
            return {'error': str(e)}, 500
    
    
    @app.route('/api/v2/payments/charge', methods=['POST'])
    @jwt_required()
    def charge_payment():
        """Charge installment payment"""
        try:
            customer_id = get_jwt_identity()
            data = request.get_json()
            
            if 'installment_id' not in data or 'amount' not in data:
                return {'error': 'Missing fields'}, 400
            
            session = get_db_session()
            
            # Get installment
            installment = session.query(Installment)\
                .filter_by(id=data['installment_id'])\
                .first()
            
            if not installment:
                return {'error': 'Installment not found'}, 404
            
            # Get customer's Stripe ID
            customer = session.query(Customer).get(customer_id)
            if not customer.stripe_customer_id:
                return {'error': 'Customer not found'}, 404
            
            # Charge with Stripe
            charge = payment_processor.charge_installment(
                customer_id=customer.stripe_customer_id,
                amount=data['amount'],
                description=f"Installment {installment.installment_number}"
            )
            
            # Create payment record
            payment = Payment(
                customer_id=customer_id,
                installment_id=installment.id,
                amount=data['amount'],
                stripe_charge_id=charge['id'],
                status='succeeded',
                processed_at=datetime.utcnow()
            )
            session.add(payment)
            
            # Update installment
            installment.paid_amount = data['amount']
            installment.status = InstallmentStatusEnum.PAID
            installment.paid_date = datetime.utcnow()
            
            # Update credit
            credit = installment.credit
            credit.total_paid += data['amount']
            credit.payments_completed += 1
            
            # Audit log
            audit = AuditLog(
                customer_id=customer_id,
                action='payment',
                entity_type='payment',
                entity_id=payment.id,
                changes=json.dumps({'amount': data['amount']})
            )
            session.add(audit)
            session.commit()
            
            return {
                'payment_id': payment.id,
                'charge_id': charge['id'],
                'status': 'succeeded',
                'amount': data['amount']
            }, 200
            
        except Exception as e:
            logger.error(f'Charge error: {str(e)}')
            return {'error': str(e)}, 500
    
    
    # ========================
    # 3. CUSTOMER DASHBOARD
    # ========================
    
    @app.route('/api/v2/customer/dashboard', methods=['GET'])
    @jwt_required()
    def get_customer_dashboard():
        """Get customer dashboard data"""
        try:
            customer_id = get_jwt_identity()
            session = get_db_session()
            
            customer = session.query(Customer).get(customer_id)
            if not customer:
                return {'error': 'Customer not found'}, 404
            
            # Get active credits
            credits = session.query(Credit)\
                .filter_by(customer_id=customer_id, status=CreditStatusEnum.ACTIVE)\
                .all()
            
            # Get upcoming installments
            installments = session.query(Installment)\
                .join(Credit)\
                .filter(Credit.customer_id == customer_id)\
                .order_by(Installment.due_date)\
                .limit(10)\
                .all()
            
            # Calculate stats
            total_debt = sum(c.principal_amount - c.total_paid for c in credits)
            monthly_payment = sum(c.monthly_payment for c in credits)
            next_due = min([i.due_date for i in installments], default=None)
            
            return {
                'customer': {
                    'id': customer.id,
                    'full_name': customer.full_name,
                    'email': customer.email,
                    'phone': customer.phone,
                    'annual_income': customer.annual_income,
                    'employment_status': customer.employment_status,
                    'created_at': customer.created_at.isoformat()
                },
                'stats': {
                    'active_credits': len(credits),
                    'total_debt': total_debt,
                    'monthly_payment': monthly_payment,
                    'next_due_date': next_due.strftime('%d.%m.%Y') if next_due else None
                },
                'credits': [{
                    'id': c.id,
                    'principal_amount': float(c.principal_amount),
                    'interest_rate_annual': float(c.interest_rate_annual or 0),
                    'term_months': c.term_months,
                    'monthly_payment': float(c.monthly_payment),
                    'disbursed_date': c.disbursed_date.isoformat() if c.disbursed_date else None,
                    'maturity_date': c.maturity_date.isoformat() if c.maturity_date else None,
                    'total_paid': float(c.total_paid),
                    'payments_completed': c.payments_completed,
                    'status': c.status.value
                } for c in credits],
                'installments': [{
                    'id': i.id,
                    'installment_number': i.installment_number,
                    'due_date': i.due_date.isoformat(),
                    'total_due': float(i.total_due),
                    'paid_amount': float(i.paid_amount),
                    'status': i.status.value
                } for i in installments]
            }, 200
            
        except Exception as e:
            logger.error(f'Dashboard error: {str(e)}')
            return {'error': str(e)}, 500


# ========================
# HELPER FUNCTIONS
# ========================

def prepare_features_for_model(data):
    """Prepare features for ML model"""
    # This should match your model's expected feature format
    income_quintile = get_income_quintile(data['annual_income'])
    
    features = np.array([[
        data['annual_income'],
        data['requested_amount'],
        data['requested_term_months'],
        income_quintile
    ]])
    
    return features


def get_income_quintile(annual_income):
    """Get income quintile (1-5)"""
    # These should be calibrated based on your dataset
    quintile_boundaries = [0, 50000, 100000, 150000, 200000]
    for i, boundary in enumerate(quintile_boundaries):
        if annual_income < boundary:
            return i
    return 5


def calculate_interest_rate(annual_income, requested_amount):
    """Calculate interest rate based on risk"""
    # Risk-based pricing
    base_rate = 0.12  # 12% base
    
    # Income factor
    if annual_income < 50000:
        base_rate += 0.05
    elif annual_income < 100000:
        base_rate += 0.03
    elif annual_income > 250000:
        base_rate -= 0.03
    
    # Amount factor
    if requested_amount > 100000:
        base_rate -= 0.02
    
    return min(max(base_rate, 0.05), 0.25)  # 5% - 25% range


def calculate_monthly_payment(principal, annual_rate, months):
    """Calculate monthly payment (amortization formula)"""
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return principal / months
    
    payment = principal * (monthly_rate * (1 + monthly_rate)**months) / \
              ((1 + monthly_rate)**months - 1)
    return round(payment, 2)


def build_ai_risk_explanation(model_prediction, customer_data):
    """Build deterministic, natural-language risk explanation from model output + customer features."""
    income = float(customer_data.get('annual_income', 0.0) or 0.0)
    amount = float(customer_data.get('requested_amount', 0.0) or 0.0)
    term = int(customer_data.get('requested_term_months', 0) or 0)
    employment_status = str(customer_data.get('employment_status', 'unknown') or 'unknown').lower()
    credit_history = float(customer_data.get('cb_person_cred_hist_length', 0.0) or 0.0)

    dti_like = (amount / max(income, 1.0)) if income > 0 else 999.0
    key_factors = []

    if dti_like >= 0.8:
        key_factors.append('Requested amount is high relative to annual income')
    elif dti_like <= 0.25:
        key_factors.append('Requested amount is moderate relative to annual income')

    if credit_history > 0 and credit_history < 3:
        key_factors.append('Limited credit history increases uncertainty')
    elif credit_history >= 8:
        key_factors.append('Longer credit history supports repayment stability')

    if employment_status in ('unemployed', 'temporary', 'part-time'):
        key_factors.append('Employment profile may indicate income instability')
    elif employment_status in ('employed', 'self-employed'):
        key_factors.append('Employment profile indicates regular income potential')

    if term >= 48:
        key_factors.append('Long repayment term may increase lifecycle risk')

    if model_prediction >= 0.7:
        risk_level = 'high'
        recommendation = 'Manual review recommended; request additional collateral or guarantor.'
        explanation = (
            f'Applicant is assessed as high risk (default probability {model_prediction:.1%}). '
            'Primary drivers suggest elevated repayment risk under current credit terms.'
        )
    elif model_prediction >= 0.4:
        risk_level = 'medium'
        recommendation = 'Consider adjusted pricing and tighter affordability checks.'
        explanation = (
            f'Applicant is assessed as medium risk (default probability {model_prediction:.1%}). '
            'Decision should consider affordability sensitivity and policy constraints.'
        )
    else:
        risk_level = 'low'
        recommendation = 'Eligible for standard underwriting flow.'
        explanation = (
            f'Applicant is assessed as low risk (default probability {model_prediction:.1%}). '
            'Current profile indicates relatively stable repayment capacity.'
        )

    if not key_factors:
        key_factors.append('Prediction is driven by combined model features without a single dominant factor')

    return {
        'risk_level': risk_level,
        'explanation': explanation,
        'key_factors': key_factors,
        'recommendation': recommendation,
    }


def build_fairness_interpretation(di_ratio, dp_diff, eo_diff, passes_80_rule, alert_triggered):
    """Create deterministic natural-language interpretation for fairness metrics."""
    recommended_actions = []
    compliance_notes = []

    if passes_80_rule:
        risk_level = 'low'
        base_text = (
            f'Disparate Impact ratio is {di_ratio:.3f}, which is above the 80% rule threshold. '
            'Current approval distribution is broadly aligned with fair-lending baseline.'
        )
        compliance_notes.append('ECOA 80% rule check: PASS')
    else:
        risk_level = 'high' if di_ratio < 0.70 else 'medium'
        base_text = (
            f'Disparate Impact ratio is {di_ratio:.3f}, below the 80% rule threshold. '
            'This indicates potential disparity between lower and higher income quintiles.'
        )
        compliance_notes.append('ECOA 80% rule check: FAIL')
        recommended_actions.append('Review threshold policy and segment-level approval cutoffs')
        recommended_actions.append('Trigger manual compliance review for recent declined applications in Q1')

    if dp_diff is not None:
        try:
            dp_diff = float(dp_diff)
            compliance_notes.append(f'Demographic parity difference: {dp_diff:.3f}')
            if dp_diff > 0.10:
                recommended_actions.append('Demographic parity gap is elevated; run targeted bias remediation')
        except (TypeError, ValueError):
            compliance_notes.append('Demographic parity difference: invalid input ignored')

    if eo_diff is not None:
        try:
            eo_diff = float(eo_diff)
            compliance_notes.append(f'Equal opportunity difference: {eo_diff:.3f}')
            if eo_diff > 0.10:
                recommended_actions.append('Equal opportunity gap is elevated; inspect false negative disparities')
        except (TypeError, ValueError):
            compliance_notes.append('Equal opportunity difference: invalid input ignored')

    if alert_triggered:
        if risk_level == 'low':
            risk_level = 'medium'
        recommended_actions.append('Escalate to fairness monitoring workflow and schedule follow-up audit')

    if not recommended_actions:
        recommended_actions.append('Continue monthly fairness monitoring with current thresholds')

    return {
        'risk_level': risk_level,
        'text': base_text,
        'compliance_notes': compliance_notes,
        'recommended_actions': recommended_actions,
    }


def build_ai_assistant_response(question, model_prediction, customer_data, fairness_context):
    """Generate deterministic analyst-style answer grounded on local model/fairness context."""
    q = question.lower()

    risk_pack = build_ai_risk_explanation(model_prediction, customer_data)
    di_ratio = fairness_context.get('disparate_impact_ratio')
    dp_diff = fairness_context.get('demographic_parity_difference')
    eo_diff = fairness_context.get('equal_opportunity_difference')

    evidence = []
    evidence.append(f"Model default probability: {model_prediction:.1%}")
    evidence.extend(risk_pack['key_factors'][:3])

    # Why rejected / why high risk
    if ('why' in q and 'reject' in q) or ('neden' in q and ('red' in q or 'redded' in q)):
        answer = (
            f"Başvuru yüksek risk bandında değerlendirildi ({model_prediction:.1%}). "
            f"Ana nedenler: {', '.join(risk_pack['key_factors'][:2])}."
        )
        return {
            'answer_type': 'decision_explanation',
            'answer': answer,
            'confidence': 'high',
            'evidence': evidence,
            'next_actions': [
                'Manuel inceleme başlat',
                'Ek gelir/teminat belgesi talep et',
                risk_pack['recommendation']
            ]
        }

    # Which factors increased risk
    if ('factor' in q and 'risk' in q) or ('hangi' in q and ('risk' in q or 'fakt' in q)):
        answer = (
            f"Riski artıran başlıca faktörler: {', '.join(risk_pack['key_factors'][:3])}. "
            f"Mevcut risk seviyesi: {risk_pack['risk_level']}."
        )
        return {
            'answer_type': 'risk_factors',
            'answer': answer,
            'confidence': 'high',
            'evidence': evidence,
            'next_actions': [
                'Fiyatlama ve vade koşullarını yeniden değerlendir',
                'Alternatif kredi limiti öner'
            ]
        }

    # Fairness-focused question
    if 'fair' in q or 'bias' in q or 'adil' in q:
        fairness_evidence = []
        if di_ratio is not None:
            try:
                di_ratio = float(di_ratio)
                fairness_evidence.append(f"Disparate Impact ratio: {di_ratio:.3f}")
            except (TypeError, ValueError):
                pass
        if dp_diff is not None:
            fairness_evidence.append(f"Demographic parity difference: {dp_diff}")
        if eo_diff is not None:
            fairness_evidence.append(f"Equal opportunity difference: {eo_diff}")

        if isinstance(di_ratio, float) and di_ratio >= 0.80:
            fairness_answer = '80% kuralı açısından model uygun görünüyor; yine de periyodik izleme sürdürülmeli.'
            fairness_actions = ['Aylık fairness audit çalıştır', 'Q1/Q5 oran trendini izle']
        elif isinstance(di_ratio, float):
            fairness_answer = '80% kuralı açısından potansiyel fairness riski var; eşik ve segment bazlı kararlar gözden geçirilmeli.'
            fairness_actions = ['Uyum ekibine eskalasyon', 'Q1 red kararları için manuel gözden geçirme']
        else:
            fairness_answer = 'Fairness değerlendirmesi için DI ratio gibi metrikler paylaşılmalı.'
            fairness_actions = ['fairness_summary endpoint çıktısını bu çağrıya ekle']

        return {
            'answer_type': 'fairness_assessment',
            'answer': fairness_answer,
            'confidence': 'medium' if fairness_evidence else 'low',
            'evidence': fairness_evidence or ['No fairness metrics provided'],
            'next_actions': fairness_actions
        }

    # Generic fallback
    answer = (
        f"Model riski {model_prediction:.1%} olarak hesapladı ve risk seviyesi '{risk_pack['risk_level']}' görünüyor. "
        "Daha hedefli bir yanıt için karar/fairness/risk faktörleri hakkında daha spesifik soru sorabilirsiniz."
    )
    return {
        'answer_type': 'general_guidance',
        'answer': answer,
        'confidence': 'medium',
        'evidence': evidence,
        'next_actions': ['Soru tipini netleştir: neden red, hangi faktörler, fairness durumu']
    }


def maybe_generate_llm_assistant_answer(question, model_prediction, customer_data, fairness_context, deterministic_result):
    """Optionally refine assistant answer via LLM if provider/key are configured."""
    if AI_ASSISTANT_PROVIDER not in ('openai', 'anthropic'):
        return None

    try:
        if AI_ASSISTANT_PROVIDER == 'openai':
            return _call_openai_assistant(question, model_prediction, customer_data, fairness_context, deterministic_result)
        return _call_anthropic_assistant(question, model_prediction, customer_data, fairness_context, deterministic_result)
    except Exception as exc:
        logger.warning(f'LLM assistant fallback to deterministic mode: {exc}')
        return None


def _build_llm_prompt(question, model_prediction, customer_data, fairness_context, deterministic_result):
    """Build grounded prompt so generated text stays tied to numeric evidence."""
    context = {
        'question': question,
        'model_prediction': model_prediction,
        'customer_data': customer_data,
        'fairness_context': fairness_context,
        'deterministic_answer': deterministic_result,
    }
    return (
        'You are a credit risk analyst assistant. Use only the provided JSON context. '
        'Do not invent facts. Keep response concise (max 4 sentences) and compliance-aware. '
        'If information is missing, explicitly state it. '\
        '\n\nContext JSON:\n' + json.dumps(context, ensure_ascii=False)
    )


def _call_openai_assistant(question, model_prediction, customer_data, fairness_context, deterministic_result):
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key:
        return None

    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini').strip()
    prompt = _build_llm_prompt(question, model_prediction, customer_data, fairness_context, deterministic_result)

    response = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        json={
            'model': model,
            'temperature': 0.2,
            'messages': [
                {'role': 'system', 'content': 'You are a cautious financial risk assistant.'},
                {'role': 'user', 'content': prompt},
            ],
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    choices = data.get('choices', [])
    if not choices:
        return None
    return choices[0].get('message', {}).get('content', '').strip() or None


def _call_anthropic_assistant(question, model_prediction, customer_data, fairness_context, deterministic_result):
    api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        return None

    model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-latest').strip()
    prompt = _build_llm_prompt(question, model_prediction, customer_data, fairness_context, deterministic_result)

    response = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json',
        },
        json={
            'model': model,
            'max_tokens': 220,
            'temperature': 0.2,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    content = data.get('content', [])
    if not content:
        return None
    first = content[0]
    if isinstance(first, dict):
        return first.get('text', '').strip() or None
    return None


if __name__ == '__main__':
    print('API routes defined')

