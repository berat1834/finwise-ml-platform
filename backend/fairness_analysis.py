"""
Enhanced Bias and Fairness Analysis System
Regulatory compliance for financial institutions
- Disparate Impact Analysis (80% rule)
- Equal Credit Opportunity Act (ECOA) compliance
- Fair Lending Laws monitoring
- Comprehensive fairness metrics
"""

import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

from fairlearn.metrics import (
    demographic_parity_difference,
    demographic_parity_ratio,
    equalized_odds_difference,
    equalized_odds_ratio,
    MetricFrame,
    selection_rate,
    false_positive_rate,
    false_negative_rate,
    true_positive_rate
)


class FairnessAnalyzer:
    """
    Comprehensive fairness analysis for credit risk models
    Ensures compliance with fair lending regulations
    """
    
    def __init__(self, model_path='production_model.joblib', meta_path='production_model_meta.json'):
        """Initialize analyzer"""
        self.model = joblib.load(model_path)
        with open(meta_path, 'r') as f:
            self.meta = json.load(f)
        self.threshold = self.meta['threshold']
        self.reports_dir = Path('bias_reports/detailed')
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Regulatory thresholds
        self.DISPARATE_IMPACT_THRESHOLD = 0.80  # 80% rule
        self.ACCEPTABLE_PARITY_DIFFERENCE = 0.10  # 10%
        
    def load_data(self, data_path='credit_risk_dataset.csv'):
        """Load and prepare data"""
        try:
            df = pd.read_csv(data_path)
        except FileNotFoundError:
            print(f"Warning: {data_path} not found, generating synthetic data")
            df = self._generate_synthetic_data(1000)
        
        X = df.drop('loan_status', axis=1)
        y = df['loan_status']
        
        # Use last 30% as test
        test_size = int(len(df) * 0.3)
        return X.iloc[-test_size:], y.iloc[-test_size:]
    
    def _generate_synthetic_data(self, n=1000):
        """Generate synthetic credit data"""
        np.random.seed(42)
        
        data = {
            'person_age': np.random.randint(18, 70, n),
            'person_income': np.random.lognormal(10.5, 0.5, n),
            'person_emp_length': np.random.randint(0, 30, n),
            'loan_amnt': np.random.lognormal(9.5, 0.7, n),
            'loan_int_rate': np.random.uniform(5, 20, n),
            'loan_percent_income': np.random.uniform(0.05, 0.5, n),
            'cb_person_cred_hist_length': np.random.randint(0, 30, n),
            'person_home_ownership': np.random.choice(['RENT', 'OWN', 'MORTGAGE', 'OTHER'], n, p=[0.4, 0.3, 0.25, 0.05]),
            'loan_intent': np.random.choice(['PERSONAL', 'EDUCATION', 'MEDICAL', 'VENTURE', 'HOMEIMPROVEMENT', 'DEBTCONSOLIDATION'], n),
            'loan_grade': np.random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G'], n, p=[0.1, 0.15, 0.25, 0.25, 0.15, 0.07, 0.03]),
            'cb_person_default_on_file': np.random.choice(['Y', 'N'], n, p=[0.2, 0.8])
        }
        
        df = pd.DataFrame(data)
        risk_score = (
            (df['person_age'] < 25).astype(int) * 0.2 +
            (df['person_income'] < 30000).astype(int) * 0.3 +
            (df['loan_percent_income'] > 0.4).astype(int) * 0.3 +
            (df['cb_person_default_on_file'] == 'Y').astype(int) * 0.4
        )
        df['loan_status'] = (risk_score > np.random.uniform(0.3, 0.7, n)).astype(int)
        
        return df
    
    def create_protected_groups(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Define protected characteristic groups for fairness analysis
        Note: In production, use actual demographic data
        """
        protected = pd.DataFrame(index=X.index)
        
        # Age groups (proxy for age discrimination analysis)
        protected['age_group'] = pd.cut(
            X['person_age'],
            bins=[0, 25, 35, 45, 55, 100],
            labels=['18-25', '26-35', '36-45', '46-55', '56+']
        )
        
        # Income quintiles
        protected['income_quintile'] = pd.qcut(
            X['person_income'],
            q=5,
            labels=['Q1 (Lowest)', 'Q2', 'Q3', 'Q4', 'Q5 (Highest)'],
            duplicates='drop'
        )
        
        # Employment stability
        protected['employment_stability'] = pd.cut(
            X['person_emp_length'],
            bins=[-1, 1, 3, 7, 100],
            labels=['New (0-1y)', 'Junior (2-3y)', 'Mid (4-7y)', 'Senior (8+y)']
        )
        
        # Home ownership status (can correlate with race/ethnicity)
        protected['home_ownership'] = X['person_home_ownership']
        
        # Credit history length
        protected['credit_history'] = pd.cut(
            X['cb_person_cred_hist_length'],
            bins=[-1, 3, 7, 15, 100],
            labels=['New (0-3y)', 'Building (4-7y)', 'Established (8-15y)', 'Long (16+y)']
        )
        
        return protected
    
    def analyze_disparate_impact(self, y_pred: np.ndarray, protected_groups: pd.DataFrame) -> Dict:
        """
        Analyze disparate impact using 80% rule
        Legal standard from Equal Credit Opportunity Act
        """
        results = {}
        
        for group_name in protected_groups.columns:
            groups = protected_groups[group_name]
            unique_groups = groups.dropna().unique()
            
            # Calculate approval rates per group
            approval_rates = {}
            for group in unique_groups:
                mask = groups == group
                approval_rate = y_pred[mask].sum() / mask.sum() if mask.sum() > 0 else 0
                approval_rates[str(group)] = float(approval_rate)
            
            # Find max and min rates
            max_rate = max(approval_rates.values())
            min_rate = min(approval_rates.values())
            
            # Calculate disparate impact ratio
            di_ratio = min_rate / max_rate if max_rate > 0 else 0
            
            # Determine compliance with 80% rule
            compliant = di_ratio >= self.DISPARATE_IMPACT_THRESHOLD
            
            results[group_name] = {
                'approval_rates': approval_rates,
                'disparate_impact_ratio': float(di_ratio),
                'max_approval_rate': float(max_rate),
                'min_approval_rate': float(min_rate),
                'passes_80_percent_rule': compliant,
                'risk_level': 'LOW' if compliant else ('MEDIUM' if di_ratio >= 0.70 else 'HIGH')
            }
        
        return results
    
    def analyze_demographic_parity(self, y_true: np.ndarray, y_pred: np.ndarray, 
                                   protected_groups: pd.DataFrame) -> Dict:
        """Analyze demographic parity across protected groups"""
        results = {}
        
        # Ensure y_true and y_pred are numpy arrays
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        
        for group_name in protected_groups.columns:
            groups = protected_groups[group_name].dropna()
            
            # Filter data to remove NaN groups
            valid_idx = groups.index
            # Use integer array indices to avoid pandas indexing issues
            valid_positions = [i for i, idx in enumerate(protected_groups.index) if idx in valid_idx]
            
            y_true_filtered = y_true[valid_positions]
            y_pred_filtered = y_pred[valid_positions]
            
            try:
                # Calculate demographic parity metrics
                dp_diff = demographic_parity_difference(
                    y_true_filtered, y_pred_filtered, sensitive_features=groups
                )
                dp_ratio = demographic_parity_ratio(
                    y_true_filtered, y_pred_filtered, sensitive_features=groups
                )
                
                # Per-group metrics
                metric_frame = MetricFrame(
                    metrics={
                        'selection_rate': selection_rate,
                        'true_positive_rate': true_positive_rate,
                        'false_positive_rate': false_positive_rate
                    },
                    y_true=y_true_filtered,
                    y_pred=y_pred_filtered,
                    sensitive_features=groups
                )
                
                results[group_name] = {
                    'demographic_parity_difference': float(dp_diff),
                    'demographic_parity_ratio': float(dp_ratio),
                    'group_metrics': {
                        str(k): {metric: float(v) for metric, v in vals.items()}
                        for k, vals in metric_frame.by_group.to_dict('index').items()
                    },
                    'overall_metrics': {
                        metric: float(val) for metric, val in metric_frame.overall.items()
                    },
                    'compliant': abs(dp_diff) <= self.ACCEPTABLE_PARITY_DIFFERENCE
                }
            except Exception as e:
                results[group_name] = {'error': str(e)}
        
        return results
    
    def analyze_equal_opportunity(self, y_true: np.ndarray, y_pred: np.ndarray,
                                   protected_groups: pd.DataFrame) -> Dict:
        """
        Analyze equal opportunity (equal TPR across groups)
        Important for ensuring fair access to credit
        """
        results = {}
        
        for group_name in protected_groups.columns:
            groups = protected_groups[group_name].dropna()
            valid_idx = groups.index
            
            try:
                # Calculate true positive rates per group
                metric_frame = MetricFrame(
                    metrics={
                        'true_positive_rate': true_positive_rate,
                        'false_negative_rate': false_negative_rate
                    },
                    y_true=y_true[valid_idx],
                    y_pred=y_pred[valid_idx],
                    sensitive_features=groups
                )
                
                tpr_by_group = metric_frame.by_group['true_positive_rate']
                tpr_diff = tpr_by_group.max() - tpr_by_group.min()
                
                results[group_name] = {
                    'true_positive_rates': {str(k): float(v) for k, v in tpr_by_group.items()},
                    'tpr_difference': float(tpr_diff),
                    'false_negative_rates': {
                        str(k): float(v) for k, v in 
                        metric_frame.by_group['false_negative_rate'].items()
                    },
                    'compliant': tpr_diff <= self.ACCEPTABLE_PARITY_DIFFERENCE
                }
            except Exception as e:
                results[group_name] = {'error': str(e)}
        
        return results
    
    def analyze_equalized_odds(self, y_true: np.ndarray, y_pred: np.ndarray,
                                protected_groups: pd.DataFrame) -> Dict:
        """Analyze equalized odds (equal TPR and FPR)"""
        results = {}
        
        for group_name in protected_groups.columns:
            groups = protected_groups[group_name].dropna()
            valid_idx = groups.index
            
            try:
                eo_diff = equalized_odds_difference(
                    y_true[valid_idx], y_pred[valid_idx], sensitive_features=groups
                )
                eo_ratio = equalized_odds_ratio(
                    y_true[valid_idx], y_pred[valid_idx], sensitive_features=groups
                )
                
                metric_frame = MetricFrame(
                    metrics={
                        'tpr': true_positive_rate,
                        'fpr': false_positive_rate,
                        'fnr': false_negative_rate
                    },
                    y_true=y_true[valid_idx],
                    y_pred=y_pred[valid_idx],
                    sensitive_features=groups
                )
                
                results[group_name] = {
                    'equalized_odds_difference': float(eo_diff),
                    'equalized_odds_ratio': float(eo_ratio),
                    'group_metrics': {
                        str(k): {metric: float(v) for metric, v in vals.items()}
                        for k, vals in metric_frame.by_group.to_dict('index').items()
                    },
                    'compliant': abs(eo_diff) <= self.ACCEPTABLE_PARITY_DIFFERENCE
                }
            except Exception as e:
                results[group_name] = {'error': str(e)}
        
        return results
    
    def generate_compliance_report(self, X: pd.DataFrame, y_true: np.ndarray) -> Dict:
        """Generate comprehensive regulatory compliance report"""
        print("Generating Fairness & Compliance Report...")
        
        # Make predictions
        y_proba = self.model.predict_proba(X)[:, 1]
        y_pred = (y_proba >= self.threshold).astype(int)
        
        # Create protected groups
        protected_groups = self.create_protected_groups(X)
        
        # Run all analyses
        report = {
            'timestamp': datetime.now().isoformat(),
            'model_version': self.meta.get('timestamp', 'unknown'),
            'threshold': float(self.threshold),
            'sample_size': len(X),
            'overall_performance': {
                'roc_auc': float(roc_auc_score(y_true, y_proba)),
                'approval_rate': float(y_pred.sum() / len(y_pred))
            },
            'disparate_impact_analysis': self.analyze_disparate_impact(y_pred, protected_groups),
            'demographic_parity': self.analyze_demographic_parity(y_true, y_pred, protected_groups),
            'equal_opportunity': self.analyze_equal_opportunity(y_true, y_pred, protected_groups),
            'equalized_odds': self.analyze_equalized_odds(y_true, y_pred, protected_groups)
        }
        
        # Determine overall compliance status
        compliance_issues = []
        
        for group_name, analysis in report['disparate_impact_analysis'].items():
            if not analysis.get('passes_80_percent_rule', True):
                compliance_issues.append({
                    'type': 'Disparate Impact',
                    'group': group_name,
                    'severity': analysis.get('risk_level', 'UNKNOWN'),
                    'ratio': analysis['disparate_impact_ratio']
                })
        
        report['compliance_summary'] = {
            'compliant': len(compliance_issues) == 0,
            'issues_found': len(compliance_issues),
            'issues': compliance_issues,
            'recommendation': self._get_compliance_recommendation(compliance_issues)
        }
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.reports_dir / f'compliance_report_{timestamp}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Report saved to: {report_file}")
        
        return report
    
    def _get_compliance_recommendation(self, issues: List[Dict]) -> str:
        """Generate recommendation based on compliance issues"""
        if not issues:
            return "Model passes all fairness checks. Continue monitoring."
        
        high_severity = [i for i in issues if i['severity'] == 'HIGH']
        medium_severity = [i for i in issues if i['severity'] == 'MEDIUM']
        
        if high_severity:
            return ("CRITICAL: Model shows significant disparate impact. "
                   "Immediate review required before production deployment. "
                   "Consider: 1) Threshold adjustment, 2) Feature review, "
                   "3) Bias mitigation techniques, 4) Legal consultation.")
        elif medium_severity:
            return ("WARNING: Model shows moderate bias concerns. "
                   "Recommend bias mitigation before deployment. "
                   "Consider fairness constraints in retraining.")
        else:
            return "Minor fairness concerns detected. Monitor closely in production."
    
    def visualize_fairness_metrics(self, report: Dict):
        """Create visualizations for fairness analysis"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Fairness Analysis Dashboard', fontsize=16, fontweight='bold')
        
        # 1. Disparate Impact Ratios
        ax1 = axes[0, 0]
        di_data = report['disparate_impact_analysis']
        groups = list(di_data.keys())
        ratios = [di_data[g]['disparate_impact_ratio'] for g in groups]
        
        colors = ['red' if r < 0.8 else 'orange' if r < 0.9 else 'green' for r in ratios]
        ax1.barh(groups, ratios, color=colors, alpha=0.7)
        ax1.axvline(x=0.8, color='red', linestyle='--', label='80% Rule Threshold')
        ax1.set_xlabel('Disparate Impact Ratio')
        ax1.set_title('Disparate Impact Analysis (80% Rule)')
        ax1.legend()
        ax1.grid(axis='x', alpha=0.3)
        
        # 2. Selection Rates by Group
        ax2 = axes[0, 1]
        if 'age_group' in di_data:
            age_data = di_data['age_group']['approval_rates']
            ax2.bar(age_data.keys(), age_data.values(), color='steelblue', alpha=0.7)
            ax2.set_xlabel('Age Group')
            ax2.set_ylabel('Approval Rate')
            ax2.set_title('Approval Rates by Age Group')
            ax2.tick_params(axis='x', rotation=45)
            ax2.grid(axis='y', alpha=0.3)
        
        # 3. True Positive Rates by Group
        ax3 = axes[1, 0]
        eo_data = report['equal_opportunity']
        if 'age_group' in eo_data and 'true_positive_rates' in eo_data['age_group']:
            tpr_data = eo_data['age_group']['true_positive_rates']
            ax3.bar(tpr_data.keys(), tpr_data.values(), color='green', alpha=0.7)
            ax3.set_xlabel('Age Group')
            ax3.set_ylabel('True Positive Rate')
            ax3.set_title('Equal Opportunity: TPR by Age Group')
            ax3.tick_params(axis='x', rotation=45)
            ax3.grid(axis='y', alpha=0.3)
        
        # 4. Compliance Summary
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        summary = report['compliance_summary']
        summary_text = f"""
        COMPLIANCE SUMMARY
        {'='*40}
        
        Status: {'âœ“ COMPLIANT' if summary['compliant'] else 'âœ— NON-COMPLIANT'}
        Issues Found: {summary['issues_found']}
        
        Recommendation:
        {summary['recommendation'][:200]}
        
        Model Threshold: {report['threshold']:.4f}
        Sample Size: {report['sample_size']:,}
        Overall Approval Rate: {report['overall_performance']['approval_rate']:.2%}
        """
        
        ax4.text(0.1, 0.5, summary_text, fontsize=10, family='monospace',
                verticalalignment='center')
        
        plt.tight_layout()
        
        # Save figure
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        fig_path = self.reports_dir / f'fairness_dashboard_{timestamp}.png'
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        print(f"Dashboard saved to: {fig_path}")
        plt.close()


# CLI Interface
if __name__ == '__main__':
    print("=" * 80)
    print("FAIRNESS & REGULATORY COMPLIANCE ANALYSIS")
    print("=" * 80)
    
    analyzer = FairnessAnalyzer()
    
    # Load data
    X_test, y_test = analyzer.load_data()
    print(f"\nAnalyzing {len(X_test)} credit applications...")
    
    # Generate report
    report = analyzer.generate_compliance_report(X_test, y_test.values)
    
    # Print summary
    print("\n" + "=" * 80)
    print("COMPLIANCE SUMMARY")
    print("=" * 80)
    print(f"Status: {'âœ“ COMPLIANT' if report['compliance_summary']['compliant'] else 'âœ— NON-COMPLIANT'}")
    print(f"Issues Found: {report['compliance_summary']['issues_found']}")
    
    if report['compliance_summary']['issues']:
        print("\nIssues:")
        for issue in report['compliance_summary']['issues']:
            print(f"  - {issue['type']} in {issue['group']}: "
                  f"Ratio={issue['ratio']:.3f} (Severity: {issue['severity']})")
    
    print(f"\nRecommendation:")
    print(f"  {report['compliance_summary']['recommendation']}")
    
    # Create visualizations
    print("\nGenerating visualizations...")
    analyzer.visualize_fairness_metrics(report)
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)

