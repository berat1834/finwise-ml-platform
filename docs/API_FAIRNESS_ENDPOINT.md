# API Fairness Endpoint

## Endpoint
- Method: `GET`
- Path: `/fairness/daily`

## Query Parameters
- `date` (optional): `YYYY-MM-DD`

If `date` is omitted, endpoint returns metrics for current UTC date.

## Response Schema

```json
{
  "date": "2026-03-06",
  "total_applications": 42,
  "approval_rates": {
    "Q1": 8.33,
    "Q2": 10.0,
    "Q3": 12.5,
    "Q4": 15.0,
    "Q5": 20.0
  },
  "sample_counts": {
    "Q1": 6,
    "Q2": 8,
    "Q3": 8,
    "Q4": 10,
    "Q5": 10
  },
  "di_ratio": 0.4165,
  "tpr_by_group": {
    "Q1": null,
    "Q2": null,
    "Q3": null,
    "Q4": null,
    "Q5": null
  },
  "fpr_by_group": {
    "Q1": null,
    "Q2": null,
    "Q3": null,
    "Q4": null,
    "Q5": null
  },
  "note": "TPR/FPR unavailable without ground-truth repayment labels."
}
```

## Curl Example

```bash
curl -s "http://127.0.0.1:5000/fairness/daily?date=2026-03-06"
```

## Daily CSV Script

`daily_fairness_report.py` uses this endpoint to generate:

- `fairness_report_YYYY-MM-DD.csv`

Run:

```bash
python daily_fairness_report.py --date 2026-03-06
```
