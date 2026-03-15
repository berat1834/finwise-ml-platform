# -*- coding: utf-8 -*-
"""
Production server runner using Waitress with scoped session management
"""
import os
import sys

# Ensure we're in the right directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

from waitress import serve
from app import app

if __name__ == '__main__':
    print("\n" + "="*60)
    print("KREDİ RİSK ANALİZİ - PRODUCTION SERVER")
    print("="*60)
    print("\nStarting Waitress server...")
    print("📱 Web UI: http://localhost:5000")
    print("📊 Health: http://localhost:5000/health")
    print("🔍 API: POST http://localhost:5000/degerlendir")
    print("💡 Explain: POST http://localhost:5000/explain")
    print("\nPress Ctrl+C to stop\n")
    print("="*60 + "\n")
    
    # Initialize database with Flask app context management
    # This ensures session cleanup at end of each request
    try:
        from database_models import init_db_with_app
        init_db_with_app(app)
        print("✓ Database session management initialized\n")
    except ImportError:
        print("⚠ Warning: database_models not available, proceeding without scoped sessions\n")
    
    serve(app, host='0.0.0.0', port=5000, threads=4)
