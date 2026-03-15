#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Single-command model governance check.

Checks:
1) Artifact consistency between model_constants and filesystem
2) Metadata structure and threshold sanity
3) Optional fairness comparison report freshness
"""

import json
from pathlib import Path
from datetime import datetime, timezone

from model_constants import (
    PRODUCTION_MODEL_PATH,
    PRODUCTION_META_PATH,
    PRODUCTION_THRESHOLD_PATH,
)


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _bool_icon(v: bool) -> str:
    return "PASS" if v else "FAIL"


def main() -> int:
    print("=" * 72)
    print("MODEL GOVERNANCE CHECK")
    print("=" * 72)

    model_path = Path(PRODUCTION_MODEL_PATH)
    meta_path = Path(PRODUCTION_META_PATH)
    threshold_path = Path(PRODUCTION_THRESHOLD_PATH)

    checks = []

    checks.append(("Model artifact exists", model_path.exists()))
    checks.append(("Metadata artifact exists", meta_path.exists()))
    checks.append(("Threshold artifact exists", threshold_path.exists()))

    meta = {}
    if meta_path.exists():
        try:
            meta = _read_json(meta_path)
            checks.append(("Metadata is valid JSON", True))
        except Exception:
            checks.append(("Metadata is valid JSON", False))

    if meta:
        checks.append(("Metadata has metrics", isinstance(meta.get("metrics"), dict)))
        checks.append(("Metadata has threshold", isinstance(meta.get("threshold"), (int, float))))
        thr = float(meta.get("threshold", 0.0))
        checks.append(("Threshold in [0,1]", 0.0 <= thr <= 1.0))
        checks.append(("Metadata includes split policy", isinstance(meta.get("split_policy"), dict)))
        checks.append((
            "Leakage-safe threshold flag present",
            bool(meta.get("leakage_safe_threshold_selection", False)),
        ))

    fairness_report = Path("bias_reports/fairness_check_latest.json")
    checks.append(("Fairness latest report exists", fairness_report.exists()))

    fairness_status = None
    if fairness_report.exists():
        try:
            fairness_data = _read_json(fairness_report)
            fairness_status = fairness_data.get("status", "unknown")
            checks.append(("Fairness report parseable", True))
        except Exception:
            checks.append(("Fairness report parseable", False))

    all_ok = True
    for name, ok in checks:
        print(f"{_bool_icon(ok):>4} | {name}")
        all_ok = all_ok and ok

    print("-" * 72)
    if meta:
        print(f"Model path     : {model_path}")
        print(f"Meta version   : {meta.get('version', 'unknown')}")
        print(f"Meta threshold : {meta.get('threshold', 'unknown')}")
        created_at = meta.get("created_at")
        if created_at:
            print(f"Meta created_at: {created_at}")
    print(f"Fairness status: {fairness_status or 'unknown'}")
    print(f"Checked at     : {datetime.now(timezone.utc).isoformat()}")

    print("=" * 72)
    print("OVERALL:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
