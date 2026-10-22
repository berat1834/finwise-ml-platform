#!/usr/bin/env python
"""Generate a daily fairness CSV snapshot from the secure API endpoint."""

from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate fairness daily CSV report")
    parser.add_argument("--date", dest="date_str", help="Target date in YYYY-MM-DD format")
    parser.add_argument(
        "--base-url",
        dest="base_url",
        default=os.getenv("FAIRNESS_API_BASE_URL", "http://127.0.0.1:5000"),
        help="API base URL (default: http://127.0.0.1:5000)",
    )
    return parser.parse_args()


def validate_date(date_str: str | None) -> str:
    if not date_str:
        return datetime.utcnow().date().isoformat()
    datetime.strptime(date_str, "%Y-%m-%d")
    return date_str


def fetch_fairness_metrics(base_url: str, date_str: str) -> dict:
    url = f"{base_url.rstrip('/')}/fairness/daily"
    response = requests.get(url, params={"date": date_str}, timeout=20)
    response.raise_for_status()
    return response.json()


def write_csv(payload: dict) -> str:
    date_str = payload["date"]
    output_file = f"fairness_report_{date_str}.csv"

    approval_rates = payload.get("approval_rates", {})
    tpr = payload.get("tpr_by_group", {})
    fpr = payload.get("fpr_by_group", {})

    row = {
        "date": date_str,
        "total_applications": payload.get("total_applications", 0),
        "q1_approval": approval_rates.get("Q1"),
        "q2_approval": approval_rates.get("Q2"),
        "q3_approval": approval_rates.get("Q3"),
        "q4_approval": approval_rates.get("Q4"),
        "q5_approval": approval_rates.get("Q5"),
        "di_ratio": payload.get("di_ratio"),
        "tpr_q1": tpr.get("Q1"),
        "tpr_q5": tpr.get("Q5"),
        "fpr_q1": fpr.get("Q1"),
        "fpr_q5": fpr.get("Q5"),
        "note": payload.get("note", ""),
    }

    fieldnames = list(row.keys())
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

    return output_file


def main() -> int:
    args = parse_args()
    try:
        date_str = validate_date(args.date_str)
    except ValueError:
        print("ERROR: Invalid --date value. Use YYYY-MM-DD format.")
        return 1

    try:
        payload = fetch_fairness_metrics(args.base_url, date_str)
    except requests.RequestException as exc:
        print(f"ERROR: Failed to fetch fairness metrics: {exc}")
        return 1

    output_file = write_csv(payload)
    print(f"Fairness report generated: {output_file}")
    print(f"Date: {payload.get('date')}, total applications: {payload.get('total_applications', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
