"""
SQLite → PostgreSQL Migration Script
=====================================
Mevcut SQLite veritabanını PostgreSQL'e taşır.
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
from datetime import datetime

# Database bağlantı bilgileri
SQLITE_DB = 'credit_risk.db'
POSTGRES_CONFIG = {
    'host': '127.0.0.1',  # IPv4 kullan
    'port': 5432,
    'database': 'finwise_production',
    'user': 'postgres',
    'password': 'postgres123'
}

def test_postgres_connection():
    """PostgreSQL bağlantısını test et."""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✓ PostgreSQL bağlantısı başarılı!")
        print(f"  Versiyon: {version[0][:50]}...")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"✗ PostgreSQL bağlantı hatası: {e}")
        return False

def get_sqlite_data(table_name):
    """SQLite'tan veri çek."""
    if not os.path.exists(SQLITE_DB):
        print(f"⚠ {SQLITE_DB} bulunamadı, boş veri döndürülüyor")
        return []
    
    try:
        conn = sqlite3.connect(SQLITE_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            print(f"⚠ SQLite'ta '{table_name}' tablosu yok")
            conn.close()
            return []
        
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        print(f"✓ SQLite'tan {len(rows)} kayıt çekildi ({table_name})")
        return rows
    except Exception as e:
        print(f"✗ SQLite okuma hatası ({table_name}): {e}")
        return []

def migrate_applications():
    """Applications tablosunu migrate et."""
    print("\n[1/5] Applications tablosu migrate ediliyor...")
    
    rows = get_sqlite_data('applications')
    if not rows:
        print("  → Veri yok, atlanıyor")
        return
    
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        # Mevcut kayıtları temizle (test için)
        cursor.execute("TRUNCATE TABLE applications CASCADE")
        
        # Veriyi insert et
        for row in rows:
            cursor.execute("""
                INSERT INTO applications (
                    application_id, customer_id, created_at,
                    person_age, person_income, person_emp_length, person_home_ownership,
                    loan_amnt, loan_intent, loan_grade, loan_int_rate, loan_percent_income,
                    cb_person_cred_hist_length, cb_person_default_on_file,
                    prediction, probability, model_version,
                    decision, decision_reason, manual_override, override_reason,
                    processing_time_ms, api_version
                ) VALUES (
                    %(application_id)s, %(customer_id)s, %(created_at)s,
                    %(person_age)s, %(person_income)s, %(person_emp_length)s, %(person_home_ownership)s,
                    %(loan_amnt)s, %(loan_intent)s, %(loan_grade)s, %(loan_int_rate)s, %(loan_percent_income)s,
                    %(cb_person_cred_hist_length)s, %(cb_person_default_on_file)s,
                    %(prediction)s, %(probability)s, %(model_version)s,
                    %(decision)s, %(decision_reason)s, %(manual_override)s, %(override_reason)s,
                    %(processing_time_ms)s, %(api_version)s
                )
            """, row)
        
        conn.commit()
        print(f"  ✓ {len(rows)} kayıt migrate edildi")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"  ✗ Migration hatası: {e}")

def migrate_users():
    """Users tablosunu migrate et."""
    print("\n[2/5] Users tablosu migrate ediliyor...")
    
    rows = get_sqlite_data('users')
    if not rows:
        print("  → Veri yok (varsayılan admin kullanıcısı zaten mevcut)")
        return
    
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        for row in rows:
            cursor.execute("""
                INSERT INTO users (username, password_hash, email, role, created_at, last_login, is_active)
                VALUES (%(username)s, %(password_hash)s, %(email)s, %(role)s, %(created_at)s, %(last_login)s, %(is_active)s)
                ON CONFLICT (username) DO NOTHING
            """, row)
        
        conn.commit()
        print(f"  ✓ {len(rows)} kullanıcı migrate edildi")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"  ✗ Migration hatası: {e}")

def migrate_decisions():
    """Decisions tablosunu migrate et."""
    print("\n[3/5] Decisions tablosu migrate ediliyor...")
    
    rows = get_sqlite_data('decisions')
    if not rows:
        print("  → Veri yok, atlanıyor")
        return
    
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("TRUNCATE TABLE decisions CASCADE")
        
        for row in rows:
            cursor.execute("""
                INSERT INTO decisions (application_id, decision, decision_reason, decided_at, decided_by)
                VALUES (%(application_id)s, %(decision)s, %(decision_reason)s, %(decided_at)s, %(decided_by)s)
            """, row)
        
        conn.commit()
        print(f"  ✓ {len(rows)} karar migrate edildi")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"  ✗ Migration hatası: {e}")

def migrate_manual_overrides():
    """Manual overrides tablosunu migrate et."""
    print("\n[4/5] Manual overrides tablosu migrate ediliyor...")
    
    rows = get_sqlite_data('manual_overrides')
    if not rows:
        print("  → Veri yok, atlanıyor")
        return
    
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("TRUNCATE TABLE manual_overrides CASCADE")
        
        for row in rows:
            cursor.execute("""
                INSERT INTO manual_overrides (
                    application_id, original_decision, new_decision, 
                    override_reason, overridden_by, overridden_at
                )
                VALUES (%(application_id)s, %(original_decision)s, %(new_decision)s, 
                        %(override_reason)s, %(overridden_by)s, %(overridden_at)s)
            """, row)
        
        conn.commit()
        print(f"  ✓ {len(rows)} override migrate edildi")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"  ✗ Migration hatası: {e}")

def verify_migration():
    """Migration sonrası doğrulama."""
    print("\n[5/5] Migration doğrulanıyor...")
    
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        tables = ['applications', 'users', 'decisions', 'manual_overrides']
        results = {}
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            results[table] = count
            print(f"  ✓ {table}: {count} kayıt")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ MİGRATİON TAMAMLANDI!")
        print("=" * 60)
        print("\n📊 PostgreSQL Bağlantı Bilgileri:")
        print(f"  Host: {POSTGRES_CONFIG['host']}")
        print(f"  Port: {POSTGRES_CONFIG['port']}")
        print(f"  Database: {POSTGRES_CONFIG['database']}")
        print(f"  User: {POSTGRES_CONFIG['user']}")
        print(f"  Password: {POSTGRES_CONFIG['password']}")
        
        print("\n🔍 PgAdmin Erişim:")
        print("  URL: http://localhost:5050")
        print("  Email: admin@finwise.local")
        print("  Password: admin123")
        
        return True
        
    except Exception as e:
        print(f"✗ Doğrulama hatası: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("SQLite → PostgreSQL MIGRATION")
    print("=" * 60)
    
    # Bağlantı testi
    if not test_postgres_connection():
        print("\n❌ PostgreSQL bağlantısı kurulamadı!")
        print("Docker container'ın çalıştığından emin olun:")
        print("  docker-compose -f docker-compose.local.yml ps")
        exit(1)
    
    # Migration
    migrate_applications()
    migrate_users()
    migrate_decisions()
    migrate_manual_overrides()
    
    # Doğrulama
    verify_migration()
    
    print("\n✅ PostgreSQL production database hazır!")
    print("Şimdi API'yi PostgreSQL ile başlatabilirsiniz.\n")
