from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, FieldList, FormField, IntegerField, HiddenField, BooleanField, RadioField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from docxtpl import DocxTemplate, RichText, InlineImage
from docx import Document
from docx.shared import Inches, Pt
from werkzeug.utils import secure_filename
from flask_wtf.file import FileField, FileAllowed
import os
import shutil
import tempfile
from datetime import datetime

# Add database and authentication imports
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Update app configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'temp_uploads'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///nola_docs.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database and migrations
from models import db, User, FormDraft, GeneratedDocument, TemplateFile, ActivityLog
db.init_app(app)
migrate = Migrate(app, db)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
from auth import auth
app.register_blueprint(auth)

# Helper function to escape XML special characters for DOCX
def escape_xml(text):
    """Escape special XML characters for safe inclusion in DOCX templates"""
    if not text:
        return text
    
    # XML special characters that need escaping
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&apos;'
    }
    
    # Apply replacements
    for char, escaped in replacements.items():
        text = text.replace(char, escaped)
    
    return text

# Custom validator for correct answer field
def validate_answer_choice(form, field):
    """Validate that the answer is A, B, C, or D"""
    if field.data and field.data.upper() not in ['A', 'B', 'C', 'D', '']:
        raise ValidationError('Answer must be A, B, C, or D')

# Form for individual vocabulary words
class VocabularyWordForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    word = StringField('Term', validators=[Optional(), Length(min=1, max=100)])

# Main vocabulary worksheet form
class VocabularyWorksheetForm(FlaskForm):
    module_acronym = StringField('Module Acronym', 
                                validators=[DataRequired(), Length(min=1, max=20)],
                                render_kw={"placeholder": "e.g., APHY, CHEM, BIOE"})
    
    # Increased to 25 term fields for more vocabulary words
    words = FieldList(FormField(VocabularyWordForm), min_entries=25, max_entries=30)
    
    submit = SubmitField('Generate Worksheet')
    
    def validate_words(self, field):
        # Check if at least one word is provided
        has_words = any(word_data['word'] for word_data in field.data if word_data.get('word'))
        if not has_words:
            raise ValidationError('Please enter at least one vocabulary term.')

# ===== PBA WORKSHEET FORMS =====

# Form for individual assessments
class PBAAssessmentForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    assessment = StringField('Assessment', validators=[Optional(), Length(min=1, max=500)])

# Main PBA worksheet form
class PBAWorksheetForm(FlaskForm):
    module_acronym = StringField('Module Acronym', 
                                validators=[DataRequired(), Length(min=1, max=20)],
                                render_kw={"placeholder": "e.g., APHY, CHEM, BIOE"})
    
    session_number = StringField('Session Number', 
                                validators=[DataRequired(), Length(min=1, max=10)],
                                render_kw={"placeholder": "e.g., 1, 2, 3"})
    
    section_header = StringField('Section Header', 
                                validators=[DataRequired(), Length(min=1, max=100)],
                                render_kw={"placeholder": "e.g., Squares and Square Roots"})
    
    # 4 assessment fields
    assessments = FieldList(FormField(PBAAssessmentForm), min_entries=4, max_entries=4)
    
    submit = SubmitField('Generate PBA Worksheet')
    
    def validate_assessments(self, field):
        # Check if at least one assessment is provided
        has_assessments = any(assessment_data['assessment'] for assessment_data in field.data if assessment_data.get('assessment'))
        if not has_assessments:
            raise ValidationError('Please enter at least one assessment.')

# ===== POST TEST WORKSHEET FORMS =====

# Form for individual multiple choice questions
class PostTestQuestionForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    question_text = StringField('Question', validators=[Optional(), Length(min=1, max=500)])
    choice_a = StringField('Choice A', validators=[Optional(), Length(min=1, max=200)])
    choice_b = StringField('Choice B', validators=[Optional(), Length(min=1, max=200)])
    choice_c = StringField('Choice C', validators=[Optional(), Length(min=1, max=200)])
    choice_d = StringField('Choice D', validators=[Optional(), Length(min=1, max=200)])

# Main Post Test worksheet form
class PostTestWorksheetForm(FlaskForm):
    module_acronym = StringField('Module Acronym', 
                                validators=[DataRequired(), Length(min=1, max=20)],
                                render_kw={"placeholder": "e.g., APHY, CHEM, BIOE"})
    
    # Multiple choice questions (let's start with 10 questions)
    questions = FieldList(FormField(PostTestQuestionForm), min_entries=10, max_entries=15)
    
    submit = SubmitField('Generate Post Test Worksheet')
    
    def validate_questions(self, field):
        # Check if at least one question is provided
        has_questions = any(question_data['question_text'] for question_data in field.data if question_data.get('question_text'))
        if not has_questions:
            raise ValidationError('Please enter at least one question.')

# ===== PRE TEST WORKSHEET FORMS =====

# Form for individual multiple choice questions
class PreTestQuestionForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    question_text = StringField('Question', validators=[Optional(), Length(min=1, max=500)])
    choice_a = StringField('Choice A', validators=[Optional(), Length(min=1, max=200)])
    choice_b = StringField('Choice B', validators=[Optional(), Length(min=1, max=200)])
    choice_c = StringField('Choice C', validators=[Optional(), Length(min=1, max=200)])
    choice_d = StringField('Choice D', validators=[Optional(), Length(min=1, max=200)])

# Main Pre Test worksheet form
class PreTestWorksheetForm(FlaskForm):
    module_acronym = StringField('Module Acronym', 
                                validators=[DataRequired(), Length(min=1, max=20)],
                                render_kw={"placeholder": "e.g., APHY, CHEM, BIOE"})
    
    # Multiple choice questions (let's start with 10 questions)
    questions = FieldList(FormField(PreTestQuestionForm), min_entries=10, max_entries=15)
    
    submit = SubmitField('Generate Pre Test Worksheet')
    
    def validate_questions(self, field):
        # Check if at least one question is provided
        has_questions = any(question_data['question_text'] for question_data in field.data if question_data.get('question_text'))
        if not has_questions:
            raise ValidationError('Please enter at least one question.')

# ===== TEST WORKSHEET FORMS (Combined Pre-Test and Post-Test) =====

# Form for individual multiple choice questions
class TestQuestionForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    question_text = StringField('Question', validators=[Optional(), Length(min=1, max=500)])
    choice_a = StringField('Choice A', validators=[Optional(), Length(min=1, max=200)])
    choice_b = StringField('Choice B', validators=[Optional(), Length(min=1, max=200)])
    choice_c = StringField('Choice C', validators=[Optional(), Length(min=1, max=200)])
    choice_d = StringField('Choice D', validators=[Optional(), Length(min=1, max=200)])

# Main Test worksheet form (handles both Pre-Test and Post-Test)
class TestWorksheetForm(FlaskForm):
    test_type = RadioField('Test Type',
                          choices=[('pre', 'Pre-Test Worksheet'), ('post', 'Post-Test Worksheet')],
                          default='pre',
                          validators=[DataRequired()])
    
    module_acronym = StringField('Module Acronym', 
                                validators=[DataRequired(), Length(min=1, max=20)],
                                render_kw={"placeholder": "e.g., APHY, CHEM, BIOE"})
    
    # Multiple choice questions (10-15 questions)
    questions = FieldList(FormField(TestQuestionForm), min_entries=10, max_entries=15)
    
    submit = SubmitField('Generate Test Worksheet')
    
    def validate_questions(self, field):
        # Check if at least one question is provided
        has_questions = any(question_data['question_text'] for question_data in field.data if question_data.get('question_text'))
        if not has_questions:
            raise ValidationError('Please enter at least one question.')

# ===== GENERIC WORKSHEET FORMS =====

# Dynamic field form - represents one field in the worksheet
class DynamicFieldForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    field_type = HiddenField()  # Store the field type
    
    # Section Header fields
    section_title = StringField('Section Title', validators=[Optional(), Length(max=200)])
    
    # Question fields (shared)
    question_number = IntegerField('Question Number', validators=[Optional()])
    question_text = TextAreaField('Question Text', validators=[Optional(), Length(max=2000)])
    
    # Multiple Choice specific fields
    choice_count = SelectField('Number of Choices', 
                              choices=[('2', '2 choices'), ('3', '3 choices'), ('4', '4 choices')],
                              default='4')
    choice_a = StringField('Choice A', validators=[Optional(), Length(max=200)])
    choice_b = StringField('Choice B', validators=[Optional(), Length(max=200)])
    choice_c = StringField('Choice C', validators=[Optional(), Length(max=200)])
    choice_d = StringField('Choice D', validators=[Optional(), Length(max=200)])
    
    # Section Instructions field
    instructions_text = TextAreaField('Instructions', validators=[Optional(), Length(max=3000)])
    
    # Paragraph Text field
    paragraph_text = TextAreaField('Paragraph Text', validators=[Optional(), Length(max=3000)])
    
    # Math Problem field
    math_expression = StringField('Math Expression', validators=[Optional(), Length(max=1000)])
    
    # Image upload fields
    image_file = FileField('Image File', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])

# Worksheet Answer Key form - represents a single worksheet container
class WorksheetAnswerKeyForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    worksheet_title = StringField('Worksheet Title', 
                                 validators=[Optional(), Length(max=200)],
                                 render_kw={"placeholder": "e.g., Chapter 3 Review, Lab Answer Key"})
    
    # Dynamic fields for this specific worksheet
    dynamic_content = FieldList(FormField(DynamicFieldForm), min_entries=0)

# Main Generic Worksheet form
class GenericWorksheetForm(FlaskForm):
    # Fixed fields that always appear first
    module_acronym = StringField('Module Acronym', 
                                validators=[DataRequired(), Length(min=1, max=20)],
                                render_kw={"placeholder": "e.g., APHY, CHEM, BIOE"})
    
    worksheet_title = StringField('Worksheet Title', 
                                 validators=[DataRequired(), Length(min=1, max=100)],
                                 render_kw={"placeholder": "e.g., Heat Transfer Lab"})
    
    # Dynamic fields
    dynamic_fields = FieldList(FormField(DynamicFieldForm), min_entries=0)
    
    submit = SubmitField('Generate Generic Worksheet')

# ===== FAMILY BRIEFING FORM =====

class FamilyBriefingForm(FlaskForm):
    # Module name
    module_name = StringField('Module Acronym', 
                            validators=[DataRequired(), Length(min=1, max=100)],
                            render_kw={"placeholder": "e.g., APHY, CHEM, BIOE"})
    
    # Intro sentence
    introsentence = TextAreaField('Finish the sentence: During this module, your child will...', 
                                validators=[Optional(), Length(max=500)],
                                render_kw={"placeholder": "Enter 1-2 sentences from the original Parent Briefing document (e.g., explore the properties of matter and how it interacts with the environment.)"})
    
    # Learning Objectives (4)
    learningobjective1 = TextAreaField('Learning Objective 1', validators=[Optional(), Length(max=300)])
    learningobjective2 = TextAreaField('Learning Objective 2', validators=[Optional(), Length(max=300)])
    learningobjective3 = TextAreaField('Learning Objective 3', validators=[Optional(), Length(max=300)])
    learningobjective4 = TextAreaField('Learning Objective 4', validators=[Optional(), Length(max=300)])
    
    # Session Activities (7)
    activityname1 = StringField('Activity 1', validators=[Optional(), Length(max=300)])
    activityname2 = StringField('Activity 2', validators=[Optional(), Length(max=300)])
    activityname3 = StringField('Activity 3', validators=[Optional(), Length(max=300)])
    activityname4 = StringField('Activity 4', validators=[Optional(), Length(max=300)])
    activityname5 = StringField('Activity 5', validators=[Optional(), Length(max=300)])
    activityname6 = StringField('Activity 6', validators=[Optional(), Length(max=300)])
    activityname7 = StringField('Activity 7', validators=[Optional(), Length(max=300)])
    
    # Key Terminology (21 terms)
    term1 = StringField('Term 1', validators=[Optional(), Length(max=100)])
    term2 = StringField('Term 2', validators=[Optional(), Length(max=100)])
    term3 = StringField('Term 3', validators=[Optional(), Length(max=100)])
    term4 = StringField('Term 4', validators=[Optional(), Length(max=100)])
    term5 = StringField('Term 5', validators=[Optional(), Length(max=100)])
    term6 = StringField('Term 6', validators=[Optional(), Length(max=100)])
    term7 = StringField('Term 7', validators=[Optional(), Length(max=100)])
    term8 = StringField('Term 8', validators=[Optional(), Length(max=100)])
    term9 = StringField('Term 9', validators=[Optional(), Length(max=100)])
    term10 = StringField('Term 10', validators=[Optional(), Length(max=100)])
    term11 = StringField('Term 11', validators=[Optional(), Length(max=100)])
    term12 = StringField('Term 12', validators=[Optional(), Length(max=100)])
    term13 = StringField('Term 13', validators=[Optional(), Length(max=100)])
    term14 = StringField('Term 14', validators=[Optional(), Length(max=100)])
    term15 = StringField('Term 15', validators=[Optional(), Length(max=100)])
    term16 = StringField('Term 16', validators=[Optional(), Length(max=100)])
    term17 = StringField('Term 17', validators=[Optional(), Length(max=100)])
    term18 = StringField('Term 18', validators=[Optional(), Length(max=100)])
    term19 = StringField('Term 19', validators=[Optional(), Length(max=100)])
    term20 = StringField('Term 20', validators=[Optional(), Length(max=100)])
    term21 = StringField('Term 21', validators=[Optional(), Length(max=100)])
    
    # Key Concepts (3 concepts with explanations)
    keyconcept1_name = StringField('Key Concept 1 Name', validators=[Optional(), Length(max=100)])
    keyconcept1_explanation = TextAreaField('Key Concept 1 Explanation', validators=[Optional(), Length(max=600)])
    
    keyconcept2_name = StringField('Key Concept 2 Name', validators=[Optional(), Length(max=100)])
    keyconcept2_explanation = TextAreaField('Key Concept 2 Explanation', validators=[Optional(), Length(max=600)])
    
    keyconcept3_name = StringField('Key Concept 3 Name', validators=[Optional(), Length(max=100)])
    keyconcept3_explanation = TextAreaField('Key Concept 3 Explanation', validators=[Optional(), Length(max=600)])
    
    submit = SubmitField('Generate Family Briefing')

# ===== RCA WORKSHEET FORMS =====

# Form for individual RCA questions (Research, Challenge, Application)
class RCAQuestionForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    question_text = StringField('Question', validators=[Optional(), Length(min=1, max=500)])
    choice_a = StringField('Choice A', validators=[Optional(), Length(min=1, max=200)])
    choice_b = StringField('Choice B', validators=[Optional(), Length(min=1, max=200)])
    choice_c = StringField('Choice C', validators=[Optional(), Length(min=1, max=200)])
    choice_d = StringField('Choice D', validators=[Optional(), Length(min=1, max=200)])

# Main RCA worksheet form
class RCAWorksheetForm(FlaskForm):
    module_acronym = StringField('Module Acronym', 
                                validators=[DataRequired(), Length(min=1, max=20)],
                                render_kw={"placeholder": "e.g., APHY, CHEM, BIOE"})
    
    session_number = StringField('Session Number', 
                                validators=[DataRequired(), Length(min=1, max=10)],
                                render_kw={"placeholder": "e.g., 1, 2, 3"})
    
    # Exactly 3 questions - one for Research, Challenge, and Application
    questions = FieldList(FormField(RCAQuestionForm), min_entries=3, max_entries=3)
    
    # Image upload field
    image_file = FileField('Image File', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    
    submit = SubmitField('Generate RCA Worksheet')
    
    def validate_questions(self, field):
        # Check if at least one question is provided
        has_questions = any(question_data['question_text'] for question_data in field.data if question_data.get('question_text'))
        if not has_questions:
            raise ValidationError('Please enter at least one question.')

# ===== MODULE GUIDE FORMS =====

# Form for individual standards
class ModuleGuideStandardForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    standard = StringField('Standard', validators=[Optional(), Length(min=1, max=600)])

# Form for individual vocabulary terms (reuse pattern from vocabulary template)
class ModuleGuideVocabForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    term = StringField('Term', validators=[Optional(), Length(min=1, max=100)])

# Form for individual career entries
class ModuleGuideCareersForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    career = StringField('Career', validators=[Optional(), Length(min=1, max=300)])

# Session Notes forms for Module Guide
class SessionGoalForm(FlaskForm):
    class Meta:
        csrf = False
    
    goal = StringField('Goal', validators=[Optional(), Length(min=1, max=600)])

class SessionPrepForm(FlaskForm):
    class Meta:
        csrf = False
    
    prep = StringField('Teacher Preparation', validators=[Optional(), Length(min=1, max=600)])

class SessionAssessmentForm(FlaskForm):
    class Meta:
        csrf = False
    
    assessment = StringField('Assessment', validators=[Optional(), Length(min=1, max=600)])

# Additional Resources form classes
class EnrichmentActivityForm(FlaskForm):
    class Meta:
        csrf = False
    
    activity = StringField('Enrichment Activity', validators=[Optional(), Length(min=1, max=600)])

class LocallySourcedMaterialForm(FlaskForm):
    class Meta:
        csrf = False
    
    material = StringField('Locally Sourced Material', validators=[Optional(), Length(min=1, max=600)])

class MaintenanceItemForm(FlaskForm):
    class Meta:
        csrf = False
    
    item = StringField('Maintenance Item', validators=[Optional(), Length(min=1, max=600)])

class AssemblyInstructionForm(FlaskForm):
    class Meta:
        csrf = False
    
    instruction = StringField('Assembly Instruction', validators=[Optional(), Length(min=1, max=600)])

class RecommendedWebsiteForm(FlaskForm):
    class Meta:
        csrf = False
    
    title = StringField('Website Title', validators=[Optional(), Length(min=1, max=100)])
    url = StringField('Website URL', validators=[Optional(), Length(min=1, max=300)])

class SessionNoteForm(FlaskForm):
    class Meta:
        csrf = False
    
    # Focus field
    focus = StringField('Session Focus', validators=[Optional(), Length(min=1, max=200)])
    
    # Goals - dynamic list (6-8 goals)
    goals = FieldList(FormField(SessionGoalForm), min_entries=6, max_entries=8)
    
    # Materials - fixed fields (15 materials like vocabulary)
    material1 = StringField('Material 1', validators=[Optional(), Length(max=100)])
    material2 = StringField('Material 2', validators=[Optional(), Length(max=100)])
    material3 = StringField('Material 3', validators=[Optional(), Length(max=100)])
    material4 = StringField('Material 4', validators=[Optional(), Length(max=100)])
    material5 = StringField('Material 5', validators=[Optional(), Length(max=100)])
    material6 = StringField('Material 6', validators=[Optional(), Length(max=100)])
    material7 = StringField('Material 7', validators=[Optional(), Length(max=100)])
    material8 = StringField('Material 8', validators=[Optional(), Length(max=100)])
    material9 = StringField('Material 9', validators=[Optional(), Length(max=100)])
    material10 = StringField('Material 10', validators=[Optional(), Length(max=100)])
    material11 = StringField('Material 11', validators=[Optional(), Length(max=100)])
    material12 = StringField('Material 12', validators=[Optional(), Length(max=100)])
    material13 = StringField('Material 13', validators=[Optional(), Length(max=100)])
    material14 = StringField('Material 14', validators=[Optional(), Length(max=100)])
    material15 = StringField('Material 15', validators=[Optional(), Length(max=100)])
    
    # Teacher Preparations - dynamic list (4-6 items)
    preparations = FieldList(FormField(SessionPrepForm), min_entries=4, max_entries=6)
    
    # Performance Based Assessments - dynamic list (4-6 items)
    assessments = FieldList(FormField(SessionAssessmentForm), min_entries=4, max_entries=6)

# Main Module Guide form (Section 1 - Teacher Tips)
class ModuleGuideForm(FlaskForm):
    module_acronym = StringField('Module Acronym', 
                               validators=[DataRequired(), Length(min=1, max=20)],
                               render_kw={"placeholder": "e.g., APHY, CHEM, BIOE"})
    
    teachertips_statement = TextAreaField('Teacher Tips Overview', 
                                        validators=[Optional(), Length(max=1000)],
                                        render_kw={"placeholder": "Enter the overview from the Teacher Tips document (e.g., In the Environmental Math Module, students will...)"})
    
    # Standards fields (starting with 6)
    standards = FieldList(FormField(ModuleGuideStandardForm), min_entries=6, max_entries=10)
    
    # Vocabulary fields (starting with 25)
    vocab_terms = FieldList(FormField(ModuleGuideVocabForm), min_entries=25, max_entries=30)
    
    # Careers fields (starting with 14)
    careers = FieldList(FormField(ModuleGuideCareersForm), min_entries=14, max_entries=20)
    
    # Session Notes - exactly 7 sessions
    sessions = FieldList(FormField(SessionNoteForm), min_entries=7, max_entries=7)
    
    # Additional Resources fields
    enrichment_activities = FieldList(FormField(EnrichmentActivityForm), min_entries=4, max_entries=10)
    locally_sourced_materials = FieldList(FormField(LocallySourcedMaterialForm), min_entries=4, max_entries=10)
    maintenance_items = FieldList(FormField(MaintenanceItemForm), min_entries=4, max_entries=10)
    assembly_instructions = FieldList(FormField(AssemblyInstructionForm), min_entries=4, max_entries=10)
    recommended_websites = FieldList(FormField(RecommendedWebsiteForm), min_entries=3, max_entries=10)
    
    submit = SubmitField('Generate Module Guide')
    
    def validate_standards(self, field):
        # Check if at least one standard is provided
        has_standards = any(standard_data['standard'] for standard_data in field.data if standard_data.get('standard'))
        if not has_standards:
            raise ValidationError('Please enter at least one standard.')

# ===== MODULE ANSWER KEY FORMS =====

# Form for individual multiple choice questions (used in pretest, posttest, and RCA)
class AnswerKeyQuestionForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    question_text = StringField('Question', validators=[Optional(), Length(min=1, max=600)])
    choice_a = StringField('Choice A', validators=[Optional(), Length(min=1, max=200)])
    choice_b = StringField('Choice B', validators=[Optional(), Length(min=1, max=200)])
    choice_c = StringField('Choice C', validators=[Optional(), Length(min=1, max=200)])
    choice_d = StringField('Choice D', validators=[Optional(), Length(min=1, max=200)])
    # Changed from SelectField to StringField to avoid nested form issues
    correct_answer = StringField('Correct Answer', 
                                validators=[Optional(), Length(max=1), validate_answer_choice],
                                render_kw={"placeholder": "A, B, C, or D", "maxlength": "1", "style": "text-transform: uppercase;"})

# Form for RCA sessions (sessions 2-5, each with 3 questions)
class RCASessionForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    # Each session has exactly 3 questions: Research, Challenge, Application
    questions = FieldList(FormField(AnswerKeyQuestionForm), min_entries=3, max_entries=3)

# Form for individual PBA assessment questions
class PBAAssessmentQuestionForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    question = StringField('Assessment Question', validators=[Optional(), Length(min=1, max=600)])
    correct_answer = TextAreaField('Correct Answer', validators=[Optional(), Length(max=800)])

# Form for PBA sessions
class PBASessionForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    session_number = IntegerField('Session Number', validators=[Optional()])
    activity_name = StringField('Activity Name', validators=[Optional(), Length(min=1, max=200)])
    assessment_questions = FieldList(FormField(PBAAssessmentQuestionForm), min_entries=4, max_entries=4)

# Form for vocabulary terms with separate term and definition fields
class VocabularyTermForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    term = StringField('Term', validators=[Optional(), Length(min=1, max=100)])
    definition = TextAreaField('Definition', validators=[Optional(), Length(max=300)])

# Form for portfolio checklist items
class PortfolioChecklistItemForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    product = StringField('Product', validators=[Optional(), Length(min=1, max=300)])
    session_number = StringField('Session Number', validators=[Optional(), Length(min=1, max=10)])

# Main Module Answer Key form
class ModuleAnswerKeyForm(FlaskForm):
    module_acronym = StringField('Module Acronym', 
                               validators=[DataRequired(), Length(min=1, max=20)],
                               render_kw={"placeholder": "e.g., APHY, CHEM, BIOE"})
    
    # Assessments Section
    # Pre-test questions (10 questions)
    pretest_questions = FieldList(FormField(AnswerKeyQuestionForm), min_entries=10, max_entries=10)
    
    # RCA sessions (sessions 2-5, each with 3 questions)
    rca_sessions = FieldList(FormField(RCASessionForm), min_entries=4, max_entries=4)
    
    # Post-test questions (10 questions)
    posttest_questions = FieldList(FormField(AnswerKeyQuestionForm), min_entries=10, max_entries=10)
    
    # Performance Based Assessments - Changed from 4 to 3 sessions
    pba_sessions = FieldList(FormField(PBASessionForm), min_entries=3, max_entries=3)
    
    # Vocabulary (at least 25 terms)
    vocabulary = FieldList(FormField(VocabularyTermForm), min_entries=25, max_entries=30)
    
    # Student Portfolio Checklist (at least 6 items)
    portfolio_checklist = FieldList(FormField(PortfolioChecklistItemForm), min_entries=6, max_entries=10)
    
    # Enrichment Activities - Dynamic content field (like generic worksheet)
    enrichment_dynamic_content = FieldList(FormField(DynamicFieldForm), min_entries=0)
    
    # Worksheet Answer Keys - Now structured as nested worksheets
    worksheet_answer_keys = FieldList(FormField(WorksheetAnswerKeyForm), min_entries=0)
    
    submit = SubmitField('Generate Module Answer Key')
    
    def validate_pretest_questions(self, field):
        # Check if at least one question is provided
        has_questions = any(q['question_text'] for q in field.data if q.get('question_text'))
        if not has_questions:
            raise ValidationError('Please enter at least one pre-test question.')
    
    def validate_posttest_questions(self, field):
        # Check if at least one question is provided
        has_questions = any(q['question_text'] for q in field.data if q.get('question_text'))
        if not has_questions:
            raise ValidationError('Please enter at least one post-test question.')
    
    def validate_vocabulary(self, field):
        # Check if at least one vocabulary term is provided
        has_terms = any(v['term'] for v in field.data if v.get('term'))
        if not has_terms:
            raise ValidationError('Please enter at least one vocabulary term.')

# ===== MODULE ACTIVITY SHEET FORM =====

class ModuleActivitySheetForm(FlaskForm):
    module_acronym = StringField('Module Acronym', 
                               validators=[DataRequired(), Length(min=1, max=20)],
                               render_kw={"placeholder": "e.g., APHY, CHEM, BIOE"})
    
    # Session 1 - Always Pre-Test
    session1_activity = StringField('Session 1 Activity Name', 
                                  validators=[DataRequired(), Length(min=1, max=100)],
                                  render_kw={"placeholder": "e.g., Smart Cart and Track"})
    session1_is_pba = BooleanField('Session 1 includes Performance-Based Assessment')
    
    # Session 2 - Always RCA
    session2_activity = StringField('Session 2 Activity Name', 
                                  validators=[DataRequired(), Length(min=1, max=100)],
                                  render_kw={"placeholder": "e.g., Oscilloscope"})
    session2_is_pba = BooleanField('Session 2 includes Performance-Based Assessment')
    
    # Session 3 - Always RCA
    session3_activity = StringField('Session 3 Activity Name', 
                                  validators=[DataRequired(), Length(min=1, max=100)],
                                  render_kw={"placeholder": "e.g., Heat Expansion"})
    session3_is_pba = BooleanField('Session 3 includes Performance-Based Assessment')
    
    # Session 4 - Always RCA
    session4_activity = StringField('Session 4 Activity Name', 
                                  validators=[DataRequired(), Length(min=1, max=100)],
                                  render_kw={"placeholder": "e.g., Heat Experiment"})
    session4_is_pba = BooleanField('Session 4 includes Performance-Based Assessment')
    
    # Session 5 - Always RCA
    session5_activity = StringField('Session 5 Activity Name', 
                                  validators=[DataRequired(), Length(min=1, max=100)],
                                  render_kw={"placeholder": "e.g., Light Filter Experiment"})
    session5_is_pba = BooleanField('Session 5 includes Performance-Based Assessment')
    
    # Session 6 - Always Test Review
    session6_activity = StringField('Session 6 Activity Name', 
                                  validators=[DataRequired(), Length(min=1, max=100)],
                                  render_kw={"placeholder": "e.g., Laser Safety and Use"})
    session6_is_pba = BooleanField('Session 6 includes Performance-Based Assessment')
    
    # Session 7 - Always Post Test
    session7_activity = StringField('Session 7 Activity Name', 
                                  validators=[DataRequired(), Length(min=1, max=100)],
                                  render_kw={"placeholder": "e.g., Laser Experiments"})
    session7_is_pba = BooleanField('Session 7 includes Performance-Based Assessment')
    
    submit = SubmitField('Generate Module Activity Sheet')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get user's recent drafts (this will be empty for new users, which is fine)
        recent_drafts = FormDraft.query.filter_by(
            user_id=current_user.id,
            is_current=True
        ).order_by(FormDraft.updated_at.desc()).limit(10).all()
        
        # Get user's recent documents (this will be empty for new users, which is fine)
        recent_docs = GeneratedDocument.query.filter_by(
            user_id=current_user.id
        ).order_by(GeneratedDocument.created_at.desc()).limit(10).all()
        
        # Stats
        total_drafts = FormDraft.query.filter_by(user_id=current_user.id, is_current=True).count()
        total_docs = GeneratedDocument.query.filter_by(user_id=current_user.id).count()
        
        # Create a simple templates list for now (since the template expects it)
        templates = [
            {'id': 'vocabulary', 'name': 'Vocabulary Worksheet', 'description': 'Create vocabulary worksheets'},
            {'id': 'pba', 'name': 'PBA Worksheet', 'description': 'Performance-based assessments'},
            {'id': 'test', 'name': 'Test Worksheet', 'description': 'Pre and post-test worksheets'},
            {'id': 'generic', 'name': 'Generic Worksheet', 'description': 'Flexible worksheet templates'},
            {'id': 'family', 'name': 'Family Briefing', 'description': 'Parent communication documents'},
            {'id': 'rca', 'name': 'RCA Worksheet', 'description': 'Research, Challenge, Application'},
            {'id': 'guide', 'name': 'Module Guide', 'description': 'Comprehensive teaching guides'},
            {'id': 'answer', 'name': 'Module Answer Key', 'description': 'Complete answer references'},
            {'id': 'activity', 'name': 'Module Activity Sheet', 'description': 'Session planning documents'}
        ]
        
        return render_template('dashboard.html', 
                             recent_drafts=recent_drafts,
                             recent_docs=recent_docs,
                             total_drafts=total_drafts,
                             total_docs=total_docs,
                             templates=templates)
                             
    except Exception as e:
        # If there's any database error, show a simple error message
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('simple_dashboard.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/create-vocabulary', methods=['GET', 'POST'])
@login_required
def create_vocabulary():
    form = VocabularyWorksheetForm()
    
    if request.method == 'POST':
        print("Form submitted!")
        print(f"Form data: {request.form}")
        print(f"Form valid: {form.validate_on_submit()}")
        if form.errors:
            print(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        print("Form validation passed!")
        # Generate the document
        try:
            print("Attempting to generate document...")
            doc_path, filename = generate_vocabulary_worksheet(form)
            print(f"Document generated at: {doc_path}")
            
            # Save document info to database
            doc_record = GeneratedDocument(
                user_id=current_user.id,
                document_type='vocabulary',
                filename=filename,
                file_path=doc_path,
                module_acronym=form.module_acronym.data,
                file_size=os.path.getsize(doc_path)
            )
            db.session.add(doc_record)
            db.session.commit()
            
            flash('Worksheet generated successfully!', 'success')
            return redirect(url_for('download_document', doc_id=doc_record.id))
        except Exception as e:
            print(f"Error generating document: {e}")
            flash(f'Error generating worksheet: {str(e)}', 'error')
    
    return render_template('create_vocabulary.html', form=form)

@app.route('/create-pba', methods=['GET', 'POST'])
@login_required
def create_pba():
    form = PBAWorksheetForm()
    
    if request.method == 'POST':
        print("PBA form submitted!")
        print(f"Form data: {request.form}")
        print(f"Form valid: {form.validate_on_submit()}")
        if form.errors:
            print(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        print("PBA form validation passed!")
        # Generate the document
        try:
            print("Attempting to generate PBA worksheet...")
            doc_path = generate_pba_worksheet(form)
            print(f"PBA worksheet generated at: {doc_path}")
            flash('PBA worksheet generated successfully!', 'success')
            return redirect(url_for('create_pba'))
        except Exception as e:
            print(f"Error generating PBA worksheet: {e}")
            flash(f'Error generating PBA worksheet: {str(e)}', 'error')
    
    return render_template('create_pba.html', form=form)

@app.route('/create-test', methods=['GET', 'POST'])
@login_required
def create_test():
    form = TestWorksheetForm()
    
    if request.method == 'POST':
        print("Test form submitted!")
        print(f"Form data: {request.form}")
        print(f"Test type selected: {form.test_type.data}")
        print(f"Form valid: {form.validate_on_submit()}")
        if form.errors:
            print(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        print("Test form validation passed!")
        # Generate the document based on the selected test type
        try:
            test_type = form.test_type.data
            if test_type == 'pre':
                print("Attempting to generate pre-test worksheet...")
                doc_path = generate_pretest_worksheet(form)
                flash('Pre-Test worksheet generated successfully!', 'success')
            else:  # test_type == 'post'
                print("Attempting to generate post-test worksheet...")
                doc_path = generate_posttest_worksheet(form)
                flash('Post-Test worksheet generated successfully!', 'success')
            
            print(f"Test worksheet generated at: {doc_path}")
            return redirect(url_for('create_test'))
        except Exception as e:
            print(f"Error generating test worksheet: {e}")
            flash(f'Error generating test worksheet: {str(e)}', 'error')
    
    return render_template('create_test.html', form=form)

@app.route('/create-generic', methods=['GET', 'POST'])
@login_required
def create_generic():
    form = GenericWorksheetForm()
    
    if request.method == 'POST':
        print("Generic form submitted!")
        print(f"Form data: {request.form}")
        print(f"Form valid: {form.validate_on_submit()}")
        if form.errors:
            print(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        print("Generic form validation passed!")
        # Generate the document
        try:
            print("Attempting to generate generic worksheet...")
            doc_path = generate_generic_worksheet(form)
            print(f"Generic worksheet generated at: {doc_path}")
            flash('Generic worksheet generated successfully!', 'success')
            return redirect(url_for('create_generic'))
        except Exception as e:
            print(f"Error generating generic worksheet: {e}")
            flash(f'Error generating generic worksheet: {str(e)}', 'error')
    
    return render_template('create_generic.html', form=form)

@app.route('/create-familybriefing', methods=['GET', 'POST'])
@login_required
def create_familybriefing():
    form = FamilyBriefingForm()
    
    if request.method == 'POST':
        print("Family Briefing form submitted!")
        print(f"Form data: {request.form}")
        print(f"Form valid: {form.validate_on_submit()}")
        if form.errors:
            print(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        print("Family Briefing form validation passed!")
        # Generate the document
        try:
            print("Attempting to generate family briefing...")
            doc_path = generate_family_briefing(form)
            print(f"Family briefing generated at: {doc_path}")
            flash('Family Briefing generated successfully!', 'success')
            return redirect(url_for('create_familybriefing'))
        except Exception as e:
            print(f"Error generating family briefing: {e}")
            flash(f'Error generating family briefing: {str(e)}', 'error')
    
    return render_template('create_familybriefing.html', form=form)

@app.route('/create-rca', methods=['GET', 'POST'])
@login_required
def create_rca():
    form = RCAWorksheetForm()
    
    if request.method == 'POST':
        print("RCA form submitted!")
        print(f"Form data: {request.form}")
        print(f"Form valid: {form.validate_on_submit()}")
        if form.errors:
            print(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        print("RCA form validation passed!")
        # Generate the document
        try:
            print("Attempting to generate RCA worksheet...")
            doc_path = generate_rca_worksheet(form)
            print(f"RCA worksheet generated at: {doc_path}")
            flash('RCA worksheet generated successfully!', 'success')
            return redirect(url_for('create_rca'))
        except Exception as e:
            print(f"Error generating RCA worksheet: {e}")
            flash(f'Error generating RCA worksheet: {str(e)}', 'error')
    
    return render_template('create_rca.html', form=form)

@app.route('/create-moduleGuide', methods=['GET', 'POST'])
@login_required
def create_module_guide():
    form = ModuleGuideForm()
    
    if request.method == 'POST':
        print("Module Guide form submitted!")
        print(f"Form data: {request.form}")
        print(f"Form valid: {form.validate_on_submit()}")
        if form.errors:
            print(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        print("Module Guide form validation passed!")
        # Generate the document
        try:
            print("Attempting to generate Module Guide...")
            doc_path = generate_module_guide(form)
            print(f"Module Guide generated at: {doc_path}")
            flash('Module Guide generated successfully!', 'success')
            return redirect(url_for('create_module_guide'))
        except Exception as e:
            print(f"Error generating Module Guide: {e}")
            flash(f'Error generating Module Guide: {str(e)}', 'error')
    
    return render_template('create_moduleGuide.html', form=form)

@app.route('/create-moduleAnswerKey', methods=['GET', 'POST'])
@login_required
def create_module_answer_key():
    form = ModuleAnswerKeyForm()
    
    if request.method == 'POST':
        print("Module Answer Key form submitted!")
        print(f"Form data: {request.form}")
        print(f"Form valid: {form.validate_on_submit()}")
        if form.errors:
            print(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        print("Module Answer Key form validation passed!")
        # Generate the document
        try:
            print("Attempting to generate Module Answer Key...")
            doc_path = generate_module_answer_key(form)
            print(f"Module Answer Key generated at: {doc_path}")
            flash('Module Answer Key generated successfully!', 'success')
            return redirect(url_for('create_module_answer_key'))
        except Exception as e:
            print(f"Error generating Module Answer Key: {e}")
            flash(f'Error generating Module Answer Key: {str(e)}', 'error')
    
    return render_template('create_moduleAnswerKey.html', form=form)

@app.route('/create-moduleActivitySheet', methods=['GET', 'POST'])
@login_required
def create_module_activity_sheet():
    form = ModuleActivitySheetForm()
    
    if request.method == 'POST':
        print("Module Activity Sheet form submitted!")
        print(f"Form data: {request.form}")
        print(f"Form valid: {form.validate_on_submit()}")
        if form.errors:
            print(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        print("Module Activity Sheet form validation passed!")
        # Generate the document
        try:
            print("Attempting to generate Module Activity Sheet...")
            doc_path = generate_module_activity_sheet(form)
            print(f"Module Activity Sheet generated at: {doc_path}")
            flash('Module Activity Sheet generated successfully!', 'success')
            return redirect(url_for('create_module_activity_sheet'))
        except Exception as e:
            print(f"Error generating Module Activity Sheet: {e}")
            flash(f'Error generating Module Activity Sheet: {str(e)}', 'error')
    
    return render_template('create_moduleActivitySheet.html', form=form)

def generate_vocabulary_worksheet(form):
    """Generate a vocabulary worksheet using docxtpl"""
    # Use a master template that never gets touched
    master_template_path = 'templates/docx_templates/vocabulary_worksheet_master.docx'
    working_template_path = 'templates/docx_templates/vocabulary_worksheet.docx'
    
    print(f"Looking for vocabulary master template at: {master_template_path}")
    
    # Check if master template exists
    if not os.path.exists(master_template_path):
        raise FileNotFoundError("Vocabulary master DOCX template not found. Please create the master template first.")
    
    # Always copy from master to working template before processing
    print("Copying fresh vocabulary template from master...")
    shutil.copy2(master_template_path, working_template_path)
    
    print("Loading vocabulary working template...")
    
    # Create a temporary copy of the working template
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        shutil.copy2(working_template_path, temp_file.name)
        temp_template_path = temp_file.name
    
    try:
        # Load the temporary template
        doc = DocxTemplate(temp_template_path)
        
        # Prepare context data with XML escaping
        words_data = [
            {'word': escape_xml(word_data['word'])}
            for word_data in form.words.data
            if word_data.get('word')  # Only include non-empty words
        ]
        
        context = {
            'date': datetime.now().strftime('%B %d, %Y'),
            'words': words_data
        }
        
        print(f"Vocabulary context data: {context}")
        print(f"Number of words: {len(words_data)}")
        
        # Render the document
        print("Rendering vocabulary document...")
        doc.render(context)
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"Vocabulary {escape_xml(form.module_acronym.data).replace(' ', '_')}_v2.0.docx"
        output_path = os.path.join(output_dir, filename)
        
        print(f"Saving vocabulary document to: {output_path}")
        doc.save(output_path)
        
        print("Vocabulary document saved successfully!")
        return output_path, filename
        
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_template_path)
        except:
            pass  # Ignore cleanup errors

def generate_pba_worksheet(form):
    """Generate a PBA worksheet using docxtpl"""
    # Use a master template that never gets touched
    master_template_path = 'templates/docx_templates/pba_worksheet_master.docx'
    working_template_path = 'templates/docx_templates/pba_worksheet.docx'
    
    print(f"Looking for PBA master template at: {master_template_path}")
    
    # Check if master template exists
    if not os.path.exists(master_template_path):
        raise FileNotFoundError("PBA master DOCX template not found. Please create the master template first.")
    
    # Always copy from master to working template before processing
    print("Copying fresh PBA template from master...")
    shutil.copy2(master_template_path, working_template_path)
    
    print("Loading PBA working template...")
    
    # Create a temporary copy of the working template
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        shutil.copy2(working_template_path, temp_file.name)
        temp_template_path = temp_file.name
    
    try:
        # Load the temporary template
        doc = DocxTemplate(temp_template_path)
        
        # Prepare context data with XML escaping
        assessments_data = [
            {'assessment': escape_xml(assessment_data['assessment'])}
            for assessment_data in form.assessments.data
            if assessment_data.get('assessment')  # Only include non-empty assessments
        ]
        
        context = {
            'module_acronym': escape_xml(form.module_acronym.data),
            'session_number': escape_xml(form.session_number.data),
            'section_header': escape_xml(form.section_header.data),
            'assessments': assessments_data
        }
        
        print(f"PBA context data: {context}")
        print(f"Number of assessments: {len(assessments_data)}")
        
        # Render the document
        print("Rendering PBA document...")
        doc.render(context)
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"PBA (Session {escape_xml(form.session_number.data)}) {escape_xml(form.module_acronym.data).replace(' ', '_')}_v2.0.docx"
        output_path = os.path.join(output_dir, filename)
        
        print(f"Saving PBA document to: {output_path}")
        doc.save(output_path)
        
        print("PBA document saved successfully!")
        return output_path
        
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_template_path)
        except:
            pass  # Ignore cleanup errors

def generate_posttest_worksheet(form):
    """Generate a post test worksheet using docxtpl"""
    # Use a master template that never gets touched
    master_template_path = 'templates/docx_templates/post_test_worksheet_master.docx'
    working_template_path = 'templates/docx_templates/post_test_worksheet.docx'
    
    print(f"Looking for post test master template at: {master_template_path}")
    
    # Check if master template exists
    if not os.path.exists(master_template_path):
        raise FileNotFoundError("Post test master DOCX template not found. Please create the master template first.")
    
    # Always copy from master to working template before processing
    print("Copying fresh post test template from master...")
    shutil.copy2(master_template_path, working_template_path)
    
    print("Loading post test working template...")
    
    # Create a temporary copy of the working template
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        shutil.copy2(working_template_path, temp_file.name)
        temp_template_path = temp_file.name
    
    try:
        # Load the temporary template
        doc = DocxTemplate(temp_template_path)
        
        # Prepare context data with new structure for template and XML escaping
        questions_data = []
        for question_data in form.questions.data:
            if question_data.get('question_text'):  # Only include questions with text
                # Create choice array for template indexing with XML escaping
                questions_data.append({
                    'question': escape_xml(question_data['question_text']),
                    'choice': [
                        escape_xml(question_data['choice_a']),
                        escape_xml(question_data['choice_b']),
                        escape_xml(question_data['choice_c']),
                        escape_xml(question_data['choice_d'])
                    ]
                })
        
        context = {
            'module_acronym': escape_xml(form.module_acronym.data),
            'questions': questions_data
        }
        
        print(f"Post test context data: {context}")
        print(f"Number of questions: {len(questions_data)}")
        
        # Render the document
        print("Rendering post test document...")
        doc.render(context)
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"Post-Test WS {escape_xml(form.module_acronym.data).replace(' ', '_')}_v2.0.docx"
        output_path = os.path.join(output_dir, filename)
        
        print(f"Saving post test document to: {output_path}")
        doc.save(output_path)
        
        print("Post test document saved successfully!")
        return output_path
        
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_template_path)
        except:
            pass  # Ignore cleanup errors

def generate_pretest_worksheet(form):
    """Generate a pre test worksheet using docxtpl"""
    # Use a master template that never gets touched
    master_template_path = 'templates/docx_templates/pre_test_worksheet_master.docx'
    working_template_path = 'templates/docx_templates/pre_test_worksheet.docx'
    
    print(f"Looking for pre test master template at: {master_template_path}")
    
    # Check if master template exists
    if not os.path.exists(master_template_path):
        raise FileNotFoundError("Pre test master DOCX template not found. Please create the master template first.")
    
    # PROTECTION: Verify master template integrity before proceeding
    master_stat = os.stat(master_template_path)
    print(f"Master template size: {master_stat.st_size} bytes, modified: {datetime.fromtimestamp(master_stat.st_mtime)}")
    
    # Always copy from master to working template before processing
    print("Copying fresh pre test template from master...")
    try:
        shutil.copy2(master_template_path, working_template_path)
        print(f"✓ Successfully copied master to working template")
    except Exception as e:
        raise Exception(f"Failed to copy master template: {e}")
    
    print("Loading pre test working template...")
    
    # Create a temporary copy of the working template - NEVER touch master directly
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        try:
            shutil.copy2(working_template_path, temp_file.name)
            temp_template_path = temp_file.name
            print(f"✓ Created temporary template at: {temp_template_path}")
        except Exception as e:
            raise Exception(f"Failed to create temporary template: {e}")
    
    try:
        # Load the temporary template - NEVER the master
        print(f"Loading DocxTemplate from temporary file: {temp_template_path}")
        doc = DocxTemplate(temp_template_path)
        
        # Prepare context data with new structure for template and XML escaping
        questions_data = []
        for question_data in form.questions.data:
            if question_data.get('question_text'):  # Only include questions with text
                # Create choice array for template indexing with XML escaping
                questions_data.append({
                    'question': escape_xml(question_data['question_text']),
                    'choice': [
                        escape_xml(question_data['choice_a']),
                        escape_xml(question_data['choice_b']),
                        escape_xml(question_data['choice_c']),
                        escape_xml(question_data['choice_d'])
                    ]
                })
        
        context = {
            'module_acronym': escape_xml(form.module_acronym.data),
            'questions': questions_data
        }
        
        print(f"Pre test context data: {context}")
        print(f"Number of questions: {len(questions_data)}")
        
        # Render the document
        print("Rendering pre test document...")
        doc.render(context)
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"Pre-Test WS {escape_xml(form.module_acronym.data).replace(' ', '_')}_v2.0.docx"
        output_path = os.path.join(output_dir, filename)
        
        print(f"Saving pre test document to: {output_path}")
        doc.save(output_path)
        
        print("Pre test document saved successfully!")
        
        # PROTECTION: Verify master template wasn't accidentally modified
        master_stat_after = os.stat(master_template_path)
        if master_stat.st_mtime != master_stat_after.st_mtime:
            print("⚠️  WARNING: Master template modification time changed during processing!")
        else:
            print("✓ Master template integrity verified - no accidental changes")
            
        return output_path
        
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(temp_template_path):
                os.unlink(temp_template_path)
                print(f"✓ Cleaned up temporary file: {temp_template_path}")
        except Exception as e:
            print(f"Warning: Could not clean up temporary file {temp_template_path}: {e}")

def generate_generic_worksheet(form):
    """Generate a generic worksheet using docxtpl with dynamic content"""
    # Use the generic master template (formerly homework template)
    master_template_path = 'templates/docx_templates/generic_worksheet_master.docx'
    working_template_path = 'templates/docx_templates/generic_worksheet.docx'
    
    print(f"Looking for generic master template at: {master_template_path}")
    
    # Check if master template exists
    if not os.path.exists(master_template_path):
        raise FileNotFoundError("Generic master DOCX template not found. Please create the master template first.")
    
    # Always copy from master to working template before processing
    print("Copying fresh generic template from master...")
    shutil.copy2(master_template_path, working_template_path)
    
    print("Loading generic working template...")
    
    # Create a temporary copy of the working template
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        shutil.copy2(working_template_path, temp_file.name)
        temp_template_path = temp_file.name
    
    saved_images = []  # Track saved images for cleanup
    
    try:
        # Load the temporary template
        doc = DocxTemplate(temp_template_path)
        
        # Create a subdocument to hold all dynamic content
        subdoc = doc.new_subdoc()
        
        # Track processed image fields to avoid duplicates
        processed_image_fields = set()
        
        # Debug: Print all image files available in request
        image_files_in_request = [key for key in request.files.keys() if 'image_file' in key]
        print(f"Available image files in request: {image_files_in_request}")
        
        question_counter = 1
        
        for i, field_data in enumerate(form.dynamic_fields.data):
            field_type = field_data.get('field_type')
            
            print(f"Processing field {i}: type = {field_type}")
            
            if field_type == 'section_header':
                title = (field_data.get('section_title') or '').strip()
                if title:
                    # Add header paragraph with direct formatting
                    p = subdoc.add_paragraph(title)
                    # Apply header formatting: Segoe UI 14pt Bold
                    for run in p.runs:
                        run.font.name = 'Segoe UI'
                        run.font.size = Pt(14)
                        run.font.bold = True
                    p.paragraph_format.space_before = Pt(12)
                    p.paragraph_format.space_after = Pt(6)
            
            elif field_type == 'section_instructions':
                inst_text = (field_data.get('instructions_text') or '').strip()
                if inst_text:
                    # Add instruction paragraph with direct formatting
                    p = subdoc.add_paragraph(inst_text)
                    # Apply instructions formatting: Segoe UI 11pt Italic
                    for run in p.runs:
                        run.font.name = 'Segoe UI'
                        run.font.size = Pt(11)
                        run.font.italic = True
                    p.paragraph_format.space_after = Pt(6)
            
            elif field_type == 'paragraph_text':
                para_text = (field_data.get('paragraph_text') or '').strip()
                if para_text:
                    # Add body text paragraph with direct formatting
                    p = subdoc.add_paragraph(para_text)
                    # Apply body text formatting: Segoe UI 11pt Regular
                    for run in p.runs:
                        run.font.name = 'Segoe UI'
                        run.font.size = Pt(11)
                    p.paragraph_format.space_after = Pt(6)
            
            elif field_type == 'image':
                # Handle image upload - check if there's a file in the request
                # Updated approach: search for the field in request.files more robustly
                image_file = None
                field_name = f'dynamic_fields-{i}-image_file'
                
                # First try the expected field name
                if field_name in request.files:
                    image_file = request.files[field_name]
                else:
                    # If not found, search through all files for this field pattern
                    # This handles cases where frontend indices don't match backend indices due to deletions
                    for file_key in request.files.keys():
                        if file_key.startswith('dynamic_fields-') and file_key.endswith('-image_file'):
                            # Extract the index from the field name
                            try:
                                parts = file_key.split('-')
                                if len(parts) >= 3:
                                    file_index = int(parts[2])
                                    # Check if this file hasn't been processed yet
                                    if file_key not in processed_image_fields:
                                        image_file = request.files[file_key]
                                        processed_image_fields.add(file_key)
                                        print(f"Found image file with key: {file_key} for field at position {i}")
                                        break
                            except (ValueError, IndexError):
                                continue
                
                if image_file and image_file.filename:
                    # Save the uploaded file temporarily
                    filename = secure_filename(image_file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    
                    # Save the file
                    image_file.save(filepath)
                    saved_images.append(filepath)  # Track for cleanup
                    
                    # Add image to subdocument with fixed width of 4 inches
                    p = subdoc.add_paragraph()
                    run = p.add_run()
                    run.add_picture(filepath, width=Inches(4))
                    p.alignment = 1  # Center alignment
                    # Caption removed per user request
            
            elif field_type in ['multiple_choice', 'fill_in_blank', 'text_entry', 'math_problem']:
                question_text = (field_data.get('question_text') or '').strip()
                math_expression = (field_data.get('math_expression') or '').strip()
                
                if question_text or math_expression:
                    # Add question or math problem with direct formatting
                    if field_type == 'math_problem' and math_expression:
                        p = subdoc.add_paragraph(f"{question_counter}. {math_expression}")
                    else:
                        p = subdoc.add_paragraph(f"{question_counter}. {question_text}")
                    
                    # Apply question formatting: Segoe UI 11pt Regular
                    for run in p.runs:
                        run.font.name = 'Segoe UI'
                        run.font.size = Pt(11)
                    p.paragraph_format.space_after = Pt(6)
                    
                    if field_type == 'multiple_choice':
                        # Create a 2x4 table for the choices (2 rows, 4 columns)
                        table = subdoc.add_table(rows=2, cols=4)
                        
                        # Set column widths to be reasonable
                        table.autofit = False
                        for row in table.rows:
                            # Letters get smaller width, choices get larger width
                            row.cells[0].width = Inches(0.3)  # A.
                            row.cells[1].width = Inches(3)  # Choice A text
                            row.cells[2].width = Inches(0.3)  # C.
                            row.cells[3].width = Inches(3)  # Choice C text
                        
                        # Remove table borders for a cleaner look
                        from docx.oxml.shared import qn
                        for row in table.rows:
                            for cell in row.cells:
                                # Set cell margins
                                cell.paragraphs[0].paragraph_format.space_after = Pt(0)
                                cell.paragraphs[0].paragraph_format.space_before = Pt(0)
                        
                        # Get all choices
                        choices = [
                            ('A', field_data.get('choice_a', '')),
                            ('B', field_data.get('choice_b', '')),
                            ('C', field_data.get('choice_c', '')),
                            ('D', field_data.get('choice_d', ''))
                        ]
                        
                        # Populate the table cells in 2x4 format
                        # Row 0: A. | Choice A text | C. | Choice C text
                        # Row 1: B. | Choice B text | D. | Choice D text
                        
                        for i, (letter, choice_text) in enumerate(choices):
                            if choice_text.strip():
                                if i == 0:  # A
                                    row, letter_col, text_col = 0, 0, 1
                                elif i == 1:  # B  
                                    row, letter_col, text_col = 1, 0, 1
                                elif i == 2:  # C
                                    row, letter_col, text_col = 0, 2, 3
                                else:  # D
                                    row, letter_col, text_col = 1, 2, 3
                                
                                # Add letter (A., B., C., D.)
                                letter_cell = table.cell(row, letter_col)
                                letter_cell.text = f"{letter}."
                                for paragraph in letter_cell.paragraphs:
                                    paragraph.paragraph_format.space_before = Pt(6)
                                    for run in paragraph.runs:
                                        run.font.name = 'Segoe UI'
                                        run.font.size = Pt(11)
                                        run.font.bold = False
                                
                                # Add choice text
                                text_cell = table.cell(row, text_col)
                                text_cell.text = choice_text.strip()
                                for paragraph in text_cell.paragraphs:
                                    paragraph.paragraph_format.space_before = Pt(6)
                                    for run in paragraph.runs:
                                        run.font.name = 'Segoe UI'
                                        run.font.size = Pt(11)
                        
                        # Add spacing after the table
                        subdoc.add_paragraph().paragraph_format.space_after = Pt(6)
                    
                    elif field_type == 'fill_in_blank':
                        p = subdoc.add_paragraph("")
                        p.paragraph_format.left_indent = Pt(36)
                    
                    elif field_type == 'text_entry':
                        # Add blank lines for text entry
                        for _ in range(3):
                            p = subdoc.add_paragraph()
                            p.paragraph_format.space_after = Pt(12)
                    
                    # Add spacing after question
                    subdoc.add_paragraph()
                    question_counter += 1
        
        # Initialize context with subdoc as dynamic_content
        context = {
            'module_acronym': escape_xml(form.module_acronym.data),
            'worksheet_title': escape_xml(form.worksheet_title.data),
            'date': datetime.now().strftime('%B %d, %Y'),
            'dynamic_content': subdoc
        }
        
        print(f"Built dynamic content as subdocument")
        print(f"Saved {len(saved_images)} images")
        print(f"Processed image fields: {processed_image_fields}")
        
        # Render the document
        print("Rendering generic document...")
        doc.render(context)
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{escape_xml(form.worksheet_title.data).replace(' ', '_')} {escape_xml(form.module_acronym.data).replace(' ', '_')}_v2.0.docx"
        output_path = os.path.join(output_dir, filename)
        
        print(f"Saving generic document to: {output_path}")
        doc.save(output_path)
        
        print("Generic document saved successfully!")
        return output_path, filename
        
    finally:
        # Clean up the temporary files
        try:
            os.unlink(temp_template_path)
        except:
            pass  # Ignore cleanup errors
        
        # Clean up uploaded images
        for image_path in saved_images:
            try:
                if os.path.exists(image_path):
                    os.unlink(image_path)
                    print(f"Cleaned up temporary image: {image_path}")
            except Exception as e:
                print(f"Warning: Could not clean up image {image_path}: {e}")

def generate_family_briefing(form):
    """Generate a family briefing document using docxtpl"""
    # Use a master template that never gets touched
    master_template_path = 'templates/docx_templates/family_briefing_master.docx'
    working_template_path = 'templates/docx_templates/family_briefing.docx'
    
    print(f"Looking for family briefing master template at: {master_template_path}")
    
    # Check if master template exists
    if not os.path.exists(master_template_path):
        raise FileNotFoundError("Family briefing master DOCX template not found. Please create the master template first.")
    
    # Always copy from master to working template before processing
    print("Copying fresh family briefing template from master...")
    shutil.copy2(master_template_path, working_template_path)
    
    print("Loading family briefing working template...")
    
    # Create a temporary copy of the working template
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        shutil.copy2(working_template_path, temp_file.name)
        temp_template_path = temp_file.name
    
    try:
        # Load the temporary template
        doc = DocxTemplate(temp_template_path)
        
        # Build the context dictionary
        context = {
            'module_name': escape_xml(form.module_name.data) if form.module_name.data else '',
            'introsentence': escape_xml(form.introsentence.data) if form.introsentence.data else '',
            
            # Learning Objectives
            'learningobjective1': escape_xml(form.learningobjective1.data) if form.learningobjective1.data else '',
            'learningobjective2': escape_xml(form.learningobjective2.data) if form.learningobjective2.data else '',
            'learningobjective3': escape_xml(form.learningobjective3.data) if form.learningobjective3.data else '',
            'learningobjective4': escape_xml(form.learningobjective4.data) if form.learningobjective4.data else '',
            
            # Session Activities
            'activityname1': escape_xml(form.activityname1.data) if form.activityname1.data else '',
            'activityname2': escape_xml(form.activityname2.data) if form.activityname2.data else '',
            'activityname3': escape_xml(form.activityname3.data) if form.activityname3.data else '',
            'activityname4': escape_xml(form.activityname4.data) if form.activityname4.data else '',
            'activityname5': escape_xml(form.activityname5.data) if form.activityname5.data else '',
            'activityname6': escape_xml(form.activityname6.data) if form.activityname6.data else '',
            'activityname7': escape_xml(form.activityname7.data) if form.activityname7.data else '',
            
            # Key Terminology
            'term1': escape_xml(form.term1.data) if form.term1.data else '',
            'term2': escape_xml(form.term2.data) if form.term2.data else '',
            'term3': escape_xml(form.term3.data) if form.term3.data else '',
            'term4': escape_xml(form.term4.data) if form.term4.data else '',
            'term5': escape_xml(form.term5.data) if form.term5.data else '',
            'term6': escape_xml(form.term6.data) if form.term6.data else '',
            'term7': escape_xml(form.term7.data) if form.term7.data else '',
            'term8': escape_xml(form.term8.data) if form.term8.data else '',
            'term9': escape_xml(form.term9.data) if form.term9.data else '',
            'term10': escape_xml(form.term10.data) if form.term10.data else '',
            'term11': escape_xml(form.term11.data) if form.term11.data else '',
            'term12': escape_xml(form.term12.data) if form.term12.data else '',
            'term13': escape_xml(form.term13.data) if form.term13.data else '',
            'term14': escape_xml(form.term14.data) if form.term14.data else '',
            'term15': escape_xml(form.term15.data) if form.term15.data else '',
            'term16': escape_xml(form.term16.data) if form.term16.data else '',
            'term17': escape_xml(form.term17.data) if form.term17.data else '',
            'term18': escape_xml(form.term18.data) if form.term18.data else '',
            'term19': escape_xml(form.term19.data) if form.term19.data else '',
            'term20': escape_xml(form.term20.data) if form.term20.data else '',
            'term21': escape_xml(form.term21.data) if form.term21.data else '',
            
            # Key Concepts - Using simple variable names
            'keyconcept1': escape_xml(form.keyconcept1_name.data) if form.keyconcept1_name.data else '',
            'keyconcept1_explanation': escape_xml(form.keyconcept1_explanation.data) if form.keyconcept1_explanation.data else '',
            'keyconcept2': escape_xml(form.keyconcept2_name.data) if form.keyconcept2_name.data else '',
            'keyconcept2_explanation': escape_xml(form.keyconcept2_explanation.data) if form.keyconcept2_explanation.data else '',
            'keyconcept3': escape_xml(form.keyconcept3_name.data) if form.keyconcept3_name.data else '',
            'keyconcept3_explanation': escape_xml(form.keyconcept3_explanation.data) if form.keyconcept3_explanation.data else ''
        }
        
        print(f"Family briefing context data: {context}")
        
        # Render the document
        print("Rendering family briefing document...")
        doc.render(context)
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"Family Briefing {escape_xml(form.module_name.data).replace(' ', '_')}_v2.0.docx"
        output_path = os.path.join(output_dir, filename)
        
        print(f"Saving family briefing document to: {output_path}")
        doc.save(output_path)
        
        print("Family briefing document saved successfully!")
        return output_path
        
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_template_path)
        except:
            pass  # Ignore cleanup errors

def generate_rca_worksheet(form):
    """Generate an RCA worksheet using docxtpl"""
    # Use a master template that never gets touched
    master_template_path = 'templates/docx_templates/rca_worksheet_master.docx'
    working_template_path = 'templates/docx_templates/rca_worksheet.docx'
    
    print(f"Looking for RCA master template at: {master_template_path}")
    
    # Check if master template exists
    if not os.path.exists(master_template_path):
        raise FileNotFoundError("RCA master DOCX template not found. Please create the master template first.")
    
    # PROTECTION: Verify master template integrity before proceeding
    master_stat = os.stat(master_template_path)
    print(f"Master template size: {master_stat.st_size} bytes, modified: {datetime.fromtimestamp(master_stat.st_mtime)}")
    
    # Always copy from master to working template before processing
    print("Copying fresh RCA template from master...")
    try:
        shutil.copy2(master_template_path, working_template_path)
        print(f"✓ Successfully copied master to working template")
    except Exception as e:
        raise Exception(f"Failed to copy master template: {e}")
    
    print("Loading RCA working template...")
    
    # Create a temporary copy of the working template - NEVER touch master directly
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        try:
            shutil.copy2(working_template_path, temp_file.name)
            temp_template_path = temp_file.name
            print(f"✓ Created temporary template at: {temp_template_path}")
        except Exception as e:
            raise Exception(f"Failed to create temporary template: {e}")
    
    temp_image_path = None
    try:
        # Load the temporary template - NEVER the master
        print(f"Loading DocxTemplate from temporary file: {temp_template_path}")
        doc = DocxTemplate(temp_template_path)
        
        # Prepare context data with same structure as test templates
        questions_data = []
        
        # Always include exactly 3 questions (Research, Challenge, Application)
        # Even if some are empty, to match template expectations
        for i in range(3):
            if i < len(form.questions.data):
                question_data = form.questions.data[i]
                questions_data.append({
                    'question': escape_xml(question_data.get('question_text', '')),
                    'choice': [
                        escape_xml(question_data.get('choice_a', '')),
                        escape_xml(question_data.get('choice_b', '')),
                        escape_xml(question_data.get('choice_c', '')),
                        escape_xml(question_data.get('choice_d', ''))
                    ]
                })
            else:
                # Add empty question if form doesn't have enough
                questions_data.append({
                    'question': '',
                    'choice': ['', '', '', '']
                })
        
        # Start with basic context
        context = {
            'module_acronym': escape_xml(form.module_acronym.data),
            'questions': questions_data
        }
        
        # Handle image upload if provided
        if form.image_file.data:
            print("Processing uploaded image...")
            
            # Save the uploaded file temporarily
            image_file = form.image_file.data
            temp_dir = os.path.join('temp', 'uploads')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Create a unique filename
            filename = secure_filename(image_file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_filename = f"{timestamp}_{filename}"
            temp_image_path = os.path.join(temp_dir, temp_filename)
            
            # Save the file
            image_file.save(temp_image_path)
            print(f"✓ Image saved temporarily at: {temp_image_path}")
            
            # Create InlineImage for the template
            # Using width of 5 inches and maintaining aspect ratio
            image_obj = InlineImage(doc, temp_image_path, width=Inches(5))
            
            # Add image to context
            context['image'] = image_obj
        
        print(f"RCA context data: {context}")
        print(f"Number of questions: {len(questions_data)}")
        
        # Debug logging to help identify triplication issue
        for i, q in enumerate(questions_data):
            print(f"Question {i}: {q['question'][:50] if q['question'] else '[empty]'}...")
        
        # Render the document
        print("Rendering RCA document...")
        doc.render(context)
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"RCA {escape_xml(form.session_number.data)} {escape_xml(form.module_acronym.data).replace(' ', '_')}_v2.0.docx"
        output_path = os.path.join(output_dir, filename)
        
        print(f"Saving RCA document to: {output_path}")
        doc.save(output_path)
        
        print("RCA document saved successfully!")
        
        # PROTECTION: Verify master template wasn't accidentally modified
        master_stat_after = os.stat(master_template_path)
        if master_stat.st_mtime != master_stat_after.st_mtime:
            print("⚠️  WARNING: Master template modification time changed during processing!")
        else:
            print("✓ Master template integrity verified - no accidental changes")
            
        return output_path
        
    finally:
        # Clean up the temporary files
        try:
            if os.path.exists(temp_template_path):
                os.unlink(temp_template_path)
                print(f"✓ Cleaned up temporary file: {temp_template_path}")
        except Exception as e:
            print(f"Warning: Could not clean up temporary file {temp_template_path}: {e}")
            
        # Clean up temporary image if it exists
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.unlink(temp_image_path)
                print(f"✓ Cleaned up temporary image: {temp_image_path}")
            except Exception as e:
                print(f"Warning: Could not clean up temporary image {temp_image_path}: {e}")

def generate_module_guide(form):
    """Generate a Module Guide using docxtpl"""
    # Use a master template that never gets touched
    master_template_path = 'templates/docx_templates/module_guide_master.docx'
    working_template_path = 'templates/docx_templates/module_guide.docx'
    
    print(f"Looking for Module Guide master template at: {master_template_path}")
    
    # Check if master template exists
    if not os.path.exists(master_template_path):
        raise FileNotFoundError("Module Guide master DOCX template not found. Please create the master template first.")
    
    # PROTECTION: Verify master template integrity before proceeding
    master_stat = os.stat(master_template_path)
    print(f"Master template size: {master_stat.st_size} bytes, modified: {datetime.fromtimestamp(master_stat.st_mtime)}")
    
    # Always copy from master to working template before processing
    print("Copying fresh Module Guide template from master...")
    try:
        shutil.copy2(master_template_path, working_template_path)
        print(f"✓ Successfully copied master to working template")
    except Exception as e:
        raise Exception(f"Failed to copy master template: {e}")
    
    print("Loading Module Guide working template...")
    
    # Create a temporary copy of the working template - NEVER touch master directly
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        try:
            shutil.copy2(working_template_path, temp_file.name)
            temp_template_path = temp_file.name
            print(f"✓ Created temporary template at: {temp_template_path}")
        except Exception as e:
            raise Exception(f"Failed to create temporary template: {e}")
    
    try:
        # Load the temporary template - NEVER the master
        print(f"Loading DocxTemplate from temporary file: {temp_template_path}")
        doc = DocxTemplate(temp_template_path)
        
        # Prepare context data for Teacher Tips section
        standards_data = [
            escape_xml(standard_data['standard'])
            for standard_data in form.standards.data
            if standard_data.get('standard')  # Only include non-empty standards
        ]
        
        # Prepare vocabulary terms data
        vocab_terms_data = [
            escape_xml(vocab_data['term'])
            for vocab_data in form.vocab_terms.data
            if vocab_data.get('term')  # Only include non-empty terms
        ]
        
        # Prepare careers data
        careers_data = [
            escape_xml(career_data['career'])
            for career_data in form.careers.data
            if career_data.get('career')  # Only include non-empty careers
        ]
        
        # Build context with individual numbered vocabulary terms
        context = {
            'teachertips': {
                'overview': escape_xml(form.teachertips_statement.data) if form.teachertips_statement.data else '',
                'standard': standards_data  # Array for template indexing
            },
            # Add empty vocab and careers objects to prevent undefined errors in template
            'vocab': {},
            'careers': {}
        }
        
        # Add individual vocabulary terms (term1, term2, etc.)
        for i, term in enumerate(vocab_terms_data):
            context[f'term{i+1}'] = term
        
        # Fill remaining vocabulary terms with empty strings (up to 25 like Family Briefing)
        for i in range(len(vocab_terms_data), 25):
            context[f'term{i+1}'] = ''
            
        # Add individual careers (career1, career2, etc.)
        for i, career in enumerate(careers_data):
            context[f'career{i+1}'] = career
            
        # Fill remaining careers with empty strings (up to 14)
        for i in range(len(careers_data), 14):
            context[f'career{i+1}'] = ''
        
        # Process Session Notes data
        sessions_data = []
        for session_form in form.sessions.data:
            session_obj = {
                'focus': escape_xml(session_form.get('focus', '')),
                'goals': [],
                'prep': [],
                'assessments': []
            }
            
            # Process goals
            if 'goals' in session_form:
                for goal_data in session_form['goals']:
                    if goal_data.get('goal'):
                        session_obj['goals'].append(escape_xml(goal_data['goal']))
            
            # Add material fields (material1 through material15)
            for i in range(1, 16):
                material_key = f'material{i}'
                material_value = (session_form.get(material_key) or '').strip()
                session_obj[material_key] = escape_xml(material_value) if material_value else ''
            
            # Also add materials as a list for easier template processing
            materials_list = []
            for i in range(1, 16):
                material_key = f'material{i}'
                material_value = (session_form.get(material_key) or '').strip()
                if material_value:  # Only add non-empty materials
                    materials_list.append(escape_xml(material_value))
            session_obj['materials'] = materials_list
            
            # Process preparations
            if 'preparations' in session_form:
                for prep_data in session_form['preparations']:
                    if prep_data.get('prep'):
                        session_obj['prep'].append(escape_xml(prep_data['prep']))
            
            # Process assessments
            if 'assessments' in session_form:
                for assessment_data in session_form['assessments']:
                    if assessment_data.get('assessment'):
                        session_obj['assessments'].append(escape_xml(assessment_data['assessment']))
            
            sessions_data.append(session_obj)
        
        # Add sessions to context
        context['sessions'] = sessions_data
        
        # Process Additional Resources data
        # Enrichment Activities
        enrichment_activities_data = [
            escape_xml(activity_data['activity'])
            for activity_data in form.enrichment_activities.data
            if activity_data.get('activity')  # Only include non-empty activities
        ]
        
        # Locally Sourced Materials
        locally_sourced_materials_data = [
            escape_xml(material_data['material'])
            for material_data in form.locally_sourced_materials.data
            if material_data.get('material')  # Only include non-empty materials
        ]
        
        # Maintenance Items
        maintenance_items_data = [
            escape_xml(item_data['item'])
            for item_data in form.maintenance_items.data
            if item_data.get('item')  # Only include non-empty items
        ]
        
        # Assembly Instructions
        assembly_instructions_data = [
            escape_xml(instruction_data['instruction'])
            for instruction_data in form.assembly_instructions.data
            if instruction_data.get('instruction')  # Only include non-empty instructions
        ]
        
        # Recommended Websites
        recommended_websites_data = [
            {
                'title': website_data['title'],
                'url': website_data['url']
            }
            for website_data in form.recommended_websites.data
            if website_data.get('title') and website_data.get('url')  # Only include websites with both title and URL
        ]
        
        # Add Additional Resources to context following template variable names
        context['enrichment'] = {
            'activities': enrichment_activities_data
        }
        context['locally'] = {
            'sourced': locally_sourced_materials_data
        }
        context['maintenance'] = {
            'list': maintenance_items_data
        }
        context['assembly'] = {
            'instructions': assembly_instructions_data
        }
        context['recommended'] = {
            'websites': recommended_websites_data
        }
        
        print(f"Module Guide context data: {context}")
        print(f"Number of standards: {len(standards_data)}")
        print(f"Number of vocabulary terms: {len(vocab_terms_data)}")
        print(f"Number of careers: {len(careers_data)}")
        print(f"Number of sessions: {len(sessions_data)}")
        print(f"Number of enrichment activities: {len(enrichment_activities_data)}")
        print(f"Number of locally sourced materials: {len(locally_sourced_materials_data)}")
        print(f"Number of maintenance items: {len(maintenance_items_data)}")
        print(f"Number of assembly instructions: {len(assembly_instructions_data)}")
        print(f"Number of recommended websites: {len(recommended_websites_data)}")
        
        # Render the document
        print("Rendering Module Guide document...")
        doc.render(context)
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"Module Guide {form.module_acronym.data.replace(' ', '_')}_v2.0.docx"
        output_path = os.path.join(output_dir, filename)
        
        print(f"Saving Module Guide document to: {output_path}")
        doc.save(output_path)
        
        print("Module Guide document saved successfully!")
        
        # PROTECTION: Verify master template wasn't accidentally modified
        master_stat_after = os.stat(master_template_path)
        if master_stat.st_mtime != master_stat_after.st_mtime:
            print("⚠️  WARNING: Master template modification time changed during processing!")
        else:
            print("✓ Master template integrity verified - no accidental changes")
            
        return output_path
        
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(temp_template_path):
                os.unlink(temp_template_path)
                print(f"✓ Cleaned up temporary file: {temp_template_path}")
        except Exception as e:
            print(f"Warning: Could not clean up temporary file {temp_template_path}: {e}")

def generate_module_answer_key(form):
    """Generate a Module Answer Key using docxtpl"""
    # Use a master template that never gets touched
    master_template_path = 'templates/docx_templates/module_answer_key_master.docx'
    working_template_path = 'templates/docx_templates/module_answer_key.docx'
    
    print(f"Looking for Module Answer Key master template at: {master_template_path}")
    
    # Check if master template exists
    if not os.path.exists(master_template_path):
        raise FileNotFoundError("Module Answer Key master DOCX template not found. Please create the master template first.")
    
    # PROTECTION: Verify master template integrity before proceeding
    master_stat = os.stat(master_template_path)
    print(f"Master template size: {master_stat.st_size} bytes, modified: {datetime.fromtimestamp(master_stat.st_mtime)}")
    
    # Always copy from master to working template before processing
    print("Copying fresh Module Answer Key template from master...")
    try:
        shutil.copy2(master_template_path, working_template_path)
        print(f"✓ Successfully copied master to working template")
    except Exception as e:
        raise Exception(f"Failed to copy master template: {e}")
    
    print("Loading Module Answer Key working template...")
    
    # Create a temporary copy of the working template - NEVER touch master directly
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        try:
            shutil.copy2(working_template_path, temp_file.name)
            temp_template_path = temp_file.name
            print(f"✓ Created temporary template at: {temp_template_path}")
        except Exception as e:
            raise Exception(f"Failed to create temporary template: {e}")
    
    # Track saved images for cleanup
    saved_images = []
    
    # Track processed image fields to avoid duplicates across both sections
    processed_enrichment_image_fields = set()
    processed_worksheet_image_fields = set()
    
    # Debug: Print all image files available in request
    image_files_in_request = [key for key in request.files.keys() if 'image_file' in key]
    print(f"Available image files in request: {image_files_in_request}")
    
    try:
        # Load the temporary template - NEVER the master
        print(f"Loading DocxTemplate from temporary file: {temp_template_path}")
        doc = DocxTemplate(temp_template_path)
        
        # Prepare context data matching the template structure
        
        # 1. Assessments Section
        # Pre-test questions
        pretest_questions_data = []
        for question_data in form.pretest_questions.data:
            if question_data.get('question_text'):
                pretest_questions_data.append({
                    'question': escape_xml(question_data['question_text']),
                    'choice': [
                        escape_xml(question_data['choice_a']),
                        escape_xml(question_data['choice_b']),
                        escape_xml(question_data['choice_c']),
                        escape_xml(question_data['choice_d'])
                    ],
                    'correct_answer': question_data.get('correct_answer', '').upper()
                })
        
        # RCA sessions (sessions 2-5, each with 3 questions)
        rca_sessions_data = []
        for i, session_data in enumerate(form.rca_sessions.data):
            session_obj = {
                'session_number': i + 2,  # Sessions 2-5
            }
            
            # Process the 3 questions in each session (Research, Challenge, Application)
            questions = session_data.get('questions', [])
            
            # Add research question (first question)
            if len(questions) > 0 and questions[0].get('question_text'):
                session_obj['research_question'] = {
                    'text': escape_xml(questions[0]['question_text']),
                    'choice': [
                        escape_xml(questions[0]['choice_a']),
                        escape_xml(questions[0]['choice_b']),
                        escape_xml(questions[0]['choice_c']),
                        escape_xml(questions[0]['choice_d'])
                    ],
                    'correct_answer': questions[0].get('correct_answer', '').upper()
                }
            
            # Add challenge question (second question)
            if len(questions) > 1 and questions[1].get('question_text'):
                session_obj['challenge_question'] = {
                    'text': escape_xml(questions[1]['question_text']),
                    'choice': [
                        escape_xml(questions[1]['choice_a']),
                        escape_xml(questions[1]['choice_b']),
                        escape_xml(questions[1]['choice_c']),
                        escape_xml(questions[1]['choice_d'])
                    ],
                    'correct_answer': questions[1].get('correct_answer', '').upper()
                }
            
            # Add application question (third question)
            if len(questions) > 2 and questions[2].get('question_text'):
                session_obj['application_question'] = {
                    'text': escape_xml(questions[2]['question_text']),
                    'choice': [
                        escape_xml(questions[2]['choice_a']),
                        escape_xml(questions[2]['choice_b']),
                        escape_xml(questions[2]['choice_c']),
                        escape_xml(questions[2]['choice_d'])
                    ],
                    'correct_answer': questions[2].get('correct_answer', '').upper()
                }
            
            # Only add sessions that have at least one question
            if any(key in session_obj for key in ['research_question', 'challenge_question', 'application_question']):
                rca_sessions_data.append(session_obj)
        
        # Post-test questions
        posttest_questions_data = []
        for question_data in form.posttest_questions.data:
            if question_data.get('question_text'):
                posttest_questions_data.append({
                    'question': escape_xml(question_data['question_text']),
                    'choice': [
                        escape_xml(question_data['choice_a']),
                        escape_xml(question_data['choice_b']),
                        escape_xml(question_data['choice_c']),
                        escape_xml(question_data['choice_d'])
                    ],
                    'correct_answer': question_data.get('correct_answer', '').upper()
                })
        
        # 2. Performance Based Assessments - Changed from 4 to 3 sessions
        pba_sessions_data = []
        for i, session_data in enumerate(form.pba_sessions.data):
            if session_data.get('activity_name'):
                session_obj = {
                    'session_number': session_data.get('session_number', i + 1),  # Default to index + 1 if not provided
                    'activity_name': escape_xml(session_data['activity_name']),
                    'assessment_questions': []
                }
                
                # Process assessment questions for this session
                for question_data in session_data.get('assessment_questions', []):
                    if question_data.get('question'):
                        session_obj['assessment_questions'].append({
                            'question': escape_xml(question_data['question']),
                            'correct_answer': escape_xml(question_data.get('correct_answer', ''))
                        })
                
                if session_obj['assessment_questions']:  # Only add sessions with questions
                    pba_sessions_data.append(session_obj)
        
        # 3. Vocabulary
        vocabulary_data = []
        for term_data in form.vocabulary.data:
            if term_data.get('term'):
                vocabulary_data.append({
                    'term': escape_xml(term_data['term']),
                    'definition': escape_xml(term_data.get('definition', ''))
                })
        
        # 4. Student Portfolio Checklist
        portfolio_checklist_data = []
        for item_data in form.portfolio_checklist.data:
            if item_data.get('product'):
                portfolio_checklist_data.append({
                    'product': escape_xml(item_data['product']),
                    'session_number': escape_xml(item_data.get('session_number', ''))
                })
        
        # 5. Enrichment Activities - Dynamic content (build as string instead of RichText)
        enrichment_subdoc = doc.new_subdoc()
        question_counter = 1
        
        for i, field_data in enumerate(form.enrichment_dynamic_content.data):
            field_type = field_data.get('field_type')
            
            print(f"Processing enrichment field {i}: type = {field_type}")
            
            if field_type == 'section_header':
                title = (field_data.get('section_title') or '').strip()
                if title:
                    p = enrichment_subdoc.add_paragraph(title)
                    # Apply header formatting: Segoe UI 14pt Bold
                    for run in p.runs:
                        run.font.name = 'Segoe UI'
                        run.font.size = Pt(14)
                        run.font.bold = True
                    p.paragraph_format.space_before = Pt(12)
                    p.paragraph_format.space_after = Pt(6)
            
            elif field_type == 'section_instructions':
                inst_text = (field_data.get('instructions_text') or '').strip()
                if inst_text:
                    p = enrichment_subdoc.add_paragraph(inst_text)
                    # Apply instructions formatting: Segoe UI 11pt Italic
                    for run in p.runs:
                        run.font.name = 'Segoe UI'
                        run.font.size = Pt(11)
                        run.font.italic = True
                    p.paragraph_format.space_after = Pt(6)
            
            elif field_type == 'paragraph_text':
                para_text = (field_data.get('paragraph_text') or '').strip()
                if para_text:
                    p = enrichment_subdoc.add_paragraph(para_text)
                    # Apply body text formatting: Segoe UI 11pt Regular
                    for run in p.runs:
                        run.font.name = 'Segoe UI'
                        run.font.size = Pt(11)
                    p.paragraph_format.space_after = Pt(6)
            
            elif field_type == 'image':
                # Handle image upload with robust detection logic
                image_file = None
                field_name = f'enrichment_dynamic_content-{i}-image_file'
                
                # First try the expected field name
                if field_name in request.files:
                    image_file = request.files[field_name]
                else:
                    # If not found, search through all files for this field pattern
                    # This handles cases where frontend indices don't match backend indices due to deletions
                    for file_key in request.files.keys():
                        if file_key.startswith('enrichment_dynamic_content-') and file_key.endswith('-image_file'):
                            # Extract the index from the field name
                            try:
                                parts = file_key.split('-')
                                if len(parts) >= 3:
                                    file_index = int(parts[2])
                                    # Check if this file hasn't been processed yet
                                    if file_key not in processed_enrichment_image_fields:
                                        image_file = request.files[file_key]
                                        processed_enrichment_image_fields.add(file_key)
                                        print(f"Found enrichment image file with key: {file_key} for field at position {i}")
                                        break
                            except (ValueError, IndexError):
                                continue
                
                if image_file and image_file.filename:
                    # Save the uploaded file temporarily
                    filename = secure_filename(image_file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    
                    # Save the file
                    image_file.save(filepath)
                    saved_images.append(filepath)  # Track for cleanup
                    
                    # Add image to subdocument with fixed width of 4 inches
                    p = enrichment_subdoc.add_paragraph()
                    run = p.add_run()
                    run.add_picture(filepath, width=Inches(4))
                    p.alignment = 1  # Center alignment
            
            elif field_type in ['multiple_choice', 'fill_in_blank', 'text_entry', 'math_problem']:
                question_text = (field_data.get('question_text') or '').strip()
                math_expression = (field_data.get('math_expression') or '').strip()
                
                if question_text or math_expression:
                    # Add question or math problem
                    if field_type == 'math_problem' and math_expression:
                        p = enrichment_subdoc.add_paragraph(f"{question_counter}. {math_expression}")
                    else:
                        p = enrichment_subdoc.add_paragraph(f"{question_counter}. {question_text}")
                    
                    # Apply question formatting: Segoe UI 11pt Regular
                    for run in p.runs:
                        run.font.name = 'Segoe UI'
                        run.font.size = Pt(11)
                    p.paragraph_format.space_after = Pt(6)
                    
                    if field_type == 'multiple_choice':
                        # Create a 2x4 table for the choices (2 rows, 4 columns)
                        table = enrichment_subdoc.add_table(rows=2, cols=4)
                        
                        # Set column widths to be reasonable
                        table.autofit = False
                        for row in table.rows:
                            # Letters get smaller width, choices get larger width
                            row.cells[0].width = Inches(0.3)  # A.
                            row.cells[1].width = Inches(3)  # Choice A text
                            row.cells[2].width = Inches(0.3)  # C.
                            row.cells[3].width = Inches(3)  # Choice C text
                        
                        # Remove table borders for a cleaner look
                        from docx.oxml.shared import qn
                        for row in table.rows:
                            for cell in row.cells:
                                # Set cell margins
                                cell.paragraphs[0].paragraph_format.space_after = Pt(0)
                                cell.paragraphs[0].paragraph_format.space_before = Pt(0)
                        
                        # Get all choices
                        choices = [
                            ('A', field_data.get('choice_a', '')),
                            ('B', field_data.get('choice_b', '')),
                            ('C', field_data.get('choice_c', '')),
                            ('D', field_data.get('choice_d', ''))
                        ]
                        
                        # Populate the table cells in 2x4 format
                        # Row 0: A. | Choice A text | C. | Choice C text
                        # Row 1: B. | Choice B text | D. | Choice D text
                        
                        for i, (letter, choice_text) in enumerate(choices):
                            if choice_text.strip():
                                if i == 0:  # A
                                    row, letter_col, text_col = 0, 0, 1
                                elif i == 1:  # B  
                                    row, letter_col, text_col = 1, 0, 1
                                elif i == 2:  # C
                                    row, letter_col, text_col = 0, 2, 3
                                else:  # D
                                    row, letter_col, text_col = 1, 2, 3
                                
                                # Add letter (A., B., C., D.)
                                letter_cell = table.cell(row, letter_col)
                                letter_cell.text = f"{letter}."
                                for paragraph in letter_cell.paragraphs:
                                    paragraph.paragraph_format.space_before = Pt(6)
                                    for run in paragraph.runs:
                                        run.font.name = 'Segoe UI'
                                        run.font.size = Pt(11)
                                        run.font.bold = False
                                
                                # Add choice text
                                text_cell = table.cell(row, text_col)
                                text_cell.text = choice_text.strip()
                                for paragraph in text_cell.paragraphs:
                                    paragraph.paragraph_format.space_before = Pt(6)
                                    for run in paragraph.runs:
                                        run.font.name = 'Segoe UI'
                                        run.font.size = Pt(11)
                        
                        # Add spacing after the table
                        enrichment_subdoc.add_paragraph().paragraph_format.space_after = Pt(6)
                    
                    elif field_type == 'fill_in_blank':
                        p = enrichment_subdoc.add_paragraph("_________________________________________")
                        p.paragraph_format.left_indent = Pt(36)
                    
                    elif field_type == 'text_entry':
                        # Add blank lines for text entry
                        for _ in range(3):
                            p = enrichment_subdoc.add_paragraph()
                            p.paragraph_format.space_after = Pt(12)
                    
                    # Add spacing after question
                    enrichment_subdoc.add_paragraph()
                    question_counter += 1
        
        # 6. Worksheet Answer Keys - Now structured as nested worksheets
        worksheet_keys_subdoc = doc.new_subdoc()
        overall_question_counter = 1
        
        for worksheet_index, worksheet_data in enumerate(form.worksheet_answer_keys.data):
            worksheet_title = (worksheet_data.get('worksheet_title') or '').strip()
            
            # Add worksheet title as a major section header if provided
            if worksheet_title:
                p = worksheet_keys_subdoc.add_paragraph(worksheet_title)
                # Apply section header formatting: Segoe UI 14pt Bold
                for run in p.runs:
                    run.font.name = 'Segoe UI'
                    run.font.size = Pt(14)
                    run.font.bold = True
                p.paragraph_format.space_before = Pt(12)
                p.paragraph_format.space_after = Pt(6)
            
            # Process fields within this worksheet
            for field_index, field_data in enumerate(worksheet_data.get('dynamic_content', [])):
                field_type = field_data.get('field_type')
                
                print(f"Processing worksheet {worksheet_index} field {field_index}: type = {field_type}")
                
                if field_type == 'section_header':
                    title = (field_data.get('section_title') or '').strip()
                    if title:
                        p = worksheet_keys_subdoc.add_paragraph(title)
                        # Apply section header formatting: Segoe UI 14pt Bold
                        for run in p.runs:
                            run.font.name = 'Segoe UI'
                            run.font.size = Pt(14)
                            run.font.bold = True
                        p.paragraph_format.space_before = Pt(12)
                        p.paragraph_format.space_after = Pt(6)
                
                elif field_type == 'section_instructions':
                    inst_text = (field_data.get('instructions_text') or '').strip()
                    if inst_text:
                        p = worksheet_keys_subdoc.add_paragraph(inst_text)
                        # Apply instructions formatting: Segoe UI 11pt Italic
                        for run in p.runs:
                            run.font.name = 'Segoe UI'
                            run.font.size = Pt(11)
                            run.font.italic = True
                        p.paragraph_format.space_after = Pt(6)
                
                elif field_type == 'paragraph_text':
                    para_text = (field_data.get('paragraph_text') or '').strip()
                    if para_text:
                        p = worksheet_keys_subdoc.add_paragraph(para_text)
                        # Apply body text formatting: Segoe UI 11pt Regular
                        for run in p.runs:
                            run.font.name = 'Segoe UI'
                            run.font.size = Pt(11)
                        p.paragraph_format.space_after = Pt(6)
                
                elif field_type == 'image':
                    # Handle image upload with robust detection logic for worksheet fields
                    image_file = None
                    field_name = f'worksheet_answer_keys-{worksheet_index}-dynamic_content-{field_index}-image_file'
                    
                    # First try the expected field name
                    if field_name in request.files:
                        image_file = request.files[field_name]
                    else:
                        # If not found, search through all files for this field pattern
                        # This handles cases where frontend indices don't match backend indices due to deletions
                        for file_key in request.files.keys():
                            if file_key.startswith('worksheet_answer_keys-') and file_key.endswith('-image_file'):
                                # Extract the worksheet and field indices from the field name
                                try:
                                    # Expected format: worksheet_answer_keys-{worksheet_index}-dynamic_content-{field_index}-image_file
                                    parts = file_key.split('-')
                                    if len(parts) >= 5 and parts[2] == 'dynamic' and parts[3] == 'content':
                                        worksheet_idx = int(parts[1])
                                        field_idx = int(parts[4])
                                        # Check if this file hasn't been processed yet
                                        if file_key not in processed_worksheet_image_fields:
                                            image_file = request.files[file_key]
                                            processed_worksheet_image_fields.add(file_key)
                                            print(f"Found worksheet image file with key: {file_key} for worksheet {worksheet_index} field {field_index}")
                                            break
                                except (ValueError, IndexError):
                                    continue
                    
                    if image_file and image_file.filename:
                        # Save the uploaded file temporarily
                        filename = secure_filename(image_file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"{timestamp}_{filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        
                        # Save the file
                        image_file.save(filepath)
                        saved_images.append(filepath)  # Track for cleanup
                        
                        # Add image to subdocument with fixed width of 4 inches
                        p = worksheet_keys_subdoc.add_paragraph()
                        run = p.add_run()
                        run.add_picture(filepath, width=Inches(4))
                        p.alignment = 1  # Center alignment
                
                elif field_type in ['multiple_choice', 'fill_in_blank', 'text_entry', 'math_problem']:
                    question_text = (field_data.get('question_text') or '').strip()
                    math_expression = (field_data.get('math_expression') or '').strip()
                    
                    if question_text or math_expression:
                        # Add question or math problem
                        if field_type == 'math_problem' and math_expression:
                            p = worksheet_keys_subdoc.add_paragraph(f"{overall_question_counter}. {math_expression}")
                        else:
                            p = worksheet_keys_subdoc.add_paragraph(f"{overall_question_counter}. {question_text}")
                        
                        # Apply question formatting: Segoe UI 11pt Regular
                        for run in p.runs:
                            run.font.name = 'Segoe UI'
                            run.font.size = Pt(11)
                        p.paragraph_format.space_after = Pt(6)
                        
                        if field_type == 'multiple_choice':
                            # Create a 2x4 table for the choices (2 rows, 4 columns)
                            table = worksheet_keys_subdoc.add_table(rows=2, cols=4)
                            
                            # Set column widths to be reasonable
                            table.autofit = False
                            for row in table.rows:
                                # Letters get smaller width, choices get larger width
                                row.cells[0].width = Inches(0.3)  # A.
                                row.cells[1].width = Inches(3)  # Choice A text
                                row.cells[2].width = Inches(0.3)  # C.
                                row.cells[3].width = Inches(3)  # Choice C text
                            
                            # Remove table borders for a cleaner look
                            from docx.oxml.shared import qn
                            for row in table.rows:
                                for cell in row.cells:
                                    # Set cell margins
                                    cell.paragraphs[0].paragraph_format.space_after = Pt(0)
                                    cell.paragraphs[0].paragraph_format.space_before = Pt(0)
                            
                            # Get all choices
                            choices = [
                                ('A', field_data.get('choice_a', '')),
                                ('B', field_data.get('choice_b', '')),
                                ('C', field_data.get('choice_c', '')),
                                ('D', field_data.get('choice_d', ''))
                            ]
                            
                            # Populate the table cells in 2x4 format
                            # Row 0: A. | Choice A text | C. | Choice C text
                            # Row 1: B. | Choice B text | D. | Choice D text
                            
                            for i, (letter, choice_text) in enumerate(choices):
                                if choice_text.strip():
                                    if i == 0:  # A
                                        row, letter_col, text_col = 0, 0, 1
                                    elif i == 1:  # B  
                                        row, letter_col, text_col = 1, 0, 1
                                    elif i == 2:  # C
                                        row, letter_col, text_col = 0, 2, 3
                                    else:  # D
                                        row, letter_col, text_col = 1, 2, 3
                                    
                                    # Add letter (A., B., C., D.)
                                    letter_cell = table.cell(row, letter_col)
                                    letter_cell.text = f"{letter}."
                                    for paragraph in letter_cell.paragraphs:
                                        paragraph.paragraph_format.space_before = Pt(6)
                                        for run in paragraph.runs:
                                            run.font.name = 'Segoe UI'
                                            run.font.size = Pt(11)
                                            run.font.bold = False
                                    
                                    # Add choice text
                                    text_cell = table.cell(row, text_col)
                                    text_cell.text = choice_text.strip()
                                    for paragraph in text_cell.paragraphs:
                                        paragraph.paragraph_format.space_before = Pt(6)
                                        for run in paragraph.runs:
                                            run.font.name = 'Segoe UI'
                                            run.font.size = Pt(11)
                            
                            # Add spacing after the table
                            worksheet_keys_subdoc.add_paragraph().paragraph_format.space_after = Pt(6)
                        
                        elif field_type == 'fill_in_blank':
                            p = worksheet_keys_subdoc.add_paragraph("_________________________________________")
                            p.paragraph_format.left_indent = Pt(36)
                        
                        elif field_type == 'text_entry':
                            # Add blank lines for text entry
                            for _ in range(3):
                                p = worksheet_keys_subdoc.add_paragraph()
                                p.paragraph_format.space_after = Pt(12)
                        
                        # Add spacing after question
                        worksheet_keys_subdoc.add_paragraph()
                        overall_question_counter += 1
            
            # Add spacing between worksheets
            if worksheet_index < len(form.worksheet_answer_keys.data) - 1:
                worksheet_keys_subdoc.add_paragraph()
                worksheet_keys_subdoc.add_paragraph()
        
        # Build the complete context
        context = {
            'module_acronym': escape_xml(form.module_acronym.data),
            'pretest_questions': pretest_questions_data,
            'rca_sessions': rca_sessions_data,
            'posttest_questions': posttest_questions_data,
            'pba_sessions': pba_sessions_data,
            'vocabulary': vocabulary_data,
            'portfolio_checklist': portfolio_checklist_data,
            'enrichment_dynamic_content': enrichment_subdoc,
            'worksheet_answer_keys': worksheet_keys_subdoc
        }
        
        print(f"Module Answer Key context data prepared")
        print(f"Number of pre-test questions: {len(pretest_questions_data)}")
        print(f"Number of RCA sessions: {len(rca_sessions_data)}")
        print(f"Number of post-test questions: {len(posttest_questions_data)}")
        print(f"Number of PBA sessions: {len(pba_sessions_data)}")
        print(f"Number of vocabulary terms: {len(vocabulary_data)}")
        print(f"Number of portfolio checklist items: {len(portfolio_checklist_data)}")
        print(f"Saved {len(saved_images)} images")
        print(f"Processed enrichment image fields: {processed_enrichment_image_fields}")
        print(f"Processed worksheet image fields: {processed_worksheet_image_fields}")
        
        # Render the document
        print("Rendering Module Answer Key document...")
        doc.render(context)
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"Module Answer Key {escape_xml(form.module_acronym.data).replace(' ', '_')}_v2.0.docx"
        output_path = os.path.join(output_dir, filename)
        
        print(f"Saving Module Answer Key document to: {output_path}")
        doc.save(output_path)
        
        print("Module Answer Key document saved successfully!")
        
        # PROTECTION: Verify master template wasn't accidentally modified
        master_stat_after = os.stat(master_template_path)
        if master_stat.st_mtime != master_stat_after.st_mtime:
            print("⚠️  WARNING: Master template modification time changed during processing!")
        else:
            print("✓ Master template integrity verified - no accidental changes")
            
        return output_path
        
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(temp_template_path):
                os.unlink(temp_template_path)
                print(f"✓ Cleaned up temporary file: {temp_template_path}")
        except Exception as e:
            print(f"Warning: Could not clean up temporary file {temp_template_path}: {e}")
        
        # Clean up uploaded images
        for image_path in saved_images:
            try:
                if os.path.exists(image_path):
                    os.unlink(image_path)
                    print(f"✓ Cleaned up temporary image: {image_path}")
            except Exception as e:
                print(f"Warning: Could not clean up image {image_path}: {e}")

def generate_module_activity_sheet(form):
    """Generate a Module Activity Sheet using docxtpl"""
    # Use a master template that never gets touched
    master_template_path = 'templates/docx_templates/module_activity_sheet_master.docx'
    working_template_path = 'templates/docx_templates/module_activity_sheet.docx'
    
    print(f"Looking for Module Activity Sheet master template at: {master_template_path}")
    
    # Check if master template exists
    if not os.path.exists(master_template_path):
        raise FileNotFoundError("Module Activity Sheet master DOCX template not found. Please create the master template first.")
    
    # PROTECTION: Verify master template integrity before proceeding
    master_stat = os.stat(master_template_path)
    print(f"Master template size: {master_stat.st_size} bytes, modified: {datetime.fromtimestamp(master_stat.st_mtime)}")
    
    # Always copy from master to working template before processing
    print("Copying fresh Module Activity Sheet template from master...")
    try:
        shutil.copy2(master_template_path, working_template_path)
        print(f"✓ Successfully copied master to working template")
    except Exception as e:
        raise Exception(f"Failed to copy master template: {e}")
    
    print("Loading Module Activity Sheet working template...")
    
    # Create a temporary copy of the working template - NEVER touch master directly
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        try:
            shutil.copy2(working_template_path, temp_file.name)
            temp_template_path = temp_file.name
            print(f"✓ Created temporary template at: {temp_template_path}")
        except Exception as e:
            raise Exception(f"Failed to create temporary template: {e}")
    
    try:
        # Load the temporary template - NEVER the master
        print(f"Loading DocxTemplate from temporary file: {temp_template_path}")
        doc = DocxTemplate(temp_template_path)
        
        # Build context with session data
        context = {
            'module_acronym': escape_xml(form.module_acronym.data),
        }
        
        # Process each session
        for i in range(1, 8):
            activity = getattr(form, f'session{i}_activity').data
            is_pba = getattr(form, f'session{i}_is_pba').data
            
            # Escape XML special characters for DOCX compatibility
            activity = escape_xml(activity)
            
            # Create session object matching template syntax
            session_data = {
                'activity': activity,
                'is_pba': is_pba,
                'has_pba': is_pba  # Same as is_pba for assessment logic
            }
            
            context[f'session{i}'] = session_data
        
        print(f"Module Activity Sheet context data: {context}")
        
        # Render the document
        print("Rendering Module Activity Sheet document...")
        doc.render(context)
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"Module Activity Sheet {escape_xml(form.module_acronym.data).replace(' ', '_')}_v2.0.docx"
        output_path = os.path.join(output_dir, filename)
        
        print(f"Saving Module Activity Sheet document to: {output_path}")
        doc.save(output_path)
        
        print("Module Activity Sheet document saved successfully!")
        
        # PROTECTION: Verify master template wasn't accidentally modified
        master_stat_after = os.stat(master_template_path)
        if master_stat.st_mtime != master_stat_after.st_mtime:
            print("⚠️  WARNING: Master template modification time changed during processing!")
        else:
            print("✓ Master template integrity verified - no accidental changes")
            
        return output_path
        
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(temp_template_path):
                os.unlink(temp_template_path)
                print(f"✓ Cleaned up temporary file: {temp_template_path}")
        except Exception as e:
            print(f"Warning: Could not clean up temporary file {temp_template_path}: {e}")

@app.route('/debug/db-status')
def debug_db_status():
    """Debug route to check database status and create tables if needed"""
    try:
        # Try to create all tables
        with app.app_context():
            db.create_all()
        
        # Test database connection
        total_users = User.query.count()
        admin_count = User.query.filter_by(is_admin=True).count()
        
        # Test if we can create a simple log entry
        test_log = ActivityLog(
            action='database_test',
            details={'test': True}
        )
        db.session.add(test_log)
        db.session.commit()
        
        # Clean up test log
        db.session.delete(test_log)
        db.session.commit()
        
        return f"""
        <h1>Database Status - OK</h1>
        <ul>
        <li>Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')[:50]}...</li>
        <li>Total users: {total_users}</li>
        <li>Admin users: {admin_count}</li>
        <li>Tables created: SUCCESS</li>
        <li>Database operations: SUCCESS</li>
        </ul>
        <p><a href="/setup">Go to Setup</a> | <a href="/">Home</a></p>
        """
        
    except Exception as e:
        return f"""
        <h1>Database Status - ERROR</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><strong>Database URL:</strong> {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')[:50]}...</p>
        <p><a href="/">Home</a></p>
        """

@app.route('/force-db-init')
def force_db_init():
    """Force database initialization - EMERGENCY USE ONLY"""
    try:
        # Drop and recreate all tables (CAREFUL!)
        with app.app_context():
            db.drop_all()
            db.create_all()
        
        return f"""
        <h1>🚨 Database Reinitialized</h1>
        <p><strong>WARNING:</strong> All data has been reset!</p>
        <p>You need to recreate your admin user.</p>
        <p><a href="/create-admin-simple">Create Admin User</a></p>
        """
        
    except Exception as e:
        return f"""
        <h1>Database Initialization - ERROR</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><a href="/debug/db-status">Check Database Status</a></p>
        """

@app.route('/migrate-db')
def migrate_db():
    """Safely migrate database - add missing tables only"""
    try:
        # Create only missing tables (safe operation)
        with app.app_context():
            db.create_all()
        
        # Test that we can query existing users
        total_users = User.query.count()
        
        return f"""
        <h1>✅ Database Migration Complete</h1>
        <p><strong>Status:</strong> Missing tables created successfully</p>
        <p><strong>Existing users preserved:</strong> {total_users} users found</p>
        <p>Your login should now work!</p>
        <p><a href="/login">Try Login Again</a> | <a href="/">Home</a></p>
        """
        
    except Exception as e:
        return f"""
        <h1>Database Migration - ERROR</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><strong>Try force reset:</strong> <a href="/force-db-init">Force DB Reinitialization</a></p>
        <p><a href="/debug/db-status">Check Database Status</a></p>
        """

@app.route('/create-admin-simple', methods=['GET', 'POST'])
def create_admin_simple():
    """Simple admin creation with better error handling"""
    try:
        # Ensure tables exist
        with app.app_context():
            db.create_all()
        
        if request.method == 'GET':
            # Check if admin already exists
            existing_admin = User.query.filter_by(is_admin=True).first()
            if existing_admin:
                return f"""
                <h2>Admin Already Exists</h2>
                <p>Email: {existing_admin.email}</p>
                <p>Username: {existing_admin.username}</p>
                <p><a href="/login">Go to Login</a></p>
                """
            
            return """
            <h2>Create Admin User</h2>
            <form method="POST">
                <p><label>Email: <input type="email" name="email" required></label></p>
                <p><label>Username: <input type="text" name="username" required></label></p>
                <p><label>Password: <input type="password" name="password" required></label></p>
                <p><label>First Name: <input type="text" name="first_name"></label></p>
                <p><label>Last Name: <input type="text" name="last_name"></label></p>
                <p><button type="submit">Create Admin</button></p>
            </form>
            """
        
        # POST request - create admin
        email = request.form.get('email')
        username = request.form.get('username') 
        password = request.form.get('password')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        
        if not email or not username or not password:
            return "<h2>Error: Email, username and password required</h2><a href='/create-admin-simple'>Try Again</a>"
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            return f"<h2>Error: Email {email} already exists</h2><a href='/create-admin-simple'>Try Again</a>"
        
        # Create admin user
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
        
        return f"""
        <h2>Admin Created Successfully!</h2>
        <p>Email: {email}</p>
        <p>Username: {username}</p>
        <p><a href="/login">Go to Login</a></p>
        """
        
    except Exception as e:
        return f"""
        <h2>Error Creating Admin</h2>
        <p>{str(e)}</p>
        <p><a href="/debug/db-status">Check Database Status</a></p>
        """

# New routes for save/load/download functionality
@app.route('/save-vocabulary-draft', methods=['POST'])
@login_required
def save_vocabulary_draft():
    """Save vocabulary worksheet as draft"""
    form = VocabularyWorksheetForm()
    
    if form.validate_on_submit():
        try:
            # Prepare form data for JSON storage
            form_data = {
                'module_acronym': form.module_acronym.data,
                'words': [{'word': word.word.data} for word in form.words if word.word.data]
            }
            
            # Check if this is updating an existing draft
            draft_id = request.form.get('draft_id')
            if draft_id:
                draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id).first()
                if draft:
                    # Update existing draft
                    draft.form_data = form_data
                    draft.updated_at = datetime.utcnow()
                else:
                    flash('Draft not found', 'error')
                    return redirect(url_for('create_vocabulary'))
            else:
                # Create new draft
                title = f"Vocabulary Worksheet - {form.module_acronym.data}" if form.module_acronym.data else "Vocabulary Worksheet - Untitled"
                draft = FormDraft(
                    user_id=current_user.id,
                    form_type='vocabulary',
                    title=title,
                    module_acronym=form.module_acronym.data,
                    form_data=form_data
                )
                db.session.add(draft)
            
            db.session.commit()
            flash('Draft saved successfully!', 'success')
            
        except Exception as e:
            print(f"Error saving draft: {e}")
            flash(f'Error saving draft: {str(e)}', 'error')
    else:
        flash('Please fix form errors before saving', 'error')
    
    return redirect(url_for('create_vocabulary'))

@app.route('/load-vocabulary-draft/<int:draft_id>')
@login_required
def load_vocabulary_draft(draft_id):
    """Load vocabulary worksheet draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='vocabulary').first()
    
    if not draft:
        flash('Draft not found', 'error')
        return redirect(url_for('create_vocabulary'))
    
    try:
        # Create form and populate with draft data
        form = VocabularyWorksheetForm()
        form_data = draft.form_data
        
        # Populate form fields
        form.module_acronym.data = form_data.get('module_acronym', '')
        
        # Populate vocabulary words
        words_data = form_data.get('words', [])
        for i, word_data in enumerate(words_data):
            if i < len(form.words):
                form.words[i].word.data = word_data.get('word', '')
        
        flash(f'Draft "{draft.title}" loaded successfully!', 'success')
        return render_template('create_vocabulary.html', form=form, draft_id=draft.id)
        
    except Exception as e:
        print(f"Error loading draft: {e}")
        flash(f'Error loading draft: {str(e)}', 'error')
        return redirect(url_for('create_vocabulary'))

@app.route('/vocabulary-drafts')
@login_required
def vocabulary_drafts():
    """List user's vocabulary worksheet drafts"""
    drafts = FormDraft.query.filter_by(
        user_id=current_user.id, 
        form_type='vocabulary',
        is_current=True
    ).order_by(FormDraft.updated_at.desc()).all()
    
    return render_template('vocabulary_drafts.html', drafts=drafts)

@app.route('/delete-vocabulary-draft/<int:draft_id>', methods=['POST'])
@login_required
def delete_vocabulary_draft(draft_id):
    """Delete vocabulary worksheet draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='vocabulary').first()
    
    if not draft:
        flash('Draft not found', 'error')
    else:
        db.session.delete(draft)
        db.session.commit()
        flash('Draft deleted successfully!', 'success')
    
    return redirect(url_for('vocabulary_drafts'))

@app.route('/download/<int:doc_id>')
@login_required
def download_document(doc_id):
    """Download a generated document"""
    document = GeneratedDocument.query.filter_by(id=doc_id, user_id=current_user.id).first()
    
    if not document:
        flash('Document not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if file exists
    if not os.path.exists(document.file_path):
        flash('Document file not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Track download
    document.increment_download()
    db.session.commit()
    
    # Activity logging
    ActivityLog.log_activity('document_downloaded', current_user.id, 
                            {'document_type': document.document_type, 'filename': document.filename}, 
                            request)
    db.session.commit()
    
    # Return file for download
    return send_file(document.file_path, as_attachment=True, download_name=document.filename)

@app.route('/my-documents')
@login_required
def my_documents():
    """List user's generated documents"""
    documents = GeneratedDocument.query.filter_by(
        user_id=current_user.id
    ).order_by(GeneratedDocument.created_at.desc()).all()
    
    return render_template('my_documents.html', documents=documents)

if __name__ == '__main__':
    app.run(debug=True) 