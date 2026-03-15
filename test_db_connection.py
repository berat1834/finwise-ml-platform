import psycopg2
import sys

try:
    print("Bağlantı deneniyor...")
    conn = psycopg2.connect(
        host='127.0.0.1',
        port=5433,
        database='credit_risk_db',
        user='postgres',
        password='postgres'
    )
    print("✓ Bağlantı başarılı!")
    cur = conn.cursor()
    cur.execute('SELECT version();')
    version = cur.fetchone()
    print(f"PostgreSQL version: {version[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Bağlantı hatası: {e}")
    sys.exit(1)
