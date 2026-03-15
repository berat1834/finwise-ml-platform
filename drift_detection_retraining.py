#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Otomatik Data Drift Detection ve Model Retraining Pipeline
Model 6-12 ay sonra eski kalmasını önler
"""
import os
import json
import logging
import pickle
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, List
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from scipy.stats import ks_2samp, chi2_contingency
from pathlib import Path
import joblib

logger = logging.getLogger(__name__)


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class DriftMetrics:
    """Data drift metrikleri"""
    check_date: datetime
    customer_id: str
    feature_name: str
    drift_detected: bool
    drift_score: float  # 0-1, 1 = full drift
    test_statistic: float
    p_value: float
    feature_type: str  # 'numeric' or 'categorical'
    threshold: float = 0.05
    severity: str = 'none'  # none, low, medium, high


@dataclass
class DriftReport:
    """Aylık drift raporu"""
    report_id: str
    customer_id: str
    month: str
    total_features_checked: int
    features_with_drift: int
    drift_percentage: float
    overall_psi: float  # Population Stability Index
    retraining_triggered: bool
    retraining_reason: str = None
    generated_at: datetime = None


@dataclass
class RetrainingJob:
    """Retraining iş kaydı"""
    job_id: str
    customer_id: str
    triggered_by: str  # 'drift', 'performance', 'scheduled'
    start_time: datetime
    end_time: datetime = None
    status: str = 'pending'  # pending, running, completed, failed
    new_model_version: str = None
    improvement_metrics: Dict = None
    error_message: str = None


# ============================================================
# DATA DRIFT DETECTOR
# ============================================================

class DataDriftDetector:
    """
    Production verisi vs training verisi arasındaki drift'i tespit eder
    """
    
    def __init__(self, db_path: str = 'drift_detection.db'):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Drift detection database"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drift_metrics (
                metric_id TEXT PRIMARY KEY,
                check_date TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                drift_detected BOOLEAN NOT NULL,
                drift_score REAL NOT NULL,
                test_statistic REAL NOT NULL,
                p_value REAL NOT NULL,
                feature_type TEXT NOT NULL,
                severity TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drift_reports (
                report_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                month TEXT NOT NULL,
                total_features_checked INTEGER NOT NULL,
                features_with_drift INTEGER NOT NULL,
                drift_percentage REAL NOT NULL,
                overall_psi REAL NOT NULL,
                retraining_triggered BOOLEAN NOT NULL,
                retraining_reason TEXT,
                generated_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS retraining_jobs (
                job_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                triggered_by TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL,
                new_model_version TEXT,
                improvement_metrics TEXT,
                error_message TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def detect_drift(self, 
                    customer_id: str,
                    feature_name: str,
                    train_data: pd.Series,
                    prod_data: pd.Series,
                    threshold: float = 0.05) -> DriftMetrics:
        """
        Tek özellik için drift tespit et
        
        Numeric features: Kolmogorov-Smirnov test
        Categorical features: Chi-square test
        """
        
        if pd.api.types.is_numeric_dtype(train_data):
            # Numeric drift
            test_stat, p_value = ks_2samp(train_data.dropna(), prod_data.dropna())
            feature_type = 'numeric'
            
            # Drift score (0-1)
            drift_score = min(1.0, test_stat)
            
        else:
            # Categorical drift - Chi-square
            train_counts = train_data.value_counts()
            prod_counts = prod_data.value_counts()
            
            # Make sure we have same categories
            all_categories = set(train_counts.index) | set(prod_counts.index)
            
            train_dist = [train_counts.get(cat, 0) for cat in all_categories]
            prod_dist = [prod_counts.get(cat, 0) for cat in all_categories]
            
            # Chi-square test
            chi2, p_value, dof, expected = chi2_contingency([train_dist, prod_dist])
            test_stat = chi2
            feature_type = 'categorical'
            
            # Drift score
            drift_score = min(1.0, chi2 / (len(all_categories) + 1))
        
        # Determine severity
        if p_value < threshold:
            drift_detected = True
            if drift_score > 0.7:
                severity = 'high'
            elif drift_score > 0.4:
                severity = 'medium'
            else:
                severity = 'low'
        else:
            drift_detected = False
            severity = 'none'
        
        metric = DriftMetrics(
            check_date=datetime.now(timezone.utc),
            customer_id=customer_id,
            feature_name=feature_name,
            drift_detected=drift_detected,
            drift_score=drift_score,
            test_statistic=test_stat,
            p_value=p_value,
            feature_type=feature_type,
            threshold=threshold,
            severity=severity
        )
        
        self._save_metric(metric)
        
        if drift_detected:
            logger.warning(f"DRIFT DETECTED: {customer_id}/{feature_name} (score: {drift_score:.3f})")
        
        return metric
    
    def check_psi(self, 
                 customer_id: str,
                 train_data: pd.DataFrame,
                 prod_data: pd.DataFrame) -> Tuple[float, List[str]]:
        """
        Population Stability Index hesapla
        PSI > 0.25: significant drift
        PSI > 0.1: small drift
        
        Returns: (overall_psi, drifted_features)
        """
        psi_scores = {}
        drifted_features = []
        
        for column in train_data.columns:
            if column not in prod_data.columns:
                continue
            
            train_col = train_data[column].dropna()
            prod_col = prod_data[column].dropna()
            
            if len(train_col) == 0 or len(prod_col) == 0:
                continue
            
            if pd.api.types.is_numeric_dtype(train_col):
                # Numeric PSI using quantile binning
                n_bins = min(10, len(train_col) // 100)
                if n_bins < 2:
                    continue
                
                train_binned = pd.qcut(train_col, q=n_bins, duplicates='drop')
                prod_binned = pd.cut(prod_col, bins=pd.qcut(train_col, q=n_bins, duplicates='drop', retbins=True)[1])
                
                train_dist = train_binned.value_counts(normalize=True).sort_index()
                prod_dist = prod_binned.value_counts(normalize=True).sort_index()
            else:
                # Categorical PSI
                train_dist = train_col.value_counts(normalize=True)
                prod_dist = prod_col.value_counts(normalize=True)
            
            # Align distributions
            all_categories = set(train_dist.index) | set(prod_dist.index)
            
            train_dist_aligned = pd.Series(
                [train_dist.get(cat, 0.0001) for cat in all_categories],
                index=all_categories
            )
            prod_dist_aligned = pd.Series(
                [prod_dist.get(cat, 0.0001) for cat in all_categories],
                index=all_categories
            )
            
            # PSI = sum((prod% - train%) * ln(prod% / train%))
            psi = np.sum(
                (prod_dist_aligned - train_dist_aligned) * 
                np.log(prod_dist_aligned / train_dist_aligned)
            )
            
            psi_scores[column] = psi
            
            if psi > 0.1:  # Drift threshold
                drifted_features.append(column)
        
        overall_psi = np.mean(list(psi_scores.values())) if psi_scores else 0
        
        return overall_psi, drifted_features
    
    def _save_metric(self, metric: DriftMetrics):
        """Metriği database'e kaydet"""
        import sqlite3
        import uuid
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metric_id = f"DRIFT-{uuid.uuid4().hex[:8]}"
        
        cursor.execute('''
            INSERT INTO drift_metrics
            (metric_id, check_date, customer_id, feature_name, drift_detected, 
             drift_score, test_statistic, p_value, feature_type, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metric_id, metric.check_date.isoformat(), metric.customer_id,
            metric.feature_name, metric.drift_detected, metric.drift_score,
            metric.test_statistic, metric.p_value, metric.feature_type, metric.severity
        ))
        
        conn.commit()
        conn.close()
    
    def generate_drift_report(self, 
                             customer_id: str,
                             train_data: pd.DataFrame,
                             prod_data: pd.DataFrame,
                             month: str = None) -> DriftReport:
        """Aylık drift raporu oluştur"""
        if not month:
            now = datetime.now()
            month = f"{now.year}-{now.month:02d}"
        
        # PSI hesapla
        overall_psi, drifted_features = self.check_psi(customer_id, train_data, prod_data)
        
        total_features = len(train_data.columns)
        features_with_drift = len(drifted_features)
        drift_percentage = (features_with_drift / total_features * 100) if total_features > 0 else 0
        
        # Retraining trigger
        retraining_triggered = False
        retraining_reason = None
        
        if overall_psi > 0.25:
            retraining_triggered = True
            retraining_reason = f"High PSI ({overall_psi:.3f}) > 0.25"
        elif drift_percentage > 30:
            retraining_triggered = True
            retraining_reason = f"30%+ features with drift ({features_with_drift}/{total_features})"
        
        report_id = f"DRIFT-REPORT-{customer_id}-{month}"
        
        report = DriftReport(
            report_id=report_id,
            customer_id=customer_id,
            month=month,
            total_features_checked=total_features,
            features_with_drift=features_with_drift,
            drift_percentage=drift_percentage,
            overall_psi=overall_psi,
            retraining_triggered=retraining_triggered,
            retraining_reason=retraining_reason,
            generated_at=datetime.now(timezone.utc)
        )
        
        self._save_report(report)
        
        return report
    
    def _save_report(self, report: DriftReport):
        """Raporu database'e kaydet"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO drift_reports
            (report_id, customer_id, month, total_features_checked, features_with_drift,
             drift_percentage, overall_psi, retraining_triggered, retraining_reason, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report.report_id, report.customer_id, report.month,
            report.total_features_checked, report.features_with_drift,
            report.drift_percentage, report.overall_psi,
            report.retraining_triggered, report.retraining_reason,
            report.generated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_drift_status(self, customer_id: str) -> Dict:
        """Müşteri drift durumunu getir"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Latest report
        cursor.execute('''
            SELECT overall_psi, features_with_drift, total_features_checked,
                   retraining_triggered, generated_at
            FROM drift_reports 
            WHERE customer_id = ? 
            ORDER BY month DESC LIMIT 1
        ''', (customer_id,))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {'status': 'No data available'}
        
        psi, drift_features, total_features, retrain, date = result
        
        # Recent high-severity drifts
        cursor.execute('''
            SELECT feature_name, drift_score, severity 
            FROM drift_metrics 
            WHERE customer_id = ? AND severity != 'none'
            ORDER BY check_date DESC LIMIT 10
        ''', (customer_id,))
        
        drifts = cursor.fetchall()
        conn.close()
        
        return {
            'overall_psi': psi,
            'features_with_drift': drift_features,
            'total_features': total_features,
            'drift_percentage': f"{drift_features/total_features*100:.1f}%",
            'retraining_triggered': retrain,
            'last_check': date,
            'high_severity_drifts': [
                {'feature': d[0], 'score': d[1], 'severity': d[2]} 
                for d in drifts
            ]
        }


# ============================================================
# AUTO RETRAINING SCHEDULER
# ============================================================

class AutoRetrainingScheduler:
    """
    Otomatik model retraining'i yönet
    """
    
    def __init__(self, db_path: str = 'drift_detection.db'):
        self.db_path = db_path
        self.drift_detector = DataDriftDetector(db_path)
    
    def trigger_retraining(self, 
                          customer_id: str,
                          reason: str,
                          training_func) -> RetrainingJob:
        """
        Retraining job'ı tetikle
        
        Args:
            customer_id: Müşteri ID
            reason: Tetikle nedeni ('drift', 'performance', 'scheduled')
            training_func: Eğitim fonksiyonu (customer_id, job_id) -> new_version
        """
        import sqlite3
        import uuid
        
        job_id = f"RETRAIN-{uuid.uuid4().hex[:8]}"
        
        job = RetrainingJob(
            job_id=job_id,
            customer_id=customer_id,
            triggered_by=reason,
            start_time=datetime.now(timezone.utc),
            status='running'
        )
        
        self._save_job(job)
        
        try:
            logger.info(f"Starting retraining job {job_id} for {customer_id}")
            
            # Run training
            new_version = training_func(customer_id, job_id)
            
            # Update job
            job.end_time = datetime.now(timezone.utc)
            job.status = 'completed'
            job.new_model_version = new_version
            job.improvement_metrics = {
                'reason': reason,
                'duration_seconds': (job.end_time - job.start_time).total_seconds()
            }
            
            logger.info(f"Retraining job {job_id} completed with model version {new_version}")
            
        except Exception as e:
            job.end_time = datetime.now(timezone.utc)
            job.status = 'failed'
            job.error_message = str(e)
            logger.error(f"Retraining job {job_id} failed: {e}")
        
        self._save_job(job)
        return job
    
    def _save_job(self, job: RetrainingJob):
        """Retraining job'ı database'e kaydet"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO retraining_jobs
            (job_id, customer_id, triggered_by, start_time, end_time, status,
             new_model_version, improvement_metrics, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job.job_id, job.customer_id, job.triggered_by, job.start_time.isoformat(),
            job.end_time.isoformat() if job.end_time else None, job.status,
            job.new_model_version,
            json.dumps(job.improvement_metrics) if job.improvement_metrics else None,
            job.error_message
        ))
        
        conn.commit()
        conn.close()
    
    def get_retraining_history(self, customer_id: str, limit: int = 10) -> List[Dict]:
        """Müşteri retraining geçmişini getir"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT job_id, triggered_by, start_time, end_time, status, new_model_version
            FROM retraining_jobs 
            WHERE customer_id = ? 
            ORDER BY start_time DESC 
            LIMIT ?
        ''', (customer_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'job_id': r[0],
                'reason': r[1],
                'start_time': r[2],
                'end_time': r[3],
                'status': r[4],
                'new_version': r[5]
            } for r in results
        ]
    
    def schedule_periodic_check(self, 
                               customer_id: str,
                               interval_days: int = 30):
        """
        Periyodik drift kontrolü zamanla
        Product'da cronjob olarak çalıştırılır
        """
        logger.info(f"Scheduled drift check for {customer_id} every {interval_days} days")
        # Product'da: APScheduler veya Celery ile yapılır


if __name__ == '__main__':
    # Test
    detector = DataDriftDetector()
    
    # Dummy data
    np.random.seed(42)
    train_data = pd.DataFrame({
        'age': np.random.normal(40, 15, 5000),
        'income': np.random.normal(50000, 20000, 5000),
        'credit_score': np.random.uniform(300, 850, 5000),
        'home_ownership': np.random.choice(['RENT', 'OWN', 'MORTGAGE'], 5000)
    })
    
    # Prod data with drift
    prod_data = pd.DataFrame({
        'age': np.random.normal(35, 15, 5000),  # Younger customers
        'income': np.random.normal(45000, 20000, 5000),  # Lower income
        'credit_score': np.random.uniform(300, 850, 5000),
        'home_ownership': np.random.choice(['RENT', 'OWN'], 5000, p=[0.7, 0.3])  # More rent
    })
    
    # Check drift
    psi, drift_features = detector.check_psi('CUST-001', train_data, prod_data)
    print(f"PSI Score: {psi:.3f}")
    print(f"Drifted Features: {drift_features}")
    
    # Generate report
    report = detector.generate_drift_report('CUST-001', train_data, prod_data)
    print(f"Retraining Triggered: {report.retraining_triggered}")
    print(f"Reason: {report.retraining_reason}")
    
    # Auto retraining
    scheduler = AutoRetrainingScheduler()
    
    def dummy_training_func(customer_id, job_id):
        # Simulate training
        import time
        time.sleep(2)
        return "1.1.0"
    
    job = scheduler.trigger_retraining('CUST-001', 'drift', dummy_training_func)
    print(f"Training Job: {job.job_id} -> {job.status}")
    print(f"New Model Version: {job.new_model_version}")
