#!/usr/bin/env python3
"""
Quick setup script for MedSynEval with MySQL
Run this after setting up MySQL database
"""

import os
import sys
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'med_syn_eval.settings')

def main():
    print("=" * 50)
    print("MedSynEval - Quick Setup Check")
    print("=" * 50)
    print()
    
    # Check MySQL client
    try:
        import MySQLdb
        print("✓ mysqlclient is installed")
    except ImportError:
        print("✗ mysqlclient not found")
        print("  Run: pip install mysqlclient")
        return False
    
    # Check Django
    try:
        import django
        print(f"✓ Django {django.get_version()} is installed")
    except ImportError:
        print("✗ Django not found")
        print("  Run: pip install Django")
        return False
    
    # Try to setup Django
    try:
        django.setup()
        print("✓ Django setup successful")
    except Exception as e:
        print(f"✗ Django setup failed: {e}")
        print("\nCommon issues:")
        print("  1. MySQL database not created")
        print("     Run: ./setup_mysql.sh")
        print("  2. Wrong MySQL password in settings.py")
        print("     Edit: med_syn_eval/settings.py")
        print("  3. MySQL server not running")
        print("     Run: sudo systemctl start mysql")
        return False
    
    # Check database connection
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("\nPlease check:")
        print("  1. MySQL server is running")
        print("  2. Database 'med_syn_eval' exists")
        print("  3. Credentials in settings.py are correct")
        return False
    
    # Check migrations
    try:
        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        call_command('showmigrations', '--plan', stdout=out)
        output = out.getvalue()
        
        if '[X]' in output or not output.strip():
            print("✓ Migrations are up to date")
        else:
            print("⚠ Migrations need to be applied")
            print("  Run: python manage.py migrate")
    except Exception as e:
        print(f"⚠ Could not check migrations: {e}")
    
    print()
    print("=" * 50)
    print("Setup Status: READY")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. python manage.py migrate")
    print("  2. python manage.py createsuperuser")
    print("  3. python manage.py runserver")
    print()
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
