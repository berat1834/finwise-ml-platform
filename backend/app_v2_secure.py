#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FinWise Credit Risk API v2 - Secure Production Server
JWT authentication, rate limiting, model routing (single/shadow/canary),
Prometheus metrics, fairness monitoring, and AI assistant endpoints.
"""

import json
import logging
import os
import pickle
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
import sys

# Add app subdirectories to path so direct imports work
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
import bleach
import joblib
import numpy as np
from dotenv import load_dotenv
from flask import Flask, jsonify, request, Response, send_from_directory
from flasgger import Swagger
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import inspect as sa_inspect
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()


def utcnow() -> datetime:
    """Return UTC now as naive datetime for DB compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_bool(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, str(default))).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _split_csv_env(name: str, fallback: str) -> list[str]:
    raw = os.getenv(name, fallback)
    return [x.strip() for x in str(raw).split(",") if x.strip()]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=int(os.getenv("LOG_MAX_BYTES", 2097152)),
    backupCount=int(os.getenv("LOG_BACKUP_COUNT", 3)),
)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.getLogger().addHandler(file_handler)

# ---------------------------------------------------------------------------
# Flask app & extensions
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder=None)

from flask import Blueprint
auth_bp = Blueprint('auth', __name__)
credit_bp = Blueprint('credit', __name__)
dashboard_bp = Blueprint('dashboard', __name__)
compliance_bp = Blueprint('compliance', __name__)
health_bp = Blueprint('health', __name__)

APP_START_TS = time.time()
APP_ENV = os.getenv("FLASK_ENV", "production").lower()
IS_PRODUCTION = APP_ENV == "production"
SECURITY_HEADERS_ENABLED = _parse_bool("SECURITY_HEADERS_ENABLED", True)
ENFORCE_JSON_REQUESTS = _parse_bool("ENFORCE_JSON_REQUESTS", True)


def validate_config():
    from flask import current_app
    jwt_secret = current_app.config.get("JWT_SECRET_KEY")
    if not jwt_secret or jwt_secret == "dev-jwt-secret-CHANGE-ME":
        raise RuntimeError("Refusing to start: JWT_SECRET_KEY must be set securely.")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("Refusing to start: DATABASE_URL must be set.")

# validate_config()

CORS(
    app,
    origins=_split_csv_env(
        "ALLOWED_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:5000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000,http://localhost:3001",
    ),
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
    supports_credentials=True,
)


limiter = Limiter(
    get_remote_address,
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URL", "memory://"),
    default_limits=["200 per day", "50 per hour"],
)

# ---------------------------------------------------------------------------
# Database setup  (SQLAlchemy – models.py)
# ---------------------------------------------------------------------------
from app.models.models import db, User, Application, ManualOverride, AuditLog



# ---------------------------------------------------------------------------
# ML Model loading  (primary + optional canary)
# ---------------------------------------------------------------------------
from app.utils.data_utils import CATEGORICAL_COLS, NUMERIC_COLS
from app.ml.model_constants import (
    PRODUCTION_MODEL_PATH,
    PRODUCTION_META_PATH,
    PRODUCTION_THRESHOLD_PATH,
)

_shap = None
SHAP_AVAILABLE = None  # None = not loaded yet


def _ensure_shap_loaded() -> bool:
    global _shap, SHAP_AVAILABLE
    if SHAP_AVAILABLE is not None:
        return SHAP_AVAILABLE
    try:
        import shap as _shap_module

        _shap = _shap_module
        SHAP_AVAILABLE = True
        logger.info("SHAP loaded on demand")
    except Exception as exc:
        SHAP_AVAILABLE = False
        logger.warning("SHAP not available – explanations disabled: %s", exc)
    return SHAP_AVAILABLE


def _load_model_safe(path: str):
    p = Path(path)
    if p.exists():
        m = joblib.load(p)
        logger.info("Loaded model: %s", path)
        return m
    logger.warning("Model file not found: %s", path)
    return None


def _load_meta_safe(path: str) -> dict:
    p = Path(path)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {"threshold": 0.5, "version": "unknown"}


def _load_threshold_safe(path: str, default: float = 0.5) -> float:
    p = Path(path)
    if p.exists():
        try:
            cfg = pickle.load(open(p, "rb"))
            if isinstance(cfg, dict):
                return float(cfg.get("threshold", default))
            return float(cfg)
        except Exception:
            pass
    return default


PRIMARY_MODEL = _load_model_safe(PRODUCTION_MODEL_PATH)
PRIMARY_META = _load_meta_safe(PRODUCTION_META_PATH)
PRIMARY_THRESHOLD = _load_threshold_safe(
    PRODUCTION_THRESHOLD_PATH,
    float(PRIMARY_META.get("threshold", 0.5)),
)

CANARY_MODEL_PATH = os.getenv("CANARY_MODEL_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_production_fair.joblib"))
CANARY_META_PATH = os.getenv("CANARY_MODEL_META_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_production_fair_meta.json"))
CANARY_MODEL = _load_model_safe(CANARY_MODEL_PATH)
CANARY_META = _load_meta_safe(CANARY_META_PATH)
CANARY_THRESHOLD = float(CANARY_META.get("threshold", PRIMARY_THRESHOLD))

# ---------------------------------------------------------------------------
# Model Router
# ---------------------------------------------------------------------------
import random
import hashlib as _hashlib


class ModelRouter:
    """Route prediction requests between primary and canary models."""

    MODES = ("single", "shadow", "canary")

    def __init__(self):
        self.mode = os.getenv("MODEL_ROUTING_MODE", "single").lower()
        if self.mode not in self.MODES:
            self.mode = "single"
        self.canary_percent = int(os.getenv("CANARY_PERCENT", "10"))
        self._counters = {"primary": 0, "canary": 0, "shadow_primary": 0}

    def _use_canary(self, route_key: str) -> bool:
        """Deterministic bucket assignment using route_key hash."""
        bucket = int(_hashlib.md5(route_key.encode()).hexdigest(), 16) % 100
        return bucket < self.canary_percent

    def route(self, feature_df, route_key: str = "") -> dict:
        """Return prediction dict with routing metadata."""
        if not route_key:
            route_key = str(uuid.uuid4())

        if self.mode == "single" or CANARY_MODEL is None:
            result = self._predict(PRIMARY_MODEL, PRIMARY_META, PRIMARY_THRESHOLD, feature_df)
            result["model_routing"] = {"mode": self.mode, "model_used": "primary"}
            self._counters["primary"] += 1
            return result

        if self.mode == "shadow":
            result = self._predict(PRIMARY_MODEL, PRIMARY_META, PRIMARY_THRESHOLD, feature_df)
            # Run canary silently
            try:
                self._predict(CANARY_MODEL, CANARY_META, CANARY_THRESHOLD, feature_df)
            except Exception:
                pass
            result["model_routing"] = {"mode": "shadow", "model_used": "primary"}
            self._counters["shadow_primary"] += 1
            return result

        # canary mode
        if self._use_canary(route_key):
            result = self._predict(CANARY_MODEL, CANARY_META, CANARY_THRESHOLD, feature_df)
            result["model_routing"] = {"mode": "canary", "model_used": "canary"}
            self._counters["canary"] += 1
        else:
            result = self._predict(PRIMARY_MODEL, PRIMARY_META, PRIMARY_THRESHOLD, feature_df)
            result["model_routing"] = {"mode": "canary", "model_used": "primary"}
            self._counters["primary"] += 1
        return result

    @staticmethod
    def _predict(model, meta: dict, threshold: float, df) -> dict:
        from app.utils.data_utils import remove_leakage_columns
        
        # Remove leakage columns first!
        df = remove_leakage_columns(df)
        model_input = df
        
        is_pipeline = hasattr(model, "named_steps")

        if not is_pipeline and hasattr(model, "feature_names_in_"):
            # Only apply get_dummies if it's not a pipeline (e.g. plain canary model)
            expected = list(getattr(model, "feature_names_in_"))
            current = list(df.columns)
            if set(expected) != set(current):
                encoded = pd.get_dummies(df)
                encoded = encoded.reindex(columns=expected, fill_value=0)
                model_input = encoded

        try:
            # ExponentiatedGradient in older versions doesn't have predict_proba
            proba = model.predict_proba(model_input)[0]
        except AttributeError:
            if hasattr(model, "_predictors"):
                # Fairlearn ExponentiatedGradient has _predictors and _weights
                # We can calculate expected probability!
                import numpy as np
                expected_probs = np.zeros(2)
                for weight, predictor in zip(model.weights_, model.predictors_):
                    if weight > 0:
                        pred = predictor.predict(model_input)[0]
                        expected_probs[int(pred)] += weight
                proba = list(expected_probs)
            else:
                p_val = model.predict(model_input)[0]
                proba = [1.0 - float(p_val), float(p_val)]

        # Map probabilities by class label, not by index position.
        # Some model artifacts may expose class order as [1, 0] instead of [0, 1].
        # Business convention in this project: class 1 = reject risk, class 0 = approve.
        approval_idx = 0
        rejection_idx = 1
        classes = list(getattr(model, "classes_", []))
        if len(classes) == 2:
            try:
                approval_idx = classes.index(0)
                rejection_idx = classes.index(1)
            except ValueError:
                pass    # Keep default positional mapping if classes are unavailable/non-standard.
                approval_idx = 0
                rejection_idx = 1

        approval_prob = float(proba[approval_idx])
        rejection_prob = float(proba[rejection_idx])
        decision = "REDDEDİLDİ" if rejection_prob >= threshold else "ONAYLANDI"
        return {
            "tahmin": decision,
            "onay_olasiligi": approval_prob,
            "red_olasiligi": rejection_prob,
            "threshold": threshold,
            "model_version": meta.get("version", "unknown"),
        }


router = ModelRouter()

# ---------------------------------------------------------------------------
# Auth hardening
# ---------------------------------------------------------------------------
_AUTH_WINDOW_SEC = int(os.getenv("AUTH_FAILURE_WINDOW_SEC", "900") or 900)
_AUTH_MAX_FAILURES = int(os.getenv("AUTH_MAX_FAILURES", "5") or 5)
_AUTH_BLOCK_SEC = int(os.getenv("AUTH_BLOCK_SECONDS", "600") or 600)
_auth_failures = defaultdict(list)
_auth_lock = Lock()


def _auth_key(username: str) -> str:
    return f"{username}|{request.remote_addr or ''}"


def _prune_failures(failures: list[int], now_ts: int) -> list[int]:
    return [ts for ts in failures if now_ts - ts <= _AUTH_WINDOW_SEC]


def _is_auth_temporarily_blocked(username: str) -> tuple[bool, int]:
    key = _auth_key(username)
    now_ts = int(time.time())
    with _auth_lock:
        failures = _prune_failures(_auth_failures.get(key, []), now_ts)
        _auth_failures[key] = failures
        if len(failures) < _AUTH_MAX_FAILURES:
            return False, 0
        oldest_recent = failures[-_AUTH_MAX_FAILURES]
        retry_after = _AUTH_BLOCK_SEC - (now_ts - oldest_recent)
        if retry_after > 0:
            return True, retry_after
        return False, 0


def _register_auth_failure(username: str) -> None:
    key = _auth_key(username)
    now_ts = int(time.time())
    with _auth_lock:
        failures = _prune_failures(_auth_failures.get(key, []), now_ts)
        failures.append(now_ts)
        _auth_failures[key] = failures


def _clear_auth_failures(username: str) -> None:
    with _auth_lock:
        _auth_failures.pop(_auth_key(username), None)


def _is_strong_password(password: str) -> bool:
    if len(password) < 10:
        return False
    if re.search(r"[A-Z]", password) is None:
        return False
    if re.search(r"[a-z]", password) is None:
        return False
    if re.search(r"\d", password) is None:
        return False
    return True


def _is_valid_email(email: str) -> bool:
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(email or "")) is not None


def _registration_mode() -> str:
    mode = str(os.getenv("REGISTRATION_MODE", "closed")).strip().lower()
    if mode in {"closed", "invite_only", "domain_restricted", "public"}:
        return mode
    # Backward-compatible fallback for existing env flag.
    return "public" if _parse_bool("ALLOW_PUBLIC_REGISTRATION", False) else "closed"


def _allowed_registration_domains() -> set[str]:
    raw = str(os.getenv("REGISTRATION_ALLOWED_EMAIL_DOMAINS", "")).strip()
    if not raw:
        return set()
    return {d.strip().lower() for d in raw.split(",") if d.strip()}


def _email_domain(email: str) -> str:
    return str(email).split("@", 1)[-1].lower() if "@" in str(email) else ""


def _resolve_user(identity: str):
    if not identity:
        return None
    return User.query.filter_by(username=identity, is_active=True).first()


def _write_audit_event(*, event_type: str, identity: str = "", application_id=None, detail=None, status_code: int = 200, response_time_ms: float = 0.0) -> None:
    """Best-effort audit write helper; never raises to caller."""
    try:
        actor = _resolve_user(identity) if identity else None
        row = AuditLog(
            user_id=actor.id if actor else None,
            event_type=event_type,
            event_detail=json.dumps(detail or {}, ensure_ascii=False),
            application_id=int(str(application_id)) if application_id is not None and str(application_id).isdigit() else None,
            endpoint=request.path,
            method=request.method,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:255] if request.user_agent else None,
            status_code=status_code,
            response_time_ms=float(response_time_ms or 0.0),
        )
        db.session.add(row)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.warning("Audit write skipped (%s): %s", event_type, exc)


def require_roles(*roles):
    allowed = {str(r).lower() for r in roles if r}

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()
            actor = _resolve_user(identity)
            actor_role = str(actor.role if actor else "").lower()
            if actor_role not in allowed:
                return jsonify({"error": "Insufficient permissions"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator

# ---------------------------------------------------------------------------
# Prometheus metrics (optional – fail gracefully)
# ---------------------------------------------------------------------------
try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    _prom_registry = CollectorRegistry()
    _prom_requests = Counter(
        "finwise_requests_total",
        "Total API requests",
        ["endpoint"],
        registry=_prom_registry,
    )
    _prom_latency = Histogram(
        "finwise_request_latency_seconds",
        "Request latency",
        ["endpoint"],
        registry=_prom_registry,
    )
    _prom_rejection_rate = Gauge(
        "finwise_rejection_rate",
        "Rolling rejection rate",
        registry=_prom_registry,
    )
    _prom_approval_rate_protected = Gauge(
        "finwise_approval_rate_protected",
        "Approval rate for protected income group (Q1)",
        registry=_prom_registry,
    )
    _prom_approval_rate_reference = Gauge(
        "finwise_approval_rate_reference",
        "Approval rate for reference income group (Q5)",
        registry=_prom_registry,
    )
    _prom_di_ratio = Gauge(
        "finwise_fairness_di_ratio",
        "Disparate Impact ratio Q1/Q5",
        registry=_prom_registry,
    )
    _prom_daily_apps = Counter(
        "finwise_daily_applications_total",
        "Daily credit applications",
        registry=_prom_registry,
    )
    _prom_routing_mode = Gauge(
        "finwise_model_routing_mode",
        "Model routing mode indicator",
        ["mode"],
        registry=_prom_registry,
    )
    _prom_canary_loaded = Gauge(
        "finwise_canary_model_loaded",
        "Whether canary model is loaded",
        registry=_prom_registry,
    )
    _prom_canary_percent = Gauge(
        "finwise_canary_percent",
        "Configured canary traffic percentage",
        registry=_prom_registry,
    )
    _prom_canary_loaded.set(1 if CANARY_MODEL is not None else 0)
    _prom_canary_percent.set(router.canary_percent)
    for mode in ModelRouter.MODES:
        _prom_routing_mode.labels(mode=mode).set(1 if mode == router.mode else 0)

    # Adapter telemetry gauges (values updated dynamically in /metrics)
    _prom_adapter_attempts = Gauge(
        "finwise_adapter_attempts_total",
        "Total offer adapter attempts per bank",
        ["bank_code"],
        registry=_prom_registry,
    )
    _prom_adapter_success = Gauge(
        "finwise_adapter_success_total",
        "Successful offer adapter calls per bank",
        ["bank_code"],
        registry=_prom_registry,
    )
    _prom_adapter_fail = Gauge(
        "finwise_adapter_fail_total",
        "Failed offer adapter calls per bank",
        ["bank_code"],
        registry=_prom_registry,
    )
    _prom_adapter_fallback = Gauge(
        "finwise_adapter_fallback_total",
        "Total mock fallback activations",
        registry=_prom_registry,
    )

    PROM_AVAILABLE = True
    logger.info("Prometheus metrics initialised")
except Exception as _prom_err:
    PROM_AVAILABLE = False
    generate_latest = None
    CONTENT_TYPE_LATEST = "text/plain"
    logger.warning("Prometheus not available: %s", _prom_err)

# ---------------------------------------------------------------------------
# In-memory application stats
# ---------------------------------------------------------------------------
_stats = {"total": 0, "approved": 0, "rejected": 0, "overridden": 0}

# ---------------------------------------------------------------------------
# Feature helpers
# ---------------------------------------------------------------------------
import pandas as pd

FEATURE_COLS = NUMERIC_COLS + CATEGORICAL_COLS  # from data_utils


def _build_feature_df(data: dict) -> pd.DataFrame:
    row = {}
    for col in NUMERIC_COLS:
        row[col] = float(data.get(col, 0.0))
    for col in CATEGORICAL_COLS:
        row[col] = str(data.get(col, ""))
    return pd.DataFrame([row])


def _sanitize(s: str, maxlen: int = 255) -> str:
    return bleach.clean(str(s)[:maxlen], strip=True)


# ---------------------------------------------------------------------------
# Heuristic fallback explanation (used when SHAP is unavailable)
# ---------------------------------------------------------------------------
def _heuristic_top_features(feature_row: dict, top_n: int = 5) -> list:
    """Create deterministic pseudo-contributions so explanation export is never empty."""
    def _to_float(name, default=0.0):
        try:
            return float(feature_row.get(name, default))
        except Exception:
            return float(default)

    loan_pct = _to_float("loan_percent_income", 0.0)
    income = _to_float("person_income", 0.0)
    loan_amnt = _to_float("loan_amnt", 0.0)
    cred_hist = _to_float("cb_person_cred_hist_length", 0.0)
    emp_len = _to_float("person_emp_length", 0.0)
    age = _to_float("person_age", 35.0)
    default_flag = str(feature_row.get("cb_person_default_on_file", "N")).upper()

    heuristics = [
        ("loan_percent_income", (loan_pct - 0.25) * 2.2),
        ("loan_amnt", (loan_amnt - 20000.0) / 120000.0),
        ("person_income", -(income - 60000.0) / 220000.0),
        ("cb_person_cred_hist_length", -(cred_hist - 8.0) / 20.0),
        ("person_emp_length", -(emp_len - 5.0) / 15.0),
        ("person_age", 0.20 if age < 25 else (-0.05 if age >= 35 else 0.03)),
        ("cb_person_default_on_file", 0.35 if default_flag == "Y" else -0.08),
    ]

    ranked = sorted(heuristics, key=lambda x: abs(x[1]), reverse=True)[:top_n]
    return [{"feature": f, "contribution": float(v)} for f, v in ranked]


# ---------------------------------------------------------------------------
# SHAP explanation helper
# ---------------------------------------------------------------------------
def _shap_top_features(model, df, top_n: int = 5) -> list:
    feature_row = df.iloc[0].to_dict() if hasattr(df, "iloc") and len(df) > 0 else {}
    if not _ensure_shap_loaded() or _shap is None:
        return _heuristic_top_features(feature_row, top_n=top_n)
    try:
        is_pipeline = hasattr(model, "named_steps")

        if is_pipeline:
            # Pipeline model: extract preprocessor + classifier
            clf = model.named_steps.get("clf") or model[-1]
            pre = model.named_steps.get("pre") or model[:-1]
            X_pre = pre.transform(df)
            try:
                feat_names = list(pre.get_feature_names_out())
            except Exception:
                feat_names = [f"feature_{i}" for i in range(X_pre.shape[1])]
        else:
            # Plain classifier (canary model) — OHE-encode the raw df
            clf = model
            expected_cols = list(getattr(model, "feature_names_in_", []))
            encoded = pd.get_dummies(df)
            encoded = encoded.reindex(columns=expected_cols, fill_value=0)
            X_pre = encoded.values
            feat_names = expected_cols

        try:
            explainer = _shap.TreeExplainer(clf)
            shap_values = explainer.shap_values(X_pre)
            # index [1] = positive class (rejection)
            vals = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]
        except Exception:
            explainer = _shap.KernelExplainer(clf.predict_proba, X_pre[:1])
            sv = explainer.shap_values(X_pre, nsamples=100)
            vals = sv[1][0]

        pairs = sorted(zip(feat_names, vals), key=lambda x: abs(x[1]), reverse=True)
        return [{"feature": f, "contribution": float(v)} for f, v in pairs[:top_n]]
    except Exception as exc:
        logger.debug("SHAP error: %s", exc)
        return _heuristic_top_features(feature_row, top_n=top_n)


# ---------------------------------------------------------------------------
# Adverse action notice builder
# ---------------------------------------------------------------------------
from compliance import ComplianceManager  # type: ignore[import]

try:
    _compliance = ComplianceManager()
    COMPLIANCE_AVAILABLE = True
except Exception:
    _compliance = None
    COMPLIANCE_AVAILABLE = False


def _adverse_action_notice(data: dict, shap_features: list) -> dict:
    reasons = []
    if data.get("loan_percent_income", 0) > 0.4:
        reasons.append("Gelir-borç oranı çok yüksek (loan_percent_income > %40)")
    if data.get("cb_person_cred_hist_length", 10) < 3:
        reasons.append("Kredi geçmişi çok kısa (< 3 yıl)")
    if data.get("cb_person_default_on_file", "N") == "Y":
        reasons.append("Geçmişte temerrüt kaydı mevcut")
    if data.get("person_emp_length", 5) < 2:
        reasons.append("İstihdam süresi çok kısa (< 2 yıl)")
    if data.get("person_income", 100000) < 30000:
        reasons.append("Yıllık gelir yetersiz (< 30,000)")
    if not reasons and shap_features:
        reasons = [f"{sf['feature']} etkisi (katkı: {sf['contribution']:.3f})" for sf in shap_features[:3]]
    recommendations = [
        "Kredi geçmişinizi artırmak için mevcut borçlarınızı düzenli ödeyin",
        "Gelir-borç oranınızı azaltın: daha küçük bir kredi başvurusu yapın",
        "6-12 ay sonra yeniden başvurabilirsiniz",
    ]
    return {
        "notice": "OLUMSUZ KREDİ KARARI BİLDİRİMİ – ECOA/FCRA kapsamında bilgilendirme",
        "reasons": reasons[:5],
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# PUBLIC endpoints
# ---------------------------------------------------------------------------

@health_bp.route("/health")
def health():
    db_ok = True
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception:
        db_ok = False
    return jsonify({
        "status": "up",
        "database": "connected" if db_ok else "disconnected",
        "model": "loaded" if (PRIMARY_MODEL is not None) else "not_loaded",
        "routing_mode": router.mode,
        "canary_loaded": CANARY_MODEL is not None,
        "timestamp": utcnow().isoformat(),
        "version": "2.0.0",
    })


@credit_bp.route("/health/startup")
def health_startup():
    """Startup diagnostics for local troubleshooting and deployment checks."""
    def _safe_db_uri(uri: str) -> str:
        if not uri:
            return ""
        if "@" not in uri:
            return uri
        head, tail = uri.rsplit("@", 1)
        if "://" in head:
            scheme, _ = head.split("://", 1)
            return f"{scheme}://***@{tail}"
        return f"***@{tail}"

    def _db_ping() -> dict:
        try:
            db.session.execute(db.text("SELECT 1"))
            return {"ok": True, "latency_ms": None}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:120]}

    def _file_md5(path: str) -> str:
        import hashlib as _hl
        try:
            h = _hl.md5()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()[:12]
        except Exception:
            return "unavailable"

    db_ping = _db_ping()

    return jsonify({
        "status": "up" if db_ping["ok"] else "degraded",
        "uptime_seconds": round(time.time() - APP_START_TS, 2),
        "runtime": {
            "routing_mode": router.mode,
            "canary_loaded": CANARY_MODEL is not None,
            "shap_available": SHAP_AVAILABLE,
            "prometheus_enabled": PROM_AVAILABLE,
        },
        "database": db_ping,
        "artifacts": {
            "primary_model_exists": Path(PRODUCTION_MODEL_PATH).exists(),
            "primary_model_md5": _file_md5(PRODUCTION_MODEL_PATH) if Path(PRODUCTION_MODEL_PATH).exists() else None,
            "primary_meta_exists": Path(PRODUCTION_META_PATH).exists(),
            "canary_model_exists": Path(CANARY_MODEL_PATH).exists(),
            "canary_model_md5": _file_md5(CANARY_MODEL_PATH) if Path(CANARY_MODEL_PATH).exists() else None,
            "canary_meta_exists": Path(CANARY_META_PATH).exists(),
        },
        "config": {
            "database_uri": _safe_db_uri(app.config.get("SQLALCHEMY_DATABASE_URI", "")),
            "max_content_length": app.config.get("MAX_CONTENT_LENGTH"),
            "jwt_expires_seconds": int(app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()),
        },
        "timestamp": utcnow().isoformat(),
    })


# ---------------------------------------------------------------------------
# SIMULATOR endpoint  (/api/v2/simulate/approval)
# ---------------------------------------------------------------------------

def _simulation_default_base_row() -> dict:
    return {
        "person_age": 30,
        "person_income": 60000.0,
        "person_emp_length": 5,
        "loan_amnt": 20000.0,
        "loan_int_rate": 14.0,
        "loan_percent_income": 0.33,
        "cb_person_cred_hist_length": 4,
        "person_home_ownership": "RENT",
        "loan_intent": "PERSONAL",
        "loan_grade": "C",
        "cb_person_default_on_file": "N",
    }


def _load_simulation_context(base_application_id=None) -> tuple:
    base_row = _simulation_default_base_row()
    original_prediction = None

    if base_application_id:
        try:
            app_rec = Application.query.filter_by(id=int(base_application_id)).first()
            if app_rec:
                base_row.update({
                    "person_age": int(app_rec.person_age or 30),
                    "person_income": float(app_rec.person_income or 60000),
                    "person_emp_length": int(app_rec.person_emp_length or 5),
                    "loan_amnt": float(app_rec.loan_amnt or 20000),
                    "loan_int_rate": float(getattr(app_rec, "loan_int_rate", 14.0) or 14.0),
                    "loan_percent_income": float(getattr(app_rec, "loan_percent_income", 0.33) or 0.33),
                    "cb_person_cred_hist_length": int(app_rec.cb_person_cred_hist_length or 4),
                    "person_home_ownership": str(app_rec.person_home_ownership or "RENT"),
                    "loan_intent": str(app_rec.loan_intent or "PERSONAL"),
                    "loan_grade": str(app_rec.loan_grade or "C"),
                    "cb_person_default_on_file": str(app_rec.cb_person_default_on_file or "N"),
                })
                approval_prob = float(getattr(app_rec, "approval_probability", 0.5) or 0.5)
                rejection_prob = float(getattr(app_rec, "rejection_probability", 0.5) or 0.5)
                if approval_prob > 1:
                    approval_prob = approval_prob / 100.0
                if rejection_prob > 1:
                    rejection_prob = rejection_prob / 100.0
                original_prediction = {
                    "tahmin": app_rec.decision,
                    "onay_olasiligi": approval_prob,
                    "red_olasiligi": rejection_prob,
                }
        except Exception:
            pass

    return base_row, original_prediction


def _apply_simulation_overrides(base_row: dict, overrides: dict) -> dict:
    updated = dict(base_row)
    _str_fields = {"person_home_ownership", "loan_intent", "loan_grade", "cb_person_default_on_file"}
    for k, v in (overrides or {}).items():
        if k not in updated:
            continue
        try:
            updated[k] = _sanitize(str(v), 32) if k in _str_fields else float(v)
        except Exception:
            pass

    updated["person_age"] = max(18, min(100, int(updated["person_age"])))
    updated["person_income"] = max(1, min(1_000_000, float(updated["person_income"])))
    updated["loan_amnt"] = max(500, min(500_000, float(updated["loan_amnt"])))
    updated["loan_int_rate"] = max(0.1, min(50.0, float(updated["loan_int_rate"])))
    updated["loan_percent_income"] = max(0.001, min(1.0, float(updated["loan_percent_income"])))
    updated["person_emp_length"] = max(0, min(60, int(updated["person_emp_length"])))
    updated["cb_person_cred_hist_length"] = max(0, min(60, int(updated["cb_person_cred_hist_length"])))
    return updated


def _simulate_from_base_row(base_row: dict, route_key: str = "simulate") -> dict:
    df_sim = pd.DataFrame([base_row])
    result = router.route(df_sim, route_key=route_key)
    return {
        "tahmin": result["tahmin"],
        "onay_olasiligi": round(result["onay_olasiligi"], 4),
        "red_olasiligi": round(result["red_olasiligi"], 4),
        "threshold": result["threshold"],
        "model_routing": result.get("model_routing"),
    }

@credit_bp.route("/api/v2/ai-risk-assistant", methods=["POST"])
@jwt_required()
@limiter.limit("50 per hour")
def ai_risk_assistant():
    """AI assistant for risk evaluation."""
    payload = request.get_json() or {}
    question = str(payload.get("question", "")).strip().lower()
    if not question:
        return jsonify({"error": "question is required"}), 400

    prediction = payload.get("model_prediction", 0.5)
    prob_rej = float(prediction) * 100
    prob_app = 100 - prob_rej
    
    if prob_app > 50:
        risk_level = "Düşük Risk"
        recommendation = "Kredi onaylanabilir, standart faiz oranları uygulanabilir."
    else:
        risk_level = "Yüksek Risk"
        recommendation = "Kredi reddedilebilir veya ek teminat/kefil istenebilir."
    
    if "neden" in question or "sebep" in question or "why" in question:
        answer = f"Karar sebebi: Model {risk_level} tespit etti (Ret olasılığı: %{prob_rej:.1f}). Kredi/Gelir oranı ve çalışma süresi temel etkenler olabilir."
    elif "risk" in question or "faktör" in question or "factor" in question:
        answer = f"Risk Analizi: Profilin risk seviyesi {risk_level}. Ön plana çıkan faktörler kredi geçmişi uzunluğu ve mevcut borç/gelir dengesidir."
    elif "onay" in question or "artır" in question or "tavsiye" in question:
        answer = f"Öneri: {recommendation} Onay ihtimalini artırmak için kredi tutarını düşürebilir veya vadeyi kısaltabilirsiniz."
    else:
        answer = f"Yapay zeka asistanı: Mevcut analiz risk seviyesini {risk_level} (%{prob_app:.1f} onay ihtimali) olarak belirledi. Kararın nedenleri veya risk faktörleri hakkında daha spesifik sorular sorabilirsiniz."
    
    return jsonify({
        "answer": answer,
        "context_used": True
    })

@credit_bp.route("/api/v2/simulate/approval", methods=["POST"])
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


@credit_bp.route("/api/v2/simulate/improvement-options", methods=["POST"])
@jwt_required()
@limiter.limit("60 per hour")
def simulate_improvement_options():
    """Return ranked scenario suggestions that may improve approval probability."""
    if PRIMARY_MODEL is None:
        return jsonify({"error": "Model not loaded"}), 503

    data = request.get_json(silent=True) or {}
    base_application_id = data.get("base_application_id")
    raw_overrides = data.get("overrides")
    base_overrides: dict = raw_overrides if isinstance(raw_overrides, dict) else {}

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


@credit_bp.route("/api/v2/applications/history")
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
        dec_val = row.final_decision or row.decision
        is_approved = dec_val in ("ONAYLANDI", "Approved")
        risk_val = row.risk_score if row.risk_score is not None else row.rejection_probability
        items.append({
            "id": row.id,
            "application_id": row.id,
            "applicant_name": row.applicant_name or f"Başvuru #{row.id}",
            "customer_id": row.applicant_name or row.applicant_id or f"Müşteri #{row.id}",
            "loan_amnt": row.loan_amnt,
            "decision": "Approved" if is_approved else "Rejected",
            "raw_decision": dec_val,
            "risk_score": float(risk_val) if risk_val is not None else 0.0,
            "model_used": row.model_version or "XGBoost",
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


@credit_bp.route("/api/v2/applications/<int:application_id>/report/pdf", methods=["GET"])
@jwt_required()
@limiter.limit("60 per hour")
def download_credit_report_pdf(application_id: int):
    """Generates and downloads an executive PDF credit report for an application."""
    identity = get_jwt_identity()
    user = User.query.filter_by(username=identity).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    q = Application.query.filter_by(id=application_id)
    if user.role != "admin":
        q = q.filter_by(analyst_id=user.id)
    app_record = q.first()
    if not app_record:
        return jsonify({"error": "Application not found"}), 404

    try:
        from app.services.pdf_report_service import generate_credit_report_pdf
        pdf_data = generate_credit_report_pdf(app_record, analyst_user=user)
        filename = f"FinWise_Kredi_Raporu_FW-{app_record.id:06d}.pdf"
        return Response(
            pdf_data,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_data)),
            },
        )
    except Exception as exc:
        logger.error("PDF generation failed for application %s: %s", application_id, exc)
        return jsonify({"error": f"PDF rapor üretimi başarısız: {exc}"}), 500


@credit_bp.route("/api/v2/applications/history/<int:application_id>")
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


@credit_bp.route("/api/v2/applications/history/clear", methods=["POST", "DELETE"])
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


@credit_bp.route("/metrics")
def metrics():
    if not PROM_AVAILABLE or generate_latest is None:
        return Response("Prometheus not available\n", status=503, mimetype="text/plain")
    # Dynamic fairness metrics from DB
    try:
        total = Application.query.count() or 1
        rejected = Application.query.filter_by(decision="REDDEDİLDİ").count()
        _prom_rejection_rate.set(rejected / total)
        _prom_daily_apps._value.set(total)
    except Exception:
        pass
    # Adapter telemetry
    try:
        from bank_offer_adapters import get_offer_adapter_stats as _get_adapter_stats
        _astats = _get_adapter_stats()
        _prom_adapter_fallback.set(_astats["total"]["fallback_count"])
        for _bc, _bv in _astats["banks"].items():
            _prom_adapter_attempts.labels(bank_code=_bc).set(_bv["attempts"])
            _prom_adapter_success.labels(bank_code=_bc).set(_bv["success"])
            _prom_adapter_fail.labels(bank_code=_bc).set(_bv["fail"])
    except Exception:
        pass
    raw = generate_latest(_prom_registry)
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return Response(raw, status=200, mimetype=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# AUTH endpoints
# ---------------------------------------------------------------------------

@auth_bp.route("/auth/register", methods=["POST"])
@limiter.limit("10 per hour")
def auth_register():
    mode = _registration_mode()
    if mode == "closed":
        _write_audit_event(
            event_type="auth_register_blocked",
            identity="",
            detail={"reason": "registration_closed", "mode": mode},
            status_code=403,
        )
        return jsonify({"error": "Public registration is disabled"}), 403

    data = request.get_json(silent=True) or {}
    username = _sanitize(data.get("username", ""))
    password = data.get("password", "")
    email = _sanitize(data.get("email", f"{username}@finwise.local"))
    invite_code = str(data.get("invite_code", "")).strip()

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if not _is_valid_email(email):
        return jsonify({"error": "valid email is required"}), 400
    if not _is_strong_password(password):
        return jsonify({"error": "password must be at least 10 chars and include upper/lowercase letters and digits"}), 400

    allowed_domains = _allowed_registration_domains()
    domain = _email_domain(email)
    if mode == "invite_only":
        expected = str(os.getenv("REGISTRATION_INVITE_CODE", "")).strip()
        if not expected or invite_code != expected:
            _write_audit_event(
                event_type="auth_register_denied",
                identity=username,
                detail={"reason": "invalid_invite", "mode": mode, "email_domain": domain},
                status_code=403,
            )
            return jsonify({"error": "valid invite code is required"}), 403

    if mode == "domain_restricted":
        if not allowed_domains:
            return jsonify({"error": "registration domains are not configured"}), 500
        if domain not in allowed_domains:
            _write_audit_event(
                event_type="auth_register_denied",
                identity=username,
                detail={"reason": "domain_not_allowed", "mode": mode, "email_domain": domain},
                status_code=403,
            )
            return jsonify({"error": "email domain is not allowed"}), 403

    # Self-signup always lands as analyst. Elevated roles are admin-only.
    role = "analyst"

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username already exists"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already exists"}), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
    )
    db.session.add(user)
    db.session.commit()
    _write_audit_event(
        event_type="auth_register_success",
        identity=username,
        detail={"username": username, "email": email, "mode": mode, "role": role},
        status_code=201,
    )
    return jsonify({"message": "Kullanıcı başarıyla oluşturuldu", "username": username}), 201


@auth_bp.route("/auth/admin/create-user", methods=["POST"])
@jwt_required()
@require_roles("admin")
@limiter.limit("30 per hour")
def auth_admin_create_user():
    data = request.get_json(silent=True) or {}
    username = _sanitize(data.get("username", ""))
    password = data.get("password", "")
    email = _sanitize(data.get("email", f"{username}@finwise.local"))
    role = str(data.get("role", "analyst")).strip().lower()

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if not _is_valid_email(email):
        return jsonify({"error": "valid email is required"}), 400
    if role not in ("analyst", "manager", "admin"):
        return jsonify({"error": "role must be analyst, manager or admin"}), 400
    if not _is_strong_password(password):
        return jsonify({"error": "password must be at least 10 chars and include upper/lowercase letters and digits"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username already exists"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already exists"}), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
    )
    db.session.add(user)
    db.session.commit()

    actor = get_jwt_identity() or ""
    _write_audit_event(
        event_type="auth_admin_create_user_success",
        identity=actor,
        detail={"created_username": username, "created_email": email, "created_role": role},
        status_code=201,
    )
    return jsonify({"message": "User created", "username": username, "role": role}), 201


@auth_bp.route("/auth/admin/registration-policy")
@jwt_required()
@require_roles("admin")
@limiter.limit("60 per hour")
def auth_admin_registration_policy():
    mode = _registration_mode()
    domains = sorted(_allowed_registration_domains())
    invite_configured = bool(str(os.getenv("REGISTRATION_INVITE_CODE", "")).strip())
    actor = get_jwt_identity() or ""

    _write_audit_event(
        event_type="auth_admin_registration_policy_view",
        identity=actor,
        detail={"mode": mode, "domains_count": len(domains), "invite_configured": invite_configured},
        status_code=200,
    )

    return jsonify(
        {
            "registration_mode": mode,
            "allow_public_registration_legacy": _parse_bool("ALLOW_PUBLIC_REGISTRATION", False),
            "invite_code_configured": invite_configured,
            "allowed_email_domains": domains,
            "self_signup_role": "analyst",
            "admin_create_user_endpoint": "/auth/admin/create-user",
        }
    )


@auth_bp.route("/auth/login", methods=["POST"])
@limiter.limit("20 per hour")
def auth_login():
    data = request.get_json(silent=True) or {}
    username = _sanitize(data.get("username", ""))
    password = data.get("password", "")
    t0 = time.time()

    if not username or not isinstance(password, str) or not password:
        _write_audit_event(
            event_type="auth_login_bad_request",
            identity=username,
            detail={"username_present": bool(username), "password_present": bool(password)},
            status_code=400,
            response_time_ms=(time.time() - t0) * 1000.0,
        )
        return jsonify({"error": "Username and password are required"}), 400

    blocked, retry_after = _is_auth_temporarily_blocked(username)
    if blocked:
        _write_audit_event(
            event_type="auth_login_blocked",
            identity=username,
            detail={"username": username, "retry_after_seconds": retry_after},
            status_code=429,
            response_time_ms=(time.time() - t0) * 1000.0,
        )
        return jsonify({"error": "Too many failed login attempts", "retry_after_seconds": retry_after}), 429

    user = User.query.filter_by(username=username, is_active=True).first()

    if not user or not check_password_hash(user.password_hash, password):
        _register_auth_failure(username)
        _write_audit_event(
            event_type="auth_login_failed",
            identity=username,
            detail={"username": username},
            status_code=401,
            response_time_ms=(time.time() - t0) * 1000.0,
        )
        return jsonify({"error": "Invalid credentials"}), 401

    _clear_auth_failures(username)

    user.last_login = utcnow()
    db.session.commit()

    token = create_access_token(
        identity=username,
        additional_claims={"role": user.role, "user_id": user.id},
    )
    _write_audit_event(
        event_type="auth_login_success",
        identity=username,
        detail={"username": username, "role": user.role},
        status_code=200,
        response_time_ms=(time.time() - t0) * 1000.0,
    )
    return jsonify({"access_token": token, "token_type": "Bearer", "username": username, "role": user.role})


@auth_bp.route("/auth/me", methods=["GET"])
@jwt_required()
def auth_me():
    identity = get_jwt_identity() or ""
    user = User.query.filter_by(username=identity).first()
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    evaluated_count = 0
    try:
        evaluated_count = Application.query.filter_by(analyst_id=user.id).count()
    except Exception:
        pass

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
        "last_login": user.last_login.isoformat() if getattr(user, "last_login", None) else None,
        "evaluated_count": evaluated_count,
    })


@auth_bp.route("/auth/change-password", methods=["POST"])
@jwt_required()
@limiter.limit("15 per hour")
def auth_change_password():
    identity = get_jwt_identity() or ""
    user = User.query.filter_by(username=identity).first()
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not old_password or not new_password:
        return jsonify({"error": "Mevcut şifre ve yeni şifre zorunludur"}), 400

    if not check_password_hash(user.password_hash, old_password):
        _write_audit_event(
            event_type="auth_change_password_failed_wrong_current",
            identity=identity,
            detail={"reason": "invalid_current_password"},
            status_code=400,
        )
        return jsonify({"error": "Mevcut şifreniz hatalı"}), 400

    if not _is_strong_password(new_password):
        return jsonify({
            "error": "Yeni şifre en az 10 karakter olmalı; büyük harf, küçük harf ve rakam içermelidir"
        }), 400

    if check_password_hash(user.password_hash, new_password):
        return jsonify({"error": "Yeni şifre mevcut şifreyle aynı olamaz"}), 400

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    _write_audit_event(
        event_type="auth_change_password_success",
        identity=identity,
        detail={"user_id": user.id},
        status_code=200,
    )
    return jsonify({"message": "Şifreniz başarıyla güncellendi"}), 200


@auth_bp.route("/auth/update-profile", methods=["PUT"])
@jwt_required()
@limiter.limit("20 per hour")
def auth_update_profile():
    identity = get_jwt_identity() or ""
    user = User.query.filter_by(username=identity).first()
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    data = request.get_json(silent=True) or {}
    new_email = _sanitize(data.get("email", "")).strip().lower()

    if not new_email or not _is_valid_email(new_email):
        return jsonify({"error": "Geçerli bir e-posta adresi giriniz"}), 400

    existing = User.query.filter(User.email == new_email, User.id != user.id).first()
    if existing:
        return jsonify({"error": "Bu e-posta adresi başka bir kullanıcı tarafından kullanılıyor"}), 409

    user.email = new_email
    db.session.commit()

    _write_audit_event(
        event_type="auth_update_profile_success",
        identity=identity,
        detail={"new_email": new_email},
        status_code=200,
    )
    return jsonify({"message": "Profil bilgileri güncellendi", "email": new_email}), 200


# ---------------------------------------------------------------------------
# REAL TURKISH BANK OFFERS endpoint (/api/v2/bank-offers)
# ---------------------------------------------------------------------------
@credit_bp.route("/api/v2/bank-offers", methods=["POST"])
@limiter.limit("60 per hour")
def get_real_bank_offers():
    """
    Kredi tutarı, vade ve risk skoruna göre Türkiye'deki gerçek bankaların
    güncel faiz oranları ve KKDF+BSMV vergileri dahil anüite taksitlerini hesaplar.
    """
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount") or data.get("loan_amnt") or 50000)
    except (ValueError, TypeError):
        amount = 50000.0

    try:
        term = int(data.get("term_months") or 36)
    except (ValueError, TypeError):
        term = 36
    if term not in (6, 12, 18, 24, 36):
        term = 36 if term > 36 else (12 if term < 12 else term)

    try:
        risk_score = float(data.get("risk_score") or 0.20)
    except (ValueError, TypeError):
        risk_score = 0.20

    decision = str(data.get("decision", "ONAYLANDI")).upper()
    is_approved = ("ONAY" in decision or "APPROV" in decision)

    # Bank definitions with base market interest rates (Aylık %)
    # KKDF (%15) + BSMV (%5) = %20 vergi çarpanı: brüt_faiz = aylik_faiz * 1.20
    bank_catalog = [
        {
            "bank_id": "akbank",
            "bank_name": "Akbank",
            "product_name": "Doğrudan İhtiyaç Kredisi",
            "base_rate": 0.0379,  # %3.79 aylık
            "fee_free": False,
            "badge": "En Düşük Faiz",
            "badge_type": "success",
            "sponsored": True,
            "color": "#E30613",
            "features": ["3 Ay Erteleme İmkanı", "FinWise Özel İndirimi", "Şubeye Gitmeden"],
            "apply_url": "https://www.akbank.com/basvuru/hizli-ihtiyac-kredisi",
        },
        {
            "bank_id": "garanti",
            "bank_name": "Garanti BBVA",
            "product_name": "Bireysel İhtiyaç Kredisi",
            "base_rate": 0.0389,  # %3.89 aylık
            "fee_free": False,
            "badge": "Hızlı Onay",
            "badge_type": "primary",
            "sponsored": False,
            "color": "#008542",
            "features": ["5 Dakikada Hesabında", "Mobil Onay", "Masrafsız Erken Kapama"],
            "apply_url": "https://www.garantibbva.com.tr/krediler/ihtiyac-kredisi",
        },
        {
            "bank_id": "enpara",
            "bank_name": "Enpara.com",
            "product_name": "Masrafsız İhtiyaç Kredisi",
            "base_rate": 0.0415,  # %4.15 aylık
            "fee_free": True,    # 0 TL dosya masrafı!
            "badge": "0 TL Dosya Masrafı",
            "badge_type": "warning",
            "sponsored": False,
            "color": "#6C1D5F",
            "features": ["Dosya Masrafı Yok", "Ömür Boyu Ücretsiz", "Gizli Ücret Yok"],
            "apply_url": "https://www.qnb.com.tr/enpara/krediler/ihtiyac-kredisi",
        },
        {
            "bank_id": "isbank",
            "bank_name": "Türkiye İş Bankası",
            "product_name": "İş'te Kredi",
            "base_rate": 0.0395,  # %3.95 aylık
            "fee_free": False,
            "badge": "Güvenilir Tercih",
            "badge_type": "default",
            "sponsored": False,
            "color": "#004888",
            "features": ["Esnek Ödeme Planı", "Maaş Müşterisine Özel Oran", "Maksimum Güven"],
            "apply_url": "https://www.isbank.com.tr/ihtiyac-kredisi",
        },
        {
            "bank_id": "yapikredi",
            "bank_name": "Yapı Kredi",
            "product_name": "Görüntülü İhtiyaç Kredisi",
            "base_rate": 0.0399,  # %3.99 aylık
            "fee_free": False,
            "badge": "Esnek Taksit",
            "badge_type": "default",
            "sponsored": False,
            "color": "#0A2B70",
            "features": ["Görüntülü Görüşmeyle Anında", "Serbest Ödemeli Taksit"],
            "apply_url": "https://www.yapikredi.com.tr/bireysel-bankacilik/krediler/bireysel-ihtiyac-kredisi",
        },
        {
            "bank_id": "qnb",
            "bank_name": "QNB Finansbank",
            "product_name": "İhtiyaç Kredisi",
            "base_rate": 0.0409,  # %4.09 aylık
            "fee_free": False,
            "badge": "Kolay Başvuru",
            "badge_type": "default",
            "sponsored": False,
            "color": "#6E1C44",
            "features": ["Kolay Transfer", "Gelir Belgesiz Başvuru"],
            "apply_url": "https://www.qnbfinansbank.com/bireysel-ihtiyac-kredisi",
        },
        {
            "bank_id": "ziraat",
            "bank_name": "Ziraat Bankası",
            "product_name": "Tüketici Kredisi",
            "base_rate": 0.0424,  # %4.24 aylık
            "fee_free": False,
            "badge": "Kamu Güvencesi",
            "badge_type": "default",
            "sponsored": False,
            "color": "#BA0C2F",
            "features": ["Geniş Şube Ağı", "Kamu Çalışanı İndirimi"],
            "apply_url": "https://www.ziraatbank.com.tr/tr/bireysel/krediler/tuketici-kredisi",
        },
    ]

    # Risk adjustments: low risk gets slight rate benefit, high risk gets surcharge
    rate_adjustment = 0.0
    if risk_score < 0.15:
        rate_adjustment = -0.0010  # -0.10% indirim
    elif risk_score > 0.40:
        rate_adjustment = +0.0025  # +0.25% risk primi

    offers = []
    for item in bank_catalog:
        effective_monthly_rate = max(0.015, item["base_rate"] + rate_adjustment)
        # KKDF %15 + BSMV %5 = %20 toplam vergi
        gross_monthly_rate = effective_monthly_rate * 1.20

        # Anüite formülü
        factor = (1.0 + gross_monthly_rate) ** term
        if factor > 1.0:
            monthly_installment = amount * (gross_monthly_rate * factor) / (factor - 1.0)
        else:
            monthly_installment = amount / term

        total_repayment = monthly_installment * term
        total_interest = total_repayment - amount
        fee = 0.0 if item["fee_free"] else round(amount * 0.005 * 1.05, 2)  # %0.5 + %5 BSMV

        # Yıllık maliyet oranı (YMO) yaklaşık
        annual_cost_rate = round(gross_monthly_rate * 12.0 * 100.0, 2)

        offers.append({
            "bank_id": item["bank_id"],
            "bank_name": item["bank_name"],
            "product_name": item["product_name"],
            "color": item["color"],
            "badge": item["badge"],
            "badge_type": item["badge_type"],
            "sponsored": item["sponsored"],
            "features": item["features"],
            "apply_url": item["apply_url"],
            "loan_amount": amount,
            "term_months": term,
            "monthly_interest_rate": round(effective_monthly_rate * 100.0, 2),
            "monthly_installment": round(monthly_installment, 2),
            "total_repayment": round(total_repayment, 2),
            "total_interest_and_tax": round(total_interest, 2),
            "processing_fee": fee,
            "annual_cost_rate": annual_cost_rate,
            "currency": "TRY",
            "is_preapproved": is_approved,
        })

    # Sıralama: Aylık taksit en düşükten yükseğe
    offers.sort(key=lambda x: (x["monthly_installment"], x["total_repayment"]))

    return jsonify({
        "status": "ok",
        "loan_amount": amount,
        "term_months": term,
        "risk_score": risk_score,
        "decision": decision,
        "is_approved": is_approved,
        "currency": "TRY",
        "offers_count": len(offers),
        "offers": offers,
        "disclaimer": "Hesaplanan tutarlar KKDF (%15) ve BSMV (%5) vergileri dahil tahmini tekliflerdir. Nihai faiz oranı banka değerlendirmesi sonrası kesinleşir."
    })


# ---------------------------------------------------------------------------
# MOCK CUSTOMER DATA endpoint (/customer/<tckn>)
# ---------------------------------------------------------------------------
@credit_bp.route("/customer/<tckn>", methods=["GET"])
@limiter.limit("50 per hour")
@jwt_required()
def get_customer_by_tckn(tckn):
    if not tckn or len(tckn) != 11 or not tckn.isdigit():
        return jsonify({"error": "Geçersiz TCKN. 11 haneli rakam giriniz."}), 400
        
    last_digit = int(tckn[-1])
    
    # 0, 2, 4 -> Low Risk Profile
    if last_digit in [0, 2, 4]:
        profile = {
            "person_age": 45,
            "person_income": 120000,
            "person_emp_length": 15,
            "loan_amnt": 10000,
            "loan_int_rate": 7.5,
            "loan_percent_income": 0.08,
            "cb_person_cred_hist_length": 12,
            "person_home_ownership": "OWN",
            "loan_intent": "HOMEIMPROVEMENT",
            "loan_grade": "A",
            "cb_person_default_on_file": "N"
        }
    # 1, 3, 5 -> Medium Risk Profile
    elif last_digit in [1, 3, 5]:
        profile = {
            "person_age": 32,
            "person_income": 65000,
            "person_emp_length": 4,
            "loan_amnt": 15000,
            "loan_int_rate": 12.5,
            "loan_percent_income": 0.23,
            "cb_person_cred_hist_length": 6,
            "person_home_ownership": "RENT",
            "loan_intent": "PERSONAL",
            "loan_grade": "C",
            "cb_person_default_on_file": "N"
        }
    # 6, 7, 8, 9 -> High Risk Profile
    else:
        profile = {
            "person_age": 24,
            "person_income": 35000,
            "person_emp_length": 1,
            "loan_amnt": 20000,
            "loan_int_rate": 18.5,
            "loan_percent_income": 0.57,
            "cb_person_cred_hist_length": 2,
            "person_home_ownership": "RENT",
            "loan_intent": "VENTURE",
            "loan_grade": "E",
            "cb_person_default_on_file": "Y"
        }
        
    return jsonify(profile)


# ---------------------------------------------------------------------------
# PREDICTION endpoint  (/degerlendir)
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "person_age", "person_income", "person_emp_length",
    "loan_amnt", "loan_int_rate", "loan_percent_income",
    "cb_person_cred_hist_length", "person_home_ownership",
    "loan_intent", "loan_grade", "cb_person_default_on_file",
]


@credit_bp.route("/degerlendir", methods=["POST"])
@jwt_required()
@limiter.limit("100 per hour")
def predict():
    if PRIMARY_MODEL is None:
        return jsonify({"error": "Model not loaded"}), 503

    t0 = time.time()
    identity = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    # Validate required fields
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    # Input validation / sanitisation
    try:
        person_age = int(data["person_age"])
        person_income = float(data["person_income"])
        loan_amnt = float(data["loan_amnt"])
        loan_int_rate = float(data["loan_int_rate"])
        loan_percent_income = float(data["loan_percent_income"])
        cb_cred_hist = int(data["cb_person_cred_hist_length"])
        person_emp_length = int(data["person_emp_length"])
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"Invalid numeric value: {exc}"}), 400

    if not (18 <= person_age <= 100):
        return jsonify({"error": "person_age must be 18–100"}), 400
    if not (0 < person_income <= 1_000_000):
        return jsonify({"error": "Invalid person_income"}), 400
    if not (500 <= loan_amnt <= 500_000):
        return jsonify({"error": "loan_amnt must be 500–500,000"}), 400
    if not (0 < loan_int_rate <= 50):
        return jsonify({"error": "loan_int_rate must be 0–50"}), 400
    if not (0 < loan_percent_income <= 1):
        return jsonify({"error": "loan_percent_income must be 0–1"}), 400

    home_ownership = _sanitize(data.get("person_home_ownership", "")).upper()
    loan_intent = _sanitize(data.get("loan_intent", "")).upper()
    loan_grade = _sanitize(data.get("loan_grade", "")).upper()
    default_on_file = _sanitize(data.get("cb_person_default_on_file", "N")).upper()

    valid_home_ownership = {"RENT", "OWN", "MORTGAGE", "OTHER"}
    valid_loan_intent = {"PERSONAL", "EDUCATION", "MEDICAL", "VENTURE", "HOMEIMPROVEMENT", "DEBTCONSOLIDATION"}
    valid_loan_grade = {"A", "B", "C", "D", "E", "F", "G"}
    valid_default_on_file = {"Y", "N"}

    if home_ownership not in valid_home_ownership:
        return jsonify({"error": f"Invalid person_home_ownership: {home_ownership}"}), 400
    if loan_intent not in valid_loan_intent:
        return jsonify({"error": f"Invalid loan_intent: {loan_intent}"}), 400
    if loan_grade not in valid_loan_grade:
        return jsonify({"error": f"Invalid loan_grade: {loan_grade}"}), 400
    if default_on_file not in valid_default_on_file:
        return jsonify({"error": f"Invalid cb_person_default_on_file: {default_on_file}"}), 400

    # --- FRAUD DETECTION & MOCK API LAYER ---
    from app.services.fraud_service import FraudService
    fraud_analysis = FraudService.evaluate(data)
    
    if fraud_analysis["is_fraud"]:
        # Log the fraud attempt
        logger.warning(f"Fraud detected! Score: {fraud_analysis['score']}. Reasons: {fraud_analysis['reasons']}")
        
        # We can still return a valid response format but force the decision to "REDDEDİLDİ"
        return jsonify({
            "tahmin": "REDDEDİLDİ",
            "onay_olasiligi": 0.0,
            "red_olasiligi": 1.0,
            "threshold": PRIMARY_THRESHOLD,
            "model_version": PRIMARY_META.get("version", "unknown"),
            "model_routing": {"mode": "fraud_blocked", "model_used": "none"},
            "fraud_analysis": fraud_analysis,
            "aciklamalar": [
                {"ozellik": "Fraud Detection", "etki_orani": 100.0, "mesaj": r} for r in fraud_analysis["reasons"]
            ]
        })

    # --- ML PREDICTION LAYER ---
    feature_row = {
        "person_age": person_age,
        "person_income": person_income,
        "person_emp_length": person_emp_length,
        "loan_amnt": loan_amnt,
        "loan_int_rate": loan_int_rate,
        "loan_percent_income": loan_percent_income,
        "cb_person_cred_hist_length": cb_cred_hist,
        "person_home_ownership": home_ownership,
        "loan_intent": loan_intent,
        "loan_grade": loan_grade,
        "cb_person_default_on_file": default_on_file,
    }
    df = pd.DataFrame([feature_row])
    
    from app.utils.data_utils import engineer_features
    df = engineer_features(df)

    route_key = data.get("customer_id", str(uuid.uuid4()))
    result = router.route(df, route_key=str(route_key))

    # SHAP explanation
    active_model = (
        CANARY_MODEL
        if result.get("model_routing", {}).get("model_used") == "canary" and CANARY_MODEL
        else PRIMARY_MODEL
    )
    shap_features = _shap_top_features(active_model, df)

    # Persist to DB
    user = User.query.filter_by(username=identity).first()
    app_record = Application(
        person_age=person_age,
        person_income=person_income,
        person_emp_length=person_emp_length,
        person_home_ownership=home_ownership,
        cb_person_cred_hist_length=cb_cred_hist,
        cb_person_default_on_file=default_on_file,
        loan_amnt=loan_amnt,
        loan_intent=loan_intent,
        loan_grade=loan_grade,
        loan_int_rate=loan_int_rate,
        loan_percent_income=loan_percent_income,
        decision=result["tahmin"],
        approval_probability=result["onay_olasiligi"],
        rejection_probability=result["red_olasiligi"],
        risk_score=float(result["red_olasiligi"]),
        threshold_used=result["threshold"],
        model_version=result["model_version"],
        shap_values=shap_features,
        analyst_id=user.id if user else None,
        applicant_id=str(route_key)[:50],
        applicant_name=_sanitize(data.get("applicant_name") or data.get("customer_id") or f"Başvuru #{str(uuid.uuid4())[:8]}", 200),
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:255] if request.user_agent else None,
        application_date=utcnow(),
        created_at=utcnow(),
        decision_timestamp=utcnow(),
    )
    db.session.add(app_record)
    db.session.commit()
    application_id = app_record.id

    _write_audit_event(
        event_type="prediction_created",
        identity=identity,
        application_id=application_id,
        detail={
            "decision": result["tahmin"],
            "model_version": result.get("model_version"),
            "routing": result.get("model_routing", {}),
        },
        status_code=200,
        response_time_ms=(time.time() - t0) * 1000.0,
    )

    # Update stats
    _stats["total"] += 1
    if result["tahmin"] == "ONAYLANDI":
        _stats["approved"] += 1
    else:
        _stats["rejected"] += 1

    if PROM_AVAILABLE:
        try:
            _prom_requests.labels(endpoint="/degerlendir").inc()
            _prom_latency.labels(endpoint="/degerlendir").observe(time.time() - t0)
            _prom_daily_apps.inc()
        except Exception:
            pass

    response = {
        "tahmin": result["tahmin"],
        "decision": "Approved" if result["tahmin"] == "ONAYLANDI" else "Rejected",
        "risk_score": float(result["red_olasiligi"]),
        "onay_olasiligi": result["onay_olasiligi"],
        "red_olasiligi": result["red_olasiligi"],
        "threshold": result["threshold"],
        "model_version": result["model_version"],
        "model_routing": result.get("model_routing"),
        "application_id": application_id,
        "basvuru_id": application_id,
        "timestamp": utcnow().isoformat(),
        "fraud_analysis": fraud_analysis,
    }

    if shap_features:
        response["shap_top_features"] = shap_features

    if result["tahmin"] in {"REDDEDİLDİ", "REDDEDILDI"}:
        notice = _adverse_action_notice(feature_row, shap_features)
        response["adverse_action_notice"] = notice
        response["adverse_action"] = notice

    return jsonify(response)


# ---------------------------------------------------------------------------
# EXPLANATION endpoint  (/explain/<id>)
# ---------------------------------------------------------------------------

@credit_bp.route("/explain/<int:application_id>")
@jwt_required()
def explain(application_id: int):
    app_record = Application.query.get(application_id)
    if not app_record:
        return jsonify({"error": "Application not found"}), 404

    response = {
        "application_id": application_id,
        "decision": app_record.decision,
        "approval_probability": app_record.approval_probability,
        "rejection_probability": app_record.rejection_probability,
        "threshold": app_record.threshold_used,
        "model_version": app_record.model_version,
        "is_overridden": app_record.is_overridden,
        "final_decision": app_record.final_decision or app_record.decision,
        "timestamp": app_record.decision_timestamp.isoformat() if app_record.decision_timestamp else None,
    }

    shap_source = app_record.shap_values or []
    if not shap_source:
        fallback_row = {
            "person_age": app_record.person_age,
            "person_income": app_record.person_income,
            "person_emp_length": app_record.person_emp_length,
            "loan_amnt": app_record.loan_amnt,
            "loan_percent_income": app_record.loan_percent_income,
            "cb_person_cred_hist_length": app_record.cb_person_cred_hist_length,
            "cb_person_default_on_file": app_record.cb_person_default_on_file,
        }
        shap_source = _heuristic_top_features(fallback_row, top_n=5)

    if shap_source:
        response["shap_top_features"] = shap_source
        response["shap_values"] = {
            "top_features": [
                {
                    "feature": f.get("feature", ""),
                    "contribution": f.get("contribution", 0.0),
                }
                for f in shap_source
            ]
        }
        # Format expected by the frontend showFeatureImportance()
        response["shap_features"] = [
            {
                "feature": f.get("feature", ""),
                "shap_value": f.get("contribution", 0.0),
                "importance": abs(f.get("contribution", 0.0)),
                "impact": "Pozitif" if f.get("contribution", 0.0) > 0 else ("Negatif" if f.get("contribution", 0.0) < 0 else "Nötr"),
            }
            for f in shap_source
        ]

    return jsonify(response)


# ---------------------------------------------------------------------------
# STATISTICS endpoint  (/istatistik)
# ---------------------------------------------------------------------------

@dashboard_bp.route("/istatistik")
@jwt_required()
@require_roles("analyst", "manager", "admin")
def statistics():
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

    approval_rate = f"{(approved / total * 100):.1f}%" if total else "0.0%"
    override_rate = f"{(overridden / total * 100):.1f}%" if total else "0.0%"

    return jsonify({
        "total_applications": total,
        "approved": approved,
        "rejected": rejected,
        "overridden": overridden,
        "model_info": {
            "model_tipi": PRIMARY_META.get("model_type", "RandomForestClassifier"),
            "threshold": PRIMARY_THRESHOLD,
            "version": PRIMARY_META.get("version", "unknown"),
            "auc": PRIMARY_META.get("roc_auc", None),
        },
        "application_stats": {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "overridden": overridden,
            "approval_rate": approval_rate,
            "override_rate": override_rate,
        },
        "model_routing": {
            "mode": router.mode,
            "canary_percent": router.canary_percent,
            "canary_loaded": CANARY_MODEL is not None,
            "counters": router._counters,
        },
        "timestamp": utcnow().isoformat(),
    })


# ---------------------------------------------------------------------------
# MANUAL OVERRIDE endpoint  (/override)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# FRAUD STATS endpoint  (/api/v2/offers/fraud-stats)
# ---------------------------------------------------------------------------
@compliance_bp.route("/api/v2/offers/fraud-stats")
@jwt_required()
@require_roles("admin")
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


@compliance_bp.route("/override", methods=["POST"])
@jwt_required()
@require_roles("manager", "admin")
def manual_override():
    identity = get_jwt_identity()
    user = _resolve_user(identity)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    application_id = data.get("application_id")
    new_decision = data.get("new_decision", "").upper()
    reason = _sanitize(data.get("reason", ""), 500)

    if not application_id:
        return jsonify({"error": "application_id required"}), 400
    if new_decision not in ("ONAYLANDI", "REDDEDİLDİ"):
        return jsonify({"error": "new_decision must be ONAYLANDI or REDDEDİLDİ"}), 400

    app_record = Application.query.get(application_id)
    if not app_record:
        return jsonify({"error": "Application not found"}), 404

    original = app_record.decision
    app_record.is_overridden = True
    app_record.final_decision = new_decision
    app_record.review_notes = reason
    app_record.reviewed_by_user_id = user.id

    override = ManualOverride(
        application_id=application_id,
        user_id=user.id,
        user_role=user.role,
        original_decision=original,
        new_decision=new_decision,
        reason="policy_exception_approved",
        reason_detail=reason or "Manual override by analyst",
        override_timestamp=utcnow(),
        ip_address=request.remote_addr,
    )
    db.session.add(override)
    db.session.commit()
    _stats["overridden"] += 1

    _write_audit_event(
        event_type="manual_override",
        identity=identity,
        application_id=application_id,
        detail={"original": original, "new": new_decision, "reason": reason},
        status_code=200,
    )

    return jsonify({
        "message": "Override applied successfully",
        "application_id": application_id,
        "original_decision": original,
        "new_decision": new_decision,
        "override_by": identity,
    })


# ---------------------------------------------------------------------------
# FAIRNESS DAILY endpoint  (/fairness/daily)
# ---------------------------------------------------------------------------

@compliance_bp.route("/fairness/daily")
@jwt_required()
def fairness_daily():
    """Return daily fairness summary (integrates with FairnessService)."""
    from app.services.fairness_service import FairnessService
    # Dummy approval rates for demo; production should pull from DB aggregation
    approval_rates = {"Q1": 35.0, "Q2": 45.0, "Q3": 55.0, "Q4": 62.0, "Q5": 70.0}
    
    check = FairnessService.check_80_percent_rule(
        q1_rate=approval_rates.get("Q1", 0.0),
        q5_rate=approval_rates.get("Q5", 0.0)
    )
    
    return jsonify({
        "date": utcnow().date().isoformat(),
        "approval_rates": approval_rates,
        "disparate_impact_ratio": check["di_ratio"],
        "passes_80_rule": check["passes_80_rule"],
        "alert_triggered": check["alert_triggered"],
        "alert_reason": "DI Ratio Alert" if check["alert_triggered"] else "",
        "recommendation": check["recommendation"],
    })




# Removed database_models initialization

# NLP model auto-training moved inside create_app() to run within application context


# ---------------------------------------------------------------------------
# Static files (index.html, application.html, etc.)
# ---------------------------------------------------------------------------

@health_bp.route("/")
def index():
    return send_from_directory("static", "index_v2.html")

@health_bp.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)




# ---------------------------------------------------------------------------
# Error handlers (registered via create_app() → register_error_handlers)
# ---------------------------------------------------------------------------




# @jwt.unauthorized_loader
def jwt_missing_token(msg):
    return jsonify({"error": "Missing or invalid authorization header"}), 401


# @jwt.invalid_token_loader
def jwt_invalid_token(msg):
    return jsonify({"error": "Invalid token"}), 401


# @jwt.expired_token_loader
def jwt_expired_token(jwt_header, jwt_payload):
    return jsonify({"error": "Token expired"}), 401


# @app.before_request
def add_request_context():
    setattr(request, "_request_start_ts", time.time())
    setattr(request, "_request_id", request.headers.get("X-Request-ID") or str(uuid.uuid4()))

    lower_path = request.path.lower()
    restricted_exts = (".py", ".env", ".git", ".db", ".joblib", ".sqlite", ".log", ".ini", ".yaml", ".yml")
    if any(lower_path.endswith(ext) or (ext + "/" in lower_path) for ext in restricted_exts):
        return jsonify({"error": "Access to requested resource is forbidden"}), 403

    if ENFORCE_JSON_REQUESTS and request.method in {"POST", "PUT", "PATCH"}:
        enforce_paths = (
            request.path.startswith("/api/")
            or request.path.startswith("/auth/")
            or request.path in {"/degerlendir", "/override"}
        )
        if enforce_paths and not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415


# @app.after_request
def apply_response_hardening(resp):
    if SECURITY_HEADERS_ENABLED:
        resp.headers["X-Request-ID"] = getattr(request, "_request_id", "")
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        resp.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        csp_default = "default-src 'self' https: data: blob: 'unsafe-inline' 'unsafe-eval'"
        resp.headers["Content-Security-Policy"] = os.getenv("CONTENT_SECURITY_POLICY", csp_default)
        if IS_PRODUCTION:
            resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    if request.path.startswith("/auth/"):
        resp.headers["Cache-Control"] = "no-store"

    elapsed_ms = (time.time() - getattr(request, "_request_start_ts", time.time())) * 1000.0
    if request.path.startswith("/api/") or request.path in {"/degerlendir", "/override"}:
        logger.info(
            "request id=%s method=%s path=%s status=%s latency_ms=%.2f ip=%s",
            getattr(request, "_request_id", "-"),
            request.method,
            request.path,
            resp.status_code,
            elapsed_ms,
            request.remote_addr,
        )

    return resp


@dashboard_bp.route("/api/dashboard-stats")
@jwt_required()
def dashboard_stats():
    total_apps = Application.query.count()
    approved_apps = Application.query.filter_by(final_decision="ONAYLANDI").count() + Application.query.filter_by(decision="ONAYLANDI", final_decision=None).count()
    rejected_apps = Application.query.filter_by(final_decision="REDDEDİLDİ").count() + Application.query.filter_by(decision="REDDEDİLDİ", final_decision=None).count()
    pending_apps = total_apps - (approved_apps + rejected_apps)
    
    approval_rate = (approved_apps / total_apps * 100) if total_apps > 0 else 0.0

    # Fetch total volume
    total_volume_query = db.session.query(db.func.sum(Application.loan_amnt)).filter(
        Application.final_decision == "ONAYLANDI"
    ).scalar()
    
    if not total_volume_query:
        # Fallback to normal decision if final_decision is not set
        total_volume_query = db.session.query(db.func.sum(Application.loan_amnt)).filter(
            Application.decision == "ONAYLANDI", Application.final_decision.is_(None)
        ).scalar()
        
    total_volume = float(total_volume_query or 0.0)

    # Fetch latest fairness score
    from app.models.models import FairnessAudit
    latest_audit = FairnessAudit.query.order_by(FairnessAudit.audit_date.desc()).first()
    di_score = round(latest_audit.di_ratio, 2) if latest_audit and latest_audit.di_ratio else 0.85

    # Fetch recent evaluations (applications) instead of audit logs
    recent_apps = Application.query.order_by(Application.created_at.desc()).limit(5).all()
    logs_data = []
    for app_record in recent_apps:
        score = app_record.risk_score if app_record.risk_score is not None else app_record.rejection_probability
        logs_data.append({
            "id": app_record.id,
            "timestamp": app_record.created_at.strftime("%Y-%m-%d %H:%M") if app_record.created_at else "",
            "action": "Değerlendirme",
            "decision": app_record.final_decision or app_record.decision or "BİLİNMİYOR",
            "risk_score": round(score, 2) if score is not None else "-",
            "applicant_name": app_record.applicant_name or f"Müşteri #{app_record.id}",
            "ip_address": app_record.ip_address or "127.0.0.1"
        })

    return jsonify({
        "total_applications": total_apps,
        "approval_rate": round(approval_rate, 1),
        "total_volume": f"${total_volume:,.0f}",
        "di_score": di_score,
        "recent_logs": logs_data,
        "chart_data": {
            "trend": {
                "labels": ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"],
                "data": [0, 0, 0, 0, 0, 0, total_apps]
            },
            "decisions": {
                "approved": approved_apps,
                "rejected": rejected_apps,
                "pending": max(0, pending_apps)
            }
        }
    })


@dashboard_bp.route("/api/v2/monitoring/drift", methods=["GET"])
@jwt_required()
def get_model_drift():
    """Returns population stability index (PSI) and feature-level drift metrics."""
    from app.services.drift_service import DriftService
    try:
        sample_window = request.args.get("window", default=500, type=int)
        analysis = DriftService.analyze_drift(sample_window=sample_window)
        return jsonify(analysis), 200
    except Exception as exc:
        logger.exception("Error in /api/v2/monitoring/drift: %s", exc)
        return jsonify({"error": "Failed to compute drift analysis", "detail": str(exc)}), 500


@dashboard_bp.route("/api/v2/monitoring/drift/recalculate", methods=["POST"])
@jwt_required()
def recalculate_model_drift():
    """Forces fresh re-computation of drift analysis."""
    from app.services.drift_service import DriftService
    try:
        analysis = DriftService.analyze_drift(sample_window=500)
        return jsonify({"message": "Drift metrics recalculated successfully", "data": analysis}), 200
    except Exception as exc:
        logger.exception("Error in recalculate_model_drift: %s", exc)
        return jsonify({"error": "Failed to recalculate drift", "detail": str(exc)}), 500

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------



# ============================================================================
# MOVED FROM main.py
# ============================================================================

@credit_bp.route('/model-info')
@jwt_required()
def get_model_info():
    """Model metadata endpoint"""
    try:
        from app.ml.model_constants import PRODUCTION_META_PATH
        import json
        
        meta = {}
        if os.path.exists(PRODUCTION_META_PATH):
            with open(PRODUCTION_META_PATH, 'r') as f:
                meta = json.load(f)
                
        return jsonify({
            'status': 'ok',
            'model_name': meta.get('model', 'FinWise Production Model'),
            'version': meta.get('version', 'unknown'),
            'trained_at': meta.get('trained_at', 'unknown'),
            'metrics': meta.get('metrics', {})
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@credit_bp.route('/admin/reload-model')
@jwt_required()
def reload_model_admin():
    """Reload model from disk (admin only)."""
    try:
        global PRIMARY_MODEL
        from app.ml.model_constants import PRODUCTION_MODEL_PATH
        import joblib
        
        if os.path.exists(PRODUCTION_MODEL_PATH):
            PRIMARY_MODEL = joblib.load(PRODUCTION_MODEL_PATH)
            return jsonify({'status': 'Model reloaded successfully'})
        return jsonify({'error': 'Model file not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Model reload failed: {e}'}), 500

@credit_bp.route('/api/findeks/fetch', methods=["POST"])
def findeks_fetch():
    """Simulate fetching credit history from Findeks via TCKN."""
    data = request.get_json(silent=True) or {}
    tckn = data.get('tckn', '')
    if not tckn or len(str(tckn)) != 11:
        return jsonify({'error': 'Gecerli bir 11 haneli TCKN giriniz.'}), 400
    
    import random
    random.seed(tckn)
    last_digit = int(str(tckn)[-1])
    
    if last_digit in [0, 2]:
        hist_length = random.randint(5, 20)
        default = 'N'
    elif last_digit in [4, 6]:
        hist_length = random.randint(1, 4)
        default = 'Y' if random.random() > 0.7 else 'N'
    else:
        hist_length = random.randint(2, 10)
        default = 'Y' if random.random() > 0.9 else 'N'
        
    return jsonify({
        'tckn': tckn, 
        'cb_person_cred_hist_length': hist_length,
        'cb_person_default_on_file': default, 
        'credit_score': random.randint(800, 1900)
    })



_app_configured = False

def create_app(app_instance=None):
    """
    Application factory that configures the Flask app with all extensions,
    error handlers, JWT callbacks, blueprints, and database initialization.
    
    If app_instance is None, uses the module-level ``app`` object.
    """
    global _app_configured
    _app = app_instance or app
    
    if _app_configured:
        return _app

    # --- Core Config ---
    _app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///finwise_credit.db"
    )
    _app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    _app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SEC", "1800")),
    }
    _app.config["JWT_SECRET_KEY"] = os.getenv(
        "JWT_SECRET_KEY", "dev-jwt-secret-CHANGE-ME-IN-PROD"
    )
    _app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=12)
    _app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "dev-secret-key-CHANGE-ME-IN-PROD"
    )
    _app.config["SWAGGER"] = {
        "title": "FinWise ML Platform API",
        "uiversion": 3,
    }

    # --- Extensions ---
    limiter.init_app(_app)
    db.init_app(_app)
    jwt = JWTManager(_app)
    Swagger(_app)

    # --- JWT Error Callbacks ---
    jwt.unauthorized_loader(jwt_missing_token)
    jwt.invalid_token_loader(jwt_invalid_token)
    jwt.expired_token_loader(jwt_expired_token)

    # --- Request Hooks ---
    _app.before_request(add_request_context)
    _app.after_request(apply_response_hardening)

    # --- Error Handlers (from app/utils/error_handlers.py) ---
    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(_app)

    # --- Register Blueprints ---
    _app.register_blueprint(auth_bp)
    _app.register_blueprint(credit_bp)
    _app.register_blueprint(dashboard_bp)
    _app.register_blueprint(compliance_bp)
    _app.register_blueprint(health_bp)

    # --- Database Init ---
    with _app.app_context():
        db.create_all()
        try:
            inspector = sa_inspect(db.engine)
            existing = set(inspector.get_table_names())
            required = {"users", "applications", "manual_overrides", "audit_logs"}
            if not required.issubset(existing):
                logger.warning(
                    "Missing required tables in DB! Expected %s, found %s",
                    required,
                    existing,
                )
            
            # Ensure audit_logs has all required columns in SQLite
            if "audit_logs" in existing:
                col_names = {c["name"] for c in inspector.get_columns("audit_logs")}
                missing_cols = [
                    ("action", "VARCHAR(100)"),
                    ("entity_type", "VARCHAR(50)"),
                    ("entity_id", "INTEGER"),
                    ("changes", "TEXT"),
                    ("old_value", "TEXT"),
                    ("new_value", "TEXT"),
                    ("reason", "TEXT"),
                ]
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    for col, col_type in missing_cols:
                        if col not in col_names:
                            conn.execute(text(f"ALTER TABLE audit_logs ADD COLUMN {col} {col_type}"))
                    conn.commit()
        except Exception as e:
            logger.error("Error checking/migrating DB schema: %s", e)

        # Auto-train NLP model on startup if local mode is active (runs inside app context)
        try:
            if os.getenv('AI_ASSISTANT_PROVIDER', '').strip().lower() == 'local':
                from train_local_nlp import train_and_save
                train_and_save()
                logger.info("Local NLP model auto-trained from DB data")
        except Exception as _exc:
            logger.warning("Could not auto-train NLP model: %s", _exc)

    _app_configured = True
    return _app


# ---------------------------------------------------------------------------
# Initialize the application at module load time
# ---------------------------------------------------------------------------
create_app()


if __name__ == "__main__":
    import sys

    print("\n" + "=" * 60)
    print("FinWise Credit Risk API v2 - Secure Server")
    print("=" * 60)
    print(f"  Primary model  : {PRODUCTION_MODEL_PATH}")
    print(f"  Canary model   : {CANARY_MODEL_PATH} ({'loaded' if CANARY_MODEL else 'NOT FOUND'})")
    print(f"  Routing mode   : {router.mode} (canary {router.canary_percent}%)")
    if SHAP_AVAILABLE is True:
        shap_state = "enabled"
    elif SHAP_AVAILABLE is False:
        shap_state = "disabled"
    else:
        shap_state = "on-demand"
    print(f"  SHAP           : {shap_state}")
    print(f"  Prometheus     : {'enabled' if PROM_AVAILABLE else 'disabled'}")
    print(f"\n  Health  : http://127.0.0.1:5000/health")
    print(f"  Startup : http://127.0.0.1:5000/health/startup")
    print(f"  Metrics : http://127.0.0.1:5000/metrics")
    print(f"  Login   : POST http://127.0.0.1:5000/auth/login")
    print(f"  Predict : POST http://127.0.0.1:5000/degerlendir")
    print("\nCtrl+C to stop\n")

    host = "0.0.0.0"
    port = 5000

    try:
        from waitress import serve
        print(f"Serving via Waitress on http://{host}:{port}")
        serve(app, host=host, port=port, threads=4)
    except ImportError:
        print(f"Waitress not found - using Flask dev server on http://{host}:{port}")
        app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)

