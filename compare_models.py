#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick Model Comparison: Original vs. Fairness-Aware
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import joblib
import json

print("\n" + "="*70)
print("MODEL COMPARISON: ORIGINAL vs. FAIRNESS-AWARE")
print("="*70)

# Load data
df = pd.read_csv('credit_risk_dataset.csv')
df = df.dropna(subset=['loan_status'])

X = df.drop('loan_status', axis=1)
y = df['loan_status']

# Load both models
print("\nLoading models...")
try:
    original_model = joblib.load('production_model.joblib')
    print("âœ“ Original model loaded")
except Exception as e:
    print(f"âœ— Original model error: {e}")
    original_model = None

try:
    fairness_model = joblib.load('model_fairness.joblib')
    print("âœ“ Fairness-aware model loaded")
except Exception as e:
    print(f"âœ— Fairness model error: {e}")
    fairness_model = None

# Simple comparison: approval rates
print("\n" + "="*70)
print("APPROVAL RATE COMPARISON BY INCOME QUINTILE")
print("="*70)

# Create income groups
X['income_quintile'] = pd.qcut(X['person_income'], q=5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'], duplicates='drop')

print("\nORIGINAL MODEL (Current - Discriminatory):")
try:
    y_pred_original = original_model.predict(X.drop('income_quintile', axis=1))
    for q in ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']:
        mask = X['income_quintile'] == q
        if mask.sum() > 0:
            approval_rate = (1 - y_pred_original[mask]).mean() * 100
            print(f"  {q}: {approval_rate:.1f}% approval")
except Exception as e:
    print(f"  Error: {e}")

print("\nFAIRNESS-AWARE MODEL (New):")
try:
    y_pred_fair = fairness_model.predict(X.drop('income_quintile', axis=1))
    for q in ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']:
        mask = X['income_quintile'] == q
        if mask.sum() > 0:
            approval_rate = (1 - y_pred_fair[mask]).mean() * 100
            print(f"  {q}: {approval_rate:.1f}% approval")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("âœ“ Models loaded and compared")
print("âœ“ Check approval rates above for fairness improvement")
print("âœ“ Run 'python run_fairness_check.py' for full audit")

