#!/usr/bin/env python3
"""GATE 2 canary retest: verify canary traffic split after route_key fix."""

from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime

import requests

API_BASE = "http://127.0.0.1:5000"
PROM_BASE = "http://127.0.0.1:9090"
USER = {"username": "gate2_tester", "password": "Gate2Test123!"}
TOTAL = 105
REQUEST_DELAY_SEC = 3.4


def ensure_user() -> None:
    payload = {"username": USER["username"], "password": USER["password"], "role": "analyst"}
    try:
        requests.post(f"{API_BASE}/auth/register", json=payload, timeout=5)
    except Exception:
        pass


def login_token() -> str:
    r = requests.post(f"{API_BASE}/auth/login", json=USER, timeout=10)
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token:
        raise RuntimeError("No access_token returned from /auth/login")
    return token


def check_health() -> dict:
    r = requests.get(f"{API_BASE}/health", timeout=10)
    r.raise_for_status()
    return r.json()


def build_payload(i: int) -> dict:
    incomes = [12000, 28000, 55000, 90000, 170000]
    intents = ["PERSONAL", "EDUCATION", "MEDICAL", "VENTURE"]
    grades = ["A", "B", "C", "D", "E"]
    homes = ["RENT", "OWN", "MORTGAGE"]

    person_income = float(incomes[i % len(incomes)] + (i % 10) * 300)
    loan_amnt = float(max(1000, person_income * (0.20 + (i % 20) / 100.0)))

    return {
        "person_age": 22 + (i % 43),
        "person_income": person_income,
        "person_emp_length": 1 + (i % 30),
        "loan_amnt": loan_amnt,
        "loan_int_rate": 5.0 + (i % 16),
        "loan_percent_income": round(min(0.95, loan_amnt / person_income), 4),
        "cb_person_cred_hist_length": 2 + (i % 20),
        "person_home_ownership": homes[i % len(homes)],
        "loan_intent": intents[i % len(intents)],
        "loan_grade": grades[i % len(grades)],
        "cb_person_default_on_file": "N",
    }


def run_predictions(token: str, total: int = TOTAL) -> tuple[Counter, int, list[dict]]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    routes = Counter()
    failed = 0
    errors = []

    t0 = time.time()
    for i in range(total):
        payload = build_payload(i)
        try:
            r = requests.post(f"{API_BASE}/degerlendir", json=payload, headers=headers, timeout=15)
            if r.status_code == 429:
                time.sleep(5)
                r = requests.post(f"{API_BASE}/degerlendir", json=payload, headers=headers, timeout=15)

            if r.status_code == 200:
                data = r.json()
                served_by = data.get("model_routing", {}).get("served_by", "unknown")
                routes[served_by] += 1
            else:
                failed += 1
                errors.append({"idx": i, "status": r.status_code, "body": r.text[:160]})
        except Exception as ex:
            failed += 1
            errors.append({"idx": i, "error": str(ex)[:160]})

        # Endpoint has 20/min limit; pacing keeps the test stable.
        time.sleep(REQUEST_DELAY_SEC)

        if (i + 1) % 25 == 0:
            elapsed = max(0.001, time.time() - t0)
            rate = (i + 1) / elapsed
            print(f"progress {i + 1}/{total} ({rate:.1f} req/s)")

    return routes, failed, errors


def query_prom_canary_pct() -> float | None:
    try:
        q = 'sum(finwise_model_route_total{route="canary_fair_v2_served"}) / sum(finwise_model_route_total)'
        r = requests.get(f"{PROM_BASE}/api/v1/query", params={"query": q}, timeout=10)
        if r.status_code != 200:
            return None
        body = r.json()
        result = body.get("data", {}).get("result", [])
        if not result:
            return None
        v = float(result[0]["value"][1])
        if v != v:
            return None
        return v * 100.0
    except Exception:
        return None


def main() -> int:
    print("GATE 2 canary retest started")

    health = check_health()
    print("health:", json.dumps(health, ensure_ascii=True))
    if health.get("routing_mode") != "canary":
        print("FAIL: API is not in canary mode. Start app with MODEL_ROUTING_MODE=canary and CANARY_PERCENT=10")
        return 2

    ensure_user()
    token = login_token()

    routes, failed, errors = run_predictions(token, TOTAL)
    success = sum(routes.values())
    canary = routes.get("canary_fair_v2_served", 0)
    pct = (canary / success * 100.0) if success else 0.0

    print("\nRouting distribution:")
    for k, v in routes.items():
        print(f"  {k}: {v}")

    print(f"\nSubmitted: {TOTAL}")
    print(f"Successful: {success}")
    print(f"Failed: {failed}")
    print(f"Canary split: {pct:.2f}%")

    prom_pct = query_prom_canary_pct()
    if prom_pct is None:
        print("Prometheus canary pct: unavailable")
    else:
        print(f"Prometheus canary pct: {prom_pct:.2f}%")

    ok = success >= 100 and 5.0 <= pct <= 15.0
    verdict = "PASS" if ok else "FAIL"
    print(f"\nGATE 2 CANARY RETEST: {verdict}")

    out = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "submitted": TOTAL,
        "successful": success,
        "failed": failed,
        "routes": dict(routes),
        "canary_pct": pct,
        "prometheus_canary_pct": prom_pct,
        "errors_sample": errors[:10],
        "verdict": verdict,
    }
    fn = f"gate2_canary_retest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Saved: {fn}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
