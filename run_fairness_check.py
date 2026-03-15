#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ADIM 2: Fairness Analysis Entegrasyonu
Demografik ayrımcılık analizi için API endpoint ekler
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fairness_analysis import FairnessAnalyzer
import pandas as pd
import json

def run_fairness_check():
    """Tüm sistemi fairness açısından kontrol et"""
    print("\n" + "="*70)
    print("FAIRNESS ANALYSIS - DEMOGRAPHIC DISCRIMINATION CHECK")
    print("="*70)
    
    try:
        # Initialize analyzer
        analyzer = FairnessAnalyzer()
        print("\n✓ FairnessAnalyzer initialized")
        
        # Load data
        X, y = analyzer.load_data()
        print(f"✓ Data loaded: {len(X)} samples")
        
        # Get predictions
        y_pred = analyzer.model.predict(X)
        print(f"✓ Predictions made")
        
        # Create protected groups
        protected = analyzer.create_protected_groups(X)
        print(f"✓ Protected groups identified: {protected.columns.tolist()}")
        
        # Analyze disparate impact
        disparate_impact = analyzer.analyze_disparate_impact(y_pred, protected)
        print(f"\n📊 DISPARATE IMPACT (80% RULE) ANALYSIS:")
        print("-" * 70)
        
        all_compliant = True
        for group_name, results in disparate_impact.items():
            compliant = results['passes_80_percent_rule']
            status = "✓ PASS" if compliant else "✗ FAIL"
            print(f"\n{status} {group_name.upper()}")
            print(f"  DI Ratio: {results['disparate_impact_ratio']:.3f}")
            print(f"  Max Approval Rate: {results['max_approval_rate']:.1%}")
            print(f"  Min Approval Rate: {results['min_approval_rate']:.1%}")
            print(f"  Risk Level: {results['risk_level']}")
            
            if not compliant:
                all_compliant = False
                print(f"  ⚠ WARNING: Possible disparate impact detected!")
        
        # Analyze demographic parity
        demo_parity = analyzer.analyze_demographic_parity(y, y_pred, protected)
        print(f"\n📈 DEMOGRAPHIC PARITY ANALYSIS:")
        print("-" * 70)
        for group_name, results in demo_parity.items():
            print(f"\n{group_name.upper()}")
            print(f"  Demographic Parity Difference: {results.get('parity_difference', 'N/A')}")
            print(f"  Demographic Parity Ratio: {results.get('parity_ratio', 'N/A')}")
            print(f"  Risk Assessment: {results.get('risk_assessment', 'N/A')}")
        
        # Overall status
        print(f"\n" + "="*70)
        if all_compliant:
            print("✓ FAIRNESS CHECK PASSED - Model complies with 80% rule")
        else:
            print("✗ FAIRNESS CHECK FAILED - Possible discrimination detected")
        print("="*70)
        
        return {
            'status': 'compliant' if all_compliant else 'non_compliant',
            'disparate_impact': disparate_impact,
            'demographic_parity': demo_parity
        }
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'message': str(e)}


if __name__ == "__main__":
    results = run_fairness_check()
    
    # Save results
    with open('bias_reports/fairness_check_latest.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n✓ Results saved to bias_reports/fairness_check_latest.json")
