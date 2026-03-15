#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Migration Script - Initialize PostgreSQL Database
Creates all tables and initial data
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v2_secure import app, db
from models import User, Application, ManualOverride, AuditLog, ModelPerformance
from werkzeug.security import generate_password_hash

def init_database():
    """Initialize database with tables and sample data"""
    print("=" * 60)
    print("PostgreSQL Database Migration")
    print("=" * 60)
    
    with app.app_context():
        # Drop all tables (WARNING: This deletes all data!)
        print("\n1. Dropping existing tables...")
        db.drop_all()
        print("✓ Tables dropped")
        
        # Create all tables
        print("\n2. Creating tables...")
        db.create_all()
        print("✓ Tables created:")
        print("  - users")
        print("  - applications")
        print("  - manual_overrides")
        print("  - audit_logs")
        print("  - model_performance")
        
        # Create default admin user
        print("\n3. Creating default users...")
        admin = User(
            username='admin',
            email='admin@creditrisk.com',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            is_active=True
        )
        
        analyst = User(
            username='analyst',
            email='analyst@creditrisk.com',
            password_hash=generate_password_hash('analyst123'),
            role='analyst',
            is_active=True
        )
        
        manager = User(
            username='manager',
            email='manager@creditrisk.com',
            password_hash=generate_password_hash('manager123'),
            role='manager',
            is_active=True
        )
        
        db.session.add_all([admin, analyst, manager])
        db.session.commit()
        
        print("✓ Default users created:")
        print("  - admin / admin123 (Admin)")
        print("  - analyst / analyst123 (Analyst)")
        print("  - manager / manager123 (Manager)")
        
        print("\n" + "=" * 60)
        print("✅ Database initialization completed successfully!")
        print("=" * 60)
        print("\nDatabase URL:", os.getenv('DATABASE_URL'))
        print("\nYou can now start the application with:")
        print("  python app_v2_secure.py")
        print("\n")

if __name__ == '__main__':
    try:
        init_database()
    except Exception as e:
        print("\n❌ Error during database initialization:")
        print(f"   {str(e)}")
        print("\nPlease ensure:")
        print("  1. PostgreSQL is running (docker-compose up -d db)")
        print("  2. DATABASE_URL in .env is correct")
        print("  3. Database connection is accessible")
        sys.exit(1)
