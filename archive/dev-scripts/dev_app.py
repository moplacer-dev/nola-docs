#!/usr/bin/env python3
"""
Development startup script for NOLA.docs
Uses SQLite and development configuration for local testing
"""

import os
import sys
from config_dev import DevelopmentConfig

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_dev_app():
    """Create Flask app with development configuration"""
    
    # Import after setting up path
    from app import app, db
    
    # Apply development configuration
    app.config.from_object(DevelopmentConfig)
    DevelopmentConfig.init_app(app)
    
    # Initialize database
    with app.app_context():
        # Create tables if they don't exist
        try:
            db.create_all()
            print("✅ Database tables created/verified")
        except Exception as e:
            print(f"❌ Database error: {e}")
            print("This is normal on first run - tables will be created automatically")
    
    return app

if __name__ == '__main__':
    print("🚀 Starting NOLA.docs in development mode...")
    print("=" * 50)
    
    # Create the app
    dev_app = create_dev_app()
    
    print("=" * 50)
    print("🌐 Server will start at: http://127.0.0.1:5000")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Run the development server
    dev_app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        use_reloader=True
    ) 