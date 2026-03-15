# Service Level Agreement (SLA)

**Effective Date:** March 2026  
**Version:** 1.0

---

## EXECUTIVE SUMMARY

This Service Level Agreement defines the minimum service standards and uptime guarantees for FinWise-ML Credit Risk Analysis API. The SLA applies to all paid tiers and includes remedies for non-compliance.

---

## 1. SERVICE AVAILABILITY GUARANTEES

### 1.1 Uptime Commitments

| Tier | Availability Target | Monthly Downtime Allowed | Credit |
|------|---------------------|-------------------------|--------|
| **Starter** | 99.0% | 7 hours 12 minutes | 5-10% |
| **Pro** | 99.5% | 3 hours 36 minutes | 10-20% |
| **Enterprise** | 99.9% | 43 minutes 12 seconds | 25-100% |

### 1.2 Availability Definition

**Service is AVAILABLE when:**
- API endpoint responds with HTTP 200-299 status
- Response time ≤ SLA threshold (see Section 2)
- ≥ 95% of API requests succeed

**Service is UNAVAILABLE when:**
- Error rate > 5% for ≥ 5 consecutive minutes
- API returns HTTP 500-599 errors
- Database/backend services down

### 1.3 Measurement Period

- **Calendar Month:** 1st to last day
- **Timezone:** UTC (00:00 - 23:59)
- **Measurement Source:** AWS CloudWatch metrics

---

## 2. RESPONSE TIME COMMITMENTS

### 2.1 Latency Targets (P95 percentile)

| Tier | Target | Acceptable | Degraded |
|------|--------|-----------|----------|
| **Starter** | 2000ms | < 2000ms | 2000-5000ms |
| **Pro** | 500ms | < 500ms | 500-2000ms |
| **Enterprise** | 200ms | < 200ms | 200-1000ms |

### 2.2 Causes of Latency

**NOT counted as violation if caused by:**
- Client network latency (> 100ms from Client)
- Large request payload (> 10MB)
- Model cold-start (first request after scale-down)
- Client rate limiting (too many requests)

**ARE counted as violations:**
- Backend processing delays
- Database queries > timeouts
- Model inference timeouts
- Infrastructure failures

---

## 3. SLA CREDITS

### 3.1 Credit Calculation

**Monthly Uptime %** → **Service Credit %**

```
99%+ uptime       → 0% credit (SLA met)
98.0% - 98.99%    → 5% of monthly fees
95.0% - 97.99%    → 10% of monthly fees
90.0% - 94.99%    → 25% of monthly fees
< 90%             → 30% of monthly fees
```

### 3.2 Example Calculations

**Starter ($500/month):**
- Uptime: 99.5%
- SLA met (99.5% > 99% target)
- Credit: $0

**Starter ($500/month):**
- Uptime: 98.5%
- SLA missed (98.5% < 99% target)
- Downtime: ~10 hours (within 98% band)
- Credit: 5% × $500 = **$25**

**Pro ($2000/month):**
- Uptime: 94.2%
- SLA significantly missed (94.2% < 99.5% target)
- Downtime: ~40 hours
- Credit: 25% × $2000 = **$500**

### 3.3 Maximum Monthly Credit

- Monthly credit capped at 100% of monthly subscription fee
- Exceeding credits cannot be cumulative (month-by-month)
- Credits must be requested within 30 days of incident

### 3.4 Non-Compounding

- Latency violations and availability violations are separate
- Worst violation counts only (not both)
- Scheduled maintenance does not affect credit

---

## 4. EXCLUDED EVENTS

### 4.1 No SLA Credit for:

- **Scheduled Maintenance**
  - Announced 7 days in advance
  - Performed outside business hours (if possible)
  - Typically Sundays 00:00-04:00 UTC

- **Force Majeure**
  - Natural disasters (earthquakes, floods, etc.)
  - War, terrorism, sabotage
  - Nuclear radiation
  - Government/regulatory action

- **Customer-Caused Issues**
  - DDoS attacks from Customer or Client
  - Customer misconfiguration
  - Customer API key compromise/misuse
  - Client rate limiting from overuse

- **Third-Party Issues**
  - AWS infrastructure failures (AWS SLA applies)
  - Internet backbone issues
  - DNS provider issues
  - Payment processor issues

- **Beta/Alpha Features**
  - Explicitly labeled as beta

- **Free Trial**
  - SLA does not apply

### 4.2 How Company Determines Root Cause

Investigation process:

1. **Hour 0:** Incident declared
2. **Hour 1:** Root cause investigation
3. **Day 1:** Preliminary determination
4. **Day 5:** Final determination + customer notification
5. **Day 7:** Credit applied (if eligible)

---

## 5. INCIDENT RESPONSE

### 5.1 Response Time Targets

| Severity | Initial Response | Resolution Target |
|----------|-----------------|-------------------|
| **Critical** (API down) | 15 minutes | 1 hour |
| **High** (Errors > 5%) | 30 minutes | 4 hours |
| **Medium** (Latency > 2x) | 1 hour | 8 hours |
| **Low** (Warnings, alerts) | 4 hours | 24 hours |

### 5.2 Support Channels

**Starter Tier:**
- Email support only
- Response: 24 hours

**Pro Tier:**
- Email + Slack channel
- Response: 4 hours

**Enterprise Tier:**
- Email + Slack + Phone + Dedicated account manager
- Response: 1 hour
- On-call: 24/7

### 5.3 Incident Communication

Company shall:

- Publish status updates every 30 minutes during incident
- Post updates to status page: https://status.finwise-ml.com
- Notify via email (Pro/Enterprise + relevant Starter customers)
- Include ETA for resolution

---

## 6. MAINTENANCE WINDOWS

### 6.1 Scheduled Maintenance

- Window: Sunday 00:00 - 04:00 UTC
- Frequency: Max 1 window per month
- Duration: ≤ 2 hours
- Notice: 7 days minimum

### 6.2 Security/Emergency Patches

- Can be deployed without notice
- Typical duration: < 15 minutes
- Customer notification sent ASAP

### 6.3 Maintenance Do Not Count As:

- Unscheduled downtime
- SLA violations
- Latency violations

---

## 7. PERFORMANCE METRICS

### 7.1 What Company Reports

Monthly:

- **Uptime %:** (Availability)
- **P50 Latency:** Median response time
- **P95 Latency:** 95th percentile
- **P99 Latency:** 99th percentile
- **Error Rate:** % failed requests
- **Incident Summary:** Description, duration, root cause

### 7.2 How to Access Reports

- **Pro/Enterprise:** Emailed automatically
- **Starter:** Available in dashboard (free)

---

## 8. REQUEST FOR SLA CREDIT

### 8.1 Process

1. Customer submits request within 30 days of incident
2. Email: sla-claims@finwise-ml.com
3. Include: Incident date, affected customer IDs

### 8.2 Required Information

```
SLA Credit Request Form:

Customer Name: _______________
Account ID: _______________
Incident Date: _______________
Time Period: _______________
Severity (circle one): Critical / High / Medium / Low

Explain impact:
_________________________________

Attestation: I certify this incident occurred and affected my use of the Service.

Signature: _______________ Date: _______________
```

### 8.3 Response

- Determination within 15 days
- Credit applied as account credit (not refund)
- Can be used for next month's fees
- Otherwise forfeited

---

## 9. PERFORMANCE MONITORING

### 9.1 Monitoring Tools

Company monitors:

- **Real User Monitoring (RUM):** Real browser/API client latency
- **Synthetic Monitoring:** Automated health checks every 60 seconds
- **Infrastructure Monitoring:** Server/database/network health
- **Application Monitoring:** Error tracking, warnings, exceptions

### 9.2 Alerting

Alerts triggered if:

- Uptime < 95% (non-critical)
- Error rate > 5%
- Latency P95 > 3x SLA target
- Database response time > 1 second

On-call engineer notified immediately for critical alerts.

### 9.3 Dashboard

**Customers can view:**

- Current uptime %
- Last 7/30 days metrics
- Incident history
- Maintenance schedule
- Status page

Access: https://dashboard.finwise-ml.com → Monitoring

---

## 10. SERVICE IMPROVEMENTS

### 10.1 Regular Reviews

Company commits to:

- Monthly review of SLA metrics
- Quarterly improvement analysis
- Annual SLA tier review

### 10.2 Scaling Infrastructure

Company will scale infrastructure if:

- Sustained > 80% capacity utilization
- Latency > SLA threshold for > 3 consecutive days
- Availability falls below 99% for month

---

## 11. DISPUTE RESOLUTION

### 11.1 Dispute Process

1. **Customer files claim** with documentation
2. **Company investigates** (15 days)
3. **Company makes determination** (email notification)
4. **Customer may appeal** (within 10 days)
5. **Independent audit** (if needed, customer pays audit cost)

### 11.2 Escalation

If customer disputes determination:

- **Enterprise:** Escalates to VP Engineering
- **Pro:** Escalates to Support Manager
- **Starter:** Final determination from Support

### 11.3 Binding Arbitration

- If resolution via arbitration needed
- Location: Zurich, Switzerland
- Cost: Loser pays arbitrator fees
- Timeline: Must initiate within 6 months of incident

---

## 12. AMENDMENTS

### 12.1 Changes to SLA

Company may amend SLA with:

- 90 days written notice
- Effective date announced
- Changes benefit customers (or value-neutral)

### 12.2 Tier Changes

If moving from one tier to another:

- Changes effective at next billing cycle
- Can downgrade anytime (prorated refund)
- Upgrade applies immediately

---

## 13. ACKNOWLEDGMENTS

**Company Acknowledges:**

- SLA is important to Customer business
- Incidents have real business impact
- Credits are reasonable compensation

**Customer Acknowledges:**

- 100% uptime is impossible
- Some incidents are outside Company control
- SLA credits are sole remedy for violations

---

## 14. SCHEDULE A: UPTIME CALCULATION

### 14.1 Formula

```
Monthly Uptime % = 
    (Total Time - Incident Time) / Total Time * 100

Example:
March 2026 = 31 days = 44,640 minutes

Incident 1: March 5 - 00:00 to 01:30 (90 minutes)
Incident 2: March 15 - 14:00 to 14:45 (45 minutes)

Total downtime: 135 minutes
Uptime %: (44,640 - 135) / 44,640 * 100 = 99.7%

Result: SLA met (99.7% > 99.5% target for Pro)
```

### 14.2 Rounding

- Rounding to 2 decimal places
- Rounding down (conservative)

---

## 15. SCHEDULE B: OUTAGE INCIDENT LOG

Company maintains incident log:

| Date | Duration | Cause | Severity | Impact | Root Cause |
|------|----------|-------|----------|--------|-----------|
| 2026-02-14 | 45 min | DB query timeout | Medium | 3% errors | Slow query from load test |
| 2026-02-28 | 12 min | SSL cert renewal | Low | 0% downtime | Planned maintenance |

Accessible: https://status.finwise-ml.com/history

---

## CONTACT & SUPPORT

**SLA Questions/Claims:**
- Email: sla@finwise-ml.com
- Support Portal: support.finwise-ml.com
- Enterprise: Dedicated account manager
- Status Page: https://status.finwise-ml.com

---

**Document Version:** 1.0  
**Effective Date:** March 2026  
**Next Review:** March 2027

*This SLA is binding once Customer accepts Terms of Service. Changes effective 90 days after notice.*

