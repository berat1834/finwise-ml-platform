#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FinWise - Production Environment Setup
Lokal ortam baÅŸlatma script'i
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

class ProductionSetup:
    
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.venv_python = self.project_dir / ".venv" / "Scripts" / "python.exe"
        self.api_file = self.project_dir / "app_api.py"
        self.db_file = self.project_dir / "finwise_production.db"
        
    def check_requirements(self):
        """Gerekli dosyalarÄ± kontrol et."""
        print("\n" + "="*60)
        print("FinWise - Environment Check")
        print("="*60 + "\n")
        
        checks = {
            "Python venv": self.venv_python.exists(),
            "API script": self.api_file.exists(),
            "Model file": (self.project_dir / "production_model.joblib").exists(),
            "SQLite database": self.db_file.exists(),
        }
        
        for name, exists in checks.items():
            status = "âœ“ OK" if exists else "âœ— MISSING"
            print(f"  {name:.<40} {status}")
        
        if not all(checks.values()):
            print("\nâš  Some files are missing!")
            return False
        
        return True
    
    def start_api(self):
        """API'yi baÅŸlat."""
        print("\n" + "="*60)
        print("Starting FinWise API")
        print("="*60 + "\n")
        
        print(f"  API script: {self.api_file}")
        print(f"  Database: {self.db_file}")
        print(f"  Endpoint: http://127.0.0.1:5000")
        print("\n  Starting...\n")
        
        try:
            subprocess.run([str(self.venv_python), str(self.api_file)])
        except KeyboardInterrupt:
            print("\n\nâ¹ Shutting down...")
            self.cleanup()
    
    def cleanup(self):
        """Temizlik iÅŸlemleri."""
        print("  â€¢ Saving database...")
        print("  â€¢ Closing connections...")
        print("\nâœ“ Shutdown complete")
        sys.exit(0)
    
    def show_menu(self):
        """Ana menu."""
        print("\n" + "="*60)
        print("FinWise Credit Risk API - Production Menu")
        print("="*60)
        print("""
  1. Start API
  2. Check environment
  3. View documentation
  4. Test API
  5. Database backup
  6. Reset database
  7. Exit
        """)
        choice = input("Select option (1-7): ").strip()
        return choice
    
    def run(self):
        """Interactive menu."""
        while True:
            choice = self.show_menu()
            
            if choice == '1':
                if self.check_requirements():
                    self.start_api()
            
            elif choice == '2':
                self.check_requirements()
            
            elif choice == '3':
                if (self.project_dir / "API_DOCUMENTATION.md").exists():
                    print("\nâœ“ Documentation exists: API_DOCUMENTATION.md")
                else:
                    print("\nâœ— Documentation not found")
            
            elif choice == '4':
                print("\nâœ“ Running test suite...")
                print("  (Make sure API is running on another terminal)")
                subprocess.run([str(self.venv_python), str(self.project_dir / "test_api_comprehensive.py")])
            
            elif choice == '5':
                self.backup_database()
            
            elif choice == '6':
                if input("\nâš  Reset database? (yes/no): ").lower() == 'yes':
                    if self.db_file.exists():
                        self.db_file.unlink()
                        print("âœ“ Database reset")
            
            elif choice == '7':
                print("\nGoodbye!")
                sys.exit(0)
    
    def backup_database(self):
        """Database'i yedekle."""
        if not self.db_file.exists():
            print("\nâœ— Database not found")
            return
        
        import shutil
        from datetime import datetime
        
        backup_name = f"finwise_production_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = self.project_dir / backup_name
        
        try:
            shutil.copy(str(self.db_file), str(backup_path))
            print(f"\nâœ“ Backup created: {backup_name}")
        except Exception as e:
            print(f"\nâœ— Backup failed: {e}")

if __name__ == "__main__":
    setup = ProductionSetup()
    
    # Command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == 'start':
            if setup.check_requirements():
                setup.start_api()
        elif sys.argv[1] == 'check':
            setup.check_requirements()
        else:
            print(f"Unknown command: {sys.argv[1]}")
    else:
        # Interactive menu
        setup.run()

