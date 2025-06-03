# NOLA Docs - Save/Load Implementation Plan

## 🎯 Overview

This document outlines the implementation plan for adding save/load functionality, user authentication, and version control to the NOLA Docs Flask application hosted on Render with PostgreSQL.

## 📋 Table of Contents

1. [Database Schema](#database-schema)
2. [User Authentication](#user-authentication)
3. [Save/Load Endpoints](#saveload-endpoints)
4. [UI Features](#ui-features)
5. [Additional Features](#additional-features)
6. [Implementation Phases](#implementation-phases)
7. [Deployment Guide](#deployment-guide)

## 🗄 Database Schema

### Core Tables

```python
# models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User account model"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255))
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    drafts = db.relationship('FormDraft', backref='user', lazy='dynamic')
    generated_docs = db.relationship('GeneratedDocument', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FormDraft(db.Model):
    """Form draft storage"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    form_type = db.Column(db.String(50), nullable=False, index=True)  # 'vocabulary', 'module_answer_key', etc.
    title = db.Column(db.String(200), nullable=False)
    module_acronym = db.Column(db.String(20), index=True)  # For easy filtering
    form_data = db.Column(db.JSON, nullable=False)  # PostgreSQL native JSON
    is_current = db.Column(db.Boolean, default=True)  # Latest version flag
    version = db.Column(db.Integer, default=1)
    parent_draft_id = db.Column(db.Integer, db.ForeignKey('form_draft.id'), nullable=True)  # For version tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    versions = db.relationship('FormDraft', backref=db.backref('parent_draft', remote_side=[id]))
    
    def create_new_version(self, new_data):
        """Create a new version of this draft"""
        # Mark current as not current
        self.is_current = False
        
        # Create new version
        new_version = FormDraft(
            user_id=self.user_id,
            form_type=self.form_type,
            title=self.title,
            module_acronym=self.module_acronym,
            form_data=new_data,
            is_current=True,
            version=self.version + 1,
            parent_draft_id=self.parent_draft_id or self.id
        )
        return new_version

class GeneratedDocument(db.Model):
    """Track generated documents"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    draft_id = db.Column(db.Integer, db.ForeignKey('form_draft.id'), nullable=True)
    document_type = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500))  # If storing files
    module_acronym = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SharedDraft(db.Model):
    """Share drafts between users"""
    id = db.Column(db.Integer, primary_key=True)
    draft_id = db.Column(db.Integer, db.ForeignKey('form_draft.id'), nullable=False)
    shared_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shared_with_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    permission = db.Column(db.String(20), default='view')  # 'view', 'edit', 'copy'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Optional: Activity logging
class ActivityLog(db.Model):
    """Track user activities"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50))  # 'draft_saved', 'document_generated', etc.
    details = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
```

## 👤 User Authentication

### Flask-Login Setup

```python
# auth.py

from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, redirect, url_for, flash, request
from models import User, db

auth = Blueprint('auth', __name__)
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('auth.register'))
        
        # Create new user
        user = User(
            email=email,
            username=username,
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name')
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('index'))
    
    return render_template('auth/register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        
        flash('Invalid email or password')
    
    return render_template('auth/login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
```

## 💾 Save/Load Endpoints

### Draft Management API

```python
# drafts.py

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import FormDraft, db

drafts = Blueprint('drafts', __name__)

@drafts.route('/api/drafts/save', methods=['POST'])
@login_required
def save_draft():
    """Save or update a draft"""
    data = request.json
    
    draft_id = data.get('draft_id')
    form_type = data.get('form_type')
    form_data = data.get('form_data')
    title = data.get('title')
    
    if draft_id:
        # Update existing draft
        draft = FormDraft.query.filter_by(
            id=draft_id, 
            user_id=current_user.id
        ).first()
        
        if not draft:
            return jsonify({'error': 'Draft not found'}), 404
        
        # Create new version if significant changes
        if data.get('create_version', False):
            new_draft = draft.create_new_version(form_data)
            db.session.add(new_draft)
            draft = new_draft
        else:
            draft.form_data = form_data
            draft.updated_at = datetime.utcnow()
    else:
        # Create new draft
        draft = FormDraft(
            user_id=current_user.id,
            form_type=form_type,
            title=title or f"{form_type.title()} - {datetime.now().strftime('%Y-%m-%d')}",
            form_data=form_data,
            module_acronym=form_data.get('module_acronym', '')
        )
        db.session.add(draft)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'draft_id': draft.id,
        'message': 'Draft saved successfully'
    })

@drafts.route('/api/drafts/load/<int:draft_id>')
@login_required
def load_draft(draft_id):
    """Load a specific draft"""
    draft = FormDraft.query.filter_by(
        id=draft_id,
        user_id=current_user.id
    ).first()
    
    if not draft:
        return jsonify({'error': 'Draft not found'}), 404
    
    return jsonify({
        'success': True,
        'draft': {
            'id': draft.id,
            'title': draft.title,
            'form_type': draft.form_type,
            'form_data': draft.form_data,
            'version': draft.version,
            'created_at': draft.created_at.isoformat(),
            'updated_at': draft.updated_at.isoformat()
        }
    })

@drafts.route('/api/drafts/list')
@login_required
def list_drafts():
    """List user's drafts"""
    form_type = request.args.get('form_type')
    
    query = FormDraft.query.filter_by(
        user_id=current_user.id,
        is_current=True
    )
    
    if form_type:
        query = query.filter_by(form_type=form_type)
    
    drafts = query.order_by(FormDraft.updated_at.desc()).all()
    
    return jsonify({
        'success': True,
        'drafts': [{
            'id': d.id,
            'title': d.title,
            'form_type': d.form_type,
            'module_acronym': d.module_acronym,
            'version': d.version,
            'updated_at': d.updated_at.isoformat()
        } for d in drafts]
    })

@drafts.route('/api/drafts/autosave', methods=['POST'])
@login_required
def autosave_draft():
    """Lightweight autosave endpoint"""
    data = request.json
    draft_id = data.get('draft_id')
    form_data = data.get('form_data')
    
    if not draft_id:
        # Create draft if first autosave
        return save_draft()
    
    # Update without creating new version
    draft = FormDraft.query.filter_by(
        id=draft_id,
        user_id=current_user.id
    ).first()
    
    if draft:
        draft.form_data = form_data
        draft.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'autosaved': True})
    
    return jsonify({'error': 'Draft not found'}), 404
```

### JavaScript Auto-Save Implementation

```javascript
// static/js/draft-manager.js

class DraftManager {
    constructor(formType, formElement) {
        this.formType = formType;
        this.formElement = formElement;
        this.draftId = null;
        this.autoSaveInterval = null;
        this.hasChanges = false;
        
        this.init();
    }
    
    init() {
        // Load draft ID from data attribute if exists
        this.draftId = this.formElement.dataset.draftId;
        
        // Set up auto-save
        this.startAutoSave();
        
        // Track changes
        this.formElement.addEventListener('input', () => {
            this.hasChanges = true;
            this.updateUI('unsaved');
        });
        
        // Warn before leaving with unsaved changes
        window.addEventListener('beforeunload', (e) => {
            if (this.hasChanges) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }
    
    startAutoSave() {
        // Auto-save every 30 seconds
        this.autoSaveInterval = setInterval(() => {
            if (this.hasChanges) {
                this.autoSave();
            }
        }, 30000);
    }
    
    async autoSave() {
        const formData = this.collectFormData();
        
        try {
            const response = await fetch('/api/drafts/autosave', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    draft_id: this.draftId,
                    form_type: this.formType,
                    form_data: formData
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                if (data.draft_id) {
                    this.draftId = data.draft_id;
                }
                this.hasChanges = false;
                this.updateUI('saved');
            }
        } catch (error) {
            console.error('Auto-save failed:', error);
            this.updateUI('error');
        }
    }
    
    collectFormData() {
        const formData = new FormData(this.formElement);
        const data = {};
        
        // Convert FormData to nested object structure
        for (let [key, value] of formData.entries()) {
            // Handle nested fields like 'enrichment_dynamic_content-0-field_type'
            const parts = key.split('-');
            if (parts.length > 1) {
                if (!data[parts[0]]) data[parts[0]] = [];
                const index = parseInt(parts[1]);
                if (!data[parts[0]][index]) data[parts[0]][index] = {};
                data[parts[0]][index][parts[2]] = value;
            } else {
                data[key] = value;
            }
        }
        
        return data;
    }
    
    updateUI(status) {
        const indicator = document.getElementById('save-indicator');
        
        switch(status) {
            case 'saved':
                indicator.textContent = 'All changes saved';
                indicator.className = 'text-green-600';
                break;
            case 'unsaved':
                indicator.textContent = 'Unsaved changes';
                indicator.className = 'text-yellow-600';
                break;
            case 'saving':
                indicator.textContent = 'Saving...';
                indicator.className = 'text-blue-600';
                break;
            case 'error':
                indicator.textContent = 'Error saving';
                indicator.className = 'text-red-600';
                break;
        }
    }
    
    async loadDraft(draftId) {
        try {
            const response = await fetch(`/api/drafts/load/${draftId}`);
            const data = await response.json();
            
            if (data.success) {
                this.populateForm(data.draft.form_data);
                this.draftId = data.draft.id;
                this.hasChanges = false;
                this.updateUI('saved');
            }
        } catch (error) {
            console.error('Failed to load draft:', error);
        }
    }
    
    populateForm(data) {
        // Populate form fields from saved data
        for (let [key, value] of Object.entries(data)) {
            if (typeof value === 'object' && Array.isArray(value)) {
                // Handle field arrays
                value.forEach((item, index) => {
                    for (let [field, val] of Object.entries(item)) {
                        const input = this.formElement.querySelector(
                            `[name="${key}-${index}-${field}"]`
                        );
                        if (input) input.value = val;
                    }
                });
            } else {
                // Handle simple fields
                const input = this.formElement.querySelector(`[name="${key}"]`);
                if (input) input.value = value;
            }
        }
    }
}
```

## 🎨 UI Features

### Draft Management Interface

```html
<!-- templates/components/draft_controls.html -->

<div class="draft-controls bg-gray-100 p-4 rounded-lg mb-6">
    <div class="flex justify-between items-center">
        <div class="flex items-center space-x-4">
            <!-- Load Draft Dropdown -->
            <div class="relative">
                <button id="load-draft-btn" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                    Load Draft ▼
                </button>
                <div id="draft-list" class="hidden absolute top-full mt-2 w-64 bg-white rounded-lg shadow-lg z-10">
                    <!-- Populated by JavaScript -->
                </div>
            </div>
            
            <!-- Save Controls -->
            <button id="save-draft-btn" class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                Save Draft
            </button>
            
            <button id="save-as-new-btn" class="bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600">
                Save as New
            </button>
        </div>
        
        <!-- Status Indicator -->
        <div class="flex items-center space-x-2">
            <span id="save-indicator" class="text-gray-600">All changes saved</span>
            <span id="last-saved" class="text-sm text-gray-500"></span>
        </div>
    </div>
    
    <!-- Draft Info -->
    <div id="draft-info" class="mt-4 text-sm text-gray-600 hidden">
        <span>Working on: <strong id="draft-title"></strong></span>
        <span class="ml-4">Version: <strong id="draft-version"></strong></span>
    </div>
</div>

<!-- Version History Modal -->
<div id="version-modal" class="hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg p-6 max-w-2xl w-full max-h-96 overflow-y-auto">
        <h3 class="text-lg font-bold mb-4">Version History</h3>
        <div id="version-list">
            <!-- Populated by JavaScript -->
        </div>
        <button class="mt-4 bg-gray-500 text-white px-4 py-2 rounded" onclick="closeVersionModal()">
            Close
        </button>
    </div>
</div>
```

### Dashboard for Draft Management

```html
<!-- templates/dashboard.html -->

{% extends "base.html" %}

{% block content %}
<div class="max-w-6xl mx-auto py-8 px-4">
    <h1 class="text-3xl font-bold mb-8">My Documents</h1>
    
    <!-- Filter Tabs -->
    <div class="border-b border-gray-200 mb-6">
        <nav class="-mb-px flex space-x-8">
            <a href="#" class="py-2 px-1 border-b-2 border-blue-500 text-blue-600 font-medium">
                All Drafts
            </a>
            <a href="#" class="py-2 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700">
                Recent
            </a>
            <a href="#" class="py-2 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700">
                Shared with Me
            </a>
        </nav>
    </div>
    
    <!-- Search and Filters -->
    <div class="mb-6 flex justify-between">
        <input type="text" placeholder="Search drafts..." 
               class="px-4 py-2 border rounded-lg w-64">
        
        <select class="px-4 py-2 border rounded-lg">
            <option>All Document Types</option>
            <option>Module Answer Keys</option>
            <option>Vocabulary Worksheets</option>
            <option>Generic Worksheets</option>
        </select>
    </div>
    
    <!-- Draft Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {% for draft in drafts %}
        <div class="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6">
            <div class="flex justify-between items-start mb-4">
                <h3 class="text-lg font-semibold">{{ draft.title }}</h3>
                <span class="text-xs bg-gray-100 px-2 py-1 rounded">
                    v{{ draft.version }}
                </span>
            </div>
            
            <p class="text-sm text-gray-600 mb-4">
                {{ draft.form_type | title | replace('_', ' ') }}
            </p>
            
            <p class="text-xs text-gray-500 mb-4">
                Updated {{ draft.updated_at | timeago }}
            </p>
            
            <div class="flex justify-between">
                <a href="/create-{{ draft.form_type | replace('_', '-') }}?draft={{ draft.id }}" 
                   class="text-blue-600 hover:text-blue-700">
                    Continue Editing
                </a>
                
                <div class="flex space-x-2">
                    <button class="text-gray-600 hover:text-gray-700" title="Duplicate">
                        📋
                    </button>
                    <button class="text-gray-600 hover:text-gray-700" title="Share">
                        🔗
                    </button>
                    <button class="text-red-600 hover:text-red-700" title="Delete">
                        🗑️
                    </button>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

## 🚀 Additional Features

### 1. Template System

```python
class FormTemplate(db.Model):
    """Reusable form templates"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null for system templates
    form_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    template_data = db.Column(db.JSON, nullable=False)
    is_public = db.Column(db.Boolean, default=False)
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@drafts.route('/api/templates/create-from-draft/<int:draft_id>', methods=['POST'])
@login_required
def create_template_from_draft(draft_id):
    """Convert a draft into a reusable template"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id).first()
    if not draft:
        return jsonify({'error': 'Draft not found'}), 404
    
    template = FormTemplate(
        user_id=current_user.id,
        form_type=draft.form_type,
        title=request.json.get('title', f"{draft.title} Template"),
        description=request.json.get('description', ''),
        template_data=draft.form_data,
        is_public=request.json.get('is_public', False)
    )
    
    db.session.add(template)
    db.session.commit()
    
    return jsonify({'success': True, 'template_id': template.id})
```

### 2. Bulk Operations

```python
@drafts.route('/api/drafts/bulk-update', methods=['POST'])
@login_required
def bulk_update_drafts():
    """Update multiple drafts at once (e.g., for curriculum updates)"""
    data = request.json
    module_acronym = data.get('module_acronym')
    updates = data.get('updates', {})
    
    drafts = FormDraft.query.filter_by(
        user_id=current_user.id,
        module_acronym=module_acronym,
        is_current=True
    ).all()
    
    updated_count = 0
    for draft in drafts:
        # Apply updates
        draft_data = draft.form_data.copy()
        draft_data.update(updates)
        
        # Create new version
        new_version = draft.create_new_version(draft_data)
        db.session.add(new_version)
        updated_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'updated_count': updated_count
    })
```

### 3. Export/Import

```python
@drafts.route('/api/drafts/export/<int:draft_id>')
@login_required
def export_draft(draft_id):
    """Export draft as JSON"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id).first()
    if not draft:
        return jsonify({'error': 'Draft not found'}), 404
    
    export_data = {
        'version': '1.0',
        'exported_at': datetime.utcnow().isoformat(),
        'form_type': draft.form_type,
        'title': draft.title,
        'module_acronym': draft.module_acronym,
        'form_data': draft.form_data
    }
    
    return jsonify(export_data), 200, {
        'Content-Disposition': f'attachment; filename="{draft.title}.json"'
    }

@drafts.route('/api/drafts/import', methods=['POST'])
@login_required
def import_draft():
    """Import draft from JSON"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    data = json.load(file)
    
    # Validate import data
    if data.get('version') != '1.0':
        return jsonify({'error': 'Unsupported file version'}), 400
    
    # Create new draft from import
    draft = FormDraft(
        user_id=current_user.id,
        form_type=data['form_type'],
        title=f"{data['title']} (Imported)",
        module_acronym=data.get('module_acronym', ''),
        form_data=data['form_data']
    )
    
    db.session.add(draft)
    db.session.commit()
    
    return jsonify({'success': True, 'draft_id': draft.id})
```

## 📅 Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Set up Render PostgreSQL database
- [ ] Implement User model and authentication
- [ ] Basic login/register pages
- [ ] Session management

### Phase 2: Core Functionality (Week 3-4)
- [ ] FormDraft model and basic CRUD
- [ ] Save/Load API endpoints
- [ ] JavaScript DraftManager class
- [ ] Auto-save functionality
- [ ] Integrate save/load with ALL form types:
  - [ ] Vocabulary Worksheets
  - [ ] PBA Worksheets
  - [ ] Pre Test Worksheets
  - [ ] Post Test Worksheets
  - [ ] Generic Worksheets
  - [ ] Family Briefings
  - [ ] RCA Worksheets
  - [ ] Module Guides
  - [ ] Module Answer Keys

### Phase 3: UI Enhancement (Week 5-6)
- [ ] Dashboard page
- [ ] Draft management controls
- [ ] Load draft dropdown
- [ ] Save indicators
- [ ] Version history modal

### Phase 4: Advanced Features (Week 7-8)
- [ ] Template system
- [ ] Sharing functionality
- [ ] Bulk operations
- [ ] Export/Import
- [ ] Activity logging

### Phase 5: Polish & Deploy (Week 9-10)
- [ ] Error handling
- [ ] Loading states
- [ ] Mobile responsiveness
- [ ] Performance optimization
- [ ] Production deployment

## 🚀 Deployment Guide

### 1. Render Setup

```yaml
# render.yaml
services:
  - type: web
    name: nola-docs
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn app:app"
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: nola-docs-db
          property: connectionString
      - key: SECRET_KEY
        generateValue: true
      - key: FLASK_ENV
        value: production

databases:
  - name: nola-docs-db
    databaseName: nola_docs
    user: nola_docs_user
    plan: free
```

### 2. Environment Variables

```python
# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        # Fix for SQLAlchemy 1.4+
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # File uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'temp_uploads'
```

### 3. Database Initialization

```python
# init_db.py
from app import app, db
from models import User, FormDraft, GeneratedDocument

def init_database():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create admin user if doesn't exist
        admin = User.query.filter_by(email='admin@noladocs.com').first()
        if not admin:
            admin = User(
                email='admin@noladocs.com',
                username='admin',
                is_admin=True
            )
            admin.set_password('change-this-password')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created!")

if __name__ == '__main__':
    init_database()
```

### 4. Updated Requirements

```txt
# requirements.txt (additions)
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.2
Flask-Migrate==4.0.4
psycopg2-binary==2.9.7
python-dotenv==1.0.0
gunicorn==21.2.0
```

## 🔒 Security Considerations

1. **Authentication**
   - Password hashing with werkzeug
   - Session timeouts
   - CSRF protection

2. **Authorization**
   - Users can only access their own drafts
   - Sharing permissions enforced
   - Admin-only routes protected

3. **Data Protection**
   - SQL injection prevention via ORM
   - XSS protection in templates
   - File upload validation

4. **API Security**
   - Rate limiting on save endpoints
   - JSON schema validation
   - Error message sanitization

## 📊 Monitoring & Maintenance

1. **Database Maintenance**
   ```sql
   -- Clean up old versions (keep last 5)
   DELETE FROM form_draft 
   WHERE id NOT IN (
       SELECT id FROM (
           SELECT id, ROW_NUMBER() OVER (
               PARTITION BY parent_draft_id 
               ORDER BY version DESC
           ) as rn 
           FROM form_draft
       ) t WHERE rn <= 5
   );
   ```

2. **Usage Analytics**
   - Track most-used templates
   - Monitor storage usage
   - User activity patterns

3. **Backup Strategy**
   - Daily PostgreSQL backups
   - Export critical drafts
   - Version control for templates

---

This implementation plan provides a solid foundation for adding save/load functionality to NOLA Docs. Start with Phase 1 and iterate based on user feedback. The modular approach allows you to implement features incrementally while maintaining a working application throughout the process. 