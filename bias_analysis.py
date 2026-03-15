"""
Bias and Fairness Analysis for Credit Risk Model
Analyzes model for demographic parity, equal opportunity, and disparate impact
"""
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from fairlearn.metrics import (
    demographic_parity_difference,
    demographic_parity_ratio,
    equalized_odds_difference,
    equalized_odds_ratio,
    MetricFrame
)
from fairlearn.metrics import selection_rate, false_positive_rate, false_negative_rate


class BiasAnalyzer:
    """Analyze model for bias across different demographic groups"""
    
    def __init__(self, model_path='production_model.joblib', meta_path='production_model_meta.json'):
        """Load model and metadata"""
        self.model = joblib.load(model_path)
        with open(meta_path, 'r') as f:
            self.meta = json.load(f)
        self.threshold = self.meta['threshold']
        
    def load_test_data(self, data_path='training_data.csv'):
        """Load and prepare test data"""
        try:
            df = pd.read_csv(data_path)
        except FileNotFoundError:
            try:
                df = pd.read_csv('credit_risk.csv')
            except FileNotFoundError:
                # Generate synthetic test data
                print("   No CSV found, generating synthetic test data...")
                df = self._generate_synthetic_data(1000)
        
        # Split features and target
        X = df.drop('loan_status', axis=1)
        y = df['loan_status']
        
        # Use last 30% as test set
        test_size = int(len(df) * 0.3)
        X_test = X.iloc[-test_size:]
        y_test = y.iloc[-test_size:]
        
        return X_test, y_test
    
    def _generate_synthetic_data(self, n_samples=1000):
        """Generate synthetic credit data for testing"""
        np.random.seed(42)
        
        data = {
            'person_age': np.random.randint(18, 70, n_samples),
            'person_income': np.random.lognormal(10.5, 0.5, n_samples),
            'person_emp_length': np.random.randint(0, 30, n_samples),
            'loan_amnt': np.random.lognormal(9.5, 0.7, n_samples),
            'loan_int_rate': np.random.uniform(5, 20, n_samples),
            'loan_percent_income': np.random.uniform(0.05, 0.5, n_samples),
            'cb_person_cred_hist_length': np.random.randint(0, 30, n_samples),
            'person_home_ownership': np.random.choice(['RENT', 'OWN', 'MORTGAGE', 'OTHER'], n_samples, p=[0.4, 0.3, 0.25, 0.05]),
            'loan_intent': np.random.choice(['PERSONAL', 'EDUCATION', 'MEDICAL', 'VENTURE', 'HOMEIMPROVEMENT', 'DEBTCONSOLIDATION'], n_samples),
            'loan_grade': np.random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G'], n_samples, p=[0.1, 0.15, 0.25, 0.25, 0.15, 0.07, 0.03]),
            'cb_person_default_on_file': np.random.choice(['Y', 'N'], n_samples, p=[0.2, 0.8])
        }
        
        df = pd.DataFrame(data)
        
        # Generate target based on features (simplified risk logic)
        risk_score = (
            (df['person_age'] < 25).astype(int) * 0.2 +
            (df['person_income'] < 30000).astype(int) * 0.3 +
            (df['loan_percent_income'] > 0.4).astype(int) * 0.3 +
            (df['cb_person_default_on_file'] == 'Y').astype(int) * 0.4
        )
        df['loan_status'] = (risk_score > np.random.uniform(0.3, 0.7, n_samples)).astype(int)
        
        return df
    
    def create_sensitive_features(self, X):
        """Create sensitive feature groups for fairness analysis"""
        sensitive_features = {}
        
        # Age groups
        sensitive_features['age_group'] = pd.cut(
            X['person_age'],
            bins=[0, 25, 35, 45, 100],
            labels=['18-25', '26-35', '36-45', '46+']
        )
        
        # Income groups
        sensitive_features['income_group'] = pd.cut(
            X['person_income'],
            bins=[0, 30000, 50000, 75000, np.inf],
            labels=['Low (<30K)', 'Medium (30-50K)', 'High (50-75K)', 'Very High (>75K)']
        )
        
        # Employment length groups
        sensitive_features['employment_group'] = pd.cut(
            X['person_emp_length'],
            bins=[-1, 2, 5, 10, 100],
            labels=['0-2 years', '3-5 years', '6-10 years', '10+ years']
        )
        
        # Gender proxy (using home ownership as proxy - not ideal but for demo)
        sensitive_features['home_ownership'] = X['person_home_ownership']
        
        return pd.DataFrame(sensitive_features)
    
    def make_predictions(self, X):
        """Make predictions using model threshold"""
        probas = self.model.predict_proba(X)[:, 1]
        predictions = (probas >= self.threshold).astype(int)
        return predictions, probas
    
    def analyze_demographic_parity(self, y_true, y_pred, sensitive_features):
        """Analyze demographic parity across groups"""
        results = {}
        
        for feature in sensitive_features.columns:
            sf = sensitive_features[feature]
            
            # Overall metrics
            dp_diff = demographic_parity_difference(
                y_true, y_pred, sensitive_features=sf
            )
            dp_ratio = demographic_parity_ratio(
                y_true, y_pred, sensitive_features=sf
            )
            
            # Per-group selection rates
            metric_frame = MetricFrame(
                metrics=selection_rate,
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sf
            )
            
            results[feature] = {
                'demographic_parity_difference': dp_diff,
                'demographic_parity_ratio': dp_ratio,
                'selection_rates': metric_frame.by_group.to_dict(),
                'overall_selection_rate': selection_rate(y_true, y_pred)
            }
            
        return results
    
    def analyze_equalized_odds(self, y_true, y_pred, sensitive_features):
        """Analyze equalized odds (FPR and FNR equality)"""
        results = {}
        
        for feature in sensitive_features.columns:
            sf = sensitive_features[feature]
            
            # Overall metrics
            eo_diff = equalized_odds_difference(
                y_true, y_pred, sensitive_features=sf
            )
            eo_ratio = equalized_odds_ratio(
                y_true, y_pred, sensitive_features=sf
            )
            
            # Per-group FPR and FNR
            fpr_frame = MetricFrame(
                metrics=false_positive_rate,
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sf
            )
            
            fnr_frame = MetricFrame(
                metrics=false_negative_rate,
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sf
            )
            
            results[feature] = {
                'equalized_odds_difference': eo_diff,
                'equalized_odds_ratio': eo_ratio,
                'false_positive_rates': fpr_frame.by_group.to_dict(),
                'false_negative_rates': fnr_frame.by_group.to_dict()
            }
            
        return results
    
    def calculate_disparate_impact(self, y_pred, sensitive_features):
        """Calculate 80% rule disparate impact"""
        results = {}
        
        for feature in sensitive_features.columns:
            sf = sensitive_features[feature]
            groups = sf.unique()
            
            # Calculate approval rates per group
            approval_rates = {}
            for group in groups:
                mask = sf == group
                approval_rate = y_pred[mask].mean()
                approval_rates[str(group)] = approval_rate
            
            # Calculate disparate impact ratio (min/max)
            rates = list(approval_rates.values())
            if len(rates) > 0 and max(rates) > 0:
                disparate_impact = min(rates) / max(rates)
                passes_80_rule = disparate_impact >= 0.8
            else:
                disparate_impact = None
                passes_80_rule = None
            
            results[feature] = {
                'approval_rates': approval_rates,
                'disparate_impact_ratio': disparate_impact,
                'passes_80_percent_rule': passes_80_rule
            }
            
        return results
    
    def visualize_bias(self, sensitive_features, y_pred, output_dir='bias_reports'):
        """Create visualizations for bias analysis"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        for feature in sensitive_features.columns:
            sf = sensitive_features[feature]
            
            # Approval rates by group
            fig, ax = plt.subplots(figsize=(10, 6))
            
            approval_data = pd.DataFrame({
                'Group': sf,
                'Approved': y_pred
            })
            
            approval_rates = approval_data.groupby('Group')['Approved'].agg(['mean', 'count'])
            approval_rates['mean'].plot(kind='bar', ax=ax, color='steelblue')
            
            # Add 80% rule line
            ax.axhline(y=0.8 * approval_rates['mean'].max(), 
                      color='red', linestyle='--', label='80% Rule Threshold')
            
            ax.set_title(f'Approval Rates by {feature}', fontsize=14, fontweight='bold')
            ax.set_xlabel(feature.replace('_', ' ').title())
            ax.set_ylabel('Approval Rate')
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            
            # Add count labels
            for i, (idx, row) in enumerate(approval_rates.iterrows()):
                ax.text(i, row['mean'] + 0.02, f"n={row['count']}", 
                       ha='center', fontsize=9)
            
            plt.tight_layout()
            plt.savefig(output_path / f'approval_rates_{feature}.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        print(f"âœ“ Bias visualization charts saved to {output_dir}/")
    
    def generate_report(self, output_path='bias_analysis_report.json'):
        """Generate comprehensive bias analysis report"""
        print("=" * 60)
        print("BIAS AND FAIRNESS ANALYSIS")
        print("=" * 60)
        
        # Load data
        print("\n1. Loading test data...")
        X_test, y_test = self.load_test_data()
        print(f"   Test samples: {len(X_test)}")
        
        # Create sensitive features
        print("\n2. Creating sensitive feature groups...")
        sensitive_features = self.create_sensitive_features(X_test)
        for col in sensitive_features.columns:
            print(f"   - {col}: {sensitive_features[col].nunique()} groups")
        
        # Make predictions
        print("\n3. Making predictions...")
        y_pred, probas = self.make_predictions(X_test)
        overall_approval_rate = y_pred.mean()
        print(f"   Overall approval rate: {overall_approval_rate:.2%}")
        
        # Analyze demographic parity
        print("\n4. Analyzing demographic parity...")
        dp_results = self.analyze_demographic_parity(y_test, y_pred, sensitive_features)
        
        # Analyze equalized odds
        print("\n5. Analyzing equalized odds...")
        eo_results = self.analyze_equalized_odds(y_test, y_pred, sensitive_features)
        
        # Calculate disparate impact
        print("\n6. Calculating disparate impact (80% rule)...")
        di_results = self.calculate_disparate_impact(y_pred, sensitive_features)
        
        # Visualize
        print("\n7. Creating visualizations...")
        self.visualize_bias(sensitive_features, y_pred)
        
        # Compile report
        report = {
            'model_version': self.meta.get('version', 'unknown'),
            'threshold': self.threshold,
            'test_samples': len(X_test),
            'overall_approval_rate': float(overall_approval_rate),
            'demographic_parity': dp_results,
            'equalized_odds': eo_results,
            'disparate_impact': di_results,
            'fairness_assessment': self._assess_fairness(dp_results, eo_results, di_results)
        }
        
        # Save report
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\nâœ“ Full report saved to {output_path}")
        
        # Print summary
        self._print_summary(report)
        
        return report
    
    def _assess_fairness(self, dp_results, eo_results, di_results):
        """Assess overall fairness of the model"""
        issues = []
        
        for feature, metrics in di_results.items():
            if metrics['disparate_impact_ratio'] is not None:
                if not metrics['passes_80_percent_rule']:
                    issues.append(f"{feature}: Fails 80% rule (ratio={metrics['disparate_impact_ratio']:.2f})")
        
        for feature, metrics in dp_results.items():
            if abs(metrics['demographic_parity_difference']) > 0.1:
                issues.append(f"{feature}: High demographic parity difference ({metrics['demographic_parity_difference']:.3f})")
        
        if len(issues) == 0:
            assessment = "PASS: Model shows no major fairness issues"
        else:
            assessment = f"ATTENTION: {len(issues)} potential fairness issues detected"
        
        return {
            'overall_assessment': assessment,
            'issues': issues,
            'total_issues': len(issues)
        }
    
    def _print_summary(self, report):
        """Print human-readable summary"""
        print("\n" + "=" * 60)
        print("FAIRNESS ASSESSMENT SUMMARY")
        print("=" * 60)
        
        assessment = report['fairness_assessment']
        print(f"\n{assessment['overall_assessment']}")
        
        if assessment['issues']:
            print(f"\nIssues found ({assessment['total_issues']}):")
            for issue in assessment['issues']:
                print(f"  âš  {issue}")
        else:
            print("\nâœ“ No significant fairness issues detected")
        
        print("\nKey Metrics:")
        for feature in ['age_group', 'income_group']:
            if feature in report['disparate_impact']:
                di_ratio = report['disparate_impact'][feature]['disparate_impact_ratio']
                if di_ratio:
                    print(f"  - {feature}: Disparate Impact = {di_ratio:.2f} ({'âœ“ Pass' if di_ratio >= 0.8 else 'âœ— Fail'} 80% rule)")
        
        print("\n" + "=" * 60)


if __name__ == '__main__':
    analyzer = BiasAnalyzer()
    report = analyzer.generate_report()

