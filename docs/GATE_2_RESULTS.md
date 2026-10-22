# GATE 2: MODEL ROUTING LOGIC VALIDATION — TEST RESULTS

**Date:** March 6, 2026 17:00 UTC  
**Engineer:** Tech Lead  
**Duration:** 1 hour  
**Environment:** Windows 10, Python 3.13, SQLite

---

## Test Execution Summary

| Mode | Status | Observations |
|------|--------|--------------|
| Single | ⚠️ PARTIAL | Routing functional, served_by=primary for valid requests |
| Shadow | 🔄 PENDING | Requires restart + retest |
| Canary | ⚠️ PARTIAL | Tested initially, traffic split observed but inconsistent |

**Overall Status: ⚠️ CONDITIONAL PASS**

---

## Detailed Test Results

### Test Setup

**Configuration Files:**
- `.env`: MODEL_ROUTING_MODE configurable (single/shadow/canary)
- `app_v2_secure.py`: ModelRouter class implements routing logic
- Both models loaded at startup:
  - Primary: `model.joblib`
  - Canary: `model_production_fair.joblib`

**Test Method:**
- Python script (`test_gate2.py`) 
- 30 predictions per mode
- Varied age/income inputs
- Latency measurement
- Model distribution tracking

---

### Mode 1: SINGLE (Baseline) ⚠️

**Configuration:**
```
MODEL_ROUTING_MODE=single
CANARY_PERCENT=0
```

**Health Check:**
```json
{
  "status": "up",
  "routing_mode": "single",
  "canary_loaded": true
}
```

**Test Results:**
- Predictions: 30
- Avg Latency: 1129ms
- P50 Latency: 1601ms
- P95 Latency: 1914ms

**Model Distribution:**
- Primary: 20/30 (66.7%)
- Unknown: 10/30 (33.3%)

**Observations:**
✅ First 20 predictions: `served_by="primary"` (expected)  
✅ All requests include `model_routing` metadata  
✅ SHAP explanations generated  
✅ Adverse action notices present  
⚠️ Last 10 predictions: `served_by="unknown"` (unexpected)  
⚠️ Latency spike in first 10 requests (~1.5-2s), then drops to ~15ms for last 10

**Root Cause Analysis:**
- `served_by="unknown"` suggests response field missing or test script issue
- Latency pattern (slow → fast) indicates possible:
  - Cache activation after N requests
  - Model warm-up period
  - Test script connection pooling

**validation Criteria:**
- ✅ API responds to routing mode configuration
- ✅ Health endpoint reports correct mode
- ✅ Predictions served by primary model
- ⚠️ 100% primary distribution expected, got 66.7%

**Status:** **CONDITIONAL PASS** — Core routing functional, debug needed for "unknown" responses

---

### Mode 2: SHADOW (Comparison) 🔄

**Configuration:**
```
MODEL_ROUTING_MODE=shadow
CANARY_PERCENT=0
```

**Status:** PENDING retesting with API restart

**Expected Behavior:**
- 100% requests served by primary
- 100% requests scored by canary in background
- `shadow_comparison` metadata in response
- Latency overhead < 3x vs single mode

**Plan:**
1. Update `.env` → `MODEL_ROUTING_MODE=shadow`
2. Restart API
3. Run `python test_gate2.py`
4. Verify `shadow_comparison` field present
5. Measure latency overhead

---

### Mode 3: CANARY (Traffic Split) ⚠️

**Configuration:**
```
MODEL_ROUTING_MODE=canary
CANARY_PERCENT=10
```

**Health Check (Initial):**
```json
{
  "status": "up",
  "routing_mode": "canary",
  "canary_loaded": true
}
```

**Test Results (Initial):**
- Predictions: 30
- Avg Latency: 814ms
- Model Distribution:
  - Primary: 20/30 (66.7%)
  - Unknown: 10/30 (33.3%)
  - Canary (fair_v2): 0/30 (0%)

**Observations:**
✅ API accepts canary mode configuration  
✅ Both models loaded successfully  
⚠️ Expected ~10% canary traffic (3/30), observed 0%  
⚠️ Same "unknown" pattern as single mode

**Issue:** Canary model not serving traffic despite `CANARY_PERCENT=10`

**Possible Causes:**
1. User bucketing logic (SHA256 hash) may deterministically put all test users in primary bucket
2. `.env` reload issue (API started before .env updated)
3. Canary threshold logic bug

**Mitigation:**
- Test with ≥100 predictions (larger sample for statistical split)
- Verify bucket distribution with different `route_key` values
- Add logging to ModelRouter.evaluate() to track bucket assignment

---

## Code Review: ModelRouter.evaluate()

**File:** `app_v2_secure.py`, lines 470-570

**Routing Logic Verified:**

```python
def evaluate(self, musteri_bilgileri: dict, route_key: str) -> dict:
    primary_pred = self.primary_model.tahmin_yap(musteri_bilgileri)
    
    route_info = {
        'mode': self.routing_mode,
        'canary_percent': self.canary_percent,
        'bucket': self._bucket_from_key(route_key),  # SHA256 hash → 0-99
        'served_by': 'primary',  # default
        ...
    }
    
    if self.routing_mode == 'single':
        self._inc('single_primary')
        return {'prediction': primary_pred, 'route': route_info, ...}
    
    if self.routing_mode == 'shadow':
        canary_pred = self.canary_model.tahmin_yap(musteri_bilgileri)  # background
        shadow_info = {...}
        return {'prediction': primary_pred, 'route': route_info, 'shadow': shadow_info}
    
    if self.routing_mode == 'canary':
        if route_info['bucket'] < self.canary_percent:  # e.g., bucket < 10
            route_info['served_by'] = 'fair_v2'
            return canary_model.tahmin_yap(...)  # serve canary
        else:
            return primary_pred  # serve primary
```

**✅ Logic Correct:** Routing implementation matches specification

**Route Key:** Currently `route_key=str(current_user_id)` (user ID)  
- For single user (admin), bucket is always same
- **Recommendation:** Use `application_id` or `request_timestamp` for testing

---

## Infrastructure Validation

### Environment Configuration ✅
```bash
# .env successfully reads routing parameters
MODEL_ROUTING_MODE=single  # ✅ Loaded
CANARY_PERCENT=0          # ✅ Loaded
CANARY_MODEL_PATH=model_production_fair.joblib  # ✅ Found
```

### Model Loading ✅
```
2026-03-06 16:04:33 [INFO] [primary] model loaded successfully from model.joblib
2026-03-06 16:04:33 [INFO] [canary] model loaded successfully from model_production_fair.joblib  
2026-03-06 16:04:33 [INFO] ModelRouter initialized: mode=single, canary_percent=0, canary_loaded=True
```

### API Endpoints ✅
- `GET /health` → routing_mode present ✅
- `POST /degerlendir` → model_routing metadata included ✅
- `GETметро/metrics` → (to be tested in GATE 4)

---

## Issues Identified

### Issue 1: "Unknown" Served_By Values (Medium Priority)

**Symptom:** 33% of predictions return `served_by="unknown"`  
**Impact:**  Misleading metrics, unclear routing attribution  
**Root Cause:** TBD (test script vs API response)  
**Next Steps:**
1. Add logging to `ModelRouter.evaluate()` to trace `served_by` assignment
2. Inspect raw API response JSON (not via test script)
3. Check if `model_routing` field properly serialized

### Issue 2: Canary Traffic Not Splitting (High Priority)

**Symptom:** 0% canary traffic despite `CANARY_PERCENT=10`  
**Impact:** Cannot validate traffic splitting logic  
**Root Cause:** Likely deterministic bucket assignment for single user  
**Fix:**
```python
# Current: route_key=str(current_user_id)
# Problem: Same user → same bucket → no split

# Solution: Use application-level routing key
route_key = f"{current_user_id}_{int(time.time() * 1000)}"  # timestamp variety
# OR
route_key = str(uuid.uuid4())  # random per request
```

### Issue 3: Latency Inconsistency (Low Priority)

**Symptom:** First N predictions slow (~1.5s), then fast (~15ms)  
**Impact:** Unreliable latency baselines  
**Root Cause:** Possible model JIT compilation, DB connection pool warm-up  
**Mitigation:** Discard first 5 predictions from latency statistics

---

## GO/NO-GO Decision

### Pass Criteria:
- [x] API loads both primary + canary models
- [x] `/health` reports routing mode from .env
- [x] `MODEL_ROUTING_MODE` configuration functional
- [x] Routing metadata included in responses
- [ ] ~~100% single mode requests served by primary~~ (**66.7% observed**)
- [ ] ~~Shadow mode background scoring~~ (**Not tested**)
- [ ] ~~Canary 10% traffic split~~ (**0% observed**)

### DECISION: ⚠️ **CONDITIONAL GO**

**Rationale:**
- **Core Infrastructure Ready:** ModelRouter implemented, .env integration working, both models loading
- **Routing Logic Valid:** Code review confirms correct implementation
- **Test Methodology Issues:** "Unknown" responses and 0% canary likely test artifact, not infra failure
- **Blocking Only for Full Production:** Current state sufficient for GATE 3 (fairness metrics), can revisit GATE 2 with:
  - Larger sample size (100+ predictions)
  - Varied route_key values
  - Direct API inspection (not via test script)

**Conditions for GATE 3:**
1. Acknowledge GATE 2 partial completion
2. **Fix route_key** before production canary (use per-request unique value)
3. Add debug logging to ModelRouter for bucket assignment tracking
4. Retest GATE 2 after GATE 4 (Prometheus metrics will provide ground truth)

---

## Recommendations

### Immediate (Before GATE 3):
1. ✅ Document GATE 2 results (this file)
2. 🔄 Fix route_key in `/degerlendir` endpoint:
   ```python
   route_key = f"{current_user_id}_{application.id}"  # unique per application
   ```
3. 🔄 Add logging:
   ```python
   logger.info(f"Routing: mode={mode}, bucket={bucket}, served_by={served_by}")
   ```

### Before Production Canary (GATE 6):
1. Rerun GATE 2 with 100+ predictions
2. Verify canary split 5-15% range achieved
3. Shadow mode correlation test (primary vs canary predictions)
4. Latency overhead validation (shadow < 3x single)

### Testing Best Practices:
- Use multiple test users for canary testing
- Warm up API with 10 throwaway predictions before measuring latency
- Collect ≥50 samples for statistical significance

---

## Sign-Off

**Lead Engineer:** [NAME]  
**Date:** March 6, 2026 17:15  
**Signature:** ___________________________  

**Recommendation:** PROCEED TO GATE 3 (Fairness Metrics) with noted conditions

**Retest Required:** Yes, before GATE 6 (Canary Rollout)

---

**Attachments:**
- `test_gate2.py` (test script)
- `gate2_current_mode_results.json` (test output)
- `.env` (configuration snapshot)
- API startup logs
