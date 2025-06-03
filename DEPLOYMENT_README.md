# NOLA Docs - Multi-User Document Generation System

## 🎯 Project Overview

NOLA Docs is a Flask-based web application for generating educational documents including worksheets, answer keys, module guides, and assessments. Originally a local application, it has been upgraded to a multi-user system with authentication, user management, and cloud deployment capabilities.

## ✨ Features

### 📝 Document Generation (10 Types)
- **Vocabulary Worksheets** - Term definitions and exercises
- **PBA Worksheets** - Performance-based assessments
- **Pre/Post Test Worksheets** - Multiple choice assessments
- **Generic Worksheets** - Flexible document templates
- **Family Briefings** - Parent communication documents
- **RCA Worksheets** - Research, Challenge, Application activities
- **Module Guides** - Comprehensive teaching guides
- **Module Answer Keys** - Complete answer references
- **Module Activity Sheets** - Session planning documents

### 🔐 Authentication & User Management
- **Multi-user Authentication** - Secure login/logout system
- **Admin Interface** - User creation and management
- **Role-based Access** - Admin and regular user roles
- **Session Management** - Secure session handling
- **Activity Logging** - User action tracking

### 🗄️ Database Features
- **PostgreSQL Integration** - Production-ready database
- **Migration System** - Version-controlled schema changes
- **User Data Management** - Secure user information storage
- **Draft System** - Ready for save/load functionality (Phase 2)

## 🚀 Deployment Status

**Current Version**: Phase 1 Complete - Authentication System
**Deployment Target**: Render Platform
**Database**: PostgreSQL (Render managed)

## 🏗️ Architecture

### Technology Stack
- **Backend**: Flask 3.0.0 with Python
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Flask-Login with password hashing
- **Templating**: Jinja2 templates with responsive design
- **Document Generation**: python-docx-template for .docx files
- **Deployment**: Render platform with gunicorn WSGI server

### Project Structure
```
nola.docs/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── auth.py                # Authentication blueprint
├── requirements.txt       # Python dependencies
├── render.yaml           # Render deployment config
├── seed_admin.py         # Admin user creation script
├── template_manager.py   # Template management utilities
├── templates/            # HTML templates
│   ├── auth/            # Authentication templates
│   └── docx_templates/  # Word document templates
├── static/              # CSS, JS, images
└── migrations/          # Database migrations
```

## 🔧 Environment Configuration

### Required Environment Variables
```bash
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
```

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd nola.docs

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask db upgrade

# Create admin user
python seed_admin.py

# Run development server
flask run
```

## 🚀 Render Deployment

### Prerequisites
1. GitHub repository with this code
2. Render account (free tier available)

### Deployment Steps

1. **Create Web Service**
   - Go to Render Dashboard
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**
   - **Name**: nola-docs
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt && flask db upgrade`
   - **Start Command**: `gunicorn app:app`

3. **Database Setup**
   - The `render.yaml` file automatically configures PostgreSQL
   - Database will be created and connected automatically

4. **Deploy**
   - Click "Create Web Service"
   - Render will build and deploy automatically
   - Initial deployment takes 5-10 minutes

5. **Post-Deployment Setup**
   ```bash
   # SSH into your Render service or use the web shell
   python seed_admin.py
   ```

### Render Configuration
The project includes a complete `render.yaml` file that automatically:
- Creates PostgreSQL database
- Sets up environment variables
- Configures build and start commands
- Provisions persistent storage

## 👤 User Management

### Admin User
After deployment, create an admin user:
```bash
python seed_admin.py
```

### Creating Additional Users
1. Login as admin
2. Navigate to `/admin/users`
3. Click "Create User"
4. Fill out user details and assign permissions

## 📊 Current Status & Roadmap

### ✅ Phase 1 Complete (Current Deployment)
- Multi-user authentication system
- Admin interface for user management
- All 10 document types functional
- Database models and migrations
- Production-ready deployment configuration

### 🔄 Phase 2 Planned (Future Updates)
- Save/load functionality for drafts
- Document management and history
- Auto-save capabilities
- Advanced user dashboard
- Document sharing features

## 🛠️ Development

### Local Development
```bash
# Activate virtual environment
source venv/bin/activate

# Run development server
flask run --debug

# Create database migrations
flask db migrate -m "Description of changes"
flask db upgrade
```

### Testing
```bash
# Test Flask application loads
python -c "from app import app; print('App loaded successfully')"

# Test database connection
python -c "from models import db; print('Database connected')"
```

## 📝 Usage

### Document Generation Workflow
1. **Login** to the system
2. **Select** document type from navigation
3. **Fill out** the form with required information
4. **Generate** document (downloads automatically)
5. **Manage** documents through dashboard (Phase 2)

### Admin Functions
- Create and manage users
- View system activity logs
- Monitor document generation
- Manage user permissions

## 🔒 Security Features

- **Password Hashing** - Secure password storage
- **Session Management** - Automatic session timeouts
- **CSRF Protection** - Form submission security
- **Activity Logging** - Track user actions
- **Role-based Access** - Admin vs user permissions

## 📞 Support

For deployment issues or questions:
1. Check Render service logs
2. Verify environment variables
3. Ensure database connection is working
4. Review migration status

## 📄 License

This project is developed for educational use in the NOLA educational system.

---

**Deployment Date**: January 2025  
**Version**: 1.0.0 (Phase 1 Complete)  
**Platform**: Render (render.com)  
**Database**: PostgreSQL 