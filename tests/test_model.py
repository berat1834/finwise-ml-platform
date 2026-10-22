"""
Test Suite for Model Predictions and ML Logic
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import json
import sys

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "backend"))

from app.utils.data_utils import engineer_features


class TestModelPredictions:
    """Test model prediction functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Load model before each test"""
        model_path = Path(__file__).parent.parent / 'backend' / 'production_model.joblib'
        if not model_path.exists():
            model_path = Path(__file__).parent.parent / 'production_model.joblib'
        meta_path = Path(__file__).parent.parent / 'backend' / 'production_model_meta.json'
        if not meta_path.exists():
            meta_path = Path(__file__).parent.parent / 'production_model_meta.json'
        
        if not model_path.exists():
            pytest.skip("Model not trained yet")
        
        self.model = joblib.load(model_path)
        with open(meta_path, 'r') as f:
            self.meta = json.load(f)

    def _prep(self, df):
        return engineer_features(df)
    
    def test_model_loaded(self):
        """Test model loads successfully"""
        assert self.model is not None
        assert 'threshold' in self.meta
        assert 'model' in self.meta
    
    def test_prediction_output_shape(self):
        """Test prediction returns correct shape"""
        sample_data = pd.DataFrame([{
            'person_age': 30,
            'person_income': 50000.0,
            'person_emp_length': 5,
            'loan_amnt': 10000.0,
            'loan_int_rate': 8.5,
            'loan_percent_income': 0.2,
            'cb_person_cred_hist_length': 10,
            'person_home_ownership': 'RENT',
            'loan_intent': 'PERSONAL',
            'loan_grade': 'B',
            'cb_person_default_on_file': 'N'
        }])
        sample_data = self._prep(sample_data)
        
        proba = np.array(self.model.predict_proba(sample_data) if hasattr(self.model, 'predict_proba') else [[1-p, p] for p in self.model.predict(sample_data)])
        assert proba.shape == (1, 2)
        assert 0 <= proba[0, 1] <= 1
    
    def test_low_risk_profile(self):
        """Test low risk profile gets approved"""
        low_risk = pd.DataFrame([{
            'person_age': 40,
            'person_income': 120000.0,
            'person_emp_length': 12,
            'loan_amnt': 10000.0,
            'loan_int_rate': 5.5,
            'loan_percent_income': 0.08,
            'cb_person_cred_hist_length': 15,
            'person_home_ownership': 'OWN',
            'loan_intent': 'PERSONAL',
            'loan_grade': 'A',
            'cb_person_default_on_file': 'N'
        }])
        low_risk = self._prep(low_risk)
        
        proba = ((self.model.predict_proba(low_risk) if hasattr(self.model, 'predict_proba') else [[1-p, p] for p in self.model.predict(low_risk)])[0, 1] if hasattr(self.model, 'predict_proba') else self.model.predict(low_risk)[0])
        threshold = self.meta['threshold']
        
        # Low risk should be below threshold (approved)
        assert proba < threshold
    
    def test_high_risk_profile(self):
        """Test high risk profile gets rejected"""
        high_risk = pd.DataFrame([{
            'person_age': 22,
            'person_income': 25000.0,
            'person_emp_length': 1,
            'loan_amnt': 35000.0,
            'loan_int_rate': 16.0,
            'loan_percent_income': 0.70,
            'cb_person_cred_hist_length': 2,
            'person_home_ownership': 'RENT',
            'loan_intent': 'DEBTCONSOLIDATION',
            'loan_grade': 'F',
            'cb_person_default_on_file': 'Y'
        }])
        high_risk = self._prep(high_risk)
        
        proba = ((self.model.predict_proba(high_risk) if hasattr(self.model, 'predict_proba') else [[1-p, p] for p in self.model.predict(high_risk)])[0, 1] if hasattr(self.model, 'predict_proba') else self.model.predict(high_risk)[0])
        threshold = self.meta['threshold']
        
        # High risk should be above threshold (rejected)
        assert proba > threshold
    
    def test_edge_case_zero_income(self):
        """Test handling of edge case: zero income"""
        edge_case = pd.DataFrame([{
            'person_age': 30,
            'person_income': 0.0,
            'person_emp_length': 0,
            'loan_amnt': 10000.0,
            'loan_int_rate': 10.0,
            'loan_percent_income': 0.0,
            'cb_person_cred_hist_length': 5,
            'person_home_ownership': 'RENT',
            'loan_intent': 'PERSONAL',
            'loan_grade': 'D',
            'cb_person_default_on_file': 'N'
        }])
        edge_case = self._prep(edge_case)
        
        # Should not crash
        proba = (self.model.predict_proba(edge_case) if hasattr(self.model, 'predict_proba') else [[1-p, p] for p in self.model.predict(edge_case)])
        assert proba is not None
    
    def test_categorical_encoding(self):
        """Test all categorical values are handled"""
        home_values = ['RENT', 'OWN', 'MORTGAGE', 'OTHER']
        intent_values = ['PERSONAL', 'EDUCATION', 'MEDICAL', 'VENTURE', 
                        'HOMEIMPROVEMENT', 'DEBTCONSOLIDATION']
        grade_values = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        default_values = ['Y', 'N']
        
        base_data = {
            'person_age': 30,
            'person_income': 50000.0,
            'person_emp_length': 5,
            'loan_amnt': 10000.0,
            'loan_int_rate': 8.5,
            'loan_percent_income': 0.2,
            'cb_person_cred_hist_length': 10
        }
        
        # Test sample of combinations to avoid huge iterations
        for home in home_values[:2]:
            for intent in intent_values[:2]:
                for grade in grade_values[:2]:
                    for default in default_values:
                        data = {**base_data,
                               'person_home_ownership': home,
                               'loan_intent': intent,
                               'loan_grade': grade,
                               'cb_person_default_on_file': default}
                        df = self._prep(pd.DataFrame([data]))
                        proba = (self.model.predict_proba(df) if hasattr(self.model, 'predict_proba') else [[1-p, p] for p in self.model.predict(df)])
                        assert proba is not None


class TestModelMetadata:
    """Test model metadata and configuration"""
    
    def _get_meta_path(self):
        p = Path(__file__).parent.parent / 'backend' / 'production_model_meta.json'
        if p.exists():
            return p
        return Path(__file__).parent.parent / 'production_model_meta.json'

    def test_metadata_exists(self):
        """Test metadata file exists"""
        meta_path = self._get_meta_path()
        assert meta_path.exists()
    
    def test_metadata_structure(self):
        """Test metadata has required fields"""
        meta_path = self._get_meta_path()
        
        if not meta_path.exists():
            pytest.skip("Model not trained yet")
        
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        
        required_fields = ['threshold', 'model']
        for field in required_fields:
            assert field in meta, f"Missing field: {field}"
    
    def test_threshold_range(self):
        """Test threshold is in valid range"""
        meta_path = self._get_meta_path()
        
        if not meta_path.exists():
            pytest.skip("Model not trained yet")
        
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        
        threshold = meta['threshold']
        assert 0 < threshold < 1, "Threshold must be between 0 and 1"
