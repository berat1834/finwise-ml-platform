#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Bank offer adapter layer with timeout/retry and deterministic fallback mocks."""

from __future__ import annotations

import logging
import os
import time
from threading import Lock
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

_ADAPTER_STATS = {
    "total": {"attempts": 0, "success": 0, "fail": 0, "fallback_count": 0},
    "banks": {},
}
_ADAPTER_STATS_LOCK = Lock()


def _touch_bank_stats(bank_code: str) -> Dict:
    if bank_code not in _ADAPTER_STATS["banks"]:
        _ADAPTER_STATS["banks"][bank_code] = {"attempts": 0, "success": 0, "fail": 0}
    return _ADAPTER_STATS["banks"][bank_code]


def _record_attempt(bank_code: str):
    with _ADAPTER_STATS_LOCK:
        bank_stats = _touch_bank_stats(bank_code)
        _ADAPTER_STATS["total"]["attempts"] += 1
        bank_stats["attempts"] += 1


def _record_success(bank_code: str):
    with _ADAPTER_STATS_LOCK:
        bank_stats = _touch_bank_stats(bank_code)
        _ADAPTER_STATS["total"]["success"] += 1
        bank_stats["success"] += 1


def _record_fail(bank_code: str):
    with _ADAPTER_STATS_LOCK:
        bank_stats = _touch_bank_stats(bank_code)
        _ADAPTER_STATS["total"]["fail"] += 1
        bank_stats["fail"] += 1


def _record_fallback():
    with _ADAPTER_STATS_LOCK:
        _ADAPTER_STATS["total"]["fallback_count"] += 1


def get_offer_adapter_stats() -> Dict:
    with _ADAPTER_STATS_LOCK:
        return {
            "total": dict(_ADAPTER_STATS["total"]),
            "banks": {k: dict(v) for k, v in _ADAPTER_STATS["banks"].items()},
        }


class BankOfferAdapter:
    """Base adapter contract for partner bank offer providers."""

    bank_code = "BASE"
    bank_name = "Base Bank"
    sponsored = False

    def fetch_offer(self, request_payload: Dict) -> Optional[Dict]:
        raise NotImplementedError


class HttpBankOfferAdapter(BankOfferAdapter):
    """HTTP adapter with retry/timeout support for production integrations."""

    endpoint_env_var = ""

    def __init__(self, timeout_sec: float = 2.0, retries: int = 1):
        self.timeout_sec = timeout_sec
        self.retries = retries

    def _endpoint(self) -> str:
        return os.getenv(self.endpoint_env_var, "").strip()

    def fetch_offer(self, request_payload: Dict) -> Optional[Dict]:
        _record_attempt(self.bank_code)
        endpoint = self._endpoint()
        if not endpoint:
            _record_fail(self.bank_code)
            return None

        last_err = None
        for _ in range(self.retries + 1):
            try:
                resp = requests.post(endpoint, json=request_payload, timeout=self.timeout_sec)
                if resp.status_code >= 500:
                    last_err = f"{resp.status_code}"
                    continue
                if not resp.ok:
                    _record_fail(self.bank_code)
                    return None
                data = resp.json() if resp.text else {}
                if not isinstance(data, dict):
                    _record_fail(self.bank_code)
                    return None
                _record_success(self.bank_code)
                return {
                    "application_id": request_payload.get("application_id"),
                    "bank_code": self.bank_code,
                    "bank_name": self.bank_name,
                    "currency": str(request_payload.get("currency", "USD")).upper(),
                    "term_months": int(request_payload.get("term_months", 36)),
                    "annual_rate_percent": float(data.get("annual_rate_percent", 0.0)),
                    "monthly_payment": float(data.get("monthly_payment", 0.0)),
                    "total_payment": float(data.get("total_payment", 0.0)),
                    "processing_fee": float(data.get("processing_fee", 0.0)),
                    "sponsored": bool(data.get("sponsored", self.sponsored)),
                    "redirect_url": str(data.get("redirect_url", "")).strip() or "#",
                    "provider": "http",
                    "confidence_score": 0.93,
                    "data_freshness_sec": 0,
                }
            except Exception as exc:
                last_err = str(exc)
                time.sleep(0.05)

        logger.warning("Offer adapter %s failed after retries: %s", self.bank_code, last_err)
        _record_fail(self.bank_code)
        return None


class AlfaBankAdapter(HttpBankOfferAdapter):
    bank_code = "ALFA_BANK"
    bank_name = "Alfa Bank"
    sponsored = False
    endpoint_env_var = "BANK_API_ALFA_URL"


class NovaFinanceAdapter(HttpBankOfferAdapter):
    bank_code = "NOVA_FINANCE"
    bank_name = "Nova Finance"
    sponsored = True
    endpoint_env_var = "BANK_API_NOVA_URL"


class HorizonCreditAdapter(HttpBankOfferAdapter):
    bank_code = "HORIZON_CREDIT"
    bank_name = "Horizon Credit"
    sponsored = False
    endpoint_env_var = "BANK_API_HORIZON_URL"


def build_mock_offer(request_payload: Dict, bank_code: str, bank_name: str, annual_rate: float, fee_rate: float, sponsored: bool, redirect_url: str) -> Dict:
    loan_amount = float(request_payload.get("loan_amount", 0) or 0)
    term_months = int(request_payload.get("term_months", 36) or 36)
    currency = str(request_payload.get("currency", "USD")).upper()

    monthly_rate = annual_rate / 12.0
    if monthly_rate > 0:
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** term_months) / (((1 + monthly_rate) ** term_months) - 1)
    else:
        monthly_payment = loan_amount / max(1, term_months)

    monthly_payment = round(float(monthly_payment), 2)
    total_payment = round(monthly_payment * term_months, 2)
    processing_fee = round(loan_amount * fee_rate, 2)

    return {
        "application_id": request_payload.get("application_id"),
        "bank_code": bank_code,
        "bank_name": bank_name,
        "currency": currency,
        "term_months": term_months,
        "annual_rate_percent": round(annual_rate * 100, 2),
        "monthly_payment": monthly_payment,
        "total_payment": total_payment,
        "processing_fee": processing_fee,
        "sponsored": sponsored,
        "redirect_url": redirect_url,
        "provider": "mock",
        "confidence_score": 0.62,
        "data_freshness_sec": 0,
    }


def fetch_partner_offers(request_payload: Dict, allow_mock_fallback: bool = True) -> Tuple[List[Dict], Dict]:
    """Try partner adapters first, then fallback to deterministic mock offers."""
    adapters: List[BankOfferAdapter] = [
        AlfaBankAdapter(),
        NovaFinanceAdapter(),
        HorizonCreditAdapter(),
    ]

    offers: List[Dict] = []
    for adapter in adapters:
        offer = adapter.fetch_offer(request_payload)
        if offer:
            offers.append(offer)

    if offers:
        offers.sort(key=lambda x: (x.get("monthly_payment", 10**9), x.get("annual_rate_percent", 10**9)))
        return offers, {
            "is_mock": False,
            "fallback_used": False,
            "ranking_rule": "Sorted by monthly_payment, then annual_rate_percent",
            "sponsored_disclaimer": "Sponsored offers may affect visibility. Users can compare all offers.",
            "provider_count": len(offers),
        }

    if not allow_mock_fallback:
        _record_fallback()
        return [], {
            "is_mock": False,
            "fallback_used": True,
            "ranking_rule": "Sorted by monthly_payment, then annual_rate_percent",
            "sponsored_disclaimer": "Sponsored offers may affect visibility. Users can compare all offers.",
            "provider_count": 0,
            "lead_fallback": True,
        }

    fallback_offers = [
        build_mock_offer(request_payload, "ALFA_BANK", "Alfa Bank", 0.185, 0.012, False, "https://example.com/alfa-bank/apply"),
        build_mock_offer(request_payload, "NOVA_FINANCE", "Nova Finance", 0.169, 0.017, True, "https://example.com/nova-finance/apply"),
        build_mock_offer(request_payload, "HORIZON_CREDIT", "Horizon Credit", 0.195, 0.009, False, "https://example.com/horizon-credit/apply"),
    ]
    fallback_offers.sort(key=lambda x: (x["monthly_payment"], x["annual_rate_percent"]))
    _record_fallback()

    return fallback_offers, {
        "is_mock": True,
        "fallback_used": True,
        "ranking_rule": "Sorted by monthly_payment, then annual_rate_percent",
        "sponsored_disclaimer": "Sponsored offers may affect visibility. Users can compare all offers.",
        "provider_count": 0,
    }
