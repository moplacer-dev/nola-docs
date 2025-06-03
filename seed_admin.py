from models import User, db
from app import app
import os
from getpass import getpass

def create_admin_user():
    """Create initial admin user"""
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(is_admin=True).first()
        if admin:
            print(f"Admin user already exists: {admin.email}")
            return
        
        print("Creating admin user...")
        email = input("Admin email: ")
        username = input("Admin username: ")
        first_name = input("First name: ")
        last_name = input("Last name: ")
        password = getpass("Password: ")
        
        admin = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_admin=True
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"Admin user created successfully: {email}")

if __name__ == '__main__':
    create_admin_user() 