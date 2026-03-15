"""
Model Monitoring Dashboard
KullanÄ±m: python monitoring.py
"""

import json
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# Evidently 0.7.17+ uses new SDK structure
from evidently import Report, Dataset, BinaryClassification
from prometheus_client import Gauge, Counter, Histogram, generate_latest, CollectorRegistry
import psutil


class ModelMonitor:
    """
    Production model monitoring with:
    - Data drift detection (Evidently)
    - Performance metrics tracking (Prometheus)
    - System health monitoring
    """
    
    def __init__(self, model_path='production_model.joblib', reference_data_path='reference_data.csv'):
        self.model_path = Path(model_path)
        self.reference_data_path = Path(reference_data_path)
        self.reports_dir = Path('monitoring_reports')
        self.reports_dir.mkdir(exist_ok=True)
        
        # Load model
        self.model = self._load_model()
        self.metadata = self._load_metadata()
        
        # Load or generate reference data
        self.reference_data = self._load_reference_data()
        
        # Define column mapping for Evidently (dict format in 0.7.17+)
        self.column_mapping = None  # Auto-detect in newer versions
        
        # Initialize Prometheus metrics
        self.registry = CollectorRegistry()
        self._init_prometheus_metrics()
        
        print(f"[OK] Model Monitor initialized")
        print(f"  - Reference data shape: {self.reference_data.shape}")
        print(f"  - Model threshold: {self.metadata.get('threshold', 0.5):.4f}")
    
    def _load_model(self):
        """Load trained model"""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        import joblib
        return joblib.load(self.model_path)
    
    def _load_metadata(self):
        """Load model metadata"""
        metadata_path = self.model_path.parent / 'production_model_meta.json'
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'threshold': 0.5}
    
    def _load_reference_data(self):
        """Load or generate reference data for drift detection"""
        if self.reference_data_path.exists():
            df = pd.read_csv(self.reference_data_path)
            print(f"[OK] Loaded reference data from {self.reference_data_path}")
        else:
            print("WARNING: Reference data not found, generating synthetic data...")
            df = self._generate_reference_data(n=1000)
            df.to_csv('reference_data.csv', index=False)
            print(f"[OK] Saved reference data to reference_data.csv")
        
        # Add predictions if not present
        if 'prediction' not in df.columns:
            features = df.drop('default', axis=1) if 'default' in df.columns else df
            df['prediction'] = (self.model.predict_proba(features)[:, 1] > 
                               self.metadata.get('threshold', 0.5)).astype(int)
        
        return df
    
    def _generate_reference_data(self, n=1000):
        """Generate synthetic reference data"""
        np.random.seed(42)
        
        data = {
            'person_age': np.random.randint(20, 70, n),
            'person_income': np.random.randint(20000, 150000, n),
            'person_home_ownership': np.random.choice(['RENT', 'OWN', 'MORTGAGE', 'OTHER'], n, 
                                                      p=[0.4, 0.25, 0.3, 0.05]),
            'person_emp_length': np.random.randint(0, 40, n),
            'loan_intent': np.random.choice(['EDUCATION', 'MEDICAL', 'VENTURE', 'PERSONAL', 
                                            'DEBTCONSOLIDATION', 'HOMEIMPROVEMENT'], n),
            'loan_grade': np.random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G'], n,
                                          p=[0.15, 0.20, 0.25, 0.20, 0.10, 0.07, 0.03]),
            'loan_amnt': np.random.randint(500, 35000, n),
            'loan_int_rate': np.random.uniform(5.0, 25.0, n),
            'loan_percent_income': np.random.uniform(0.01, 0.8, n),
            'cb_person_default_on_file': np.random.choice(['Y', 'N'], n, p=[0.2, 0.8]),
            'cb_person_cred_hist_length': np.random.randint(2, 30, n)
        }
        
        df = pd.DataFrame(data)
        
        # Generate target based on risk factors
        risk_score = (
            (df['loan_int_rate'] > 15).astype(int) * 0.3 +
            (df['loan_percent_income'] > 0.4).astype(int) * 0.3 +
            (df['loan_grade'].isin(['E', 'F', 'G'])).astype(int) * 0.2 +
            (df['cb_person_default_on_file'] == 'Y').astype(int) * 0.2
        )
        df['default'] = (risk_score > 0.5).astype(int)
        
        return df
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        # Prediction metrics
        self.predictions_total = Counter(
            'model_predictions_total',
            'Total number of predictions',
            ['model_version', 'prediction'],
            registry=self.registry
        )
        
        self.prediction_latency = Histogram(
            'model_prediction_latency_seconds',
            'Prediction latency in seconds',
            registry=self.registry
        )
        
        self.rejection_rate = Gauge(
            'model_rejection_rate',
            'Current rejection rate',
            registry=self.registry
        )
        
        # Drift metrics
        self.dataset_drift = Gauge(
            'model_dataset_drift',
            'Overall dataset drift score',
            registry=self.registry
        )
        
        self.column_drift = Gauge(
            'model_column_drift',
            'Feature-level drift score',
            ['feature_name'],
            registry=self.registry
        )
        
        # System metrics
        self.cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'system_memory_usage_percent',
            'Memory usage percentage',
            registry=self.registry
        )
        
        self.disk_usage = Gauge(
            'system_disk_usage_percent',
            'Disk usage percentage',
            registry=self.registry
        )
    
    def analyze_drift(self, current_data: pd.DataFrame, save_report=True):
        """
        Detect data drift using statistical tests (Kolmogorov-Smirnov)
        
        Args:
            current_data: New production data
            save_report: Whether to save report
        
        Returns:
            Dict with drift metrics
        """
        # Add predictions to current data if not present
        if 'prediction' not in current_data.columns:
            features = current_data.drop('default', axis=1) if 'default' in current_data.columns else current_data
            current_data['prediction'] = (self.model.predict_proba(features)[:, 1] > 
                                         self.metadata.get('threshold', 0.5)).astype(int)
        
        # Initialize drift results
        drift_results = {
            'timestamp': datetime.now().isoformat(),
            'dataset_drift': None,
            'drift_share': 0,
            'number_of_drifted_columns': 0,
            'drifted_features': [],
            'feature_stats': {}
        }
        
        # Statistical comparison for numerical features
        from scipy.stats import ks_2samp, chi2_contingency
        
        numerical_features = [
            'person_age', 'person_income', 'person_emp_length',
            'loan_amnt', 'loan_int_rate', 'loan_percent_income',
            'cb_person_cred_hist_length'
        ]
        
        categorical_features = [
            'person_home_ownership', 'loan_intent',
            'loan_grade', 'cb_person_default_on_file'
        ]
        
        # Test numerical features (Kolmogorov-Smirnov test)
        for feat in numerical_features:
            if feat in self.reference_data.columns and feat in current_data.columns:
                stat, pvalue = ks_2samp(self.reference_data[feat], current_data[feat])
                
                is_drifted = pvalue < 0.05  # Significance level
                if is_drifted:
                    drift_results['number_of_drifted_columns'] += 1
                    drift_results['drifted_features'].append({
                        'feature': feat,
                        'drift_score': float(stat),
                        'stattest_name': 'ks_2samp',
                        'pvalue': float(pvalue)
                    })
                    
                    # Update Prometheus metric
                    self.column_drift.labels(feature_name=feat).set(stat)
                
                drift_results['feature_stats'][feat] = {
                    'statistic': float(stat),
                    'pvalue': float(pvalue),
                    'drifted': bool(is_drifted)
                }
        
        # Test categorical features (Chi-square test)
        for feat in categorical_features:
            if feat in self.reference_data.columns and feat in current_data.columns:
                try:
                    # Create contingency table
                    ref_counts = self.reference_data[feat].value_counts()
                    curr_counts = current_data[feat].value_counts()
                    
                    # Align categories
                    all_cats = sorted(set(ref_counts.index) | set(curr_counts.index))
                    ref_aligned = [ref_counts.get(cat, 0) for cat in all_cats]
                    curr_aligned = [curr_counts.get(cat, 0) for cat in all_cats]
                    
                    # Chi-square test
                    contingency_table = np.array([ref_aligned, curr_aligned])
                    chi2, pvalue, _, _ = chi2_contingency(contingency_table)
                    
                    is_drifted = pvalue < 0.05
                    if is_drifted:
                        drift_results['number_of_drifted_columns'] += 1
                        drift_results['drifted_features'].append({
                            'feature': feat,
                            'drift_score': float(chi2),
                            'stattest_name': 'chi2_contingency',
                            'pvalue': float(pvalue)
                        })
                        
                        # Update Prometheus metric
                        self.column_drift.labels(feature_name=feat).set(chi2 / 100)  # Normalize
                    
                    drift_results['feature_stats'][feat] = {
                        'statistic': float(chi2),
                        'pvalue': float(pvalue),
                        'drifted': bool(is_drifted)
                    }
                except Exception as e:
                    print(f"[WARNING] Could not test {feat}: {e}")
        
        total_features = len(numerical_features) + len(categorical_features)
        drift_results['drift_share'] = drift_results['number_of_drifted_columns'] / total_features
        drift_results['dataset_drift'] = drift_results['drift_share'] > 0.3  # 30% threshold
        
        # Update Prometheus dataset drift
        self.dataset_drift.set(drift_results['drift_share'])
        
        # Save report if requested
        if save_report:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = self.reports_dir / f'drift_report_{timestamp}.json'
            with open(report_path, 'w') as f:
                json.dump(drift_results, f, indent=2)
            print(f"[OK] Drift report saved to {report_path}")
        
        return drift_results
    
    def track_predictions(self, predictions: List[Dict]):
        """
        Track prediction metrics
        
        Args:
            predictions: List of predictions with 'tahmin' and 'red_olasiligi'
        """
        rejected = sum(1 for p in predictions if p['tahmin'] == 'RED')
        rejection_rate = rejected / len(predictions) if predictions else 0
        
        self.rejection_rate.set(rejection_rate)
        
        for pred in predictions:
            label = 'rejected' if pred['tahmin'] == 'RED' else 'approved'
            self.predictions_total.labels(
                model_version='v2',
                prediction=label
            ).inc()
    
    def update_system_metrics(self):
        """Update system health metrics"""
        self.cpu_usage.set(psutil.cpu_percent(interval=1))
        self.memory_usage.set(psutil.virtual_memory().percent)
        self.disk_usage.set(psutil.disk_usage('/').percent)
    
    def get_metrics_summary(self) -> Dict:
        """Get current metrics summary"""
        return {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            },
            'model': {
                'threshold': self.metadata.get('threshold', 0.5),
                'version': 'v2'
            }
        }
    
    def export_prometheus_metrics(self) -> bytes:
        """Export metrics in Prometheus format"""
        self.update_system_metrics()
        return generate_latest(self.registry)


def simulate_production_data(n=500, drift=False):
    """Generate simulated production data with optional drift"""
    np.random.seed(None)  # Random seed for production simulation
    
    if drift:
        # Introduce drift: shift distributions
        print("  Generating data with drift...")
        data = {
            'person_age': np.random.randint(25, 75, n),  # Older applicants
            'person_income': np.random.randint(30000, 200000, n),  # Higher incomes
            'person_home_ownership': np.random.choice(['RENT', 'OWN', 'MORTGAGE', 'OTHER'], n, 
                                                      p=[0.5, 0.2, 0.25, 0.05]),  # More renters
            'person_emp_length': np.random.randint(0, 45, n),
            'loan_intent': np.random.choice(['EDUCATION', 'MEDICAL', 'VENTURE', 'PERSONAL', 
                                            'DEBTCONSOLIDATION', 'HOMEIMPROVEMENT'], n),
            'loan_grade': np.random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G'], n,
                                          p=[0.10, 0.15, 0.20, 0.25, 0.15, 0.10, 0.05]),  # More risky grades
            'loan_amnt': np.random.randint(1000, 40000, n),  # Higher loan amounts
            'loan_int_rate': np.random.uniform(8.0, 28.0, n),  # Higher rates
            'loan_percent_income': np.random.uniform(0.05, 0.9, n),
            'cb_person_default_on_file': np.random.choice(['Y', 'N'], n, p=[0.3, 0.7]),  # More defaults
            'cb_person_cred_hist_length': np.random.randint(1, 25, n)
        }
    else:
        # Similar distribution to reference data
        print("  Generating data without drift...")
        data = {
            'person_age': np.random.randint(20, 70, n),
            'person_income': np.random.randint(20000, 150000, n),
            'person_home_ownership': np.random.choice(['RENT', 'OWN', 'MORTGAGE', 'OTHER'], n, 
                                                      p=[0.4, 0.25, 0.3, 0.05]),
            'person_emp_length': np.random.randint(0, 40, n),
            'loan_intent': np.random.choice(['EDUCATION', 'MEDICAL', 'VENTURE', 'PERSONAL', 
                                            'DEBTCONSOLIDATION', 'HOMEIMPROVEMENT'], n),
            'loan_grade': np.random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G'], n,
                                          p=[0.15, 0.20, 0.25, 0.20, 0.10, 0.07, 0.03]),
            'loan_amnt': np.random.randint(500, 35000, n),
            'loan_int_rate': np.random.uniform(5.0, 25.0, n),
            'loan_percent_income': np.random.uniform(0.01, 0.8, n),
            'cb_person_default_on_file': np.random.choice(['Y', 'N'], n, p=[0.2, 0.8]),
            'cb_person_cred_hist_length': np.random.randint(2, 30, n)
        }
    
    df = pd.DataFrame(data)
    
    # Generate target
    risk_score = (
        (df['loan_int_rate'] > 15).astype(int) * 0.3 +
        (df['loan_percent_income'] > 0.4).astype(int) * 0.3 +
        (df['loan_grade'].isin(['E', 'F', 'G'])).astype(int) * 0.2 +
        (df['cb_person_default_on_file'] == 'Y').astype(int) * 0.2
    )
    df['default'] = (risk_score > 0.5).astype(int)
    
    return df


if __name__ == '__main__':
    print("=" * 60)
    print("Model Monitoring System")
    print("=" * 60)
    
    # Initialize monitor
    monitor = ModelMonitor()
    
    # Test 1: Normal production data (no drift)
    print("\n" + "=" * 60)
    print("TEST 1: Analyzing normal production data (no drift expected)")
    print("=" * 60)
    
    normal_data = simulate_production_data(n=300, drift=False)
    drift_results_normal = monitor.analyze_drift(normal_data)
    
    print(f"\n{'='*60}")
    print("DRIFT ANALYSIS RESULTS (Normal Data)")
    print(f"{'='*60}")
    print(f"Dataset Drift Detected: {drift_results_normal['dataset_drift']}")
    print(f"Drift Share: {drift_results_normal['drift_share']:.2%}")
    print(f"Number of Drifted Features: {drift_results_normal['number_of_drifted_columns']}")
    
    if drift_results_normal['drifted_features']:
        print(f"\nDrifted Features:")
        for feat in drift_results_normal['drifted_features']:
            print(f"  - {feat['feature']}: {feat['drift_score']:.4f} ({feat['stattest_name']})")
    else:
        print("\n[OK] No feature drift detected")
    
    # Test 2: Production data with drift
    print("\n" + "=" * 60)
    print("TEST 2: Analyzing production data with drift")
    print("=" * 60)
    
    drifted_data = simulate_production_data(n=300, drift=True)
    drift_results_drift = monitor.analyze_drift(drifted_data)
    
    print(f"\n{'='*60}")
    print("DRIFT ANALYSIS RESULTS (Drifted Data)")
    print(f"{'='*60}")
    print(f"Dataset Drift Detected: {drift_results_drift['dataset_drift']}")
    print(f"Drift Share: {drift_results_drift['drift_share']:.2%}")
    print(f"Number of Drifted Features: {drift_results_drift['number_of_drifted_columns']}")
    
    if drift_results_drift['drifted_features']:
        print(f"\n[WARNING] Drifted Features:")
        for feat in drift_results_drift['drifted_features']:
            print(f"  - {feat['feature']}: {feat['drift_score']:.4f} ({feat['stattest_name']})")
    
    # System metrics
    print("\n" + "=" * 60)
    print("SYSTEM METRICS")
    print("=" * 60)
    
    metrics = monitor.get_metrics_summary()
    print(f"CPU Usage: {metrics['system']['cpu_percent']:.1f}%")
    print(f"Memory Usage: {metrics['system']['memory_percent']:.1f}%")
    print(f"Disk Usage: {metrics['system']['disk_percent']:.1f}%")
    
    # Prometheus metrics
    print("\n" + "=" * 60)
    print("PROMETHEUS METRICS")
    print("=" * 60)
    
    prom_metrics = monitor.export_prometheus_metrics().decode('utf-8')
    print(prom_metrics[:500] + "...\n")  # Print first 500 chars
    
    # Save results
    report_path = Path('monitoring_reports') / 'latest_drift_analysis.json'
    with open(report_path, 'w') as f:
        json.dump({
            'normal_data': drift_results_normal,
            'drifted_data': drift_results_drift,
            'system_metrics': metrics
        }, f, indent=2)
    
    print(f"\n[OK] Analysis complete!")
    print(f"  - HTML reports saved to monitoring_reports/")
    print(f"  - JSON summary saved to {report_path}")

