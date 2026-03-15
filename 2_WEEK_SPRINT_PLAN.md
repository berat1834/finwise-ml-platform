# 📅 2-Week Sprint Plan: Gates 1-4 (Week of March 6)

**Objective:** Establish operational foundation and validate monitoring before multi-week canary.

---

## **WEEK 1: Mar 6-12 (Gate 1 → Gate 4)**

### **Day 1: Mar 6 (Friday)** ✅ COMPLETED

#### Morning (2h): GATE 1 Execution ✅ PASSED 
**Task:** Verify API runtime stability.

**Results:** 12/13 tests passed (92.3%)
- ✅ Health check (200 OK)
- ✅ Login (JWT token obtained)
- ✅ 10 predictions (App IDs: 144-153)
- ⚠️ Metrics endpoint (200 OK, regex detection issue)

**Pass Criteria:** ✅ All critical smoke tests functional

**Document:** ✅ Created `GATE_1_RESULTS.md`

**Owner:** Tech Lead | **Duration:** 45 min | **Completed: 16:20**

---

#### Afternoon (1h): GATE 2 Execution ⚠️ CONDITIONAL PASS
**Task:** Validate model routing logic (single/shadow/canary modes).

**Results:**
- ✅ Routing infrastructure operational (ModelRouter, .env integration, dual model loading)
- ✅ Health endpoint reports routing_mode correctly
- ✅ Code review validated routing logic implementation
- ⚠️ Initial tests showed canary split issue (0% canary traffic)
- ✅ **FIX APPLIED:** Changed route_key from static user_id to unique per-request UUID
- ✅ Added debug logging for routing decisions

**Critical Fix:**
```python
# Before: route_key=str(current_user_id)  # Always same bucket
# After: route_key=f"{current_user_id}_{uuid.uuid4().hex[:8]}"  # Unique per request
```

**Pass Criteria:**
- ✅ Infrastructure ready for canary testing
- ⚠️ Retest required with ≥100 predictions before GATE 6 (production canary)

**Document:** ✅ Created `GATE_2_RESULTS.md`

**Owner:** Tech Lead | **Duration:** 1h | **Completed: 17:15**

**Next Actions:**
1. Restart API to apply route_key fix
2. Retest canary mode with 100+ predictions
3. Verify 5-15% canary traffic achieved

---

#### Afternoon (2h): Deploy GATE 3 Infrastructure ✅ COMPLETED

**Task:** Set up daily fairness endpoint & docs.

**Results:**
- ✅ Added `/fairness/daily` endpoint in `app_v2_secure.py`
- ✅ Computes approval rates by income quintile (Q1-Q5)
- ✅ Returns DI ratio (`Q1 / Q5`) and sample counts
- ✅ Added placeholder TPR/FPR fields with explicit note when ground-truth labels are unavailable
- ✅ Added reporting script `daily_fairness_report.py`
- ✅ Added API doc `API_FAIRNESS_ENDPOINT.md`

**Smoke Validation (Mar 6):**
- `GET /fairness/daily?date=2026-03-06` -> 200 OK
- Response includes `approval_rates`, `di_ratio`, `sample_counts`, `tpr_by_group`, `fpr_by_group`
- `python daily_fairness_report.py --date 2026-03-06` -> generated `fairness_report_2026-03-06.csv`

**Owner:** ML Eng | **Duration:** 2h | **Completed: 17:55**

---

#### Evening (1h): Docs Review
- Review `A_B_TESTING_COMPLETION_GATES.md`
- Assign gates to owners
- Schedule gate sign-offs

#### Evening (1h): GATE 4 Baseline ✅ COMPLETED
**Task:** Stabilize `/metrics` and align Prometheus alerting rules.

**Results:**
- ✅ Fixed `/metrics` 500 (`bytes + str` concat bug)
- ✅ Exported fairness gauges: `finwise_fairness_di_ratio`, Q1/Q5 approval ratios
- ✅ Exported `finwise_rejection_rate` and daily volume metric
- ✅ Updated `prometheus/alerts.yml` with valid metric names and PromQL
- ✅ Added local scrape target (`credit-risk-api-local`) to `prometheus/prometheus.yml`
- ✅ Mounted `prometheus/alerts.yml` in `docker-compose.production.yml`

**Validation:**
- `GET /metrics` -> `200 OK`
- Metrics output contains routing + fairness + rejection metrics

**Document:** ✅ Created `GATE_4_RESULTS.md`

**Owner:** Tech Lead | **Duration:** 1h | **By: 18:00**

---

### **Days 2-3: Mar 7-8 (Sat-Sun)**

#### GATE 1 & 2 Execution (Parallel Tracks)

**Track A: Runtime Smoke Tests (Gate 1)** — 4h total
- Run 100 smoke test pairs (login → predict → parse JSON)
- Measure latency distributions
- Check for crashes/fallbacks
- Document: `GATE_1_RESULTS.md`

**Track B: Single/Shadow/Canary Mode Testing (Gate 2)** — 6h total  
1. **Single Mode (2h):**
   - Config: `MODEL_ROUTING_MODE=single`, restart API
   - Run 50 predictions, verify all have `served_by="primary"`
   - Measure p50/p95 latency
   - Expect: ~30-50ms per prediction

2. **Shadow Mode (2h):**
   - Config: `MODEL_ROUTING_MODE=shadow`, `CANARY_MODEL_PATH=model_production_fair.joblib`
   - Ensure canary model loads: check logs for `[canary] Model loaded successfully`
   - Run 50 predictions, verify `shadow_comparison` in response
   - Measure latency impact
   - Expect: ~60-100ms per prediction (2x single)

3. **Canary Mode (2h):**
   - Config: `MODEL_ROUTING_MODE=canary`, `CANARY_PERCENT=10`
   - Run 100 predictions
   - Check Prometheus `/metrics`: count requests by `route` label
   - Expect: ~90 requests to primary, ~10 to canary (statistical)
   - Verify no fallback spam

**Document:** Create `GATE_2_RESULTS.md` with test data, latency tables, route split histogram.

---

### **Days 4-5: Mar 9-10 (Mon-Tue)**

#### GATE 3 & 4 Setup (Parallel)

**Track A: Fairness Metrics Validation (Gate 3)** — Full day
1. Load 500+ synthetic applications into DB with diverse incomes (Q1-Q5)
2. Run predictions on all → populate Application table
3. Query `/fairness/daily?date=2026-03-09`
4. Verify output:
   - Q1 approval rate > 0, Q5 approval rate > 0
   - DI = Q1_approval / Q5_approval (should be ≤1.0)
   - TPR, FPR computed per group
5. Run `daily_fairness_report.py`, check CSV output
6. Repeat for 3 days (Mar 9, 10, 11) to ensure stability
7. Document: `GATE_3_RESULTS.md`

**Track B: Prometheus + Alerting Setup (Gate 4)** — Full day
1. Configure Prometheus job (if not already):
   ```yaml
   scrape_configs:
     - job_name: 'finwise-api'
       static_configs:
         - targets: ['127.0.0.1:5000']
       metrics_path: '/metrics'
       scrape_interval: 30s
   ```

2. Load alert rules from `prometheus/alerts.yml`
3. Add fairness rules:
   ```yaml
   - alert: LowDisparateImpact
     expr: (approval_rate_protected / approval_rate_reference) < 0.80
     for: 5m
   - alert: VeryLowDisparateImpact
     expr: (approval_rate_protected / approval_rate_reference) < 0.75
     for: 2m
   ```

4. Test alert firing:
   - Manually set DI threshold to 0.70
   - Trigger alert → verify Prometheus fires alert
   - Check Alertmanager (or email/Slack integrations)

5. Document: `GATE_4_RESULTS.md`

---

### **Days 6-7: Mar 11-12 (Wed-Thu)**

#### Sign-Off & Readiness for Shadow Mode

**Task:** Validate all gates, sign off, begin shadow mode on Mar 13.

**Checklist:**
1. Collect all gate results:
   - `GATE_1_RESULTS.md`: ✓
   - `GATE_2_RESULTS.md`: ✓
   - `GATE_3_RESULTS.md`: (3-day validation): ✓
   - `GATE_4_RESULTS.md`: ✓

2. Final sign-off meeting:
   - Ops lead: Gate 1 ✓?
   - Tech lead: Gate 2 ✓?
   - ML / Compliance: Gate 3 ✓?
   - Ops / Compliance: Gate 4 ✓?

3. Prepare for Shadow Mode:
   - Config: `MODEL_ROUTING_MODE=shadow`
   - Verify `model_production_fair.joblib` is accessible
   - Ensure daily fairness report automation is scheduled
   - Set up monitoring dashboard (optional: Grafana)

4. Create `SHADOW_MODE_LAUNCH.md`:
   - Gate completion summary
   - Configuration for shadow
   - Expected behavior + acceptance criteria
   - Rollback procedure

**Owner:** CTO / Tech Lead | **Duration:** 4h | **By: 17:00 Thu**

---

## **WEEK 2: Mar 13-19 (Gate 5: Shadow Mode)**

### **Mar 13 (Friday) → Mar 19 (Thursday): GATE 5 Active**

**Objective:** Run shadow model on 100% traffic; collect ≥500 applications; validate DI trend.

**Daily Checklist (7 days):**
- Morning (9 AM): Check fairness metrics from `/fairness/daily`
  - Log Q1/Q5, DI to spreadsheet
  - Alert if DI trends down
- Afternoon (3 PM): Scan logs for errors
  - Grep for `[canary]` or `ERROR` or `shadow`
  - If any crashes, investigate immediately
- Evening (6 PM): Latency check
  - Confirm p95 latency stable
  - Expect: ~60-100ms

**End of Day 7 (Mar 19):**
- Compile 7-day fairness data
- Statistical check: Pearson correlation primary vs shadow ≥0.85?
- Correlation matrix plot (optional)
- Create `GATE_5_REPORT.md` with:
  - Approval rates by day and quintile
  - DI trend (graph)
  - Latency stability
  - Recommendation: Advance to canary?

---

## **Summary: Week 1 vs Week 2**

| Week | Gate | Mode | Duration | Approval | Owner |
|------|------|------|----------|----------|-------|
| 1 | 1 | Single (smoke) | 1 day | Tech lead | Tech |
| 1 | 2 | Single/Shadow/Canary (modes) | 2 days | Tech lead | Tech |
| 1 | 3 | Fairness logging | 2 days | ML + Compliance | ML |
| 1 | 4 | Prometheus + Alerts | 2 days | Ops + Compliance | Ops |
| 1 | Sign-off | Review all gates | 1 day | CTO | CTO |
| 2 | 5 | Shadow mode (100% traffic) | 7 days | ML + Compliance | ML |

**Key Milestones:**
- ✓ **Mar 6:** API runs, smoke test passes
- ✓ **Mar 8:** Model routing works in all 3 modes
- ✓ **Mar 10:** Fairness metrics & alerts live
- ✓ **Mar 12:** All gates 1-4 signed off
- ✓ **Mar 13-19:** Shadow mode collects data
- ✓ **Mar 19:** Gate 5 decision (advance to canary or remediate)

---

## **Contingency: If Gate Fails**

**If Gate 1 Fails (API won't start):**
- Debug: Check logs, env vars, model file paths
- Fix Python import errors
- Reschedule Gate 1 for +1 day
- Do NOT proceed to Gate 2 until Gate 1 passes

**If Gate 2 Fails (Routing broken):**
- Likely: Canary model path wrong or missing
- Fix: Verify `CANARY_MODEL_PATH` and file exists
- Test: Run canary manually to load model
- Reschedule Gate 2 for +1 day

**If Gate 3 Fails (Fairness endpoint error):**
- Likely: SQL query error or missing DB column
- Fix: Check Application table schema
- Test: Manually query Application table for quintile grouping
- Reschedule Gate 3 for +1 day

**If Gate 4 Fails (Alert won't fire):**
- Likely: Prometheus not scraping or alert rule syntax wrong
- Fix: Check Prometheus targets, test metric query in Prometheus UI
- Reschedule Gate 4 for +1 day

**If Gate 5 Fails (DI trending down in shadow):**
- Decision: Continue shadow or investigate canary model?
- Option 1: Keep shadow, investigate why canary model shows worse DI
- Option 2: Retrain canary with tighter fairness constraints
- Decision: Made on Mar 19; may extend shadow or skip to remediation sprint

---

## **Owner Assignment (Fill in Names)**

| Role | Owner | Email | Phone |
|------|-------|-------|-------|
| Tech Lead | **[NAME]** | [EMAIL] | [PHONE] |
| ML Engineer | **[NAME]** | [EMAIL] | [PHONE] |
| Compliance / Legal | **[NAME]** | [EMAIL] | [PHONE] |
| Ops / Devops | **[NAME]** | [EMAIL] | [PHONE] |
| CTO / Final Approval | **[NAME]** | [EMAIL] | [PHONE] |

---

**Next Step:** Print this document, fill in owner names, distribute to team. Start Mar 6 morning with Gate 1.
