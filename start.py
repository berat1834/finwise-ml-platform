# -*- coding: utf-8 -*-
"""
Simple server runner - starts Flask in production mode with scoped session management
"""
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    print("\n" + "="*60)
    print("KREDİ RİSK ANALİZİ SİSTEMİ")
    print("="*60)
    print("\nSunucu başlatılıyor...")
    print("📱 Web: http://localhost:5000")
    print("📊 Health: http://localhost:5000/health")
    print("🔍 API: POST http://localhost:5000/degerlendir")
    print("💡 Explain: POST http://localhost:5000/explain")
    print("\nCtrl+C ile durdurun\n")
    
    from app import app
    # Initialize database with Flask app context management
    # This ensures session cleanup at end of each request
    try:
        from database_models import init_db_with_app
        init_db_with_app(app)
        print("✓ Database session management initialized")
    except ImportError:
        print("⚠ Warning: database_models not available, proceeding without scoped sessions")
    
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True, use_reloader=False)
