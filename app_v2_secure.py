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

import bleach
import joblib
import numpy as np
from dotenv import load_dotenv
from flask import Flask, jsonify, request, Response, send_from_directory
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
APP_START_TS = time.time()
APP_ENV = os.getenv("FLASK_ENV", "production").lower()
IS_PRODUCTION = APP_ENV == "production"
SECURITY_HEADERS_ENABLED = _parse_bool("SECURITY_HEADERS_ENABLED", True)
ENFORCE_JSON_REQUESTS = _parse_bool("ENFORCE_JSON_REQUESTS", True)

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-CHANGE-ME")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600)))
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", 1048576))
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_ERROR_MESSAGE_KEY"] = "error"
app.config["PROPAGATE_EXCEPTIONS"] = False
app.config["PREFERRED_URL_SCHEME"] = "https" if IS_PRODUCTION else "http"

if IS_PRODUCTION and _parse_bool("ENFORCE_STRONG_SECRETS", False):
    if app.config["JWT_SECRET_KEY"] == "dev-jwt-secret-CHANGE-ME":
        raise RuntimeError("Refusing to start in production with default JWT secret.")

CORS(
    app,
    origins=_split_csv_env(
        "ALLOWED_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:5000,http://localhost:5500,http://127.0.0.1:5500",
    ),
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
    supports_credentials=False,
)

jwt = JWTManager(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URL", "memory://"),
    default_limits=["200 per day", "50 per hour"],
)

# ---------------------------------------------------------------------------
# Database setup  (SQLAlchemy – models.py)
# ---------------------------------------------------------------------------
from models import db, User, Application, ManualOverride, AuditLog

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///finwise_production.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SEC", "1800")),
}
db.init_app(app)

with app.app_context():
    db.create_all()
    # Seed admin user once
    try:
        if not User.query.filter_by(username="admin").first():
            admin = User(
                username="admin",
                email="admin@finwise.local",
                password_hash=generate_password_hash("admin123"),
                role="admin",
            )
            db.session.add(admin)
            db.session.commit()
            logger.info("Seeded admin user")
    except Exception as exc:
        logger.warning("Could not seed admin: %s", exc)

    # Basic startup schema sanity check for critical tables.
    try:
        required = {"users", "applications", "manual_overrides", "audit_logs"}
        existing = set(sa_inspect(db.engine).get_table_names())
        missing = sorted(required - existing)
        if missing:
            logger.warning("Critical tables missing at startup: %s", ", ".join(missing))
        else:
            logger.info("Critical DB tables verified")
    except Exception as exc:
        logger.warning("Could not verify DB tables: %s", exc)

# ---------------------------------------------------------------------------
# ML Model loading  (primary + optional canary)
# ---------------------------------------------------------------------------
from data_utils import CATEGORICAL_COLS, NUMERIC_COLS
from model_constants import (
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

CANARY_MODEL_PATH = os.getenv("CANARY_MODEL_PATH", "model_production_fair.joblib")
CANARY_META_PATH = os.getenv("CANARY_MODEL_META_PATH", "model_production_fair_meta.json")
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
        # Support both pipeline models (raw features) and plain estimators
        # trained on already one-hot encoded columns.
        model_input = df
        if hasattr(model, "feature_names_in_"):
            expected = list(getattr(model, "feature_names_in_"))
            current = list(df.columns)
            if set(expected) != set(current):
                encoded = pd.get_dummies(df)
                encoded = encoded.reindex(columns=expected, fill_value=0)
                model_input = encoded

        proba = model.predict_proba(model_input)[0]

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
                # Keep default positional mapping if classes are unavailable/non-standard.
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
            application_id=int(application_id) if str(application_id).isdigit() else None,
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
    if not _ensure_shap_loaded():
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

@app.route("/health")
def health():
    return jsonify({
        "status": "up",
        "routing_mode": router.mode,
        "canary_loaded": CANARY_MODEL is not None,
        "timestamp": utcnow().isoformat(),
        "version": "2.0.0",
    })


@app.route("/health/startup")
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

@app.route("/api/v2/simulate/approval", methods=["POST"])
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


@app.route("/api/v2/simulate/improvement-options", methods=["POST"])
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


@app.route("/api/v2/applications/history", methods=["GET"])
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


@app.route("/api/v2/applications/history/<int:application_id>", methods=["DELETE"])
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


@app.route("/api/v2/applications/history/clear", methods=["DELETE"])
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


@app.route("/metrics")
def metrics():
    if not PROM_AVAILABLE:
        return Response("Prometheus not available\n", status=503, mimetype="text/plain")
    # Dynamic fairness metrics from DB
    try:
        with app.app_context():
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

@app.route("/auth/register", methods=["POST"])
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


@app.route("/auth/admin/create-user", methods=["POST"])
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


@app.route("/auth/admin/registration-policy", methods=["GET"])
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


@app.route("/auth/login", methods=["POST"])
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

    allow_demo_admin_login = (not IS_PRODUCTION) and _parse_bool("ALLOW_DEMO_ADMIN_LOGIN", True)

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
    if (
        allow_demo_admin_login
        and username == "admin"
        and password == "admin123"
        and (user is None or not check_password_hash(user.password_hash, password))
    ):
        # Dev convenience path: keep demo login stable for local smoke tests.
        if user is None:
            user = User(
                username="admin",
                email="admin@finwise.local",
                password_hash=generate_password_hash("admin123"),
                role="admin",
                is_active=True,
            )
            db.session.add(user)
        else:
            user.password_hash = generate_password_hash("admin123")
            user.role = "admin"
            user.is_active = True
        db.session.commit()

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


# ---------------------------------------------------------------------------
# PREDICTION endpoint  (/degerlendir)
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "person_age", "person_income", "person_emp_length",
    "loan_amnt", "loan_int_rate", "loan_percent_income",
    "cb_person_cred_hist_length", "person_home_ownership",
    "loan_intent", "loan_grade", "cb_person_default_on_file",
]


@app.route("/degerlendir", methods=["POST"])
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

    home_ownership = _sanitize(data.get("person_home_ownership", ""))
    loan_intent = _sanitize(data.get("loan_intent", ""))
    loan_grade = _sanitize(data.get("loan_grade", ""))
    default_on_file = _sanitize(data.get("cb_person_default_on_file", "N"))

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
        threshold_used=result["threshold"],
        model_version=result["model_version"],
        shap_values=shap_features,
        analyst_id=user.id if user else None,
        applicant_name=_sanitize(data.get("customer_id", ""), 200),
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:255] if request.user_agent else None,
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
        "onay_olasiligi": result["onay_olasiligi"],
        "red_olasiligi": result["red_olasiligi"],
        "threshold": result["threshold"],
        "model_version": result["model_version"],
        "model_routing": result.get("model_routing"),
        "application_id": application_id,
        "timestamp": utcnow().isoformat(),
    }

    if shap_features:
        response["shap_top_features"] = shap_features

    if result["tahmin"] == "REDDEDİLDİ":
        response["adverse_action_notice"] = _adverse_action_notice(feature_row, shap_features)

    return jsonify(response)


# ---------------------------------------------------------------------------
# EXPLANATION endpoint  (/explain/<id>)
# ---------------------------------------------------------------------------

@app.route("/explain/<int:application_id>", methods=["GET"])
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

@app.route("/istatistik", methods=["GET"])
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
@app.route("/api/v2/offers/fraud-stats", methods=["GET"])
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


@app.route("/override", methods=["POST"])
@jwt_required()
@require_roles("manager", "admin")
def manual_override():
    identity = get_jwt_identity()
    user = _resolve_user(identity)

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

@app.route("/fairness/daily", methods=["GET"])
@jwt_required()
def fairness_daily():
    """Return daily fairness summary (placeholder – integrates with FairnessMonitor)."""
    from fairness_monitor import FairnessMonitor
    monitor = FairnessMonitor()
    # Dummy approval rates for demo; production should pull from DB aggregation
    approval_rates = {"Q1": 35.0, "Q2": 45.0, "Q3": 55.0, "Q4": 62.0, "Q5": 70.0}
    check = monitor.check_fairness(approval_rates)
    return jsonify({
        "date": utcnow().date().isoformat(),
        "approval_rates": check.approval_rates,
        "disparate_impact_ratio": check.disparate_impact_ratio,
        "passes_80_rule": check.passes_80_rule,
        "alert_triggered": check.alert_triggered,
        "alert_reason": check.alert_reason,
        "recommendation": check.recommendation,
    })


# ---------------------------------------------------------------------------
# Register additional API routes from api_routes.py
# ---------------------------------------------------------------------------
from api_routes import register_application_endpoints

register_application_endpoints(app)

# Also initialise the raw-SQLAlchemy tables used by api_routes (database_models.py)
try:
    from database_models import Base as _dm_Base, engine as _dm_engine
    _dm_Base.metadata.create_all(_dm_engine)
    logger.info("database_models tables created/verified")
except Exception as _exc:
    logger.warning("Could not initialise database_models tables: %s", _exc)

# ---------------------------------------------------------------------------
# Static files (index.html, application.html, etc.)
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(".", "index_v2.html")


@app.route("/<path:filename>")
def static_files(filename):
    """Serve static files from project root (html, js, css)."""
    safe_name = os.path.basename(filename)  # prevent path traversal
    allowed_ext = {
        ".html", ".css", ".js", ".json", ".map", ".png", ".jpg", ".jpeg",
        ".gif", ".svg", ".webp", ".ico", ".txt", ".pdf",
    }
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in allowed_ext:
        return jsonify({"error": "File type not allowed"}), 403
    return send_from_directory(".", safe_name)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({"error": "Rate limit exceeded. Please slow down."}), 429


@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"error": "Authentication required"}), 401


@app.errorhandler(500)
def internal_error(e):
    logger.error("Internal server error: %s", e, exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


@jwt.unauthorized_loader
def jwt_missing_token(msg):
    return jsonify({"error": "Missing or invalid authorization header"}), 401


@jwt.invalid_token_loader
def jwt_invalid_token(msg):
    return jsonify({"error": "Invalid token"}), 401


@jwt.expired_token_loader
def jwt_expired_token(jwt_header, jwt_payload):
    return jsonify({"error": "Token expired"}), 401


@app.before_request
def add_request_context():
    request._request_start_ts = time.time()
    request._request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    if ENFORCE_JSON_REQUESTS and request.method in {"POST", "PUT", "PATCH"}:
        enforce_paths = (
            request.path.startswith("/api/")
            or request.path.startswith("/auth/")
            or request.path in {"/degerlendir", "/override"}
        )
        if enforce_paths and not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415


@app.after_request
def apply_response_hardening(resp):
    if SECURITY_HEADERS_ENABLED:
        resp.headers["X-Request-ID"] = getattr(request, "_request_id", "")
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        resp.headers["Cross-Origin-Resource-Policy"] = "same-origin"
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

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

    host = "127.0.0.1"
    port = 5000
    debug = os.getenv("FLASK_ENV", "production") == "development"

    try:
        from waitress import serve
        print(f"Serving via Waitress on http://{host}:{port}")
        serve(app, host=host, port=port, threads=4)
    except ImportError:
        print(f"Waitress not found - using Flask dev server on http://{host}:{port}")
        app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)
