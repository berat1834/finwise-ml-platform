# FinWise-ML: Terms of Service Template

**Version:** 1.0  
**Effective Date:** March 2026  
**Last Updated:** March 2026

---

## 1. ACCEPTANCE OF TERMS

By accessing or using the FinWise-ML Credit Risk Analysis API ("Service"), you agree to be bound by these Terms of Service. If you do not agree to these terms, you may not use the Service.

The Service is provided by FinWise Systems Ltd. ("Company," "we," "us," or "our"). 

---

## 2. DESCRIPTION OF SERVICE

The Service is an automated credit risk analysis and assessment platform that uses machine learning to evaluate loan applications. The Service provides:

- **Automated Credit Scoring:** Machine learning model predictions
- **Explainability:** SHAP-based explanation of decisions
- **Compliance Tools:** Fairness analysis and bias detection
- **API Access:** RESTful API for integration
- **Dashboard:** Real-time monitoring and analytics

### 2.1 Service Limitations

- The Service provides mathematical predictions only, NOT legal advice
- All credit decisions remain the Client's responsibility
- The Company makes NO warranties about credit decision accuracy
- Model performance varies by market and customer data quality

---

## 3. USER OBLIGATIONS

### 3.1 Legal Compliance

Client shall use the Service in compliance with all applicable laws, including:

- **Fair Credit Reporting Act (FCRA)** - USA
- **Equal Credit Opportunity Act (ECOA)** - Discriminatory lending prevention
- **Truth in Lending Act (TILA)** - Loan terms transparency
- **General Data Protection Regulation (GDPR)** - EU data protection
- **Turkish Banking Regulation (BDDK)** - Turkey-specific rules
- **Basel III/IV** - Financial stability requirements

### 3.2 Data Responsibilities

Client is responsible for:

- **Data Accuracy:** Ensuring input data is accurate and complete
- **Data Legality:** Only providing legally obtained customer data
- **Consent:** Obtaining explicit customer consent for credit evaluation
- **Data Security:** Protecting credentials and API keys
- **Audit Logs:** Maintaining records of all API calls for compliance

### 3.3 Fair Lending

Client shall NOT:

- Use the Service to discriminate based on protected classes (race, religion, gender, age, etc.)
- Ignore fairness analysis reports
- Systematically reject applications from demographic groups
- Use the Service as sole basis for credit decisions without human review

---

## 4. MODEL ACCURACY & LIMITATIONS

### 4.1 No Warranty

**THE SERVICE IS PROVIDED "AS-IS" WITHOUT WARRANTY.** The Company makes NO warranties regarding:

- Model accuracy or predictive performance
- Fitness for any particular purpose
- Non-infringement of third-party rights
- Absence of defects or errors

### 4.2 Performance Metrics

Typical performance (training data):

| Metric | Value |
|--------|-------|
| AUC-ROC | 0.90+ |
| Recall | 75%+ |
| Precision | 80%+ |
| Fairness (DI Ratio) | 0.75+ |

**NOTE:** Performance may degrade on your production data. Performance is NOT guaranteed.

### 4.3 Data Drift

The Company does NOT guarantee:

- Continuous model performance
- Early warning of model degradation
- Automatic model retraining
- Performance maintenance beyond 6 months

Client is responsible for:

- Monitoring model performance
- Testing on their own data
- Requesting retraining if performance drops
- Maintaining backup decision criteria

---

## 5. PRICING & BILLING

### 5.1 Pricing Tiers

| Tier | Requests/Day | Response Time | Support | Monthly |
|------|--------------|---------------|---------|---------|
| Starter | 100 | 2 sec | Email (24h) | $500 |
| Pro | 50,000 | 500ms | Priority (4h) | $2,000 |
| Enterprise | Unlimited | 200ms | Dedicated (1h) | Custom |

### 5.2 Usage-Based Billing

- Starter & Pro tiers include usage allotment
- Overage charges: $0.001 per request
- Monthly billing cycle
- 5-day grace period before suspension

### 5.3 Invoicing

- Monthly invoices sent on 1st of each month
- Payment terms: Net 30 days
- Late payment: 1.5% monthly interest
- Accepted methods: Credit card, Bank transfer

### 5.4 Refunds

- No refunds for used services
- Pro-rata refund on annual prepayment if cancelled within 30 days
- SLA violations: Credit applied to next month's invoice

---

## 6. SERVICE LEVEL AGREEMENT (SLA)

### 6.1 Uptime Guarantee

| Tier | Target | Downtime Allowed |
|------|--------|------------------|
| Starter | 99% | 7.2 hours/month |
| Pro | 99.5% | 3.6 hours/month |
| Enterprise | 99.9% | 43 minutes/month |

### 6.2 SLA Credits

If availability falls below guarantee:

- Up-time: 98% = 5% credit
- Up-time: 95% = 10% credit
- Up-time: <95% = 30% credit

Maximum monthly credit: 100% of monthly fee

### 6.3 Eligible Downtime

Does NOT include:

- Client-side errors or misconfigurations
- Customer data issues
- Scheduled maintenance (announced 7 days in advance)
- Force majeure events

### 6.4 Response Times

| Tier | P95 | P99 |
|------|-----|-----|
| Starter | 2000ms | 5000ms |
| Pro | 500ms | 2000ms |
| Enterprise | 200ms | 1000ms |

---

## 7. DATA PROTECTION & PRIVACY

### 7.1 Data We Collect

- API request data (features, decisions)
- Model prediction results
- User account information
- Usage metrics

### 7.2 Data Retention

- Request logs: 90 days (for audit)
- Model predictions: 7 years (legally required)
- User accounts: Until deletion

### 7.3 Data Security

Company implements:

- End-to-end encryption (TLS 1.3)
- Encrypted database at rest (AES-256)
- Access controls (role-based)
- Regular security audits
- Penetration testing

### 7.4 Your Data Rights (GDPR/CCPA)

You may request:

- **Access:** All data we hold about you
- **Correction:** Fix inaccurate data
- **Deletion:** Remove your account and data (right to be forgotten)
- **Portability:** Export your data in standard format
- **Objection:** Stop using data for specific purposes

To exercise rights: support@finwise-ml.com

---

## 8. FAIR LENDING COMPLIANCE

### 8.1 Disparate Impact Testing

Company performs monthly fairness audits:

- Disparate Impact (DI) Ratio calculation (must be ≥80%)
- Approval rate by demographic groups
- Feature importance analysis
- ECOA compliance check

Client receives: Monthly fairness report

### 8.2 Adverse Action Notices

For ECOA compliance (USA only):

Company provides adverse action notice template for any credit denied containing:

- Primary reasons for decision
- FCRA disclosure
- Right to appeal
- Credit bureau contact info

Client responsibility: Deliver notice to applicants

### 8.3 Appeal Process

Clients may submit appeals which:

- Are reviewed within 5 business days
- May trigger manual credit review
- Generate appeal documentation
- Are logged for audit purposes

---

## 9. INTELLECTUAL PROPERTY RIGHTS

### 9.1 Company IP

The Company retains all right, title, and interest in:

- Machine learning models
- Algorithms and code
- Training data (non-customer)
- Documentation and materials

Client receives: Limited, non-exclusive license to use Service

### 9.2 Customer IP

Client retains ownership of:

- Customer data submitted
- Custom training data
- Derivative reports/analysis

Company may use (anonymized) to:

- Improve model performance
- Conduct fairness audits
- Generate aggregate statistics

---

## 10. LIABILITY LIMITATIONS

### 10.1 Limitation of Liability

**IN NO EVENT SHALL COMPANY BE LIABLE FOR:**

- Indirect, incidental, special, or consequential damages
- Lost profits or business opportunities
- Reputational harm
- Loss arising from model predictions

**EVEN IF COMPANY HAS BEEN ADVISED OF SUCH DAMAGES.**

### 10.2 Liability Cap

Total liability for any claim cannot exceed:

- The fees paid in the 12 months preceding claim
- Maximum: $1,000,000

### 10.3 Exceptions

Liability cap does NOT apply to:

- Gross negligence or willful misconduct
- Infringement of IP rights
- Data privacy breaches
- Confidentiality violations

---

## 11. INDEMNIFICATION

Client shall indemnify and hold harmless the Company from:

- Claims arising from Client's use of Service
- Violation of these Terms
- Violation of applicable laws
- Infringement of third-party rights
- Claims by Client's customers

---

## 12. CONFIDENTIALITY

### 12.1 Confidential Information

Client acknowledges that:

- API keys are CONFIDENTIAL
- Model parameters are CONFIDENTIAL
- Model accuracy metrics may be treated as CONFIDENTIAL (optional)

### 12.2 Disclosure

Company may disclose without consent:

- To comply with law/court order
- In response to legitimate government request
- For fraud prevention
- To enforce these Terms

---

## 13. TERM & TERMINATION

### 13.1 Term

- **Free Trial:** 30 days (auto-renews to Starter monthly)
- **Paid Tiers:** Month-to-month or annual

### 13.2 Termination

**Client may terminate:**
- Anytime (free trial)
- With 30-day written notice (paid)

**Company may terminate:**
- Immediately for material breach
- For non-payment (after 15-day notice)
- For legal/regulatory requirement

### 13.3 Effect of Termination

Upon termination:

- Access ceased immediately
- Data deleted within 30 days (unless legally required)
- Refund only if applicable under SLA
- Audit logs retained for 2 years

---

## 14. AMENDMENTS

Company reserves right to modify Terms with:

- 30 days written notice
- Changes effective upon new service renewal
- Continued use = acceptance

---

## 15. GOVERNING LAW

These Terms shall be governed by the laws of [JURISDICTION]:

- **Primary:** Swiss Law (neutral)
- **Alternative:** Turkish Law (if Turkey is primary market)
- **Dispute Resolution:** Binding arbitration before litigation

---

## 16. CONTACT INFORMATION

**Legal Inquiries:**
FinWise Systems Ltd.
Email: legal@finwise-ml.com
Phone: +41 44 XXX XXXX
Address: [Headquarters Address]

---

## APPENDIX A: SLA CALCULATION METHODOLOGY

```
Monthly Downtime = Minutes of unavailability / Days in month

Example:
- February: 28 days
- Downtime: 60 minutes
- Percentage: (60 / (28*24*60)) * 100 = 0.15% unavailable
- Uptime: 99.85% (Starter target: 99%)
- Credit: 5% of monthly fee
```

---

## APPENDIX B: FAIRNESS METRICS DEFINITION

**Disparate Impact (DI) Ratio:**
```
DI = (Approval Rate of Protected Class) / (Approval Rate of Reference Class)

Example:
- Women approval rate: 60%
- Men approval rate: 80%
- DI Ratio: 60/80 = 0.75
- Legal sufficiency: ≥0.80 (FDA rule)
- Status: Just below threshold - may need mitigation
```

**Common Protected Classes:**
- Race/Ethnicity
- Gender
- Age (40+)
- Religion
- Disability status
- Marital status

---

**Document Version:** 1.0
**Last Legal Review:** March 2026
**Next Review Date:** September 2026 (annual)

*This is a template. Consult legal counsel for your jurisdiction before using.*

