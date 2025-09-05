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
        """Return user-friendly name for the document type"""
        type_map = {
            'vocabulary': 'Vocabulary Worksheet',
            'test': 'Test Worksheet',
            'pba': 'PBA Worksheet',
            'familybriefing': 'Family Briefing',
            'rca': 'RCA Worksheet',
            'generic': 'Generic Worksheet',
            'moduleactivity': 'Module Activity Sheet',
            'moduleguide': 'Module Guide',
            'moduleAnswerKey': 'Module Answer Key',
            'module_answer_key2': 'Module Answer Key 2.0',
            'horizontal_lesson_plan': 'Horizontal Lesson Plan',
            'curriculum_design_build': 'Curriculum Design Build'
        }
        return type_map.get(self.form_type, self.form_type.title())
    
    def __repr__(self):
        return f'<FormDraft {self.title} v{self.version}>'


class LessonPlanModule(db.Model):
    """Streamlined lesson plan modules - pre-populated with all session and enrichment data"""
    __tablename__ = 'lesson_plan_modules'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True, unique=True)  # "Weather v1.1", "Weights and Measures"
    subject = db.Column(db.String(50), nullable=True, index=True)  # "Science", "Math" - can be set later
    grade_level = db.Column(db.Integer, nullable=True, index=True)  # 7, 8, or NULL for multi-grade
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sessions = db.relationship('LessonPlanSession', backref='module', lazy='dynamic',
                              cascade='all, delete-orphan',
                              order_by='LessonPlanSession.session_number')
    enrichments = db.relationship('LessonPlanEnrichment', backref='module', lazy='dynamic',
                                 cascade='all, delete-orphan',
                                 order_by='LessonPlanEnrichment.enrichment_number')

    def __repr__(self):
        return f'<LessonPlanModule {self.name}>'


class LessonPlanSession(db.Model):
    """Pre-populated session data - maps directly to CSV columns"""
    __tablename__ = 'lesson_plan_sessions'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('lesson_plan_modules.id'), nullable=False, index=True)
    session_number = db.Column(db.Integer, nullable=False)  # 1-7
    focus = db.Column(db.Text)  # "Layers of the Atmosphere; Weather Measurement"
    objectives = db.Column(db.Text)  # Bullet point objectives 
    materials = db.Column(db.Text)  # "Weather Monitor"
    teacher_preparations = db.Column(db.Text)  # "Ensure the Weather Station has been operational..."
    performance_assessment_questions = db.Column(db.Text)  # Assessment questions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('module_id', 'session_number', name='uq_module_session'),
        db.Index('ix_module_sessions', 'module_id', 'session_number'),
    )

    def __repr__(self):
        return f'<LessonPlanSession Module:{self.module_id} Session:{self.session_number}>'


class LessonPlanEnrichment(db.Model):
    """Pre-populated enrichment activities - maps directly to CSV columns"""
    __tablename__ = 'lesson_plan_enrichments'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('lesson_plan_modules.id'), nullable=False, index=True)
    enrichment_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3, etc.
    title = db.Column(db.String(500))  # "Dew Point Calculation"
    description = db.Column(db.Text)  # Full activity description
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('module_id', 'enrichment_number', name='uq_module_enrichment'),
        db.Index('ix_module_enrichments', 'module_id', 'enrichment_number'),
    )

    def __repr__(self):
        return f'<LessonPlanEnrichment Module:{self.module_id} #{self.enrichment_number}>'

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
            'module_answer_key2': 'Module Answer Key 2.0',
            'moduleActivitySheet': 'Module Activity Sheet',
            'horizontal_lesson_plan': 'Horizontal Lesson Plan',
            'curriculum_design_build': 'Curriculum Design Build'
        }
        return type_map.get(self.document_type, self.document_type.title())
    
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

class State(db.Model):
    """US States for correlation reports"""
    __tablename__ = 'states'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(2), unique=True, nullable=False, index=True)  # e.g., 'LA'
    name = db.Column(db.String(100), nullable=False)  # e.g., 'Louisiana'
    
    def __repr__(self):
        return f'<State {self.code}: {self.name}>'

class Standard(db.Model):
    """Educational standards (CCSS, NGSS, etc.)"""
    __tablename__ = 'standards'
    
    id = db.Column(db.Integer, primary_key=True)
    framework = db.Column(db.String(20), nullable=False)   # 'CCSS-M' or 'NGSS'
    subject = db.Column(db.String(10), nullable=False)      # 'MATH' or 'SCIENCE'
    grade_band = db.Column(db.String(10))                   # 'MS', 'HS', or None
    grade_level = db.Column(db.Integer)                     # 7, 8, None
    code = db.Column(db.String(50), nullable=False)         # e.g., '8.EE.A.1', 'MS-PS1-1'
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('framework', 'code', name='uq_framework_code'),
        db.Index('ix_framework_subject_grade', 'framework','subject','grade_level'),
    )
    
    # Relationships
    module_mappings = db.relationship('ModuleStandardMapping', backref='standard', lazy='dynamic')
    
    def __repr__(self):
        return f'<Standard {self.framework}:{self.code}>'

class Module(db.Model):
    """Star Academy modules"""
    __tablename__ = 'modules'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(10), nullable=False)      # 'MATH' or 'SCIENCE'
    grade_level = db.Column(db.Integer)                     # 7, 8, None for banded MS science
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('title','subject','grade_level', name='uq_module_title_subject_grade'),)
    
    # Relationships
    standard_mappings = db.relationship('ModuleStandardMapping', backref='module', lazy='dynamic')
    
    def __repr__(self):
        return f'<Module {self.title} ({self.subject})>'

class ModuleStandardMapping(db.Model):
    """Maps modules to standards"""
    __tablename__ = 'module_standard_mappings'
    
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), primary_key=True)
    standard_id = db.Column(db.Integer, db.ForeignKey('standards.id'), primary_key=True)
    source = db.Column(db.String(50), default='MATRIX_V1')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Mapping Module:{self.module_id} -> Standard:{self.standard_id}>'

# IPL (Individual Pacing List) Models
class IplModule(db.Model):
    """IPL modules - 28 total modules like 'Module: Astronomy'"""
    __tablename__ = 'ipl_modules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)  # "Module: Astronomy"
    subject = db.Column(db.String(50), nullable=True)
    grade_level = db.Column(db.Integer, nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    entries = db.relationship('IplEntry', backref='module', cascade='all, delete-orphan', order_by='IplEntry.order_index')
    
    def __repr__(self):
        return f'<IplModule {self.name}>'

class IplEntry(db.Model):
    """Individual IPL entries within a module"""
    __tablename__ = 'ipl_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('ipl_modules.id'), nullable=False)
    unit_name = db.Column(db.String(200), nullable=True)  # "Real Number Systems", "Equations" (can be null for continued rows)
    ipl_title = db.Column(db.String(200), nullable=True)  # "Ordering Numbers", "Scientific Notation 1" (can be null for continued rows)
    goal_text = db.Column(db.Text, nullable=True)  # "Order numbers using the number line."
    order_index = db.Column(db.Integer, default=0)  # To maintain original order
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<IplEntry {self.unit_name or "continued"}: {self.ipl_title or "continued"}>'