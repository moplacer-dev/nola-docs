#!/usr/bin/env python3
"""
Database debugging and admin creation script for Render deployment
This script helps diagnose database issues and ensures admin access
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User
from getpass import getpass

def test_database_connection():
    """Test if we can connect to the database"""
    print("🔍 Testing database connection...")
    
    try:
        with app.app_context():
            # Test basic connection
            result = db.engine.execute("SELECT 1")
            print("✅ Database connection successful!")
            
            # Check if tables exist
            tables = db.engine.table_names()
            print(f"📋 Found {len(tables)} tables: {', '.join(tables)}")
            
            # Test user table specifically
            user_count = User.query.count()
            print(f"👥 Found {user_count} users in database")
            
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def show_database_info():
    """Display database configuration information"""
    print("\n🔧 Database Configuration:")
    print("-" * 50)
    
    db_url = os.environ.get('DATABASE_URL', 'Not set')
    if db_url != 'Not set':
        # Hide password for security
        safe_url = db_url.split('@')[1] if '@' in db_url else db_url
        print(f"Database URL: postgresql://***:***@{safe_url}")
    else:
        print("DATABASE_URL: Not set")
    
    print(f"Flask Environment: {os.environ.get('FLASK_ENV', 'Not set')}")
    print(f"Secret Key: {'Set' if os.environ.get('SECRET_KEY') else 'Not set'}")
    print(f"Render External URL: {os.environ.get('RENDER_EXTERNAL_URL', 'Not set')}")

def list_all_users():
    """List all users in the database"""
    print("\n👥 All Users in Database:")
    print("-" * 50)
    
    try:
        with app.app_context():
            users = User.query.all()
            
            if not users:
                print("No users found in database")
                return []
            
            for user in users:
                status = "🔹" if user.is_admin else "👤"
                active = "✅" if user.is_active else "❌"
                print(f"{status} ID: {user.id}")
                print(f"   Email: {user.email}")
                print(f"   Username: {user.username}")
                print(f"   Name: {user.full_name}")
                print(f"   Admin: {'Yes' if user.is_admin else 'No'}")
                print(f"   Active: {active}")
                print(f"   Created: {user.created_at}")
                print(f"   Has Password: {'Yes' if user.password_hash else 'No'}")
                print()
            
            return users
            
    except Exception as e:
        print(f"❌ Error listing users: {e}")
        return []

def create_admin_user_interactive():
    """Create admin user with interactive prompts"""
    print("\n🔐 Creating Admin User:")
    print("-" * 50)
    
    try:
        with app.app_context():
            # Check for existing admin
            existing_admin = User.query.filter_by(is_admin=True).first()
            
            if existing_admin:
                print(f"⚠️  Admin user already exists: {existing_admin.email}")
                choice = input("Do you want to create another admin (y) or reset existing password (r) or skip (n)? [y/r/n]: ").lower()
                
                if choice == 'r':
                    new_password = getpass("New password for existing admin: ")
                    existing_admin.set_password(new_password)
                    db.session.commit()
                    print("✅ Admin password updated!")
                    return existing_admin
                elif choice != 'y':
                    print("Skipping admin creation.")
                    return existing_admin
            
            # Create new admin
            print("Creating new admin user...")
            email = input("Admin email: ").strip()
            username = input("Admin username: ").strip()
            first_name = input("First name: ").strip()
            last_name = input("Last name: ").strip()
            password = getpass("Password: ")
            confirm_password = getpass("Confirm password: ")
            
            if password != confirm_password:
                print("❌ Passwords don't match!")
                return None
            
            # Create the admin
            admin = User(
                email=email,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_admin=True,
                is_active=True
            )
            admin.set_password(password)
            
            db.session.add(admin)
            db.session.commit()
            
            print("✅ Admin user created successfully!")
            print(f"   ID: {admin.id}")
            print(f"   Email: {admin.email}")
            print(f"   Username: {admin.username}")
            
            return admin
            
    except Exception as e:
        print(f"❌ Error creating admin: {e}")
        db.session.rollback()
        return None

def create_default_admin():
    """Create a default admin user for quick setup"""
    print("\n🚀 Creating default admin user...")
    
    try:
        with app.app_context():
            # Check if any admin exists
            if User.query.filter_by(is_admin=True).first():
                print("⚠️  Admin user already exists. Use option 3 for custom admin.")
                return False
            
            # Create default admin
            admin = User(
                email="admin@nola.edu",
                username="admin",
                first_name="System",
                last_name="Administrator",
                is_admin=True,
                is_active=True
            )
            admin.set_password("admin123")  # Change this immediately!
            
            db.session.add(admin)
            db.session.commit()
            
            print("✅ Default admin created!")
            print("   Email: admin@nola.edu")
            print("   Username: admin")
            print("   Password: admin123")
            print("   ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating default admin: {e}")
        db.session.rollback()
        return False

def run_migrations():
    """Run database migrations"""
    print("\n🔄 Running database migrations...")
    
    try:
        with app.app_context():
            from flask_migrate import upgrade
            upgrade()
            print("✅ Migrations completed successfully!")
            return True
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

def main_menu():
    """Main menu for database operations"""
    print("\n" + "="*60)
    print("🗄️  NOLA Docs Database Diagnostic Tool")
    print("="*60)
    
    show_database_info()
    
    if not test_database_connection():
        print("\n❌ Cannot proceed - database connection failed!")
        print("Check your DATABASE_URL environment variable.")
        return
    
    while True:
        print("\n📋 Available Options:")
        print("1. 👥 List all users")
        print("2. 🚀 Create default admin (admin@nola.edu / admin123)")
        print("3. 🔐 Create custom admin user")
        print("4. 🔄 Run database migrations")
        print("5. 🔍 Test database connection again")
        print("6. ❌ Exit")
        
        choice = input("\nSelect option [1-6]: ").strip()
        
        if choice == '1':
            list_all_users()
        elif choice == '2':
            create_default_admin()
        elif choice == '3':
            create_admin_user_interactive()
        elif choice == '4':
            run_migrations()
        elif choice == '5':
            test_database_connection()
        elif choice == '6':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option. Please try again.")

if __name__ == '__main__':
    main_menu() 