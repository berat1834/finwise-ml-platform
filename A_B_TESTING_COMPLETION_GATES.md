# ✅ A/B Testing & Canary Rollout Completion Gates

**Date:** 2026-03-06  
**Status:** Sprint Planning Phase

---

## 🚪 GATE SYSTEM (Go/No-Go)

### **GATE 1: Runtime Stability** ✓ (IN PROGRESS)
**Objective:** API starts and handles 10 consecutive login→evaluate flows without error.

**Completion Criteria:**
- [ ] `app_v2_secure.py` starts without error on `python app_v2_secure.py`
- [ ] `/health` endpoint returns 200 with `status: "up"`
- [ ] `/auth/login` (username: `admin`, password: `admin123`) returns valid JWT
- [ ] `/degerlendir` (POST with sample credit data) returns decision + model_routing metadata
- [ ] `/metrics` returns Prometheus format with routing counters
- [ ] 10 curl smoke tests (login → predict → json parse) all pass
- [ ] No exception spam in logs

**Blocker:** If API crashes on startup or fails health check, freeze all other work.

**Go/No-Go:** RUN ONCE, document result in [GATE_1_RESULTS.md](GATE_1_RESULTS.md)

---

### **GATE 2: Model Routing Logic** ✓ (READY)
**Objective:** Verify `ModelRouter` class works in single/shadow/canary modes without side effects.

**Completion Criteria:**
1. **Single Mode (Default):**
   - [ ] Config: `MODEL_ROUTING_MODE=single`
   - [ ] Each prediction uses only `model_production_optimal.joblib`
   - [ ] `model_routing.served_by = "primary"` in response JSON
   - [ ] Baseline latency measured (e.g., p95 < 100ms)
   
2. **Shadow Mode (Offline Simulation):**
   - [ ] Config: `MODEL_ROUTING_MODE=shadow`
   - [ ] Each prediction scores BOTH models; returns primary decision
   - [ ] Response includes `"shadow_comparison"` with both tahmin + red_olasiligi
   - [ ] Latency overhead measured (e.g., ~2x single latency acceptable)
   
3. **Canary Mode (Traffic Split):**
   - [ ] Config: `MODEL_ROUTING_MODE=canary`, `CANARY_PERCENT=5` (start low)
   - [ ] ~5% of requests routed to `model_production_fair.joblib` (bucket-based)
   - [ ] Other ~95% go to primary
   - [ ] Prometheus metrics track route split (`finwise_model_route_total`)
   - [ ] Fallback behavior tested: if canary model missing, defaults to primary

**Test Data:** Use 100 synthetic applications across income quintiles.

**Go/No-Go:** RUN ONCE per mode, log results to [GATE_2_RESULTS.md](GATE_2_RESULTS.md)

---

### **GATE 3: Fairness Metrics Collection** ✓ (IN DEV)
**Objective:** Daily fairness stats (DI, approval rates by group, TPR/FPR) are logged and queryable.

**Completion Criteria:**
- [ ] `/metrics` exposes `finwise_canary_percent` (gauge)
- [ ] `/metrics` exposes `finwise_canary_model_loaded` (gauge)
- [ ] `/metrics` exposes `finwise_model_route_total{route=...}` (counter per route)
- [ ] Custom fairness endpoint (e.g., `GET /fairness/daily?date=2026-03-06`) returns:
  - Q1 approval rate (%)
  - Q2, Q3, Q4, Q5 approval rates (%)
  - Disparate Impact Ratio (Q1/Q5)
  - True Positive Rate by group
  - False Positive Rate by group
  - Can be queried from Prometheus OR directly from Application DB table
- [ ] Daily report script (`daily_fairness_report.py`) generates CSV log

**Test Data:** 500+ real production applications with income diversity.

**Go/No-Go:** RUN DAILY for 7 days, ensure consistency, log to [GATE_3_RESULTS.md](GATE_3_RESULTS.md)

---

### **GATE 4: Prometheus + Alert Rules Active** ✓ (RECIPE PROVIDED)
**Objective:** Alerts fire correctly when thresholds breached.

**Completion Criteria:**
- [ ] Prometheus job scrapes `/metrics` every 30s
- [ ] Alert rule `CanaryModelNotLoaded` fires if `finwise_model_routing_mode{mode="canary"} == 1 && finwise_canary_model_loaded == 0`
- [ ] Alert rule `LowDisparateImpact` fires if DI < 0.80 for 5 mins
- [ ] Alert rule `VeryLowDisparateImpact` fires if DI < 0.75 for 2 mins (urgent)
- [ ] Alertmanager (or email/Slack) receives + delivers alert notification
- [ ] Test: Manually trigger threshold breach, confirm alert within 5 mins

**Test:** Set DI threshold to 0.7 temporarily, verify alert fires.

**Go/No-Go:** RUN ONCE, confirm alert delivery, log to [GATE_4_RESULTS.md](GATE_4_RESULTS.md)

---

### **GATE 5: Shadow Mode Validation (7 days)** ⏳
**Objective:** Shadow model runs on 100% of traffic; verify no correlation surprise, latency acceptable, logged correctly.

**Completion Criteria:**
- [ ] Shadow mode active for ≥7 days (e.g., Mar 7 - Mar 13)
- [ ] ≥500 applications with shadow comparison logged
- [ ] Statistical test: Pearson correlation between primary + shadow predictions ≥ 0.85
- [ ] Latency overhead stable (e.g., p95 shadow < p95 single × 2.5)
- [ ] No crash/fallback on shadow scoring
- [ ] Manual review: 5% of shadow results show DI improvement?
- [ ] Compliance review: Legal OK to proceed with canary?

**Go/No-Go:** RUN OVER 7 DAYS, compile [GATE_5_REPORT.md](GATE_5_REPORT.md)

---

### **GATE 6: Canary Rollout (14 days)** ⏳
**Objective:** Fair model serves 1%→5%→10%→25%→50% traffic incrementally; each step observed 48-72 hours before advancing.

**Timeline:**
- **Mar 14 - Mar 15** (48h): Canary 1%
  - Approval rate Q1/Q5 deviation < 2% from shadow
  - No crashes, proper DI logging
  - Go? Advance to 5%
  
- **Mar 16 - Mar 17** (48h): Canary 5%
  - Same checks
  - Advance to 10%
  
- **Mar 18 - Mar 20** (72h): Canary 10%
  - DI ≥ 0.75?
  - Advance to 25% or **PAUSE**
  
- **Mar 21 - Mar 23** (72h): Canary 25%
  - If DI < 0.80, prepare remediation
  - Can rollback to primary
  
- **Mar 24 - Mar 26** (72h): Canary 50%
  - Statistical test: N_canary ≥ 100, DI estimate ± 95% CI  
  - DI CI lower bound ≥ 0.75?
  - Approve or rollback

**Win Condition:** DI ≥ 0.80 across all groups by canary 50%.

**Lose Condition:** DI trending < 0.70 → ROLLBACK to primary immediately.

**Go/No-Go:** Daily checkpoint, log all results to [GATE_6_CHECKPOINT_*.md](GATE_6_CHECKPOINT_MAR14.md), etc.

---

### **GATE 7: Statistical Decision & Legal Sign-Off** ⏳
**Objective:** Formal fairness test + compliance approval before full rollout.

**Completion Criteria:**
- [ ] Hypothesis test: DI ratio at 50% canary traffic is ≥0.80 with 95% confidence?
  - Sample size ≥ 500 canary predictions
  - Compute 95% CI: `DI ± 1.96 × SE`
  - If CI lower < 0.80: **FAIL**
  
- [ ] Comparison table (primary vs fair model):
  
  | Metric | Primary | Fair V2 | Status |
  |--------|---------|---------|--------|
  | AUC | 0.920 | 0.91? | ≥0.90 OK |
  | Recall | 77.7% | ≥75%? | ≥75% OK |
  | Precision | 73.27% | ≥70%? | ≥70% OK |
  | DI Ratio | 0.628 | ≥0.80? | ✓ WIN |
  | Q1 Approval | 54.7% | ≥65%? | ✓ BETTER |
  | Q5 Approval | 87.1% | ≤90%? | ✓ FAIR |

- [ ] Compliance review memo signed by (legal/risk/compliance):
  - Model is compliant with ECOA / FCRA /  (local banking regs)
  - DI test result documented
  - Rollback plan confirmed
  - Production sign-off

**Go/No-Go:** Final sign-off, log to [GATE_7_APPROVAL.md](GATE_7_APPROVAL.md)

---

### **GATE 8: Full Rollout & Cutover** ⏳
**Objective:** Primary → Fair model in production; shadow on old model for validation; rollback ready.

**Completion Criteria:**
- [ ] Config: `MODEL_PATH=model_production_fair.joblib` (new primary)
- [ ] Config: `MODEL_ROUTING_MODE=shadow` (shadow on `model_production_optimal` for 1 week)
- [ ] Automated canary: if DI drops below 0.75 for 1 hour, auto-rollback to old
- [ ] 24/7 fairness monitoring active
- [ ] Rollback script tested once
- [ ] Release notes + training for ops team
- [ ] Customer comms: brief of fairness improvement

**Go/No-Go:** RUN ONCE, log to [GATE_8_CUTOVER.md](GATE_8_CUTOVER.md)

---

## 📊 **Summary: When Is "Done"?**

| Gate | What | Approval | Timeline |
|------|------|----------|----------|
| 1 | API starts, smoke test 10× | ✓ Tech eng | Now |
| 2 | Model router: single/shadow/canary modes work | ✓ Tech eng | 1 day |
| 3 | Fairness metrics logged daily | ✓ ML eng + compliance | 1 day |
| 4 | Prometheus alerts fire correctly | ✓ Ops + compliance  | 1 day |
| 5 | Shadow 7 days: validate latency, correlation, DI | ✓ ML eng + legal | 7 days |
| 6 | Canary 14 days: 1%→50%, inspect DI every step | ✓ ML eng + risk | 14 days |
| 7 | Stat test DI ≥0.80 + legal approval | ✓ Legal + compliance | 1 day |
| 8 | Full rollout + old model shadow | ✓ CTO + Legal | 1 day |

**TOTAL TIMELINE: ~26 days (3.7 weeks)**

**"DONE" means:**
- ✅ DI ≥ 0.80 achieved in canary
- ✅ All performance metrics acceptable (AUC ≥0.90, Recall ≥75%)
- ✅ Legal + compliance sign-off
- ✅ Monitoring live + alert rules armed
- ✅ Rollback tested + ready
- ✅ Team trained

---

## 🚨 **Kill-Switch Protocol**

**Automatic Rollback Triggers:**
1. DI drops < 0.75 for ≥1 hour → config: `MODEL_ROUTING_MODE=single` (primary)
2. API latency p95 > 2s AND routing_mode != single → revert to single
3. Error rate > 5% for ≥5 min → revert to single
4. Any unhandled exception in `ModelRouter.evaluate()` → fallback to primary

**Manual Rollback:**
```bash
# Set environment variable
export MODEL_ROUTING_MODE=single
# Restart app
systemctl restart finwise-api
# Confirm: GET /health should show routing_mode: "single"
```

---

## 📋 **Next Immediate Actions**

1. **TODAY (Mar 6):** Run GATE 1 + GATE 2 smoke tests
2. **TOMORROW (Mar 7):** Activate GATE 3 (daily fairness endpoint) + configure Prometheus job
3. **DAY 3 (Mar 8):** Activate GATE 5 (shadow mode on 100% traffic for 7 days)
4. **DAY 10 (Mar 15):** Begin canary gate 6 (1% traffic)
5. **DAY 24 (Mar 29):** Final stat test + legal sign-off (GATE 7)
6. **DAY 25 (Mar 30):** Full cutover (GATE 8)

---

## ✍️ **Template: GATE Result Documents**

```markdown
# GATE [N] RESULT

**Date:** 2026-03-XX  
**Approved By:** [Name / Role]  
**Status:** ✓ PASS | ⏸ PAUSE | ❌ FAIL

## Summary
[1-2 line result]

## Tests Executed
- [ ] Criterion 1: PASS / FAIL
- [ ] Criterion 2: PASS / FAIL
- [ ] ...

## Key Metrics
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| ... | ... | ... | ... |

## Issues Found
[None / List]

## Next Action
[Advance to GATE X / Pause & remediate / Rollback]

## Sign-Off
Name, Date, Signature
```

---

**Remember:** The model router code is deployed and silent (defaults to `single`). Each gate is a **contract**: once you pass it, you have data-driven confidence to go to the next. No guesswork.
