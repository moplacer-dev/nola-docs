from models import User, db
from app import app
import os
from getpass import getpass
from dotenv import load_dotenv

# Load environment variables explicitly
load_dotenv()

def create_admin_user():
    """Create initial admin user with better error handling and debugging"""
    
    # Show database configuration for debugging
    print(f"Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'Not set')}")
    
    with app.app_context():
        try:
            # Test database connection
            print("Testing database connection...")
            existing_users = User.query.count()
            print(f"Found {existing_users} existing users in database")
            
            # Check if admin already exists
            admin = User.query.filter_by(is_admin=True).first()
            if admin:
                print(f"Admin user already exists: {admin.email}")
                print(f"Admin details: ID={admin.id}, Username={admin.username}, Active={admin.is_active}")
                
                # Ask if they want to reset the password
                reset = input("Would you like to reset the admin password? (y/N): ").strip().lower()
                if reset == 'y':
                    new_password = getpass("New password: ")
                    admin.set_password(new_password)
                    db.session.commit()
                    print("Admin password updated successfully!")
                return
            
            print("Creating new admin user...")
            email = input("Admin email: ")
            username = input("Admin username: ")
            first_name = input("First name: ")
            last_name = input("Last name: ")
            password = getpass("Password: ")
            
            # Create the admin user
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
            
            print(f"Admin user created successfully!")
            print(f"Email: {email}")
            print(f"Username: {username}")
            print(f"ID: {admin.id}")
            
            # Verify the user was created
            verify_user = User.query.filter_by(email=email).first()
            if verify_user:
                print("✓ User creation verified in database")
                print(f"✓ Password hash set: {bool(verify_user.password_hash)}")
                print(f"✓ Is admin: {verify_user.is_admin}")
                print(f"✓ Is active: {verify_user.is_active}")
            else:
                print("✗ ERROR: User not found after creation!")
                
        except Exception as e:
            print(f"ERROR: {e}")
            print("Make sure the database is properly configured and accessible.")

def list_users():
    """List all users in the database for debugging"""
    with app.app_context():
        try:
            users = User.query.all()
            print(f"\nAll users in database ({len(users)} total):")
            for user in users:
                print(f"  ID: {user.id}")
                print(f"  Email: {user.email}")
                print(f"  Username: {user.username}")
                print(f"  Admin: {user.is_admin}")
                print(f"  Active: {user.is_active}")
                print(f"  Has password: {bool(user.password_hash)}")
                print("  ---")
        except Exception as e:
            print(f"ERROR listing users: {e}")

if __name__ == '__main__':
    print("=== NOLA Docs Admin User Management ===")
    print("1. Create/Update Admin User")
    print("2. List All Users")
    choice = input("Choose option (1 or 2): ").strip()
    
    if choice == '2':
        list_users()
    else:
        create_admin_user() 