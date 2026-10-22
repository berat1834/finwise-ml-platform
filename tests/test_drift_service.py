import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "backend"))

try:
    from app.services.drift_service import calculate_psi, calculate_categorical_csi, DriftService
except ImportError:
    from backend.app.services.drift_service import calculate_psi, calculate_categorical_csi, DriftService  # type: ignore[import-not-found]


class TestDriftService:
    def test_psi_identical_distributions(self):
        """PSI between identical distributions should be approximately 0.0."""
        data = np.random.normal(loc=50, scale=10, size=1000)
        psi = calculate_psi(data, data)
        assert psi < 0.01

    def test_psi_shifted_distributions(self):
        """PSI between strongly shifted distributions should be elevated (> 0.25)."""
        base = np.random.normal(loc=30, scale=5, size=1000)
        shifted = np.random.normal(loc=55, scale=5, size=1000)
        psi = calculate_psi(base, shifted)
        assert psi > 0.25

    def test_csi_categorical(self):
        """CSI between categorical series should correctly detect distribution shift."""
        base = pd.Series(["RENT"] * 700 + ["OWN"] * 300)
        shifted = pd.Series(["RENT"] * 200 + ["OWN"] * 800)
        csi = calculate_categorical_csi(base, shifted)
        assert csi > 0.20

    def test_analyze_drift_structure(self, app):
        """Analyze drift should return a complete dictionary with overall status and features."""
        with app.app_context():
            result = DriftService.analyze_drift(sample_window=100)
            assert "overall_status" in result
            assert "overall_psi" in result
            assert "features" in result
            assert result["overall_status"] in ["STABLE", "MODERATE_DRIFT", "CRITICAL_DRIFT"]
            assert len(result["features"]) > 0
            assert "threshold_benchmarks" in result
