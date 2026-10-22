# -*- coding: utf-8 -*-
"""
FinWise ML Platform — Development Server Launcher

This script ensures the backend starts correctly regardless of which
directory the process is launched from. It:
  1. Changes CWD to backend/ (so relative paths resolve correctly)
  2. Loads backend/.env with python-dotenv (if available)
  3. Imports and runs the Flask/Waitress app
"""
import os
import sys

# Always set CWD to the directory containing this script (backend/)
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_BACKEND_DIR)

# Ensure backend/ is on sys.path for imports
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Load .env from backend/ directory
_env_path = os.path.join(_BACKEND_DIR, ".env")
try:
    from dotenv import load_dotenv
    load_dotenv(_env_path, override=False)
except ImportError:
    # python-dotenv not installed — env vars must be set externally
    pass


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  KREDİ RİSK ANALİZİ SİSTEMİ — FinWise ML Platform")
    print("=" * 60)
    print(f"\n  Working directory : {os.getcwd()}")
    print(f"  Python            : {sys.executable}")
    print(f"  .env loaded       : {os.path.exists(_env_path)}")
    print()
    print("  Endpoints:")
    print("  - Web     : http://localhost:5001")
    print("  - Health  : http://localhost:5001/health")
    print("  - API     : POST http://localhost:5001/degerlendir")
    print("  - Login   : POST http://localhost:5001/auth/login")
    print("  - Swagger : http://localhost:5001/apidocs")
    print("\n  Ctrl+C ile durdurun\n")

    try:
        from app_v2_secure import create_app
        app = create_app()
    except ImportError as e:
        print(f"[ERROR] Failed to import app_v2_secure: {e}")
        sys.exit(1)

    # Use waitress if available (production-grade), else Flask dev server
    try:
        from waitress import serve
        print("[OK] Starting with Waitress WSGI server")
        serve(app, host='0.0.0.0', port=5001)
    except ImportError:
        print("[WARN] Waitress not installed, using Flask dev server")
        app.run(host='0.0.0.0', port=5001, debug=False, threaded=True, use_reloader=False)
