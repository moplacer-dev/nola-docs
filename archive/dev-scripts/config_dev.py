import os

class DevelopmentConfig:
    """Development configuration for local testing"""
    
    # Database - Use SQLite for local development
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dev_nola_docs.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Debug settings
    DEBUG = True
    FLASK_ENV = 'development'
    
    # Security (relaxed for development)
    SECRET_KEY = 'dev-secret-key-change-in-production'
    WTF_CSRF_ENABLED = True  # Keep CSRF protection even in dev
    
    # File upload settings
    UPLOAD_FOLDER = 'dev_uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Generated documents folder
    GENERATED_DOCS_FOLDER = 'dev_generated_docs'
    
    # Logging
    LOG_LEVEL = 'DEBUG'
    
    # Template settings
    TEMPLATES_AUTO_RELOAD = True
    
    @staticmethod
    def init_app(app):
        """Initialize app with development settings"""
        # Create upload and generated docs folders
        os.makedirs('dev_uploads', exist_ok=True)
        os.makedirs('dev_generated_docs', exist_ok=True)
        
        # Set up logging for development
        import logging
        logging.basicConfig(level=logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)
        
        print("🔧 Development configuration loaded")
        print("📁 Using SQLite database: dev_nola_docs.db")
        print("📂 Upload folder: dev_uploads/")
        print("📄 Generated docs: dev_generated_docs/") 