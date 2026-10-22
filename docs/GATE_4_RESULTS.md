# GATE 4: PROMETHEUS + ALERTING - RESULTS

**Date:** March 6, 2026  
**Engineer:** Tech Lead / Ops  
**Gate:** GATE 4 - Monitoring and Alerting Foundation

## Summary

GATE 4 baseline is implemented and validated at API level.

- `/metrics` endpoint now returns valid Prometheus text (`200 OK`)
- Fairness and routing metrics are exported for alerting
- Prometheus scrape configuration includes local and container targets
- Alert rules are aligned with exported metric names
- Production compose now mounts both `prometheus.yml` and `alerts.yml`

## Issues Found and Fixed

## 1) `/metrics` runtime error
- **Issue:** `can't concat str to bytes`
- **Cause:** `monitor.export_prometheus_metrics()` returns bytes, then code concatenated string metrics.
- **Fix:** Decode bytes to UTF-8 before concatenation in `app_v2_secure.py`.

## 2) Alert rules mismatched metric names
- **Issue:** Alerts referenced metrics not exported by API.
- **Fix:** Updated `prometheus/alerts.yml` to use exported metrics:
  - `finwise_rejection_rate`
  - `finwise_fairness_di_ratio`
  - corrected histogram quantile expression for latency buckets

## 3) Rule file not mounted in production compose
- **Issue:** Prometheus config references `/etc/prometheus/alerts.yml` but file not mounted.
- **Fix:** Added volume mount in `docker-compose.production.yml`:
  - `./prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro`

## 4) Missing local scrape target
- **Issue:** Dev runs from VS Code use `127.0.0.1:5000`, but config only had container DNS target.
- **Fix:** Added `credit-risk-api-local` scrape job in `prometheus/prometheus.yml`.

## Exported Metrics (Validated)

From live `/metrics` output:

- `finwise_model_routing_mode{mode="single|shadow|canary"}`
- `finwise_model_route_total{route="..."}`
- `finwise_canary_model_loaded`
- `finwise_canary_percent`
- `finwise_approval_rate_protected`
- `finwise_approval_rate_reference`
- `finwise_fairness_di_ratio`
- `finwise_rejection_rate`
- `finwise_daily_applications_total`

## Alert Rules (Current)

- `CanaryModelNotLoaded`
- `CanaryFallbackTrafficDetected`
- `HighRejectionRate`
- `DataDrift`
- `ModelLatencyHigh`
- `LowDisparateImpact`
- `VeryLowDisparateImpact`
- `APIDown`
- `MetricsEndpointDown`
- `HighCPUUsage`
- `HighMemoryUsage`
- `DiskSpaceLow`

## Smoke Validation Evidence

- API Health: `GET /health` -> `200 OK`
- Metrics Endpoint: `GET /metrics` -> `200 OK`
- Metrics output includes FinWise fairness + routing gauges and counters

## Live Prometheus Validation Evidence

- Prometheus service started: `docker compose -f docker-compose.production.yml up -d prometheus`
- Readiness endpoint: `GET http://127.0.0.1:9090/-/ready` -> `200`
- Rule groups loaded from file:
  - `api_alerts`, `fairness_alerts`, `model_alerts`, `resource_alerts`
  - file: `/etc/prometheus/alerts.yml`
- Active scrape target:
  - `credit-risk-api-local` -> `http://host.docker.internal:5000/metrics` (`health=up`)
- Alert API (`/api/v1/alerts`) returned evaluated alerts (pending/firing), including:
  - `HighRejectionRate`
  - `LowDisparateImpact`
  - `VeryLowDisparateImpact`
  - `HighMemoryUsage`

Note: `APIDown` can be firing in this validation when only Prometheus service is started (without compose `api` service), which is expected behavior for `up{job="credit-risk-api"} == 0`.

## Gate Decision

**Status:** PASS (monitoring foundation ready)

## Follow-ups (recommended)

1. Add Alertmanager service and notification channel (email/Slack/Teams)
2. Add API 5xx request counter metric to support error-rate alerts
3. Persist latency observations from prediction endpoint into histogram
4. Create Grafana dashboard panels for DI ratio and canary route split
