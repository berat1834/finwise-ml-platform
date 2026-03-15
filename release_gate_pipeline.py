#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""One-command release gate pipeline.

Flow:
1) Snapshot baseline model artifacts
2) Train candidate model(s)
3) Run fairness-aware threshold/policy search per candidate
4) Run model governance checks
5) Evaluate release gates and emit GO/NO_GO report
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, recall_score
from sklearn.model_selection import train_test_split

from model_governance_check import main as governance_main
from training_pipeline import main as training_main
from model_constants import PRODUCTION_META_PATH, PRODUCTION_MODEL_PATH


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _extract_performance(meta: Dict[str, Any]) -> Dict[str, float]:
    metrics = meta.get("metrics", {})
    report = metrics.get("classification_report", {})
    class_1 = report.get("1", {})

    return {
        "roc_auc": float(metrics.get("roc_auc", 0.0)),
        "accuracy": float(metrics.get("accuracy", 0.0)),
        "recall_class_1": float(class_1.get("recall", 0.0)),
        "f1_class_1": float(class_1.get("f1-score", 0.0)),
        "pr_auc": float(metrics.get("pr_auc", 0.0)),
    }


def _prepare_dataset(csv_path: str):
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["loan_status"])
    X_raw = df.drop("loan_status", axis=1)
    y = df["loan_status"].astype(int)

    X_filled = X_raw.copy()
    X_filled = X_filled.fillna(X_filled.median(numeric_only=True))
    for col in X_filled.select_dtypes(include=["object"]).columns:
        mode = X_filled[col].mode()
        X_filled[col] = X_filled[col].fillna(mode.iloc[0] if len(mode) > 0 else "UNKNOWN")

    X_encoded = pd.get_dummies(X_filled, drop_first=True)
    return X_filled, X_encoded, y


def _predict_proba_adaptive(model, X_raw: pd.DataFrame, X_encoded: pd.DataFrame) -> np.ndarray:
    try:
        return model.predict_proba(X_raw)[:, 1]
    except Exception:
        expected = list(getattr(model, "feature_names_in_", []))
        if expected:
            X_aligned = X_encoded.reindex(columns=expected, fill_value=0)
        else:
            X_aligned = X_encoded
        return model.predict_proba(X_aligned)[:, 1]


def _predict_label_adaptive(model, X_raw: pd.DataFrame, X_encoded: pd.DataFrame) -> np.ndarray:
    try:
        return model.predict(X_raw)
    except Exception:
        expected = list(getattr(model, "feature_names_in_", []))
        if expected:
            X_aligned = X_encoded.reindex(columns=expected, fill_value=0)
        else:
            X_aligned = X_encoded
        return model.predict(X_aligned)


def _approval_by_income(y_pred: np.ndarray, income_series: pd.Series) -> Dict[str, float]:
    income_quintile = pd.qcut(
        income_series,
        q=5,
        labels=["Q1", "Q2", "Q3", "Q4", "Q5"],
        duplicates="drop",
    )
    rates: Dict[str, float] = {}
    y_pred_series = pd.Series(y_pred, index=income_series.index)
    for q in ["Q1", "Q2", "Q3", "Q4", "Q5"]:
        mask = income_quintile == q
        if mask.sum() > 0:
            rates[q] = float((1 - y_pred_series[mask]).mean() * 100)
    return rates


def _di_ratio(approval_rates: Dict[str, float]) -> float:
    if not approval_rates:
        return 0.0
    max_rate = max(approval_rates.values())
    min_rate = min(approval_rates.values())
    return float(min_rate / max_rate) if max_rate > 0 else 0.0


def _fairness_policy_search(
    baseline_model_path: Path,
    candidate_model_path: Path,
    csv_path: str,
    min_di: float,
    min_recall: float,
    min_f1: float,
    threshold_min: float,
    threshold_max: float,
    threshold_step: float,
    holdout_size: float,
    random_state: int,
) -> Dict[str, Any]:
    X_raw, X_encoded, y = _prepare_dataset(csv_path)

    X_raw_train, X_raw_holdout, y_train, y_holdout = train_test_split(
        X_raw,
        y,
        test_size=holdout_size,
        random_state=random_state,
        stratify=y,
    )
    X_enc_train, X_enc_holdout, _, _ = train_test_split(
        X_encoded,
        y,
        test_size=holdout_size,
        random_state=random_state,
        stratify=y,
    )
    _ = X_raw_train, X_enc_train, y_train

    holdout_income = X_raw_holdout["person_income"]

    baseline_model = joblib.load(baseline_model_path)
    candidate_model = joblib.load(candidate_model_path)

    baseline_pred = _predict_label_adaptive(baseline_model, X_raw_holdout, X_enc_holdout)
    baseline_approval = _approval_by_income(baseline_pred, holdout_income)
    baseline_di = _di_ratio(baseline_approval)

    candidate_proba = _predict_proba_adaptive(candidate_model, X_raw_holdout, X_enc_holdout)

    candidate_thresholds = np.arange(threshold_min, threshold_max + 1e-9, threshold_step)
    best_any: Optional[Dict[str, Any]] = None
    best_compliant: Optional[Dict[str, Any]] = None
    best_high_di_reasonable: Optional[Dict[str, Any]] = None
    best_performance_guarded: Optional[Dict[str, Any]] = None
    soft_recall_floor = max(0.55, min_recall - 0.12)
    soft_f1_floor = max(0.52, min_f1 - 0.08)

    for thr in candidate_thresholds:
        y_pred = (candidate_proba >= thr).astype(int)
        appr = _approval_by_income(y_pred, holdout_income)
        di = _di_ratio(appr)
        rec = float(recall_score(y_holdout, y_pred))
        f1 = float(f1_score(y_holdout, y_pred))

        row = {
            "threshold": float(thr),
            "candidate_di_ratio": di,
            "candidate_recall": rec,
            "candidate_f1": f1,
            "approval_rates_candidate": appr,
        }

        di_gap = max(0.0, min_di - di)
        recall_gap = max(0.0, min_recall - rec)
        f1_gap = max(0.0, min_f1 - f1)
        # Balanced score: reward DI, penalize fairness/performance misses.
        row["selection_score"] = float(di - 2.5 * di_gap - 1.0 * recall_gap - 0.8 * f1_gap)
        row["di_gap"] = float(di_gap)
        row["recall_gap"] = float(recall_gap)
        row["f1_gap"] = float(f1_gap)

        if best_any is None or row["selection_score"] > best_any["selection_score"]:
            best_any = row

        meets_perf_floor = rec >= min_recall and f1 >= min_f1
        if meets_perf_floor:
            if best_performance_guarded is None or row["candidate_di_ratio"] > best_performance_guarded["candidate_di_ratio"]:
                best_performance_guarded = row

        meets_soft_floor = rec >= soft_recall_floor and f1 >= soft_f1_floor
        if meets_soft_floor:
            if best_high_di_reasonable is None or row["candidate_di_ratio"] > best_high_di_reasonable["candidate_di_ratio"]:
                best_high_di_reasonable = row

        is_compliant = di >= min_di and meets_perf_floor
        if is_compliant:
            if best_compliant is None:
                best_compliant = row
            else:
                better_di = row["candidate_di_ratio"] > best_compliant["candidate_di_ratio"]
                same_di_better_f1 = (
                    row["candidate_di_ratio"] == best_compliant["candidate_di_ratio"]
                    and row["candidate_f1"] > best_compliant["candidate_f1"]
                )
                if better_di or same_di_better_f1:
                    best_compliant = row

    if best_compliant is not None:
        selected = best_compliant
        selection_reason = "meets_all_constraints"
    elif best_high_di_reasonable is not None:
        selected = best_high_di_reasonable
        selection_reason = "highest_di_with_soft_performance_floors"
    elif best_performance_guarded is not None:
        selected = best_performance_guarded
        selection_reason = "best_di_with_performance_floors"
    else:
        selected = best_any
        selection_reason = "best_balanced_score"

    if selected is None:
        selected = {
            "threshold": 0.5,
            "candidate_di_ratio": 0.0,
            "candidate_recall": 0.0,
            "candidate_f1": 0.0,
            "approval_rates_candidate": {},
            "selection_score": -999.0,
            "di_gap": min_di,
            "recall_gap": min_recall,
            "f1_gap": min_f1,
        }
        selection_reason = "fallback_default"

    selected["baseline_di_ratio"] = baseline_di
    selected["approval_rates_baseline"] = baseline_approval
    selected["passes_80_rule"] = selected["candidate_di_ratio"] >= min_di
    selected["status"] = "COMPLIANT" if selected["passes_80_rule"] else "NEEDS_IMPROVEMENT"
    selected["selection_reason"] = selection_reason
    selected["holdout_samples"] = int(len(X_raw_holdout))
    selected["holdout_size"] = holdout_size

    return selected


def _persist_selected_threshold(meta_path: Path, selected_threshold: float):
    if not meta_path.exists():
        return
    meta = _read_json(meta_path)
    meta["threshold"] = float(selected_threshold)
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def _gate_decision(perf: Dict[str, float], fairness: Dict[str, Any], governance_ok: bool, args) -> Dict[str, Any]:
    fairness_di = float(fairness.get("candidate_di_ratio", 0.0))

    checks = {
        "min_roc_auc": perf["roc_auc"] >= args.min_roc_auc,
        "min_recall_class_1": perf["recall_class_1"] >= args.min_recall,
        "min_f1_class_1": perf["f1_class_1"] >= args.min_f1,
        "min_di_ratio": fairness_di >= args.min_di,
        "governance_pass": governance_ok,
    }

    status = "GO" if all(checks.values()) else "NO_GO"
    failed = [k for k, v in checks.items() if not v]

    return {
        "status": status,
        "checks": checks,
        "failed_checks": failed,
        "thresholds": {
            "min_roc_auc": args.min_roc_auc,
            "min_recall_class_1": args.min_recall,
            "min_f1_class_1": args.min_f1,
            "min_di_ratio": args.min_di,
        },
    }


def _candidate_configs(args) -> List[Dict[str, Any]]:
    if not args.auto_fairness_search:
        return [
            {
                "fairness_strategy": args.fairness_strategy,
                "threshold_strategy": args.threshold_strategy,
                "min_precision": args.min_precision,
            }
        ]

    return [
        {"fairness_strategy": "class_weight", "threshold_strategy": "f2", "min_precision": 0.75},
        {"fairness_strategy": "class_weight", "threshold_strategy": "f1", "min_precision": 0.75},
        {"fairness_strategy": "threshold_tuning", "threshold_strategy": "recall", "min_precision": 0.70},
        {"fairness_strategy": "threshold_tuning", "threshold_strategy": "recall", "min_precision": 0.65},
        {"fairness_strategy": "threshold_tuning", "threshold_strategy": "f2", "min_precision": 0.70},
        {"fairness_strategy": "threshold_tuning", "threshold_strategy": "f1", "min_precision": 0.70},
        {"fairness_strategy": "fairlearn", "threshold_strategy": "f2", "min_precision": 0.70},
        {"fairness_strategy": "fairlearn", "threshold_strategy": "f1", "min_precision": 0.70},
        {"fairness_strategy": "fairlearn", "threshold_strategy": "recall", "min_precision": 0.65},
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one-command model release gate pipeline")
    parser.add_argument("--csv_path", default="credit_risk_dataset.csv")
    parser.add_argument("--fairness_strategy", default="class_weight", choices=["class_weight", "threshold_tuning", "fairlearn"])
    parser.add_argument("--threshold_strategy", default="f2", choices=["f1", "f2", "recall"])
    parser.add_argument("--min_precision", type=float, default=0.75)

    # Release gates
    parser.add_argument("--min_roc_auc", type=float, default=0.86)
    parser.add_argument("--min_recall", type=float, default=0.75)
    parser.add_argument("--min_f1", type=float, default=0.58)
    parser.add_argument("--min_di", type=float, default=0.80)
    parser.add_argument("--auto_fairness_search", action="store_true", default=True)
    parser.add_argument("--no_auto_fairness_search", action="store_false", dest="auto_fairness_search")
    parser.add_argument("--max_attempts", type=int, default=5)
    parser.add_argument("--holdout_size", type=float, default=0.2)
    parser.add_argument("--random_state", type=int, default=42)
    parser.add_argument("--policy_threshold_min", type=float, default=0.20)
    parser.add_argument("--policy_threshold_max", type=float, default=0.85)
    parser.add_argument("--policy_threshold_step", type=float, default=0.01)

    args = parser.parse_args()

    print("=" * 72)
    print("RELEASE GATE PIPELINE")
    print("=" * 72)

    baseline_model_path = Path(PRODUCTION_MODEL_PATH)
    baseline_meta_path = Path(PRODUCTION_META_PATH)
    snapshot_dir = Path("monitoring_reports") / "baseline_snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_model_path = snapshot_dir / "baseline_model.joblib"
    snapshot_meta_path = snapshot_dir / "baseline_meta.json"

    if not baseline_model_path.exists():
        print("Baseline model is missing; cannot run fairness comparison against baseline.")
        return 2

    shutil.copy2(baseline_model_path, snapshot_model_path)
    if baseline_meta_path.exists():
        shutil.copy2(baseline_meta_path, snapshot_meta_path)

    configs = _candidate_configs(args)[: max(1, args.max_attempts)]
    attempts: List[Dict[str, Any]] = []
    final_fairness: Dict[str, Any] = {}
    governance_code = 1
    governance_ok = False
    selected_attempt = -1

    for idx, cfg in enumerate(configs, start=1):
        print(f"[Attempt {idx}/{len(configs)}] Training candidate model...")
        training_main(
            csv_path=args.csv_path,
            fairness_strategy=cfg["fairness_strategy"],
            threshold_strategy=cfg["threshold_strategy"],
            min_precision=cfg["min_precision"],
        )

        print(f"[Attempt {idx}/{len(configs)}] Running fairness-aware policy search...")
        fairness_report = _fairness_policy_search(
            baseline_model_path=snapshot_model_path,
            candidate_model_path=Path(PRODUCTION_MODEL_PATH),
            csv_path=args.csv_path,
            min_di=args.min_di,
            min_recall=args.min_recall,
            min_f1=args.min_f1,
            threshold_min=args.policy_threshold_min,
            threshold_max=args.policy_threshold_max,
            threshold_step=args.policy_threshold_step,
            holdout_size=args.holdout_size,
            random_state=args.random_state,
        )

        _persist_selected_threshold(Path(PRODUCTION_META_PATH), fairness_report["threshold"])

        Path("bias_reports").mkdir(exist_ok=True)
        with Path("bias_reports/new_model_validation.json").open("w", encoding="utf-8") as f:
            json.dump(fairness_report, f, indent=2)

        print(f"[Attempt {idx}/{len(configs)}] Running governance checks...")
        governance_code = governance_main()
        governance_ok = governance_code == 0

        meta = _read_json(Path(PRODUCTION_META_PATH))
        perf = _extract_performance(meta)
        decision = _gate_decision(perf, fairness_report, governance_ok, args)

        attempt_result = {
            "attempt": idx,
            "config": cfg,
            "performance": perf,
            "fairness": fairness_report,
            "governance": {"passed": governance_ok, "exit_code": governance_code},
            "decision": decision,
        }
        attempts.append(attempt_result)

        if decision["status"] == "GO":
            selected_attempt = idx
            final_fairness = fairness_report
            break

        if idx == len(configs):
            selected_attempt = idx
            final_fairness = fairness_report

    print("[Final] Evaluating release decision...")
    meta = _read_json(Path(PRODUCTION_META_PATH))
    performance = _extract_performance(meta)
    decision = _gate_decision(performance, final_fairness, governance_ok, args)

    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path("monitoring_reports")
    out_dir.mkdir(exist_ok=True)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": {
            "csv_path": args.csv_path,
            "auto_fairness_search": args.auto_fairness_search,
            "max_attempts": args.max_attempts,
            "selected_attempt": selected_attempt,
            "holdout_size": args.holdout_size,
            "policy_threshold": {
                "min": args.policy_threshold_min,
                "max": args.policy_threshold_max,
                "step": args.policy_threshold_step,
            },
        },
        "performance": performance,
        "fairness": final_fairness,
        "governance": {
            "passed": governance_ok,
            "exit_code": governance_code,
        },
        "attempts": attempts,
        "decision": decision,
    }

    latest_path = out_dir / "release_gate_latest.json"
    ts_path = out_dir / f"release_gate_{run_ts}.json"

    with latest_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    with ts_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("-" * 72)
    print(f"Status: {decision['status']}")
    print(f"Performance: ROC_AUC={performance['roc_auc']:.4f}, Recall_1={performance['recall_class_1']:.4f}, F1_1={performance['f1_class_1']:.4f}")
    print(f"Fairness DI: {float(final_fairness.get('candidate_di_ratio', 0.0)):.4f}")
    print(f"Selected threshold: {float(final_fairness.get('threshold', 0.0)):.4f}")
    print(f"Governance: {'PASS' if governance_ok else 'FAIL'}")
    if decision["failed_checks"]:
        print("Failed checks: " + ", ".join(decision["failed_checks"]))
    print(f"Report: {latest_path}")
    print("=" * 72)

    return 0 if decision["status"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
