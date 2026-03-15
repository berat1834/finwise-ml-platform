#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Threshold Optimization Script
Fairness constraint altında model threshold'unu optimize et
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fairness_analysis import FairnessAnalyzer
import numpy as np
import json

def optimize_threshold_for_fairness():
    """Fairness gereksinimlerini karşılayacak threshold bul"""
    
    print("\n" + "="*70)
    print("THRESHOLD OPTIMIZATION FOR FAIRNESS COMPLIANCE")
    print("="*70)
    
    analyzer = FairnessAnalyzer()
    X, y = analyzer.load_data()
    
    # Get probability predictions (not binary)
    probabilities = analyzer.model.predict_proba(X)[:, 1]  # P(reject)
    
    print(f"\nTesting thresholds from 0.3 to 0.9 in steps of 0.05...")
    print("-" * 70)
    
    results = []
    
    for threshold in np.arange(0.3, 0.95, 0.05):
        # Make predictions with this threshold
        y_pred = (probabilities >= threshold).astype(int)
        
        # Analyze disparate impact
        protected = analyzer.create_protected_groups(X)
        di_results = analyzer.analyze_disparate_impact(y_pred, protected)
        
        # Check if all groups pass 80% rule
        all_pass = all(results['passes_80_percent_rule'] for results in di_results.values())
        
        # Calculate average DI ratio
        avg_di_ratio = np.mean([results['disparate_impact_ratio'] for results in di_results.values()])
        
        # Count approvals
        approval_rate = (1 - y_pred).mean() * 100
        
        results.append({
            'threshold': float(threshold),
            'all_pass_80_rule': all_pass,
            'avg_di_ratio': float(avg_di_ratio),
            'approval_rate': float(approval_rate),
            'di_details': di_results
        })
        
        status = "✓ PASS" if all_pass else "✗ FAIL"
        print(f"Threshold {threshold:.2f}: {status} | Avg DI: {avg_di_ratio:.3f} | Approval: {approval_rate:.1f}%")
    
    # Find best threshold (highest DI ratio while passing)
    passing = [r for r in results if r['all_pass_80_rule']]
    
    print("\n" + "="*70)
    if passing:
        best = max(passing, key=lambda x: x['avg_di_ratio'])
        print(f"✓ RECOMMENDED THRESHOLD: {best['threshold']:.2f}")
        print(f"  - Passes 80% rule: YES")
        print(f"  - Average DI Ratio: {best['avg_di_ratio']:.3f}")
        print(f"  - Approval Rate: {best['approval_rate']:.1f}%")
        print("="*70)
        
        return best
    else:
        print("✗ NO THRESHOLD PASSES 80% RULE")
        print("  Best candidate:")
        best = max(results, key=lambda x: x['avg_di_ratio'])
        print(f"  Threshold: {best['threshold']:.2f}")
        print(f"  Average DI Ratio: {best['avg_di_ratio']:.3f}")
        print(f"  Approval Rate: {best['approval_rate']:.1f}%")
        print("\n⚠ WARNING: Model may need retraining with better fairness constraints")
        print("="*70)
        
        return best

if __name__ == "__main__":
    optimal = optimize_threshold_for_fairness()
    
    # Save results
    with open('bias_reports/threshold_optimization.json', 'w') as f:
        json.dump(optimal, f, indent=2, default=str)
    
    print(f"\n✓ Results saved to bias_reports/threshold_optimization.json")
