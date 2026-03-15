#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Multi-tenant Custom Model Training Pipeline
Her müşteri için özel model eğitimi ve versiyonlama
"""
import os
import json
import logging
import pickle
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import joblib

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import roc_auc_score, recall_score, precision_score, f1_score, confusion_matrix

logger = logging.getLogger(__name__)


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class ModelMetadata:
    """Model metadata ve versiyonlama"""
    model_id: str
    customer_id: str
    version: str
    created_at: datetime
    training_date: datetime
    data_shape: Tuple[int, int]
    feature_count: int
    
    # Performance metrics
    train_auc: float
    test_auc: float
    train_recall: float
    test_recall: float
    precision: float
    f1_score_val: float
    
    # Training details
    training_samples: int
    test_samples: int
    class_distribution: Dict
    feature_importance: Dict
    
    # Status
    is_production: bool = False
    is_validated: bool = False
    validation_date: datetime = None


@dataclass
class TrainingConfig:
    """Model eğitim konfigurasyonu"""
    customer_id: str
    model_type: str = "random_forest"
    test_size: float = 0.3
    random_state: int = 42
    n_estimators: int = 100
    max_depth: int = 15
    min_samples_split: int = 5
    class_weight: str = "balanced"
    target_column: str = "loan_status"
    
    # Validation
    min_auc_threshold: float = 0.85
    min_recall_threshold: float = 0.75
    max_train_test_auc_diff: float = 0.05  # Overfitting kontrolü
    
    # Fairness constraints
    enforce_fairness: bool = True
    target_disparate_impact: float = 0.80
    demographic_groups: Dict = None


# ============================================================
# MULTI-TENANT MODEL MANAGER
# ============================================================

class MultiTenantModelTrainer:
    """
    Multi-tenant ortamda müşteri-spesifik model eğitimi ve yönetimi
    """
    
    def __init__(self, models_dir: str = 'customer_models'):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.metadata_dir = self.models_dir / 'metadata'
        self.metadata_dir.mkdir(exist_ok=True)
    
    def train_customer_model(self, 
                            customer_id: str, 
                            data: pd.DataFrame, 
                            config: TrainingConfig) -> ModelMetadata:
        """
        Müşteri için özel model eğit
        """
        logger.info(f"Starting training for customer {customer_id}")
        
        # Data preparation
        X = data.drop(columns=[config.target_column])
        y = data[config.target_column]
        
        # Identify feature types
        numeric_features = X.select_dtypes(include=['int64', 'float64']).columns.tolist()
        categorical_features = X.select_dtypes(include=['object']).columns.tolist()
        
        # Feature preprocessing pipeline
        numeric_transformer = Pipeline(steps=[
            ('scaler', StandardScaler())
        ])
        
        categorical_transformer = Pipeline(steps=[
            ('onehot', OneHotEncoder(drop='first', sparse_output=False))
        ])
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_features),
                ('cat', categorical_transformer, categorical_features)
            ]
        )
        
        # Build full pipeline
        model_pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', RandomForestClassifier(
                n_estimators=config.n_estimators,
                max_depth=config.max_depth,
                min_samples_split=config.min_samples_split,
                class_weight=config.class_weight,
                random_state=config.random_state,
                n_jobs=-1
            ))
        ])
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=config.test_size,
            random_state=config.random_state,
            stratify=y
        )
        
        # Train
        logger.info(f"Training on {len(X_train)} samples")
        model_pipeline.fit(X_train, y_train)
        
        # Evaluate
        y_pred_train = model_pipeline.predict(X_train)
        y_pred_test = model_pipeline.predict(X_test)
        y_proba_train = model_pipeline.predict_proba(X_train)[:, 1]
        y_proba_test = model_pipeline.predict_proba(X_test)[:, 1]
        
        # Metrics
        train_auc = roc_auc_score(y_train, y_proba_train)
        test_auc = roc_auc_score(y_test, y_proba_test)
        
        # Validate thresholds
        if test_auc < config.min_auc_threshold:
            logger.warning(f"Model AUC {test_auc} below threshold {config.min_auc_threshold}")
        
        # Check for overfitting
        auc_diff = abs(train_auc - test_auc)
        if auc_diff > config.max_train_test_auc_diff:
            logger.warning(f"Possible overfitting: train AUC {train_auc} vs test AUC {test_auc}")
        
        # Feature importance
        feature_names = (
            numeric_features +
            self._get_onehot_features(X, categorical_features)
        )
        feature_importances = model_pipeline.named_steps['classifier'].feature_importances_
        
        feature_importance_dict = dict(zip(
            feature_names,
            feature_importances
        ))
        
        # Class distribution
        class_dist = {
            'class_0': int((y_train == 0).sum()),
            'class_1': int((y_train == 1).sum())
        }
        
        # Create metadata
        model_id = f"{customer_id}_v{self._get_next_version(customer_id)}"
        metadata = ModelMetadata(
            model_id=model_id,
            customer_id=customer_id,
            version=self._get_next_version(customer_id),
            created_at=datetime.now(timezone.utc),
            training_date=datetime.now(timezone.utc),
            data_shape=(len(X), len(X.columns)),
            feature_count=len(X.columns),
            train_auc=train_auc,
            test_auc=test_auc,
            train_recall=recall_score(y_train, y_pred_train),
            test_recall=recall_score(y_test, y_pred_test),
            precision=precision_score(y_test, y_pred_test),
            f1_score_val=f1_score(y_test, y_pred_test),
            training_samples=len(X_train),
            test_samples=len(X_test),
            class_distribution=class_dist,
            feature_importance=dict(sorted(
                feature_importance_dict.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10])  # Top 10 features
        )
        
        # Save model
        self._save_model(model_pipeline, metadata)
        
        logger.info(f"Model {model_id} trained successfully (AUC: {test_auc:.4f})")
        
        return metadata
    
    def _get_onehot_features(self, X: pd.DataFrame, categorical_features: List[str]) -> List[str]:
        """One-hot encoded özellik adlarını getir"""
        features = []
        for col in categorical_features:
            unique_vals = X[col].unique()
            for val in sorted(unique_vals)[1:]:  # drop_first=True
                features.append(f"{col}_{val}")
        return features
    
    def _get_next_version(self, customer_id: str) -> str:
        """Müşteri için sonraki version numarasını getir"""
        customer_dir = self.models_dir / customer_id
        if not customer_dir.exists():
            return "1.0.0"
        
        versions = []
        for file in customer_dir.glob("model_v*.joblib"):
            version = file.stem.replace("model_v", "")
            versions.append(version)
        
        if not versions:
            return "1.0.0"
        
        # Simple versioning: increment patch version
        latest = sorted(versions)[-1]
        parts = latest.split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        return '.'.join(parts)
    
    def _save_model(self, model_pipeline, metadata: ModelMetadata):
        """Model ve metadata'yı kaydet"""
        customer_dir = self.models_dir / metadata.customer_id
        customer_dir.mkdir(exist_ok=True)
        
        # Model
        model_path = customer_dir / f"model_v{metadata.version}.joblib"
        joblib.dump(model_pipeline, model_path)
        
        # Metadata
        metadata_path = self.metadata_dir / f"{metadata.model_id}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(asdict(metadata), f, default=str, indent=2)
        
        # Latest version symlink for production
        latest_path = customer_dir / "model_latest_staging.joblib"
        if latest_path.exists():
            latest_path.unlink()
        # Symlink requires elevated privileges on many Windows setups.
        # Use a real copy as a portable "latest" pointer.
        shutil.copy2(model_path, latest_path)
    
    def get_model(self, customer_id: str, version: str = None):
        """Müşteri modeli getir"""
        customer_dir = self.models_dir / customer_id
        
        if version == "latest" or version is None:
            model_path = customer_dir / "model_latest_staging.joblib"
        else:
            model_path = customer_dir / f"model_v{version}.joblib"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        return joblib.load(model_path)
    
    def get_metadata(self, customer_id: str, version: str = None) -> ModelMetadata:
        """Model metadata getir"""
        # Find latest
        files = list(self.metadata_dir.glob(f"{customer_id}_v*_metadata.json"))
        if not files:
            raise FileNotFoundError(f"No metadata found for {customer_id}")
        
        if version is None:
            # Latest
            metadata_file = sorted(files)[-1]
        else:
            metadata_file = self.metadata_dir / f"{customer_id}_v{version}_metadata.json"
        
        with open(metadata_file, 'r') as f:
            data = json.load(f)
        
        return ModelMetadata(**data)
    
    def promote_to_production(self, customer_id: str, version: str) -> bool:
        """Model'i üretim ortamına yükselt"""
        customer_dir = self.models_dir / customer_id
        
        # Load and validate
        metadata = self.get_metadata(customer_id, version)
        
        if metadata.test_auc < 0.85:
            logger.error(f"Cannot promote: AUC {metadata.test_auc} below 0.85")
            return False
        
        # Create production symlink
        prod_path = customer_dir / "model_latest_production.joblib"
        if prod_path.exists():
            prod_path.unlink()

        source_model_path = customer_dir / f"model_v{version}.joblib"
        shutil.copy2(source_model_path, prod_path)
        
        # Update metadata
        metadata.is_production = True
        metadata.validation_date = datetime.now(timezone.utc)
        
        metadata_path = self.metadata_dir / f"{customer_id}_v{version}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(asdict(metadata), f, default=str, indent=2)
        
        logger.info(f"Promoted {customer_id} v{version} to production")
        return True
    
    def get_model_history(self, customer_id: str) -> List[Dict]:
        """Müşteri model geçmişini getir"""
        files = sorted(self.metadata_dir.glob(f"{customer_id}_v*_metadata.json"))
        
        history = []
        for file in files:
            with open(file, 'r') as f:
                metadata = json.load(f)
                history.append({
                    'version': metadata['version'],
                    'created_at': metadata['created_at'],
                    'test_auc': metadata['test_auc'],
                    'is_production': metadata['is_production'],
                    'training_samples': metadata['training_samples']
                })
        
        return sorted(history, key=lambda x: x['created_at'], reverse=True)
    
    def list_all_customers(self) -> List[str]:
        """Tüm müşterileri listele"""
        return [d.name for d in self.models_dir.iterdir() if d.is_dir()]
    
    def compare_models(self, customer_id: str, version1: str, version2: str) -> Dict:
        """İki model versiyonunu karşılaştır"""
        m1 = self.get_metadata(customer_id, version1)
        m2 = self.get_metadata(customer_id, version2)
        
        return {
            'version1': version1,
            'version2': version2,
            'auc_improvement': m2.test_auc - m1.test_auc,
            'recall_change': m2.test_recall - m1.test_recall,
            'precision_change': m2.precision - m1.precision,
            'training_samples_v1': m1.training_samples,
            'training_samples_v2': m2.training_samples,
            'feature_count_v1': m1.feature_count,
            'feature_count_v2': m2.feature_count
        }


# ============================================================
# MODEL REGISTRY
# ============================================================

class ModelRegistry:
    """Central model registry for all customers"""
    
    def __init__(self, registry_path: str = 'model_registry.json'):
        self.registry_path = Path(registry_path)
        self._ensure_registry()
    
    def _ensure_registry(self):
        """Registry dosyası oluştur"""
        if not self.registry_path.exists():
            with open(self.registry_path, 'w') as f:
                json.dump({
                    'models': {},
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
    
    def register_model(self, customer_id: str, version: str, model_path: str, 
                      is_production: bool = False):
        """Modeli registry'ye kaydet"""
        with open(self.registry_path, 'r') as f:
            registry = json.load(f)
        
        model_key = f"{customer_id}_v{version}"
        registry['models'][model_key] = {
            'customer_id': customer_id,
            'version': version,
            'model_path': model_path,
            'is_production': is_production,
            'registered_at': datetime.now(timezone.utc).isoformat()
        }
        registry['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        with open(self.registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
    
    def get_production_model(self, customer_id: str) -> Dict:
        """Müşteri production modelini getir"""
        with open(self.registry_path, 'r') as f:
            registry = json.load(f)
        
        for model_key, model_info in registry['models'].items():
            if model_info['customer_id'] == customer_id and model_info['is_production']:
                return model_info
        
        return None
    
    def get_all_models(self, customer_id: str) -> List[Dict]:
        """Müşteri tüm modellerini getir"""
        with open(self.registry_path, 'r') as f:
            registry = json.load(f)
        
        models = [
            model_info for model_info in registry['models'].values()
            if model_info['customer_id'] == customer_id
        ]
        
        return sorted(models, key=lambda x: x['registered_at'], reverse=True)


if __name__ == '__main__':
    # Test
    trainer = MultiTenantModelTrainer()
    
    # Dummy data
    np.random.seed(42)
    test_data = pd.DataFrame({
        'person_age': np.random.randint(20, 80, 1000),
        'person_income': np.random.randint(20000, 200000, 1000),
        'loan_amnt': np.random.randint(5000, 50000, 1000),
        'loan_int_rate': np.random.uniform(5, 15, 1000),
        'cb_person_cred_hist_length': np.random.randint(1, 30, 1000),
        'person_home_ownership': np.random.choice(['RENT', 'OWN', 'MORTGAGE'], 1000),
        'loan_intent': np.random.choice(['PERSONAL', 'EDUCATION', 'MEDICAL'], 1000),
        'loan_grade': np.random.choice(['A', 'B', 'C', 'D'], 1000),
        'loan_status': np.random.randint(0, 2, 1000)
    })
    
    config = TrainingConfig(customer_id='CUST-001')
    metadata = trainer.train_customer_model('CUST-001', test_data, config)
    
    print(f"Model trained: {metadata.model_id}")
    print(f"Test AUC: {metadata.test_auc:.4f}")
    print(f"Feature importance: {list(metadata.feature_importance.keys())[:3]}")
    
    # Promote to production
    trainer.promote_to_production('CUST-001', metadata.version)
    print(f"Promoted to production")
    
    # History
    history = trainer.get_model_history('CUST-001')
    print(f"Model history: {history}")
