# Data Processing Agreement (DPA)

**Effective Date:** March 2026  
**Version:** 1.0

This Data Processing Agreement ("DPA") is entered into between:

**Data Controller (Client):** [Client Legal Name]  
**Data Processor (Company):** FinWise Systems Ltd.

---

## 1. INTRODUCTION

This DPA supplements the Terms of Service and governs how FinWise Systems Ltd. ("Processor") processes personal data on behalf of the Client ("Controller").

This DPA complies with:

- **GDPR** (EU General Data Protection Regulation)
- **CCPA** (California Consumer Privacy Act)
- **KVKK** (Turkish Data Protection Law)
- **LGPD** (Brazilian Law for data protection)

---

## 2. DEFINITIONS

- **Personal Data:** Any information relating to an identified or identifiable natural person
- **Processing:** Any operation performed on data (collection, storage, use, transmission, deletion)
- **Subject:** The individual to whom personal data relates
- **Breach:** Unauthorized access, loss, or damage to personal data

---

## 3. SCOPE OF PROCESSING

### 3.1 Subject Matter

Processor processes personal data for the following purposes:

1. **Credit Risk Evaluation**
   - Variables: age, income, employment, credit history
   - Purpose: Machine learning model prediction
   - Legal basis: Legitimate interest (credit assessment)

2. **Fairness & Bias Analysis**
   - Demographic analysis for Fair Lending compliance
   - Disparate impact testing
   - Purpose: ECOA/TILA regulatory compliance

3. **Service Improvement**
   - Anonymized model training and improvement
   - Aggregate statistical analysis
   - No individual-level identification possible

### 3.2 Data Categories

| Category | Examples | Sensitivity |
|----------|----------|-------------|
| Identity | Name, DOB, SSN/SSN | HIGH |
| Financial | Income, credit score, loan history | HIGH |
| Employment | Job title, industry, tenure | MEDIUM |
| Contact | Email, phone (optional) | LOW |
| Behavioral | Loan purpose, application type | LOW |

### 3.3 Categories of Data Subjects

- Loan applicants (primary)
- Existing customers (refinancing)
- Authorized representatives (power of attorney)

### 3.4 Duration of Processing

- **Active Use:** During service subscription
- **Retention:** 7 years after decision (regulatory requirement)
- **Deletion:** Within 30 days of request (subject to legal holds)

---

## 4. PROCESSOR OBLIGATIONS

### 4.1 Legal Compliance

Processor shall:

- ✅ Process data only as instructed by Controller
- ✅ Not disclose data without prior written consent
- ✅ Comply with all data protection laws
- ✅ Implement appropriate technical/organizational measures
- ✅ Assist Controller in meeting Subject access requests
- ✅ Delete or return data upon contract termination

### 4.2 Technical & Organizational Measures

Processor implements:

**Technical Controls:**
- ✅ AES-256 encryption at rest
- ✅ TLS 1.3 encryption in transit
- ✅ Access control lists (ACL)
- ✅ Intrusion detection systems (IDS)
- ✅ Regular vulnerability scans
- ✅ Automated security patches

**Organizational Controls:**
- ✅ Employee data protection training
- ✅ Confidentiality agreements for all staff
- ✅ Background checks for access personnel
- ✅ Physical security (data center access)
- ✅ Audit logging and monitoring
- ✅ Incident response procedures

### 4.3 Subprocessors

Processor permits the following subprocessors:

| Subprocessor | Purpose | Country | Privacy Level |
|--------------|---------|---------|----------------|
| AWS | Infrastructure/hosting | Multi-region | SOC 2 Type II |
| PostgreSQL | Database storage | On-premise | N/A (self-managed) |
| Redis | Caching/sessions | AWS VPC | Data NOT stored |
| GitHub | Code repository | USA | Enterprise SLA |

**Controller Notification:** Controller notified 30 days before adding/changing subprocessors. Controller may object within 15 days.

### 4.4 Data Subject Assistance

Processor shall assist Controller in responding to Subject requests:

1. **Access Requests (Art. 15 GDPR)**
   - Response time: 5 business days
   - Format: CSV or PDF export
   - Cost: Free for reasonable frequency

2. **Rectification Requests (Art. 16)**
   - Processor does NOT modify source data
   - Controller responsible for corrections
   - Processor supports/confirms correction

3. **Deletion Requests (Art. 17)**
   - "Right to be forgotten" honored
   - Timeline: 30 days (unless legal hold)
   - Exceptions: Regulatory retention periods (7 years)

4. **Portability Requests (Art. 20)**
   - Data exported in standard format (CSV/JSON)
   - Timeline: 20 days
   - Cost: Free

### 4.5 Data Breach Notification

**Processor shall notify Controller without undue delay if:**

- Unauthorized access to personal data occurs
- Data loss or corruption suspected
- Personal data accidentally leaked

**Notification must include:**
- Description of breach
- Categories affected
- Estimated number of Subjects affected
- Likely consequences
- Measures taken/proposed

**Controller then notifies Subjects within 72 hours (if high risk).**

---

## 5. CONTROLLER OBLIGATIONS

### 5.1 Lawful Basis

Controller represents and warrants:

- ✅ All data collection is lawful
- ✅ Appropriate legal basis exists (consent, contract, legitimate interest, legal obligation)
- ✅ Subjects were informed via privacy notice
- ✅ Subjects consented where required
- ✅ Data is not obtained through deception

### 5.2 Data Accuracy

Controller ensures:

- ✅ Data provided is accurate and complete
- ✅ Outdated data is updated
- ✅ Irrelevant data is deleted
- ✅ Data quality standards are maintained

### 5.3 Cooperation

Controller shall:

- ✅ Promptly respond to Processor breach notifications
- ✅ Support Subject access requests
- ✅ Maintain records of lawful basis
- ✅ Notify Processor of regulatory inquiries
- ✅ Indemnify Processor for Controller-caused breaches

### 5.4 Conflict Resolution

If Controller requests processing that may violate data protection law, Processor shall:

1. Inform Controller of legal concern
2. Suggest compliant alternatives
3. Escalate to legal team
4. Refuse if no compliant solution exists

---

## 6. RIGHTS & REMEDIES

### 6.1 Controller Rights

Controller may:

- Audit Processor compliance (annually, with notice)
- Request security assessment
- Require compliance certification (ISO 27001)
- Terminate for material breach

### 6.2 Processor Rights

Processor may:

- Charge reasonable audit costs ($2,000+ per audit)
- Request indemnification for Controller breaches
- Suspend service for non-cooperation
- Terminate for repeated violations

### 6.3 Dispute Resolution

For disputes regarding DPA:

1. **Negotiation:** 30 days
2. **Mediation:** (optional) 60 days
3. **Arbitration:** (binding) Under ICC Rules
4. **Venue:** Zurich, Switzerland (neutral ground)

---

## 7. INTERNATIONAL DATA TRANSFERS

### 7.1 Adequacy

Germany, Austria, Switzerland, and EU countries: **Adequate protection** (no mechanisms needed)

### 7.2 Transfer Mechanisms

For non-adequate countries (USA, others):

- **Standard Contractual Clauses (SCC):** Attached as Annex
- **Supplementary Measures:** Additional safeguards document
- **Risk Assessment:** Conducted for each country

### 7.3 USA Data Transfers

If data transferred to USA:

- ✅ Schrems II assessment completed
- ✅ Contractual guarantees in place
- ✅ Additional encryption applied
- ✅ Minimization of data transfers
- ✅ Right to claim transfer illegality

### 7.4 China/Russia/Other High-Risk

- ❌ NO data transfers to high-risk jurisdictions
- ❌ Standard Contractual Clauses NOT sufficient
- Requires explicit written consent per country

---

## 8. IMPACT ASSESSMENTS

### 8.1 Data Protection Impact Assessment (DPIA)

Controller is responsible for DPIA (Art. 35 GDPR). Processor shall provide:

- Processing description
- Security measure details
- Risk analysis
- Technical specifications

DPIA required if processing involves:

- Large-scale systematic monitoring
- Automated decision-making with legal effect
- Sensitive data categories
- Criminal data

Processor assistance: Included in Professional Services (additional fees apply)

### 8.2 Privacy by Design

Processor implements Privacy by Design:

- ✅ Minimal data collection
- ✅ Purpose limitation enforced
- ✅ Retention limits coded
- ✅ Fairness safeguards built-in
- ✅ Audit logs automated

---

## 9. SPECIAL DATA CATEGORIES

### 9.1 Sensitive Data Handling

Controller must NOT provide:

- ❌ Race/ethnicity (source data)
- ❌ Political beliefs
- ❌ Religious beliefs
- ❌ Union membership
- ❌ Genetic data
- ❌ Biometric data (except as controller's requirement)
- ❌ Health information
- ❌ Sexual orientation

**Exception (USA):** ECOA monitoring requires demographic analysis by Processor (lawful, not disclosed to model)

### 9.2 Sensitive Data Safeguards

If demographic data required for fairness analysis:

1. **Separation:** Kept separate from predictive model
2. **Encryption:** Double-encrypted
3. **Access Control:** Only compliance team access
4. **Minimization:** Only needed variables
5. **Deletion:** Monthly purge of raw demographic data

---

## 10. DATA RETENTION

### 10.1 Standard Retention

| Data Type | Duration | Reason |
|-----------|----------|--------|
| Request logs | 90 days | Operational/audit |
| Model decisions | 7 years | Credit law requirement |
| API credentials | Until deletion | Active use |
| Backups | 30 days (RP) + 3 years | Disaster recovery |
| Audit logs | 2 years | Regulatory compliance |

### 10.2 Extended Retention

Data kept longer IF:

- Legal hold / dispute
- Regulatory investigation
- Law enforcement request
- Litigation

### 10.3 Deletion Upon Termination

Within 30 days of contract termination:

- ✅ All production data deleted
- ✅ Backups not restored/re-created
- ✅ Historical logs anonymized
- ✅ Confirmation certificate provided
- ❌ Exception: Legal holds, regulatory retention

---

## 11. COMPLIANCE CERTIFICATIONS

Processor maintains:

- ✅ **SOC 2 Type II:** Annual audit (security & confidentiality)
- ✅ **ISO 27001:** Information security management
- ✅ **HIPAA Compliant:** (if health data involved)
- ✅ **PCI DSS:** (if payment cards handled)
- ✅ Penetration tested: Annually
- ✅ Vulnerability management: Monthly scanning

Certificates provided upon request.

---

## 12. TERMINATION & DATA RETURN

### 12.1 Termination Procedures

Upon termination, Controller may elect:

1. **Data Deletion:** All data destroyed securely
2. **Data Transfer:** Export via secure mechanism
3. **Archival:** Keep for legal hold (with conditions)

### 12.2 Proof of Deletion

Processor provides:

- Deletion Certificate (signed, certified)
- Backup destruction log
- Third-party verification (auditor)

Retained in Controller's records for 10 years (proof of compliance).

---

## 13. AMENDMENTS

### 13.1 Required Changes

Processor may amend DPA if:

- Required by law/regulation
- Security standards improve
- Subprocessors change (30-day notice)
- Complaint filed with data authority

### 13.2 Material Changes

Material changes require:

- 90 days written notice
- Right to terminate without penalty
- Negotiation period for alternatives

---

## 14. CONTACT

**For Data Protection Matters:**

**Data Protection Officer (DPO):**
FinWise Systems Ltd.
Email: dpo@finwise-ml.com
Phone: +41 44 XXXX XXXX

**Legal/Compliance:**
Email: legal@finwise-ml.com

---

## ANNEX A: STANDARD CONTRACTUAL CLAUSES (SCCs)

*[Full SCCs text per EU Commission Decision 2021/915 included here]*

*Insert current EU/UK standard contractual clauses applicable to processor-to-processor transfers*

---

## ANNEX B: TECHNICAL & ORGANIZATIONAL MEASURES

**Security Controls Inventory:**

1. Encryption at Rest (AES-256)
2. Encryption in Transit (TLS 1.3)
3. Access Control Lists (IAM)
4. Intrusion Detection/Prevention (IDS/IPS)
5. Web Application Firewall (WAF)
6. DDoS Protection (CloudFlare/AWS Shield)
7. Audit Logging & SIEM
8. Vulnerability Management
9. Incident Response Plan
10. Business Continuity / Disaster Recovery

---

## ANNEX C: SUBPROCESSOR LIST

*Maintained at: https://finwise-ml.com/compliance/subprocessors*

*Updated quarterly, changes notified to Controllers via email*

---

**Document Status:** FINAL  
**Effective Date:** March 2026  
**Next Review:** March 2027 (annual)

**Signature:**

By clicking "I Agree" during service setup, you acknowledge that you have read, understood, and accept this Data Processing Agreement.

---

*This is a template. Consult legal counsel specializing in data protection law before using.*

