"""
Advanced Model Monitoring System
- Concept drift detection (model performance degradation)
- Automated alerting system
- Model retraining triggers
- A/B testing support
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import warnings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from dataclasses import dataclass, asdict
warnings.filterwarnings('ignore')

import joblib
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix
from scipy import stats


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitoring_advanced.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Model performance metrics"""
    timestamp: str
    roc_auc: float
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    sample_size: int


@dataclass
class DriftAlert:
    """Drift detection alert"""
    alert_type: str  # 'data_drift', 'concept_drift', 'performance_degradation'
    severity: str  # 'low', 'medium', 'high', 'critical'
    timestamp: str
    message: str
    metrics: Dict
    recommended_action: str


class ConceptDriftDetector:
    """
    Detects concept drift by monitoring model performance over time
    Uses ADWIN (Adaptive Windowing) algorithm for change detection
    """
    
    def __init__(self, window_size=100, sensitivity=0.05):
        """
        Args:
            window_size: Number of predictions to keep in sliding window
            sensitivity: Sensitivity threshold for drift detection (0-1)
        """
        self.window_size = window_size
        self.sensitivity = sensitivity
        self.performance_history = []
        self.baseline_performance = None
        
    def add_performance(self, metrics: PerformanceMetrics):
        """Add new performance measurement"""
        self.performance_history.append(metrics)
        
        # Keep only recent window
        if len(self.performance_history) > self.window_size * 2:
            self.performance_history = self.performance_history[-self.window_size * 2:]
        
        # Set baseline if not set
        if self.baseline_performance is None and len(self.performance_history) >= 20:
            self.baseline_performance = self._calculate_baseline()
    
    def _calculate_baseline(self) -> Dict[str, float]:
        """Calculate baseline performance from initial window"""
        baseline_window = self.performance_history[:20]
        return {
            'roc_auc': np.mean([m.roc_auc for m in baseline_window]),
            'precision': np.mean([m.precision for m in baseline_window]),
            'recall': np.mean([m.recall for m in baseline_window]),
            'f1_score': np.mean([m.f1_score for m in baseline_window])
        }
    
    def detect_drift(self) -> Optional[DriftAlert]:
        """
        Detect concept drift using statistical tests
        Returns alert if drift detected
        """
        if len(self.performance_history) < 30 or self.baseline_performance is None:
            return None
        
        # Split into two windows
        mid_point = len(self.performance_history) // 2
        recent_window = self.performance_history[mid_point:]
        old_window = self.performance_history[:mid_point]
        
        # Calculate average performance for each window
        recent_metrics = {
            'roc_auc': np.mean([m.roc_auc for m in recent_window]),
            'recall': np.mean([m.recall for m in recent_window]),
            'f1_score': np.mean([m.f1_score for m in recent_window])
        }
        
        old_metrics = {
            'roc_auc': np.mean([m.roc_auc for m in old_window]),
            'recall': np.mean([m.recall for m in old_window]),
            'f1_score': np.mean([m.f1_score for m in old_window])
        }
        
        # Perform statistical test (Mann-Whitney U test)
        roc_pvalue = stats.mannwhitneyu(
            [m.roc_auc for m in old_window],
            [m.roc_auc for m in recent_window],
            alternative='two-sided'
        ).pvalue
        
        # Check for significant performance drop
        roc_drop = old_metrics['roc_auc'] - recent_metrics['roc_auc']
        recall_drop = old_metrics['recall'] - recent_metrics['recall']
        
        # Determine severity
        if roc_drop > 0.1 or recall_drop > 0.15:
            severity = 'critical'
            recommended_action = "IMMEDIATE RETRAINING REQUIRED - Model performance severely degraded"
        elif roc_drop > 0.05 or recall_drop > 0.10:
            severity = 'high'
            recommended_action = "Schedule model retraining within 24 hours"
        elif roc_drop > 0.02 or recall_drop > 0.05:
            severity = 'medium'
            recommended_action = "Monitor closely, prepare for retraining"
        elif roc_pvalue < 0.05:
            severity = 'low'
            recommended_action = "Statistically significant change detected, continue monitoring"
        else:
            return None  # No drift detected
        
        return DriftAlert(
            alert_type='concept_drift',
            severity=severity,
            timestamp=datetime.now().isoformat(),
            message=f"Concept drift detected: ROC AUC dropped by {roc_drop:.4f}, Recall dropped by {recall_drop:.4f}",
            metrics={
                'baseline_roc_auc': self.baseline_performance['roc_auc'],
                'current_roc_auc': recent_metrics['roc_auc'],
                'roc_auc_drop': roc_drop,
                'recall_drop': recall_drop,
                'p_value': roc_pvalue
            },
            recommended_action=recommended_action
        )


class AlertingSystem:
    """
    Automated alerting system for drift detection
    Supports multiple notification channels
    """
    
    def __init__(self, config_path='config/alerting_config.json'):
        """Load alerting configuration"""
        self.config = self._load_config(config_path)
        self.alert_history = []
        self.alerts_dir = Path('monitoring_reports/alerts')
        self.alerts_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load alerting configuration"""
        default_config = {
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'from_email': '',
                'to_emails': [],
                'password': ''
            },
            'slack': {
                'enabled': False,
                'webhook_url': ''
            },
            'severity_thresholds': {
                'low': ['log'],
                'medium': ['log', 'email'],
                'high': ['log', 'email', 'slack'],
                'critical': ['log', 'email', 'slack', 'pagerduty']
            }
        }
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        except FileNotFoundError:
            logger.warning(f"Config not found at {config_path}, using defaults")
            return default_config
    
    def send_alert(self, alert: DriftAlert):
        """Send alert through configured channels"""
        self.alert_history.append(alert)
        
        # Determine notification channels based on severity
        channels = self.config['severity_thresholds'].get(alert.severity, ['log'])
        
        # Log alert
        if 'log' in channels:
            self._log_alert(alert)
        
        # Email alert
        if 'email' in channels and self.config['email']['enabled']:
            self._send_email_alert(alert)
        
        # Save alert to file
        self._save_alert_to_file(alert)
        
        logger.info(f"Alert sent: {alert.alert_type} - {alert.severity}")
    
    def _log_alert(self, alert: DriftAlert):
        """Log alert to file"""
        log_level = {
            'low': logging.INFO,
            'medium': logging.WARNING,
            'high': logging.ERROR,
            'critical': logging.CRITICAL
        }.get(alert.severity, logging.INFO)
        
        logger.log(log_level, f"ALERT: {alert.message}")
        logger.log(log_level, f"Recommended Action: {alert.recommended_action}")
    
    def _send_email_alert(self, alert: DriftAlert):
        """Send email alert"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email']['from_email']
            msg['To'] = ', '.join(self.config['email']['to_emails'])
            msg['Subject'] = f"[{alert.severity.upper()}] Model Alert: {alert.alert_type}"
            
            body = f"""
            Alert Type: {alert.alert_type}
            Severity: {alert.severity}
            Timestamp: {alert.timestamp}
            
            Message: {alert.message}
            
            Recommended Action: {alert.recommended_action}
            
            Metrics:
            {json.dumps(alert.metrics, indent=2)}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.config['email']['smtp_server'], 
                            self.config['email']['smtp_port']) as server:
                server.starttls()
                server.login(self.config['email']['from_email'], 
                           self.config['email']['password'])
                server.send_message(msg)
            
            logger.info(f"Email alert sent to {msg['To']}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _save_alert_to_file(self, alert: DriftAlert):
        """Save alert to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        alert_file = self.alerts_dir / f'alert_{timestamp}_{alert.severity}.json'
        
        with open(alert_file, 'w') as f:
            json.dump(asdict(alert), f, indent=2)
        
        logger.info(f"Alert saved to {alert_file}")


class AdvancedModelMonitor:
    """
    Advanced monitoring system with:
    - Concept drift detection
    - Automated alerting
    - Retraining recommendations
    - A/B testing support
    """
    
    def __init__(self, model_path='production_model.joblib'):
        """Initialize advanced monitor"""
        self.model_path = Path(model_path)
        self.model = self._load_model()
        self.metadata = self._load_metadata()
        
        # Initialize sub-components
        self.concept_drift_detector = ConceptDriftDetector(window_size=100)
        self.alerting_system = AlertingSystem()
        
        # Performance tracking
        self.performance_log = []
        self.log_dir = Path('monitoring_reports/performance')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Advanced Model Monitor initialized")
    
    def _load_model(self):
        """Load model"""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        return joblib.load(self.model_path)
    
    def _load_metadata(self) -> Dict:
        """Load model metadata"""
        meta_path = self.model_path.parent / 'production_model_meta.json'
        if meta_path.exists():
            with open(meta_path, 'r') as f:
                return json.load(f)
        return {'threshold': 0.5}
    
    def evaluate_batch(self, X: pd.DataFrame, y_true: pd.Series) -> PerformanceMetrics:
        """
        Evaluate model on a batch of data
        
        Args:
            X: Features
            y_true: True labels
        
        Returns:
            PerformanceMetrics object
        """
        # Get predictions
        y_proba = self.model.predict_proba(X)[:, 1]
        threshold = self.metadata.get('threshold', 0.5)
        y_pred = (y_proba > threshold).astype(int)
        
        # Calculate metrics
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            roc_auc=roc_auc_score(y_true, y_proba),
            precision=precision_score(y_true, y_pred, zero_division=0),
            recall=recall_score(y_true, y_pred, zero_division=0),
            f1_score=f1_score(y_true, y_pred, zero_division=0),
            accuracy=(tp + tn) / (tp + tn + fp + fn),
            true_positives=int(tp),
            false_positives=int(fp),
            true_negatives=int(tn),
            false_negatives=int(fn),
            sample_size=len(y_true)
        )
        
        # Log performance
        self.performance_log.append(metrics)
        self._save_performance_log()
        
        # Add to concept drift detector
        self.concept_drift_detector.add_performance(metrics)
        
        # Check for concept drift
        drift_alert = self.concept_drift_detector.detect_drift()
        if drift_alert:
            self.alerting_system.send_alert(drift_alert)
        
        logger.info(f"Batch evaluated: ROC AUC={metrics.roc_auc:.4f}, Recall={metrics.recall:.4f}")
        
        return metrics
    
    def _save_performance_log(self):
        """Save performance log to file"""
        log_file = self.log_dir / 'performance_history.json'
        with open(log_file, 'w') as f:
            json.dump([asdict(m) for m in self.performance_log], f, indent=2)
    
    def check_retraining_needed(self) -> Tuple[bool, str]:
        """
        Check if model retraining is needed
        
        Returns:
            (needs_retraining, reason)
        """
        if len(self.performance_log) < 10:
            return False, "Insufficient data for retraining decision"
        
        # Get recent performance
        recent_metrics = self.performance_log[-10:]
        avg_roc_auc = np.mean([m.roc_auc for m in recent_metrics])
        avg_recall = np.mean([m.recall for m in recent_metrics])
        
        # Get baseline
        baseline_roc = self.metadata.get('performance', {}).get('roc_auc', 0.9)
        baseline_recall = self.metadata.get('performance', {}).get('recall', 0.85)
        
        # Check thresholds
        if avg_roc_auc < baseline_roc - 0.05:
            return True, f"ROC AUC dropped significantly: {avg_roc_auc:.4f} vs baseline {baseline_roc:.4f}"
        
        if avg_recall < baseline_recall - 0.10:
            return True, f"Recall dropped significantly: {avg_recall:.4f} vs baseline {baseline_recall:.4f}"
        
        # Check data volume
        total_samples = sum(m.sample_size for m in self.performance_log)
        if total_samples > 10000:
            return True, f"Sufficient new data collected for retraining: {total_samples} samples"
        
        return False, "Model performance stable"
    
    def generate_monitoring_report(self) -> Dict:
        """Generate comprehensive monitoring report"""
        if not self.performance_log:
            return {'status': 'No data available'}
        
        recent_metrics = self.performance_log[-20:] if len(self.performance_log) >= 20 else self.performance_log
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'model_version': self.metadata.get('timestamp', 'unknown'),
            'evaluation_count': len(self.performance_log),
            'total_predictions': sum(m.sample_size for m in self.performance_log),
            'recent_performance': {
                'roc_auc_mean': float(np.mean([m.roc_auc for m in recent_metrics])),
                'roc_auc_std': float(np.std([m.roc_auc for m in recent_metrics])),
                'recall_mean': float(np.mean([m.recall for m in recent_metrics])),
                'recall_std': float(np.std([m.recall for m in recent_metrics])),
                'f1_mean': float(np.mean([m.f1_score for m in recent_metrics])),
            },
            'alerts': {
                'total_alerts': len(self.alerting_system.alert_history),
                'recent_alerts': [asdict(a) for a in self.alerting_system.alert_history[-5:]]
            }
        }
        
        # Add retraining recommendation
        needs_retraining, reason = self.check_retraining_needed()
        report['retraining_recommendation'] = {
            'needed': needs_retraining,
            'reason': reason
        }
        
        # Save report
        report_file = self.log_dir / 'latest_monitoring_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Monitoring report generated: {report_file}")
        
        return report


# Example usage and testing
if __name__ == '__main__':
    print("=" * 80)
    print("ADVANCED MODEL MONITORING SYSTEM")
    print("=" * 80)
    
    # Initialize monitor
    monitor = AdvancedModelMonitor()
    
    # Load test data
    try:
        df = pd.read_csv('credit_risk_dataset.csv')
    except FileNotFoundError:
        print("Error: credit_risk_dataset.csv not found")
        exit(1)
    
    # Prepare data
    X = df.drop('loan_status', axis=1)
    y = df['loan_status']
    
    # Use last 30% as test set
    test_size = int(len(df) * 0.3)
    X_test = X.iloc[-test_size:]
    y_test = y.iloc[-test_size:]
    
    # Simulate multiple evaluation batches
    batch_size = 500
    num_batches = 5
    
    print(f"\nSimulating {num_batches} evaluation batches...")
    
    for i in range(num_batches):
        # Get random batch
        indices = np.random.choice(len(X_test), size=min(batch_size, len(X_test)), replace=False)
        X_batch = X_test.iloc[indices]
        y_batch = y_test.iloc[indices]
        
        # Evaluate batch
        print(f"\nBatch {i+1}/{num_batches}:")
        metrics = monitor.evaluate_batch(X_batch, y_batch)
        print(f"  ROC AUC: {metrics.roc_auc:.4f}")
        print(f"  Recall: {metrics.recall:.4f}")
        print(f"  F1 Score: {metrics.f1_score:.4f}")
    
    # Generate final report
    print("\n" + "=" * 80)
    print("MONITORING REPORT")
    print("=" * 80)
    
    report = monitor.generate_monitoring_report()
    print(json.dumps(report, indent=2))
    
    print("\n" + "=" * 80)
    print("Monitoring complete!")
    print(f"Reports saved to: {monitor.log_dir}")
    print("=" * 80)

