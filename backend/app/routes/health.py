from flask import Blueprint, jsonify
from datetime import datetime
import time

health_bp = Blueprint('health_bp', __name__)
APP_START_TS = time.time()

@health_bp.route('/health', methods=['GET'])
def health():
    """Simple health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": round(time.time() - APP_START_TS, 2)
    }), 200
