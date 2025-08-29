#!/usr/bin/env python3
"""
Fix migration conflict by creating a proper migration that matches production state.
This creates a new migration that will work regardless of the current state.
"""

import os
from flask import Flask
from flask_migrate import Migrate, init_db, stamp
from models import db

def create_app():
    """Create Flask app for migration operations."""
    app = Flask(__name__)
    
    # Use the same database configuration as the main app
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///instance/nola_docs.db')
    # Fix for Render PostgreSQL URL format
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    migrate = Migrate(app, db)
    
    return app, migrate

def fix_migration_state():
    """Fix the migration state by stamping to the latest known good revision."""
    app, migrate = create_app()
    
    with app.app_context():
        try:
            print("🔧 Fixing migration state...")
            
            # The latest revision we know exists in both local and production
            latest_known_revision = 'e753b30421b6'
            
            print(f"Stamping database to revision: {latest_known_revision}")
            
            # This tells Alembic that the database is at this revision
            from flask_migrate import stamp
            stamp(revision=latest_known_revision)
            
            print("✅ Migration state fixed!")
            print(f"Database is now stamped at revision: {latest_known_revision}")
            print("\nNow you can run:")
            print("1. flask db migrate -m 'Add HLP models'")
            print("2. flask db upgrade")
            
        except Exception as e:
            print(f"❌ Error fixing migration state: {e}")
            print("\nAlternative approach - run these commands manually:")
            print("1. flask db stamp e753b30421b6")
            print("2. flask db migrate -m 'Add HLP models'") 
            print("3. flask db upgrade")

if __name__ == '__main__':
    fix_migration_state()