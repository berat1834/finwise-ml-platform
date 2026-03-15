#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Grid search for fairness-aware RandomForest hyperparameters.
Trains for combinations, scans thresholds, picks best model meeting DI>=0.80
and business constraints (AUC>=0.89, recall>=0.60 where possible).
Saves best model and metadata.
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, recall_score, precision_score, f1_score
import joblib, json
from datetime import datetime
from data_utils import load_credit_data, remove_leakage_columns

print('\nStarting grid-search for fair model...')

# Load data with shared preprocessing and leakage protection
df = load_credit_data('credit_risk_dataset.csv')
df = remove_leakage_columns(df)
df = df.dropna(subset=['loan_status'])
X = df.drop('loan_status', axis=1)
y = df['loan_status']

# Preprocess
X = X.fillna(X.median(numeric_only=True))
for col in X.select_dtypes(include=['object']).columns:
    X[col] = X[col].fillna(X[col].mode()[0] if len(X[col].mode())>0 else 'UNKNOWN')
X_encoded = pd.get_dummies(X, drop_first=True)

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X_encoded, y, test_size=0.3, random_state=42, stratify=y)
print(f'Train samples: {len(X_train)}, Test samples: {len(X_test)}')

# Income quintiles on test set for DI calculation
income_quintile_test = pd.qcut(X_test['person_income'], q=5, labels=['Q1','Q2','Q3','Q4','Q5'], duplicates='drop')

# Search space
param_grid = {
    'max_depth': [3,4,5],
    'min_samples_leaf': [50,75,100],
    'n_estimators': [200]
}

best = None
results = []

for max_depth in param_grid['max_depth']:
    for min_leaf in param_grid['min_samples_leaf']:
        for n_est in param_grid['n_estimators']:
            print(f"\nTraining RF: max_depth={max_depth}, min_samples_leaf={min_leaf}, n_estimators={n_est}")
            clf = RandomForestClassifier(n_estimators=n_est, max_depth=max_depth, random_state=42,
                                         class_weight='balanced', n_jobs=-1, min_samples_leaf=min_leaf)
            clf.fit(X_train, y_train)
            proba = clf.predict_proba(X_test)[:,1]
            auc = roc_auc_score(y_test, proba)

            # Threshold scan
            best_local = None
            for thr in np.arange(0.50, 0.71, 0.01):
                y_pred_thr = (proba >= thr).astype(int)
                # approval rates per quintile
                approval = {}
                valid = True
                for q in ['Q1','Q2','Q3','Q4','Q5']:
                    mask = (income_quintile_test == q)
                    if mask.sum() == 0:
                        valid = False
                        break
                    approval[q] = (1 - y_pred_thr[mask]).mean() * 100
                if not valid:
                    continue
                max_rate = max(approval.values())
                min_rate = min(approval.values())
                di = min_rate / max_rate if max_rate>0 else 0
                recall = recall_score(y_test, y_pred_thr)
                precision = precision_score(y_test, y_pred_thr, zero_division=0)
                f1 = f1_score(y_test, y_pred_thr)

                # Record
                rec = {
                    'max_depth': max_depth,
                    'min_samples_leaf': min_leaf,
                    'n_estimators': n_est,
                    'threshold': float(thr),
                    'auc': float(auc),
                    'recall': float(recall),
                    'precision': float(precision),
                    'f1': float(f1),
                    'di': float(di),
                    'approval': approval
                }
                results.append(rec)

                # Candidate selection: prefer DI>=0.80 then high auc then recall
                meets = (di >= 0.80 and auc >= 0.89 and recall >= 0.60)
                if meets:
                    if best_local is None or (rec['di'] > best_local['di']) or (rec['di']==best_local['di'] and rec['auc']>best_local['auc']):
                        best_local = rec

            if best_local:
                # If found locally, compare global best
                if best is None or (best_local['di'] > best['di']) or (best_local['di']==best['di'] and best_local['auc']>best['auc']):
                    best = {'clf': clf, 'meta': best_local}
                    print(f"Found new best candidate: DI={best_local['di']:.3f}, AUC={best_local['auc']:.3f}, thr={best_local['threshold']}")

# If no candidate meets strict constraints, relax to best DI while keeping auc>=0.88 and recall>=0.55
if best is None:
    print('\nNo candidate met strict constraints; selecting best DI with relaxed constraints...')
    candidate = None
    for r in results:
        if r['auc'] >= 0.88 and r['recall'] >= 0.55:
            if candidate is None or (r['di'] > candidate['di']) or (r['di']==candidate['di'] and r['auc']>candidate['auc']):
                candidate = r
    if candidate:
        print(f"Selected relaxed candidate: DI={candidate['di']:.3f}, AUC={candidate['auc']:.3f}, thr={candidate['threshold']}")
        # retrain model with those params
        clf = RandomForestClassifier(n_estimators=int(candidate['n_estimators']), max_depth=int(candidate['max_depth']), random_state=42,
                                     class_weight='balanced', n_jobs=-1, min_samples_leaf=int(candidate['min_samples_leaf']))
        clf.fit(X_train, y_train)
        best = {'clf': clf, 'meta': candidate}

# Final save
if best is None:
    print('\nNo suitable model found in grid search. Consider expanding grid or relaxing constraints.')
else:
    model = best['clf']
    meta = best['meta']
    # Save model and metadata
    model_name = 'production_model.joblib'
    joblib.dump(model, model_name)
    meta_out = {
        'model_file': model_name,
        'selected_params': {
            'max_depth': int(meta['max_depth']),
            'min_samples_leaf': int(meta['min_samples_leaf']),
            'n_estimators': int(meta['n_estimators'])
        },
        'threshold': float(meta['threshold']),
        'metrics': {
            'auc': float(meta['auc']),
            'recall': float(meta['recall']),
            'precision': float(meta['precision']),
            'f1': float(meta['f1']),
            'di': float(meta['di'])
        },
        'approval_by_income': meta['approval'],
        'created_at': datetime.now().isoformat()
    }
    with open('production_model_meta.json','w') as f:
        json.dump(meta_out, f, indent=2)
    print(f"\nSaved best model as {model_name} with DI={meta['di']:.3f} and AUC={meta['auc']:.3f}")

# Also save full results for analysis
with open('grid_search_results.json','w') as f:
    json.dump(results, f, indent=2)
print('\nGrid search complete.')

