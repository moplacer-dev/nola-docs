#!/usr/bin/env python3
"""
Quick fix script for immediate admin access
Run this in Render shell to immediately create admin user
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🚀 NOLA Docs Quick Fix - Creating Admin User...")

try:
    from app import app
    from models import db, User
    
    with app.app_context():
        print("📊 Connecting to database...")
        
        # Check if admin already exists
        existing_admin = User.query.filter_by(is_admin=True).first()
        
        if existing_admin:
            print(f"✅ Admin already exists: {existing_admin.email}")
            print("Try logging in with:")
            print(f"   Email: {existing_admin.email}")
            print(f"   Username: {existing_admin.username}")
            print("   If password doesn't work, run: python debug_db.py")
        else:
            print("🔐 Creating new admin user...")
            
            # Create default admin
            admin = User(
                email="admin@nola.edu",
                username="admin",
                first_name="System",
                last_name="Administrator",
                is_admin=True,
                is_active=True
            )
            admin.set_password("admin123")
            
            db.session.add(admin)
            db.session.commit()
            
            print("✅ SUCCESS! Admin user created!")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("📧 Email: admin@nola.edu")
            print("👤 Username: admin")
            print("🔑 Password: admin123")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("⚠️  CHANGE THIS PASSWORD IMMEDIATELY!")
            print("💻 Login at: https://nola-docs.onrender.com")
            
        print("🎉 Quick fix completed!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("💡 Try running the full diagnostic: python debug_db.py") 