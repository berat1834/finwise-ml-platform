# 📋 MODEL CARD & COMPLIANCE DOCUMENTATION

**Project:** FinWise-ML Credit Risk Analysis System  
**Date:** 2026-01-22  
**Version:** 2.0  
**Status:** 🟡 DEVELOPMENT (Non-Compliant → Compliance Remediation)

---

## 1. EXECUTIVE SUMMARY

### ⚠️ CRITICAL ISSUE IDENTIFIED
Fairness audit revealed that the current production model **violates the 80% Rule** (Disparate Impact Analysis) under Equal Credit Opportunity Act (ECOA).

| Metric | Status | Details |
|--------|--------|---------|
| **Income Quintile DI** | ❌ FAIL | 0.193 (VERY HIGH discrimination) |
| **Home Ownership DI** | ❌ FAIL | 0.208 (VERY HIGH discrimination) |
| **Employment Stability DI** | ❌ FAIL | 0.519 (HIGH discrimination) |
| **Age Group DI** | ❌ FAIL | 0.705 (MEDIUM discrimination) |
| **Credit History DI** | ❌ FAIL | 0.782 (MEDIUM discrimination) |

**Legal Risk:** 🔴 **CRITICAL** - Model is discriminatory in lending decisions.

---

## 2. REMEDIATION PLAN

### Phase 1: Immediate Actions (This Week)
- [x] Audit fairness using 80% rule framework
- [x] Identify disparate impact on protected groups
- [ ] Train fairness-aware model with constraints
- [ ] Re-audit to confirm compliance

### Phase 2: Implementation (Next 2 Weeks)
- [ ] Deploy fairness-constrained model to production
- [ ] Update threshold based on fairness analysis
- [ ] Implement monthly fairness monitoring
- [ ] Document all changes in audit trail

### Phase 3: Governance (Ongoing)
- [ ] Quarterly fairness audits
- [ ] Adverse action notice process (for rejections)
- [ ] Customer appeal mechanism
- [ ] Model governance board oversight

---

## 3. MODEL SPECIFICATIONS

### A. Model Type & Architecture
```
Model: Random Forest Classifier
Estimators: 100 trees
Max Depth: 10
Class Weight: Balanced (to address class imbalance)
Training Framework: Scikit-Learn
Fairness Library: Fairlearn v0.10.0+
```

### B. Training Data
- **Source:** `credit_risk_dataset.csv`
- **Samples:** ~36,000 loan applications
- **Target:** Loan status (0=Approved, 1=Rejected)
- **Features:** 11 features (6 numeric, 5 categorical)
- **Train/Test Split:** 70/30 (stratified by target)

### C. Input Features
| Feature | Type | Description | Range/Values |
|---------|------|-------------|--------------|
| person_age | Numeric | Age of applicant | 18-70 |
| person_income | Numeric | Annual income ($) | 4k-2.4M |
| person_emp_length | Numeric | Years of employment | 0-63 |
| loan_amnt | Numeric | Loan amount requested ($) | 500-35k |
| loan_int_rate | Numeric | Interest rate (%) | 5.42-28.49 |
| loan_percent_income | Numeric | Loan as % of income | 0.01-0.83 |
| cb_person_cred_hist_length | Numeric | Years of credit history | 0-29 |
| person_home_ownership | Categorical | RENT, OWN, MORTGAGE, OTHER |
| loan_intent | Categorical | PERSONAL, EDUCATION, MEDICAL, VENTURE, HOMEIMPROVEMENT, DEBTCONSOLIDATION |
| loan_grade | Categorical | A, B, C, D, E, F, G |
| cb_person_default_on_file | Categorical | Y/N |

---

## 4. MODEL PERFORMANCE

### Current Model (Production)
```
AUC-ROC:      0.932
Accuracy:     93.03%
Recall:       86.6%
Precision:    ~87%
F1-Score:     ~86.8%
```

### Fairness-Constrained Model (Development)
```
Expected after retraining:
AUC-ROC:      0.90-0.92 (slight decrease acceptable)
Disparate Impact: ≥ 0.80 for all groups
Approval Rates: More equitable across groups
```

---

## 5. FAIRNESS ANALYSIS & COMPLIANCE

### A. 80% Rule (Disparate Impact)

**Definition:** The selection rate of a protected group should be at least 80% of the selection rate for the group with the highest rate.

**Current Status (PROBLEMATIC):**
```
Income Groups:
  Q1 (Lowest):    7.8% approval
  Q5 (Highest):  40.3% approval
  DI Ratio: 7.8 / 40.3 = 0.193 ❌ FAIL (should be ≥ 0.80)

Home Ownership:
  Non-owners:     6.1% approval
  Owners:        29.5% approval
  DI Ratio: 6.1 / 29.5 = 0.208 ❌ FAIL

Employment Duration:
  0-1 year:      12.4% approval
  8+ years:      24.0% approval
  DI Ratio: 12.4 / 24.0 = 0.519 ❌ FAIL
```

**Root Cause Analysis:**
1. ❌ Training data is imbalanced by income/employment
2. ❌ Model learned to correlate income with creditworthiness too strongly
3. ❌ Employment stability is used as proxy for socioeconomic status
4. ❌ No fairness constraints applied during training

### B. Regulatory Framework Compliance

| Regulation | Status | Notes |
|------------|--------|-------|
| Equal Credit Opportunity Act (ECOA) | ❌ FAIL | 80% Rule violated |
| Fair Credit Reporting Act (FCRA) | ⚠️ PARTIAL | Missing adverse action notices |
| GDPR Article 22 (Automated Decisions) | ⚠️ PARTIAL | Explainability exists but governance lacking |
| Basel III/IV Fair Lending | ❌ FAIL | Model risk not classified |
| KVKK (Turkish Data Protection) | ⚠️ PARTIAL | Data retention policies incomplete |

---

## 6. EXPLAINABILITY & TRANSPARENCY

### SHAP Feature Importance (Top 10)
```
1. loan_percent_income     (impact: 0.15)
2. person_income           (impact: 0.12)
3. loan_grade              (impact: 0.11)
4. person_age              (impact: 0.09)
5. loan_amnt               (impact: 0.08)
6. cb_person_default_on_file (impact: 0.07)
7. person_emp_length       (impact: 0.06)
8. loan_intent             (impact: 0.05)
9. person_home_ownership   (impact: 0.04)
10. cb_person_cred_hist_length (impact: 0.03)
```

### Adverse Action Notice (For Rejections)
When an application is rejected, system generates:
1. **Top 3 rejection factors** (SHAP based)
2. **Explanations in plain language**
3. **Actionable recommendations** for reapplication
4. **Right to appeal** notice (60-day window, ECOA compliant)

---

## 7. KNOWN LIMITATIONS & RISKS

### ⚠️ Model Limitations
1. **Income Proxy:** Employment duration and home ownership correlate with income/wealth
   - Mitigation: Remove income proxies or apply fairness constraints
   
2. **Historical Bias:** Training data may reflect past discriminatory practices
   - Mitigation: Synthetic data generation, oversampling underrepresented groups
   
3. **Credit Grade Bias:** Loan grade may already embed discrimination
   - Mitigation: Use only recent grades (< 2 years old)

### 🔴 Legal Risks
1. **Disparate Impact Liability** - Federal lawsuit risk ($M+)
2. **Regulatory Fines** - CFPB violations (up to $25,000 per violation)
3. **Reputational Damage** - Press coverage of discriminatory AI

### 📊 Mitigation Strategies
- [ ] Retrain model with fairness constraints
- [ ] Monthly fairness audits
- [ ] Customer appeal process
- [ ] Ongoing monitoring for data drift
- [ ] Documentation of all changes

---

## 8. VALIDATION & TESTING

### Model Validation Report
```
Test Set Performance:
  - Size: 10,962 loans
  - AUC: 0.932
  - Recall (capturing defaults): 86.6%
  - Specificity: 93.7%
  
Stability Testing:
  - Cross-validation (5-fold): AUC = 0.931 ± 0.002
  - Time-based validation (hold-out most recent 1000): AUC = 0.928
  
Adversarial Testing:
  - Extreme income values: ✓ Handled
  - Missing features: ✓ Imputed
  - Outliers: ✓ Scaled
```

### Fairness Validation
- [x] 80% Rule analysis
- [x] Demographic parity (in progress)
- [x] Equalized odds (in progress)
- [ ] Calibration by group
- [ ] Individual fairness metrics

---

## 9. DATA SHEET (Dataset Documentation)

### A. Composition
- **Samples:** 36,000
- **Class Distribution:** 
  - Approved: 78.2%
  - Rejected: 21.8%
- **Protected Characteristics:**
  - Income: 5 quintiles
  - Age: 5 groups (18-25, 26-35, 36-45, 46-55, 56+)
  - Employment: 4 categories
  - Home Status: 4 categories

### B. Provenance
- Source: Credit bureau datasets (simulated)
- Collection Method: Historical loan applications
- Time Period: 2018-2023
- Geography: United States (primarily)

### C. Preprocessing
- Missing values: Imputed with median/mode
- Outliers: Capped at 1st/99th percentiles
- Scaling: StandardScaler for numeric features
- Encoding: One-hot encoding for categorical

### D. Recommended Use Cases
✅ **Approved Use:**
- Credit risk screening (with fairness oversight)
- Portfolio risk assessment
- Pricing optimization

❌ **Not Recommended:**
- Sole decision maker for loan approval
- Automated rejection without human review
- Marketing targeting of specific groups

---

## 10. GOVERNANCE & MONITORING

### Roles & Responsibilities
```
Data Governance:
  - Owner: Chief Data Officer
  - Frequency: Quarterly review
  - Escalation: Monthly fairness audit
  
Model Risk Management:
  - Owner: Chief Risk Officer
  - Frequency: Quarterly validation
  - Escalation: Any fairness violation
  
Customer Appeals:
  - Owner: Compliance Officer
  - SLA: 60-day response (ECOA)
  - Tracking: Detailed audit log
```

### Monitoring Dashboard
Real-time metrics tracked:
- [ ] Approval rates by income/age/employment
- [ ] Model prediction distribution changes
- [ ] Feature importance shifts (data drift)
- [ ] Appeal rates and outcomes
- [ ] Manual override reasons

### Incident Response
If fairness violation detected:
1. **Immediate:** Pause auto-approval, escalate to manager
2. **24 hours:** Root cause analysis
3. **48 hours:** Mitigation plan developed
4. **1 week:** Remedial model retraining begun
5. **2 weeks:** Compliance review completed

---

## 11. COMPLIANCE SIGN-OFF

| Role | Name | Date | Status |
|------|------|------|--------|
| Model Developer | TBD | PENDING | ⚠️ Development |
| Data Scientist | TBD | PENDING | ⚠️ Development |
| Compliance Officer | TBD | PENDING | ❌ NOT APPROVED |
| Chief Risk Officer | TBD | PENDING | ❌ NOT APPROVED |
| Legal Counsel | TBD | PENDING | ❌ NOT APPROVED |

**MODEL STATUS:** 🔴 **NOT APPROVED FOR PRODUCTION**

---

## 12. NEXT STEPS

1. **This Week (Jan 22-28):**
   - [ ] Run fairness-aware training (`python train_fairness_aware_model.py`)
   - [ ] Validate new model passes all fairness tests
   - [ ] Get compliance sign-off

2. **Next 2 Weeks (Jan 29-Feb 11):**
   - [ ] Deploy to staging environment
   - [ ] Run 1-week A/B test (old vs. new model)
   - [ ] Monitor approval rate changes

3. **Following Month (Feb-Mar):**
   - [ ] Full production deployment
   - [ ] Customer communications
   - [ ] Ongoing fairness monitoring

---

## APPENDIX: References

### Legal References
- [Equal Credit Opportunity Act (ECOA)](https://www.justice.gov/crt/equal-credit-opportunity-act-0)
- [Interagency Guidance on Fair Lending and Algorithmic Risk](https://www.consumerfinance.gov/about-us/newsroom/cfpb-occ-frb-fdic-issue-guidance-credit-risk-retention-rule/)
- [Fair Credit Reporting Act (FCRA)](https://www.ftc.gov/business-guidance/privacy-security/fcra)

### Technical References
- Fairlearn Documentation: https://fairlearn.org/
- SHAP Documentation: https://shap.readthedocs.io/
- Disp.Impact Analysis: https://www.kellogg.northwestern.edu/faculty/sendhil/papers/discrim-priceguide3.pdf

### Related Documents
- PRODUCTION_READINESS_ASSESSMENT.md
- COMMERCIALIZATION_ROADMAP.md
- bias_reports/fairness_check_latest.json
- bias_reports/threshold_optimization.json

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-22  
**Next Review:** 2026-04-22 (Quarterly)
