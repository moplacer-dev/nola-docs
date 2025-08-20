# NOLA Docs - Document Generator

A Flask-based web application for generating professional educational documents with standardized formatting and user-controlled data input.

## 🎯 Overview

**NOLA Docs** lets educators create perfectly formatted educational documents through simple web forms - no more wrestling with Word formatting! Users select a document template, fill out the form, and generate professional DOCX files instantly.

**Key Features:**
- 🔒 **Locked formatting** - Templates ensure consistent professional output
- 📝 **Form-driven** - Users focus on content, not formatting
- ⚡ **Instant generation** - Documents created in seconds
- 👥 **Multi-user** - Authentication and user management
- 📱 **Web-based** - Works on any device with a browser

## 🛠 Tech Stack

- **Backend**: Flask, SQLAlchemy, Flask-Login
- **Frontend**: Tailwind CSS, Jinja2 Templates  
- **Documents**: python-docx-template (docxtpl)
- **Database**: PostgreSQL (production), SQLite (development)
- **Deployment**: Render.com

## 📝 Available Document Types

**NOLA Docs** supports 11 different educational document templates:

### **Worksheets & Assessments**
- **📚 Vocabulary Worksheet** - Term definitions and exercises
- **🎯 PBA Worksheet** - Performance-Based Assessment activities  
- **✅ Pre/Post Test** - Multiple choice assessments
- **🔬 RCA Worksheet** - Research, Challenge & Application questions
- **⚡ Generic Worksheet** - Custom content with images and mixed field types

### **Administrative Documents**  
- **👨‍👩‍👧‍👦 Family Briefing** - Parent communication documents
- **📋 Horizontal Lesson Plan** - Daily lesson planning
- **🏗️ Curriculum Design Build** - Curriculum development forms

### **Reference Materials**
- **📖 Module Guide** - Comprehensive teacher guides
- **🔑 Module Answer Key** - Complete answer keys with nested sections
- **📊 Module Activity Sheet** - Session tracking and PBA monitoring

### **Reports**
- **📊 Correlation Report** - Standards alignment documentation

## 🚀 Getting Started

### **For Users**
1. Visit the application homepage
2. Choose a document type from the dashboard
3. Fill out the form with your content
4. Click "Generate Document" 
5. Download your perfectly formatted DOCX file

### **For Developers**

**Prerequisites:**
- Python 3.9+
- Virtual environment (recommended)

**Installation:**
```bash
# Clone the repository
git clone <repository-url>
cd nola.docs

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

**Environment Setup:**
- Development uses SQLite database (auto-created)
- Production uses PostgreSQL via DATABASE_URL environment variable
- Set SECRET_KEY environment variable for security

## 🏗️ Project Structure

```
nola.docs/
├── app.py                    # Main Flask application
├── models.py                 # Database models
├── auth.py                   # User authentication
├── template_manager.py       # Document generation
├── requirements.txt          # Dependencies
├── render.yaml              # Deployment config
├── templates/               # HTML templates
│   ├── *.html              # Form pages
│   └── docx_templates/     # Word document templates
├── static/                  # CSS and assets
├── generated_docs/         # Generated documents
├── migrations/             # Database migrations
└── archive/                # Archived development scripts
```

## 🤝 Contributing

**For Template Updates:**
- Word templates are in `templates/docx_templates/`
- Use Jinja2 syntax: `{{ variable_name }}` and `{% for item in items %}`
- Test thoroughly before deploying

**For Code Changes:**
- Core functionality is in `app.py`, `models.py`, and `auth.py`
- Development scripts have been archived to keep codebase clean
- Follow existing patterns for new document types

## 📄 License

This project is proprietary educational software for NOLA educational document generation.

---

**Last Updated**: August 20, 2025  
**Status**: Production Ready  
**Document Types**: 11 templates supported