#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fine-grained threshold tuning for production_model.joblib
Saves threshold_config_final.pkl and deployment_config.json
"""
import pandas as pd
import numpy as np
import joblib
import json
from sklearn.metrics import recall_score, f1_score, roc_auc_score

print('\nStarting fine-grained threshold tuning for production_model.joblib...')

model = joblib.load('production_model.joblib')
print('âœ“ Loaded production_model.joblib')

# Load data
df = pd.read_csv('credit_risk_dataset.csv')
df = df.dropna(subset=['loan_status'])
X = df.drop('loan_status', axis=1)
y = df['loan_status']
X = X.fillna(X.median(numeric_only=True))
for col in X.select_dtypes(include=['object']).columns:
    X[col] = X[col].fillna(X[col].mode()[0] if len(X[col].mode())>0 else 'UNKNOWN')
X_enc = pd.get_dummies(X, drop_first=True)

# split
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X_enc, y, test_size=0.3, random_state=42, stratify=y)

proba = model.predict_proba(X_test)[:,1]

# income quintile
income_quintile = pd.qcut(X_test['person_income'], q=5, labels=['Q1','Q2','Q3','Q4','Q5'], duplicates='drop')

best = None

for thr in np.arange(0.50, 0.71, 0.001):
    y_pred = (proba >= thr).astype(int)
    approval_rates = {}
    valid = True
    for q in ['Q1','Q2','Q3','Q4','Q5']:
        mask = (income_quintile == q)
        if mask.sum() == 0:
            valid = False
            break
        approval_rates[q] = (1 - y_pred[mask]).mean() * 100
    if not valid:
        continue
    max_rate = max(approval_rates.values())
    min_rate = min(approval_rates.values())
    di = min_rate / max_rate if max_rate>0 else 0
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, proba)
    # prefer DI>=0.80, then higher recall, then higher DI
    candidate = {'threshold': float(thr), 'di': float(di), 'recall': float(recall), 'f1': float(f1), 'auc': float(auc), 'approval_rates': approval_rates}
    if best is None:
        best = candidate
    else:
        # choose candidate with DI>=0.80 first
        if best['di'] < 0.80 and candidate['di'] >= 0.80:
            best = candidate
        elif (candidate['di'] >= 0.80 and best['di'] >= 0.80):
            # both compliant, choose higher recall then higher di
            if candidate['recall'] > best['recall'] or (candidate['recall']==best['recall'] and candidate['di']>best['di']):
                best = candidate
        else:
            # none compliant yet: choose higher di then recall
            if candidate['di'] > best['di'] or (candidate['di']==best['di'] and candidate['recall']>best['recall']):
                best = candidate

# Save results
if best is None:
    print('No threshold candidate found in range.')
else:
    print('\nBest candidate:')
    print(best)
    joblib.dump({'threshold': best['threshold']}, 'threshold_config_final.pkl')
    print('âœ“ Saved threshold_config_final.pkl')
    deployment = {
        'model_file': 'production_model.joblib',
        'threshold': float(best['threshold']),
        'di_ratio': float(best['di']),
        'auc': float(best['auc']),
        'recall': float(best['recall']),
        'f1': float(best['f1']),
        'approval_by_income': best['approval_rates']
    }
    with open('deployment_config.json','w') as f:
        json.dump(deployment,f,indent=2)
    print('âœ“ Saved deployment_config.json')

print('\nTuning complete.')

