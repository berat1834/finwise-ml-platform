"""
Test Suite for Model Predictions and ML Logic
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import json


class TestModelPredictions:
    """Test model prediction functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Load model before each test"""
        model_path = Path(__file__).parent.parent / 'production_model.joblib'
        meta_path = Path(__file__).parent.parent / 'production_model_meta.json'
        
        if not model_path.exists():
            pytest.skip("Model not trained yet")
        
        self.model = joblib.load(model_path)
        with open(meta_path, 'r') as f:
            self.meta = json.load(f)
    
    def test_model_loaded(self):
        """Test model loads successfully"""
        assert self.model is not None
        assert 'threshold' in self.meta
        assert 'metrics' in self.meta
    
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
        
        proba = self.model.predict_proba(sample_data)
        assert proba.shape == (1, 2)
        assert 0 <= proba[0, 1] <= 1
    
    def test_low_risk_profile(self):
        """Test low risk profile gets approved"""
        low_risk = pd.DataFrame([{
            'person_age': 35,
            'person_income': 80000.0,
            'person_emp_length': 10,
            'loan_amnt': 15000.0,
            'loan_int_rate': 6.0,
            'loan_percent_income': 0.15,
            'cb_person_cred_hist_length': 15,
            'person_home_ownership': 'OWN',
            'loan_intent': 'PERSONAL',
            'loan_grade': 'A',
            'cb_person_default_on_file': 'N'
        }])
        
        proba = self.model.predict_proba(low_risk)[0, 1]
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
        
        proba = self.model.predict_proba(high_risk)[0, 1]
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
        
        # Should not crash
        proba = self.model.predict_proba(edge_case)
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
        
        # Test all combinations
        for home in home_values:
            for intent in intent_values:
                for grade in grade_values:
                    for default in default_values:
                        data = {**base_data,
                               'person_home_ownership': home,
                               'loan_intent': intent,
                               'loan_grade': grade,
                               'cb_person_default_on_file': default}
                        df = pd.DataFrame([data])
                        proba = self.model.predict_proba(df)
                        assert proba.shape == (1, 2)


class TestModelMetadata:
    """Test model metadata and configuration"""
    
    def test_metadata_exists(self):
        """Test metadata file exists"""
        meta_path = Path(__file__).parent.parent / 'production_model_meta.json'
        assert meta_path.exists()
    
    def test_metadata_structure(self):
        """Test metadata has required fields"""
        meta_path = Path(__file__).parent.parent / 'production_model_meta.json'
        
        if not meta_path.exists():
            pytest.skip("Model not trained yet")
        
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        
        required_fields = ['threshold', 'metrics', 'model', 'version']
        for field in required_fields:
            assert field in meta, f"Missing field: {field}"
    
    def test_threshold_range(self):
        """Test threshold is in valid range"""
        meta_path = Path(__file__).parent.parent / 'production_model_meta.json'
        
        if not meta_path.exists():
            pytest.skip("Model not trained yet")
        
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        
        threshold = meta['threshold']
        assert 0 < threshold < 1, "Threshold must be between 0 and 1"

