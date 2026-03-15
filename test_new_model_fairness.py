#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Compare fairness metrics between candidate and baseline models on a holdout set."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import joblib
import json
from sklearn.model_selection import train_test_split


RANDOM_STATE = 42
HOLDOUT_SIZE = 0.2
DATASET_PATH = 'credit_risk_dataset.csv'
BASELINE_MODEL_PATH = 'production_model.joblib'
NEW_MODEL_PATH = 'model_production_optimal.joblib'
OUTPUT_PATH = 'bias_reports/new_model_validation.json'


def _prepare_common_features(raw_df: pd.DataFrame):
    X = raw_df.drop('loan_status', axis=1)
    y = raw_df['loan_status']

    X = X.fillna(X.median(numeric_only=True))
    for col in X.select_dtypes(include=['object']).columns:
        mode = X[col].mode()
        X[col] = X[col].fillna(mode.iloc[0] if len(mode) > 0 else 'UNKNOWN')

    X_encoded = pd.get_dummies(X, drop_first=True)
    return X, X_encoded, y


def _align_features_for_model(model, X_encoded: pd.DataFrame) -> pd.DataFrame:
    expected = list(getattr(model, 'feature_names_in_', []))
    if expected:
        return X_encoded.reindex(columns=expected, fill_value=0)
    return X_encoded


def _approval_by_income(y_pred: pd.Series, income_series: pd.Series):
    income_quintile = pd.qcut(
        income_series,
        q=5,
        labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'],
        duplicates='drop',
    )
    rates = {}
    for q in ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']:
        mask = income_quintile == q
        if mask.sum() > 0:
            rates[q] = float((1 - y_pred[mask]).mean() * 100)
    return rates


def _di_ratio(approval_rates: dict) -> float:
    if not approval_rates:
        return 0.0
    max_rate = max(approval_rates.values())
    min_rate = min(approval_rates.values())
    return float(min_rate / max_rate) if max_rate > 0 else 0.0

print("\n" + "=" * 70)
print("NEW VS BASELINE MODEL FAIRNESS VALIDATION")
print("=" * 70)

df = pd.read_csv(DATASET_PATH)
df = df.dropna(subset=['loan_status'])

X_raw, X_encoded, y = _prepare_common_features(df)

X_train, X_holdout, y_train, y_holdout = train_test_split(
    X_encoded,
    y,
    test_size=HOLDOUT_SIZE,
    random_state=RANDOM_STATE,
    stratify=y,
)
holdout_income = X_raw.loc[X_holdout.index, 'person_income']

if not Path(BASELINE_MODEL_PATH).exists():
    raise FileNotFoundError(f"Baseline model not found: {BASELINE_MODEL_PATH}")
if not Path(NEW_MODEL_PATH).exists():
    raise FileNotFoundError(f"Candidate model not found: {NEW_MODEL_PATH}")

model_baseline = joblib.load(BASELINE_MODEL_PATH)
model_new = joblib.load(NEW_MODEL_PATH)

X_holdout_for_baseline = _align_features_for_model(model_baseline, X_holdout)
X_holdout_for_new = _align_features_for_model(model_new, X_holdout)

y_pred_baseline = pd.Series(model_baseline.predict(X_holdout_for_baseline), index=X_holdout.index)
y_pred_new = pd.Series(model_new.predict(X_holdout_for_new), index=X_holdout.index)

print("Baseline model loaded:", BASELINE_MODEL_PATH)
print("Candidate model loaded:", NEW_MODEL_PATH)
print(f"Holdout samples: {len(X_holdout)}")

print("\n" + "=" * 70)
print("APPROVAL RATES BY INCOME QUINTILE")
print("=" * 70)

approval_rates_baseline = _approval_by_income(y_pred_baseline, holdout_income)
approval_rates_new = _approval_by_income(y_pred_new, holdout_income)

for q in ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']:
    b = approval_rates_baseline.get(q)
    n = approval_rates_new.get(q)
    if b is not None and n is not None:
        print(f"{q}: baseline={b:.1f}% | candidate={n:.1f}%")

di_ratio_baseline = _di_ratio(approval_rates_baseline)
di_ratio_new = _di_ratio(approval_rates_new)
passes_80_rule = di_ratio_new >= 0.80
improvement = ((di_ratio_new - di_ratio_baseline) / abs(di_ratio_baseline) * 100.0) if di_ratio_baseline != 0 else 0.0

print("\n" + "=" * 70)
print("DISPARATE IMPACT SUMMARY")
print("=" * 70)
print(f"Baseline DI Ratio:  {di_ratio_baseline:.3f}")
print(f"Candidate DI Ratio: {di_ratio_new:.3f}")
print(f"80% Rule Pass:      {passes_80_rule}")
print(f"Relative change:    {improvement:+.1f}%")

status = "COMPLIANT" if passes_80_rule else "NEEDS_IMPROVEMENT"

Path('bias_reports').mkdir(exist_ok=True)
results = {
    'status': status,
    'dataset_path': DATASET_PATH,
    'holdout_size': HOLDOUT_SIZE,
    'holdout_samples': int(len(X_holdout)),
    'baseline_model_path': BASELINE_MODEL_PATH,
    'candidate_model_path': NEW_MODEL_PATH,
    'baseline_di_ratio': di_ratio_baseline,
    'candidate_di_ratio': di_ratio_new,
    'passes_80_rule': passes_80_rule,
    'relative_change_percent': improvement,
    'approval_rates_baseline': approval_rates_baseline,
    'approval_rates_candidate': approval_rates_new,
}

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, default=str)

print(f"\nResults saved to {OUTPUT_PATH}")

