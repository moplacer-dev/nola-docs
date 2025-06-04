#!/usr/bin/env python3
"""
Render deployment setup script
This script runs after deployment to ensure database and admin setup
"""

import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def log_message(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def setup_for_render():
    """Setup database and admin for Render deployment"""
    log_message("🚀 Starting Render deployment setup...")
    
    try:
        # Import here to avoid import errors during build
        from app import app
        from models import db, User
        
        with app.app_context():
            log_message("📊 Testing database connection...")
            
            # Test database connection
            try:
                user_count = User.query.count()
                log_message(f"✅ Database connected. Found {user_count} users.")
            except Exception as e:
                log_message(f"❌ Database connection failed: {e}")
                return False
            
            # Check for admin user
            admin = User.query.filter_by(is_admin=True).first()
            
            if not admin:
                log_message("🔐 No admin user found. Creating default admin...")
                
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
                
                log_message("✅ Default admin created!")
                log_message("   Email: admin@nola.edu")
                log_message("   Username: admin") 
                log_message("   Password: admin123")
                log_message("   ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!")
                
            else:
                log_message(f"✅ Admin user exists: {admin.email}")
            
            # Log environment info
            log_message("🔧 Environment Configuration:")
            log_message(f"   Flask Environment: {os.environ.get('FLASK_ENV', 'Not set')}")
            log_message(f"   Database URL: {'Set' if os.environ.get('DATABASE_URL') else 'Not set'}")
            log_message(f"   Secret Key: {'Set' if os.environ.get('SECRET_KEY') else 'Not set'}")
            
            log_message("🎉 Render setup completed successfully!")
            return True
            
    except Exception as e:
        log_message(f"❌ Setup failed: {e}")
        return False

if __name__ == '__main__':
    setup_for_render() 