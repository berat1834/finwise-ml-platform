"""Project-wide model artifact constants."""
import os

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PRODUCTION_MODEL_PATH = os.path.join(_BACKEND_DIR, "production_model.joblib")
PRODUCTION_META_PATH = os.path.join(_BACKEND_DIR, "production_model_meta.json")
PRODUCTION_THRESHOLD_PATH = os.path.join(_BACKEND_DIR, "threshold_config_final.pkl")

