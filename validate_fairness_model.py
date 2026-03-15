#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validate Fairness-Aware Model
Yeni model ile 80% rule compliance kontrol et
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fairness_analysis import FairnessAnalyzer
import joblib
import json
import numpy as np

def validate_new_model():
    """Yeni fairness-aware model'i test et"""
    
    print("\n" + "="*70)
    print("FAIRNESS-AWARE MODEL VALIDATION")
    print("="*70)
    
    # Load original analyzer
    analyzer = FairnessAnalyzer()
    X, y = analyzer.load_data()
    
    # Load production model
    try:
        new_model = joblib.load('production_model.joblib')
        print("\n✓ Production model loaded: production_model.joblib")
    except Exception:
        print("\n✗ Model not found. Run training_pipeline.py first")
        return
    
    # Get predictions from new model
    try:
        y_pred_new = new_model.predict(X)
        print("✓ Predictions generated from new model")
    except Exception as e:
        print(f"✗ Error making predictions: {str(e)}")
        return
    
    # Analyze disparate impact
    protected = analyzer.create_protected_groups(X)
    di_results = analyzer.analyze_disparate_impact(y_pred_new, protected)
    
    print("\n" + "="*70)
    print("80% RULE COMPLIANCE - NEW MODEL")
    print("="*70)
    
    passed_groups = 0
    total_groups = len(di_results)
    
    for group_name, results in di_results.items():
        compliant = results['passes_80_percent_rule']
        status = "✓ PASS" if compliant else "✗ FAIL"
        
        if compliant:
            passed_groups += 1
        
        print(f"\n{status} {group_name.upper()}")
        print(f"  DI Ratio: {results['disparate_impact_ratio']:.3f}")
        print(f"  Max Approval: {results['max_approval_rate']:.1%}")
        print(f"  Min Approval: {results['min_approval_rate']:.1%}")
        print(f"  Risk Level: {results['risk_level']}")
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed_groups}/{total_groups} groups pass 80% rule")
    print("="*70)
    
    if passed_groups == total_groups:
        print("\n✓✓✓ SUCCESS! Model is fairness-compliant! ✓✓✓")
        status = "COMPLIANT"
    elif passed_groups >= total_groups - 1:
        print("\n⚠ MOSTLY COMPLIANT - 1 group fails slightly")
        status = "MOSTLY_COMPLIANT"
    else:
        print("\n✗ Model still has fairness issues")
        status = "NON_COMPLIANT"
    
    # Save results
    results = {
        'model': 'production_model.joblib',
        'status': status,
        'passed_groups': passed_groups,
        'total_groups': total_groups,
        'disparate_impact': di_results,
        'improvement': 'See comparison with optimize_threshold.json'
    }
    
    with open('bias_reports/fairness_validation_new_model.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✓ Results saved to bias_reports/fairness_validation_new_model.json")
    
    return status

if __name__ == "__main__":
    validate_new_model()
