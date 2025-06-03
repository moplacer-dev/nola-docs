from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User account model with admin/regular user roles"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    drafts = db.relationship('FormDraft', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    generated_docs = db.relationship('GeneratedDocument', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify user password"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def __repr__(self):
        return f'<User {self.username}>'

class FormDraft(db.Model):
    """Store form drafts with versioning support"""
    __tablename__ = 'form_drafts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    form_type = db.Column(db.String(50), nullable=False, index=True)  # 'vocabulary', 'module_answer_key', etc.
    title = db.Column(db.String(200), nullable=False)
    module_acronym = db.Column(db.String(20), index=True)
    form_data = db.Column(db.JSON, nullable=False)  # PostgreSQL native JSON
    is_current = db.Column(db.Boolean, default=True)  # Latest version flag
    version = db.Column(db.Integer, default=1)
    parent_draft_id = db.Column(db.Integer, db.ForeignKey('form_drafts.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    versions = db.relationship('FormDraft', backref=db.backref('parent_draft', remote_side=[id]))
    generated_documents = db.relationship('GeneratedDocument', backref='source_draft', lazy='dynamic')
    
    def create_new_version(self, new_data, new_title=None):
        """Create a new version of this draft"""
        # Mark current as not current
        self.is_current = False
        db.session.add(self)
        
        # Create new version
        new_version = FormDraft(
            user_id=self.user_id,
            form_type=self.form_type,
            title=new_title or self.title,
            module_acronym=self.module_acronym,
            form_data=new_data,
            is_current=True,
            version=self.version + 1,
            parent_draft_id=self.parent_draft_id or self.id
        )
        return new_version
    
    @property
    def document_type_display(self):
        """Human-readable document type"""
        type_map = {
            'vocabulary': 'Vocabulary Worksheet',
            'pba': 'PBA Worksheet',
            'pretest': 'Pre-Test Worksheet',
            'posttest': 'Post-Test Worksheet',
            'generic': 'Generic Worksheet',
            'familybriefing': 'Family Briefing',
            'rca': 'RCA Worksheet',
            'moduleGuide': 'Module Guide',
            'moduleAnswerKey': 'Module Answer Key',
            'moduleActivitySheet': 'Module Activity Sheet'
        }
        return type_map.get(self.form_type, self.form_type.title())
    
    def __repr__(self):
        return f'<FormDraft {self.title} v{self.version}>'

class GeneratedDocument(db.Model):
    """Track generated documents with download capabilities"""
    __tablename__ = 'generated_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    draft_id = db.Column(db.Integer, db.ForeignKey('form_drafts.id'), nullable=True)
    document_type = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500))  # Relative path to file
    module_acronym = db.Column(db.String(20))
    file_size = db.Column(db.Integer)  # File size in bytes
    download_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_downloaded = db.Column(db.DateTime)
    
    def increment_download(self):
        """Track document download"""
        self.download_count += 1
        self.last_downloaded = datetime.utcnow()
    
    @property
    def file_size_human(self):
        """Human-readable file size"""
        if not self.file_size:
            return "Unknown"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def __repr__(self):
        return f'<GeneratedDocument {self.filename}>'

class TemplateFile(db.Model):
    """Store template files in database for version control"""
    __tablename__ = 'template_files'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # e.g., 'vocabulary_worksheet_master'
    display_name = db.Column(db.String(200))  # e.g., 'Vocabulary Worksheet Template'
    file_data = db.Column(db.LargeBinary)  # BLOB storage for template
    file_size = db.Column(db.Integer)
    version = db.Column(db.String(20), default='1.0')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<TemplateFile {self.name} v{self.version}>'

# Optional: Activity logging for admin insights
class ActivityLog(db.Model):
    """Track user activities for analytics and debugging"""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # 'draft_saved', 'document_generated', etc.
    details = db.Column(db.JSON)  # Additional context
    ip_address = db.Column(db.String(45))  # Support IPv6
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    @classmethod
    def log_activity(cls, action, user_id=None, details=None, request=None):
        """Convenience method to log activities"""
        log = cls(
            user_id=user_id,
            action=action,
            details=details or {},
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None
        )
        db.session.add(log)
        return log 