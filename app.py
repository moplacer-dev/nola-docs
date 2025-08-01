from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
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
import PyPDF2
import re

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

# Database configuration with Render compatibility
database_url = os.environ.get('DATABASE_URL', 'sqlite:///nola_docs.db')
# Fix for Render PostgreSQL URL format
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Environment detection
app.config['IS_PRODUCTION'] = os.environ.get('FLASK_ENV') == 'production' or 'render.com' in os.environ.get('RENDER_EXTERNAL_URL', '')

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

# CSRF Protection setup
csrf = CSRFProtect(app)

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

def load_moduleanswerkey_draft_into_form(form, user_id):
    """Load the most recent moduleanswerkey draft data into the provided form"""
    try:
        # Get the most recent draft for this user
        latest_draft = FormDraft.query.filter_by(
            user_id=user_id, 
            form_type='moduleanswerkey'
        ).order_by(FormDraft.updated_at.desc()).first()
        
        if not latest_draft:
            print("🔍 No moduleanswerkey draft found for user")
            return False
            
        print(f"🔍 Loading draft data from draft ID {latest_draft.id}")
        form_data = latest_draft.form_data
        
        # Populate basic fields
        form.module_acronym.data = form_data.get('module_acronym', '')
        
        # Populate pre-test questions
        pretest_data = form_data.get('pretest_questions', [])
        for i, question_data in enumerate(pretest_data):
            if i < len(form.pretest_questions):
                form.pretest_questions[i].question_text.data = question_data.get('question_text', '')
                form.pretest_questions[i].choice_a.data = question_data.get('choice_a', '')
                form.pretest_questions[i].choice_b.data = question_data.get('choice_b', '')
                form.pretest_questions[i].choice_c.data = question_data.get('choice_c', '')
                form.pretest_questions[i].choice_d.data = question_data.get('choice_d', '')
                # Clean correct_answer to ensure it's valid
                correct_answer = question_data.get('correct_answer', '').strip().upper()
                form.pretest_questions[i].correct_answer.data = correct_answer if correct_answer in ['A', 'B', 'C', 'D'] else ''
        
        # Populate RCA sessions
        rca_data = form_data.get('rca_sessions', [])
        print(f"🔍 Loading RCA sessions data: {len(rca_data)} sessions found")
        for i, session_data in enumerate(rca_data):
            if i < len(form.rca_sessions):
                questions = session_data.get('questions', [])
                for j, question_data in enumerate(questions):
                    if j < len(form.rca_sessions[i].questions):
                        form.rca_sessions[i].questions[j].question_text.data = question_data.get('question_text', '')
                        form.rca_sessions[i].questions[j].choice_a.data = question_data.get('choice_a', '')
                        form.rca_sessions[i].questions[j].choice_b.data = question_data.get('choice_b', '')
                        form.rca_sessions[i].questions[j].choice_c.data = question_data.get('choice_c', '')
                        form.rca_sessions[i].questions[j].choice_d.data = question_data.get('choice_d', '')
                        # Clean correct_answer to ensure it's valid
                        correct_answer = question_data.get('correct_answer', '').strip().upper()
                        form.rca_sessions[i].questions[j].correct_answer.data = correct_answer if correct_answer in ['A', 'B', 'C', 'D'] else ''
        
        # Populate post-test questions
        posttest_data = form_data.get('posttest_questions', [])
        for i, question_data in enumerate(posttest_data):
            if i < len(form.posttest_questions):
                form.posttest_questions[i].question_text.data = question_data.get('question_text', '')
                form.posttest_questions[i].choice_a.data = question_data.get('choice_a', '')
                form.posttest_questions[i].choice_b.data = question_data.get('choice_b', '')
                form.posttest_questions[i].choice_c.data = question_data.get('choice_c', '')
                form.posttest_questions[i].choice_d.data = question_data.get('choice_d', '')
                # Clean correct_answer to ensure it's valid
                correct_answer = question_data.get('correct_answer', '').strip().upper()
                form.posttest_questions[i].correct_answer.data = correct_answer if correct_answer in ['A', 'B', 'C', 'D'] else ''
        
        # Populate PBA sessions
        pba_data = form_data.get('pba_sessions', [])
        print(f"🔍 Loading PBA sessions data: {len(pba_data)} sessions found")
        for i, session_data in enumerate(pba_data):
            if i < len(form.pba_sessions):
                form.pba_sessions[i].session_number.data = session_data.get('session_number', '')
                form.pba_sessions[i].activity_name.data = session_data.get('activity_name', '')
                
                questions = session_data.get('assessment_questions', [])
                for j, question_data in enumerate(questions):
                    if j < len(form.pba_sessions[i].assessment_questions):
                        form.pba_sessions[i].assessment_questions[j].question.data = question_data.get('question', '')
                        form.pba_sessions[i].assessment_questions[j].correct_answer.data = question_data.get('correct_answer', '')
        
        # Populate vocabulary
        vocab_data = form_data.get('vocabulary', [])
        for i, term_data in enumerate(vocab_data):
            if i < len(form.vocabulary):
                form.vocabulary[i].term.data = term_data.get('term', '')
                form.vocabulary[i].definition.data = term_data.get('definition', '')
        
        # Populate portfolio checklist
        portfolio_data = form_data.get('portfolio_checklist', [])
        for i, item_data in enumerate(portfolio_data):
            if i < len(form.portfolio_checklist):
                form.portfolio_checklist[i].product.data = item_data.get('product', '')
                form.portfolio_checklist[i].session_number.data = item_data.get('session_number', '')
        
        print(f"🔍 Successfully loaded simplified module answer key draft data")
        return True
        
    except Exception as e:
        print(f"🔍 Error loading draft data into form: {e}")
        import traceback
        traceback.print_exc()
        return False

def load_module_answer_key2_draft_into_form(form, user_id):
    """Load the most recent module_answer_key2 draft data into the provided form"""
    try:
        # Get the most recent draft for this user
        latest_draft = FormDraft.query.filter_by(
            user_id=user_id, 
            form_type='module_answer_key2'
        ).order_by(FormDraft.updated_at.desc()).first()
        
        if not latest_draft:
            print("🔍 No module_answer_key2 draft found for user")
            return False
            
        print(f"🔍 Loading draft data from Module Answer Key 2.0 draft ID {latest_draft.id}")
        form_data = latest_draft.form_data
        
        # Populate basic fields
        form.module_acronym.data = form_data.get('module_acronym', '')
        
        # Populate pre-test questions
        pretest_data = form_data.get('pretest_questions', [])
        for i, question_data in enumerate(pretest_data):
            if i < len(form.pretest_questions):
                form.pretest_questions[i].question_text.data = question_data.get('question_text', '')
                form.pretest_questions[i].choice_a.data = question_data.get('choice_a', '')
                form.pretest_questions[i].choice_b.data = question_data.get('choice_b', '')
                form.pretest_questions[i].choice_c.data = question_data.get('choice_c', '')
                form.pretest_questions[i].choice_d.data = question_data.get('choice_d', '')
                # Clean correct_answer to ensure it's valid
                correct_answer = question_data.get('correct_answer', '').strip().upper()
                form.pretest_questions[i].correct_answer.data = correct_answer if correct_answer in ['A', 'B', 'C', 'D'] else ''
        
        # Populate RCA sessions
        rca_data = form_data.get('rca_sessions', [])
        print(f"🔍 Loading RCA sessions data: {len(rca_data)} sessions found")
        for i, session_data in enumerate(rca_data):
            if i < len(form.rca_sessions):
                questions = session_data.get('questions', [])
                for j, question_data in enumerate(questions):
                    if j < len(form.rca_sessions[i].questions):
                        form.rca_sessions[i].questions[j].question_text.data = question_data.get('question_text', '')
                        form.rca_sessions[i].questions[j].choice_a.data = question_data.get('choice_a', '')
                        form.rca_sessions[i].questions[j].choice_b.data = question_data.get('choice_b', '')
                        form.rca_sessions[i].questions[j].choice_c.data = question_data.get('choice_c', '')
                        form.rca_sessions[i].questions[j].choice_d.data = question_data.get('choice_d', '')
                        # Clean correct_answer to ensure it's valid
                        correct_answer = question_data.get('correct_answer', '').strip().upper()
                        form.rca_sessions[i].questions[j].correct_answer.data = correct_answer if correct_answer in ['A', 'B', 'C', 'D'] else ''
        
        # Populate post-test questions
        posttest_data = form_data.get('posttest_questions', [])
        for i, question_data in enumerate(posttest_data):
            if i < len(form.posttest_questions):
                form.posttest_questions[i].question_text.data = question_data.get('question_text', '')
                form.posttest_questions[i].choice_a.data = question_data.get('choice_a', '')
                form.posttest_questions[i].choice_b.data = question_data.get('choice_b', '')
                form.posttest_questions[i].choice_c.data = question_data.get('choice_c', '')
                form.posttest_questions[i].choice_d.data = question_data.get('choice_d', '')
                # Clean correct_answer to ensure it's valid
                correct_answer = question_data.get('correct_answer', '').strip().upper()
                form.posttest_questions[i].correct_answer.data = correct_answer if correct_answer in ['A', 'B', 'C', 'D'] else ''
        
        # Populate PBA sessions
        pba_data = form_data.get('pba_sessions', [])
        print(f"🔍 Loading PBA sessions data: {len(pba_data)} sessions found")
        for i, session_data in enumerate(pba_data):
            if i < len(form.pba_sessions):
                form.pba_sessions[i].session_number.data = session_data.get('session_number', '')
                form.pba_sessions[i].activity_name.data = session_data.get('activity_name', '')
                
                questions = session_data.get('assessment_questions', [])
                for j, question_data in enumerate(questions):
                    if j < len(form.pba_sessions[i].assessment_questions):
                        form.pba_sessions[i].assessment_questions[j].question.data = question_data.get('question', '')
                        form.pba_sessions[i].assessment_questions[j].correct_answer.data = question_data.get('correct_answer', '')
        
        # Populate vocabulary
        vocab_data = form_data.get('vocabulary', [])
        for i, term_data in enumerate(vocab_data):
            if i < len(form.vocabulary):
                form.vocabulary[i].term.data = term_data.get('term', '')
                form.vocabulary[i].definition.data = term_data.get('definition', '')
        
        # Populate portfolio checklist
        portfolio_data = form_data.get('portfolio_checklist', [])
        for i, item_data in enumerate(portfolio_data):
            if i < len(form.portfolio_checklist):
                form.portfolio_checklist[i].product.data = item_data.get('product', '')
                form.portfolio_checklist[i].session_number.data = item_data.get('session_number', '')
        
        print(f"🔍 Successfully loaded Module Answer Key 2.0 draft data")
        return True
        
    except Exception as e:
        print(f"🔍 Error loading Module Answer Key 2.0 draft data into form: {e}")
        import traceback
        traceback.print_exc()
        return False

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
    
    # Learning Objectives (6)
    learningobjective1 = TextAreaField('Learning Objective 1', validators=[Optional(), Length(max=300)])
    learningobjective2 = TextAreaField('Learning Objective 2', validators=[Optional(), Length(max=300)])
    learningobjective3 = TextAreaField('Learning Objective 3', validators=[Optional(), Length(max=300)])
    learningobjective4 = TextAreaField('Learning Objective 4', validators=[Optional(), Length(max=300)])
    learningobjective5 = TextAreaField('Learning Objective 5', validators=[Optional(), Length(max=300)])
    learningobjective6 = TextAreaField('Learning Objective 6', validators=[Optional(), Length(max=300)])
    
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
    keyconcept1_name = StringField('Key Concept 1 Name', validators=[Optional(), Length(max=300)])
    keyconcept1_explanation = TextAreaField('Key Concept 1 Explanation', validators=[Optional(), Length(max=600)])
    
    keyconcept2_name = StringField('Key Concept 2 Name', validators=[Optional(), Length(max=300)])
    keyconcept2_explanation = TextAreaField('Key Concept 2 Explanation', validators=[Optional(), Length(max=600)])
    
    keyconcept3_name = StringField('Key Concept 3 Name', validators=[Optional(), Length(max=300)])
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

# ===== MODULE ANSWER KEY 2.0 FORM =====

# Main Module Answer Key 2.0 form - Streamlined version without Enrichment and Worksheet sections
class ModuleAnswerKey2Form(FlaskForm):
    module_acronym = StringField('Module Acronym', 
                               validators=[DataRequired(), Length(min=1, max=20)],
                               render_kw={"placeholder": "e.g., APHY, CHEM, BIOE", "data-autosave": "true"})
    
    # Assessments Section
    # Pre-test questions (10 questions)
    pretest_questions = FieldList(FormField(AnswerKeyQuestionForm), min_entries=10, max_entries=10)
    
    # RCA sessions (sessions 2-5, each with 3 questions)
    rca_sessions = FieldList(FormField(RCASessionForm), min_entries=4, max_entries=4)
    
    # Post-test questions (10 questions)
    posttest_questions = FieldList(FormField(AnswerKeyQuestionForm), min_entries=10, max_entries=10)
    
    # Performance Based Assessments (3 sessions, numbered 1-3)
    pba_sessions = FieldList(FormField(PBASessionForm), min_entries=3, max_entries=3)
    
    # Vocabulary (25-30 terms)
    vocabulary = FieldList(FormField(VocabularyTermForm), min_entries=25, max_entries=30)
    
    # Student Portfolio Checklist (6-10 items)
    portfolio_checklist = FieldList(FormField(PortfolioChecklistItemForm), min_entries=6, max_entries=10)
    
    submit = SubmitField('Generate Module Answer Key 2.0')
    
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

# ===== HORIZONTAL LESSON PLAN FORMS =====

class HorizontalLessonPlanSessionForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    focus = TextAreaField('Session Focus', validators=[Optional(), Length(max=500)])
    objectives = TextAreaField('Learning Objectives', validators=[Optional(), Length(max=1000)])
    materials = TextAreaField('Materials', validators=[Optional(), Length(max=1000)])
    teacher_prep = TextAreaField('Teacher Preparations', validators=[Optional(), Length(max=1000)])
    assessments = TextAreaField('Performance Based Assessments', validators=[Optional(), Length(max=1000)])

class HorizontalLessonPlanModuleForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for nested forms
    
    module_name = StringField('Module Name', validators=[Optional(), Length(max=200)])
    
    # PDF upload for this module
    session_notes_pdf = FileField('Session Notes PDF', validators=[
        FileAllowed(['pdf'], 'PDF files only!')
    ])
    
    # 7 sessions for this module
    sessions = FieldList(FormField(HorizontalLessonPlanSessionForm), min_entries=7, max_entries=7)
    
    enrichment_activities = TextAreaField('Enrichment Activities', validators=[Optional(), Length(max=1000)])

class HorizontalLessonPlanForm(FlaskForm):
    # Basic information
    school_name = StringField('School Name', 
                             validators=[DataRequired(), Length(min=1, max=200)],
                             render_kw={"placeholder": "e.g., Jefferson Elementary School"})
    
    teacher_name = StringField('Teacher Name', 
                              validators=[DataRequired(), Length(min=1, max=100)],
                              render_kw={"placeholder": "e.g., Ms. Johnson"})
    
    term = StringField('Term', 
                      validators=[DataRequired(), Length(min=1, max=50)],
                      render_kw={"placeholder": "e.g., Fall 2024, Spring 2025"})
    
    # Up to 5 modules
    modules = FieldList(FormField(HorizontalLessonPlanModuleForm), min_entries=5, max_entries=5)
    
    submit = SubmitField('Generate Horizontal Lesson Plan')
    
    def validate(self, extra_validators=None):
        """Custom validation to ensure at least one module has data"""
        if not super().validate(extra_validators=extra_validators):
            return False
            
        # Check if this is an extraction request - if so, allow validation to pass if PDFs are uploaded
        action = request.form.get('action', 'generate') if request else 'generate'
        
        if action == 'extract':
            # For extraction, check if at least one PDF is uploaded
            has_pdf = False
            for module in self.modules:
                if module.session_notes_pdf.data and module.session_notes_pdf.data.filename:
                    has_pdf = True
                    break
            
            if not has_pdf:
                self.modules[0].session_notes_pdf.errors.append('Please upload at least one PDF file to extract data from.')
                return False
            
            return True
        
        # For other actions (generate/save_draft), check if at least one module has data
        has_module_data = False
        for module in self.modules:
            if module.module_name.data or any(session.focus.data or session.objectives.data 
                                            for session in module.sessions):
                has_module_data = True
                break
        
        if not has_module_data:
            self.modules[0].module_name.errors.append('Please provide data for at least one module.')
            return False
            
        return True

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
        
        # Calculate total downloads across all user documents
        user_docs = GeneratedDocument.query.filter_by(user_id=current_user.id).all()
        total_downloads = sum(doc.download_count for doc in user_docs)
        
        return render_template('dashboard.html', 
                             recent_drafts=recent_drafts,
                             recent_docs=recent_docs,
                             total_drafts=total_drafts,
                             total_docs=total_docs,
                             total_downloads=total_downloads)
                             
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

@app.route('/autosave-vocabulary-draft', methods=['POST'])
@login_required
def autosave_vocabulary_draft():
    """AJAX endpoint for autosaving vocabulary draft"""
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Prepare form data for JSON storage
        form_data = {
            'module_acronym': data.get('module_acronym', ''),
            'words': []
        }
        
        # Process vocabulary words
        words_data = data.get('words', [])
        for word_data in words_data:
            word_text = word_data.get('word', '').strip()
            if word_text:  # Only include non-empty words
                form_data['words'].append({'word': word_text})
        
        # Check if this is updating an existing draft
        draft_id = data.get('draft_id')
        if draft_id:
            # Update existing draft
            draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='vocabulary').first()
            if draft:
                draft.form_data = form_data
                draft.updated_at = datetime.utcnow()
                # Update title if module acronym changed
                if form_data['module_acronym']:
                    draft.title = f"Vocabulary Worksheet - {form_data['module_acronym']}"
                    draft.module_acronym = form_data['module_acronym']
            else:
                return jsonify({'success': False, 'error': 'Draft not found'})
        else:
            # Create new draft
            title = f"Vocabulary Worksheet - {form_data['module_acronym']}" if form_data['module_acronym'] else "Vocabulary Worksheet - Untitled"
            draft = FormDraft(
                user_id=current_user.id,
                form_type='vocabulary',
                title=title,
                module_acronym=form_data['module_acronym'],
                form_data=form_data
            )
            db.session.add(draft)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'draft_id': draft.id,
            'message': 'Draft saved automatically',
            'timestamp': datetime.utcnow().strftime('%I:%M:%S %p')
        })
        
    except Exception as e:
        print(f"Error in autosave: {e}")
        return jsonify({'success': False, 'error': str(e)})

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
        
        # Check which action was requested
        action = request.form.get('action', 'generate')
        print(f"Action requested: {action}")
        
        if form.validate_on_submit():
            if action == 'save_draft':
                # Handle draft saving
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
                            return render_template('create_vocabulary.html', form=form)
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
                    return render_template('create_vocabulary.html', form=form, draft_id=draft.id)
                    
                except Exception as e:
                    print(f"Error saving draft: {e}")
                    flash(f'Error saving draft: {str(e)}', 'error')
                    return render_template('create_vocabulary.html', form=form)
            
            else:  # action == 'generate' or default
                # Handle document generation
                print("Form validation passed!")
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
                    return redirect(url_for('my_documents'))
                except Exception as e:
                    print(f"Error generating document: {e}")
                    flash(f'Error generating worksheet: {str(e)}', 'error')
        else:
            if action == 'save_draft':
                flash('Please fix form errors before saving', 'error')
    
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
    
        # Only handle document generation now - autosave handles saving
        if form.validate_on_submit():
            print("PBA form validation passed!")
            try:
                print("Attempting to generate PBA worksheet...")
                doc_path = generate_pba_worksheet(form)
                filename = os.path.basename(doc_path)
                
                print(f"PBA worksheet generated at: {doc_path}")
                
                # Save document info to database
                doc_record = GeneratedDocument(
                    user_id=current_user.id,
                    document_type='pba',
                    filename=filename,
                    file_path=doc_path,
                    module_acronym=form.module_acronym.data,
                    file_size=os.path.getsize(doc_path)
                )
                db.session.add(doc_record)
                db.session.commit()
                
                flash('PBA worksheet generated successfully!', 'success')
                return redirect(url_for('my_documents'))
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
        
        # Only handle document generation now - autosave handles saving
        if form.validate_on_submit():
            print("Test form validation passed!")
            try:
                test_type = form.test_type.data
                if test_type == 'pre':
                    print("Attempting to generate pre-test worksheet...")
                    doc_path = generate_pretest_worksheet(form)
                    filename = os.path.basename(doc_path)
                    document_type = 'pretest'
                    flash('Pre-Test worksheet generated successfully!', 'success')
                else:  # test_type == 'post'
                    print("Attempting to generate post-test worksheet...")
                    doc_path = generate_posttest_worksheet(form)
                    filename = os.path.basename(doc_path)
                    document_type = 'posttest'
                    flash('Post-Test worksheet generated successfully!', 'success')
                
                print(f"Test worksheet generated at: {doc_path}")
                
                # Save document info to database
                doc_record = GeneratedDocument(
                    user_id=current_user.id,
                    document_type=document_type,
                    filename=filename,
                    file_path=doc_path,
                    module_acronym=form.module_acronym.data,
                    file_size=os.path.getsize(doc_path)
                )
                db.session.add(doc_record)
                db.session.commit()
                
                return redirect(url_for('my_documents'))
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
            doc_path, filename = generate_generic_worksheet(form)
            print(f"Generic worksheet generated at: {doc_path}")
            
            # Save document info to database
            doc_record = GeneratedDocument(
                user_id=current_user.id,
                document_type='generic',
                filename=filename,
                file_path=doc_path,
                module_acronym=form.module_acronym.data,
                file_size=os.path.getsize(doc_path)
            )
            db.session.add(doc_record)
            db.session.commit()
            
            flash('Generic worksheet generated successfully!', 'success')
            return redirect(url_for('my_documents'))
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
            filename = os.path.basename(doc_path)
            
            print(f"Family briefing generated at: {doc_path}")
            
            # Save document info to database
            doc_record = GeneratedDocument(
                user_id=current_user.id,
                document_type='familybriefing',
                filename=filename,
                file_path=doc_path,
                module_acronym=form.module_name.data,  # Note: Family Briefing uses module_name, not module_acronym
                file_size=os.path.getsize(doc_path)
            )
            db.session.add(doc_record)
            db.session.commit()
            
            flash('Family Briefing generated successfully!', 'success')
            return redirect(url_for('my_documents'))
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
            filename = os.path.basename(doc_path)
            
            print(f"RCA worksheet generated at: {doc_path}")
            
            # Save document info to database
            doc_record = GeneratedDocument(
                user_id=current_user.id,
                document_type='rca',
                filename=filename,
                file_path=doc_path,
                module_acronym=form.module_acronym.data,
                file_size=os.path.getsize(doc_path)
            )
            db.session.add(doc_record)
            db.session.commit()
            
            flash('RCA worksheet generated successfully!', 'success')
            return redirect(url_for('my_documents'))
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
            filename = os.path.basename(doc_path)
            
            print(f"Module Guide generated at: {doc_path}")
            
            # Save document info to database
            doc_record = GeneratedDocument(
                user_id=current_user.id,
                document_type='moduleguide',
                filename=filename,
                file_path=doc_path,
                module_acronym=form.module_acronym.data,
                file_size=os.path.getsize(doc_path)
            )
            db.session.add(doc_record)
            db.session.commit()
            
            flash('Module Guide generated successfully!', 'success')
            return redirect(url_for('my_documents'))
        except Exception as e:
            print(f"Error generating Module Guide: {e}")
            flash(f'Error generating Module Guide: {str(e)}', 'error')
    
    return render_template('create_moduleGuide.html', form=form)

@app.route('/create-moduleAnswerKey', methods=['GET', 'POST'])
@login_required
def create_module_answer_key():
    form = ModuleAnswerKeyForm()
    
    if request.method == 'POST':
        print("🔍 Module Answer Key form submitted!")
        print(f"🔍 Request method: {request.method}")
        print(f"🔍 Form data keys: {list(request.form.keys())}")
        print(f"🔍 Action value: {request.form.get('action', 'NOT FOUND')}")
        print(f"🔍 Module acronym: {request.form.get('module_acronym', 'NOT FOUND')}")
        print(f"🔍 Form valid: {form.validate_on_submit()}")
        if form.errors:
            print(f"🔍 Form errors: {form.errors}")
        
        # Check if this is actually a generation request
        action = request.form.get('action')
        if action != 'generate':
            print(f"🔍 Skipping generation - action is '{action}', not 'generate'")
            return render_template('create_moduleAnswerKey.html', form=form)
        
        # Only handle document generation now - autosave handles saving
        if form.validate_on_submit():
            print("🔍 Module Answer Key form validation passed!")
            
            # CRITICAL FIX: Load autosaved draft data directly for generation
            print("🔍 Loading autosaved draft data for generation...")
            latest_draft = FormDraft.query.filter_by(
                user_id=current_user.id, 
                form_type='moduleanswerkey'
            ).order_by(FormDraft.updated_at.desc()).first()
            
            if latest_draft and latest_draft.form_data:
                print("🔍 Found draft data - merging with form data for generation")
                # Create a merged form that combines submitted data with autosaved data
                merged_form = ModuleAnswerKeyForm()
                
                # Use basic fields from submitted form (like module_acronym)
                merged_form.module_acronym.data = form.module_acronym.data
                
                # Load all data from the draft to ensure completeness
                draft_loaded = load_moduleanswerkey_draft_into_form(merged_form, current_user.id)
                if draft_loaded:
                    print(f"🔍 Successfully loaded draft - using merged form (worksheet sections removed for simplification)")
                    form = merged_form  # Use the merged form for generation
                else:
                    print("🔍 Failed to load draft - using submitted form")
            else:
                print("🔍 No draft data found - using submitted form")
            
            try:
                print("🔍 Attempting to generate Module Answer Key...")
                print(f"🔍 Form simplified - worksheet sections moved to separate template")
                doc_path = generate_module_answer_key(form)
                filename = os.path.basename(doc_path)
                
                print(f"🔍 Module Answer Key generated at: {doc_path}")
                
                # Save document info to database
                doc_record = GeneratedDocument(
                    user_id=current_user.id,
                    document_type='moduleanswerkey',
                    filename=filename,
                    file_path=doc_path,
                    module_acronym=form.module_acronym.data,
                    file_size=os.path.getsize(doc_path)
                )
                db.session.add(doc_record)
                db.session.commit()
                
                print(f"🔍 Database record created successfully")
                flash('Module Answer Key generated successfully!', 'success')
                return redirect(url_for('my_documents'))
            except Exception as e:
                print(f"🔍 Error generating Module Answer Key: {e}")
                import traceback
                traceback.print_exc()  # Print full traceback for debugging
                flash(f'Error generating Module Answer Key: {str(e)}', 'error')
                return render_template('create_moduleAnswerKey.html', form=form)
        else:
            print(f"🔍 Form validation failed!")
            print(f"🔍 Validation errors: {form.errors}")
    
    return render_template('create_moduleAnswerKey.html', form=form)

# ===== MODULE ANSWER KEY 2.0 ROUTES =====

@app.route('/create-module-answer-key2', methods=['GET', 'POST'])
@login_required
def create_module_answer_key2():
    form = ModuleAnswerKey2Form()
    
    if request.method == 'POST':
        print("🔍 Module Answer Key 2.0 form submitted!")
        print(f"🔍 Request method: {request.method}")
        print(f"🔍 Form data keys: {list(request.form.keys())}")
        print(f"🔍 Action value: {request.form.get('action', 'NOT FOUND')}")
        print(f"🔍 Module acronym: {request.form.get('module_acronym', 'NOT FOUND')}")
        print(f"🔍 Form valid: {form.validate_on_submit()}")
        if form.errors:
            print(f"🔍 Form errors: {form.errors}")
        
        # Check if this is actually a generation request
        action = request.form.get('action')
        if action != 'generate':
            print(f"🔍 Skipping generation - action is '{action}', not 'generate'")
            return render_template('create_module_answer_key2.html', form=form)
        
        # Only handle document generation - autosave handles saving
        if form.validate_on_submit():
            print("🔍 Module Answer Key 2.0 form validation passed!")
            
            # Load autosaved draft data for generation reliability
            print("🔍 Loading autosaved draft data for generation...")
            latest_draft = FormDraft.query.filter_by(
                user_id=current_user.id, 
                form_type='module_answer_key2'
            ).order_by(FormDraft.updated_at.desc()).first()
            
            if latest_draft and latest_draft.form_data:
                print("🔍 Found draft data - merging with form data for generation")
                # Create a merged form that combines submitted data with autosaved data
                merged_form = ModuleAnswerKey2Form()
                
                # Use basic fields from submitted form (like module_acronym)
                merged_form.module_acronym.data = form.module_acronym.data
                
                # Load all data from the draft to ensure completeness
                draft_loaded = load_module_answer_key2_draft_into_form(merged_form, current_user.id)
                if draft_loaded:
                    print(f"🔍 Successfully loaded draft - using merged form for generation")
                    form = merged_form  # Use the merged form for generation
                else:
                    print("🔍 Failed to load draft - using submitted form")
            else:
                print("🔍 No draft data found - using submitted form")
            
            try:
                print("🔍 Attempting to generate Module Answer Key 2.0...")
                doc_path = generate_module_answer_key2(form)
                filename = os.path.basename(doc_path)
                
                print(f"🔍 Module Answer Key 2.0 generated at: {doc_path}")
                
                # Save document info to database
                doc_record = GeneratedDocument(
                    user_id=current_user.id,
                    document_type='module_answer_key2',
                    filename=filename,
                    file_path=doc_path,
                    module_acronym=form.module_acronym.data,
                    file_size=os.path.getsize(doc_path)
                )
                db.session.add(doc_record)
                db.session.commit()
                
                print(f"🔍 Database record created successfully")
                flash('Module Answer Key 2.0 generated successfully!', 'success')
                return redirect(url_for('my_documents'))
            except Exception as e:
                print(f"🔍 Error generating Module Answer Key 2.0: {e}")
                import traceback
                traceback.print_exc()  # Print full traceback for debugging
                flash(f'Error generating Module Answer Key 2.0: {str(e)}', 'error')
                return render_template('create_module_answer_key2.html', form=form)
        else:
            print(f"🔍 Form validation failed!")
            print(f"🔍 Validation errors: {form.errors}")
    
    return render_template('create_module_answer_key2.html', form=form)

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
            filename = os.path.basename(doc_path)
            
            print(f"Module Activity Sheet generated at: {doc_path}")
            
            # Save document info to database
            doc_record = GeneratedDocument(
                user_id=current_user.id,
                document_type='moduleactivity',
                filename=filename,
                file_path=doc_path,
                module_acronym=form.module_acronym.data,
                file_size=os.path.getsize(doc_path)
            )
            db.session.add(doc_record)
            db.session.commit()
            
            flash('Module Activity Sheet generated successfully!', 'success')
            return redirect(url_for('my_documents'))
        except Exception as e:
            print(f"Error generating Module Activity Sheet: {e}")
            flash(f'Error generating Module Activity Sheet: {str(e)}', 'error')
    
    return render_template('create_moduleActivitySheet.html', form=form)

@app.route('/create-horizontal-lesson-plan', methods=['GET', 'POST'])
@login_required
def create_horizontal_lesson_plan():
    form = HorizontalLessonPlanForm()
    
    if request.method == 'POST':
        print("Horizontal Lesson Plan form submitted!")
        print(f"Form valid: {form.validate_on_submit()}")
        if form.errors:
            print(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        print("Horizontal Lesson Plan form validation passed!")
        
        # Check which action was clicked
        action = request.form.get('action', 'generate')
        print(f"Action clicked: {action}")
        
        if action == 'save_draft':
            # Handle draft saving
            try:
                # Prepare form data for JSON storage
                form_data = {
                    'school_name': form.school_name.data,
                    'teacher_name': form.teacher_name.data,
                    'term': form.term.data,
                    'modules': []
                }
                
                # Process modules
                for module in form.modules:
                    if module.module_name.data or any(session.focus.data or session.objectives.data 
                                                    for session in module.sessions):
                        module_data = {
                            'module_name': module.module_name.data,
                            'enrichment_activities': module.enrichment_activities.data,
                            'sessions': []
                        }
                        
                        # Process sessions
                        for session in module.sessions:
                            session_data = {
                                'focus': session.focus.data,
                                'objectives': session.objectives.data,
                                'materials': session.materials.data,
                                'teacher_prep': session.teacher_prep.data,
                                'assessments': session.assessments.data
                            }
                            module_data['sessions'].append(session_data)
                        
                        form_data['modules'].append(module_data)
                
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
                        return render_template('create_horizontal_lesson_plan.html', form=form)
                else:
                    # Create new draft
                    title = f"Horizontal Lesson Plan - {form.school_name.data}" if form.school_name.data else "Horizontal Lesson Plan - Untitled"
                    draft = FormDraft(
                        user_id=current_user.id,
                        form_type='horizontal_lesson_plan',
                        title=title,
                        form_data=form_data
                    )
                    db.session.add(draft)
                
                db.session.commit()
                flash('Draft saved successfully!', 'success')
                return render_template('create_horizontal_lesson_plan.html', form=form, draft_id=draft.id)
                
            except Exception as e:
                print(f"Error saving draft: {e}")
                flash(f'Error saving draft: {str(e)}', 'error')
                return render_template('create_horizontal_lesson_plan.html', form=form)
        
        elif action == 'extract':
            # Extract data from uploaded PDFs
            try:
                print("Extracting data from PDFs...")
                extracted_count = 0
                
                for i, module in enumerate(form.modules):
                    if module.session_notes_pdf.data and module.session_notes_pdf.data.filename:
                        print(f"Processing PDF for module {i+1}...")
                        try:
                            # Extract text from PDF
                            pdf_text = extract_pdf_text(module.session_notes_pdf.data)
                            print(f"Extracted text length: {len(pdf_text)}")
                            
                            # Parse session data using improved extraction
                            extracted_data = extract_session_data_from_text(pdf_text)
                            
                            print(f"DEBUG: Extracted data for module {i+1}:")
                            print(f"  Module name: {extracted_data.get('module_name', 'None')}")
                            print(f"  Enrichment: {extracted_data.get('enrichment', 'None')}")
                            print(f"  Sessions found: {len(extracted_data.get('sessions', []))}")
                            
                            # Populate form fields with extracted data
                            if extracted_data.get('module_name'):
                                module.module_name.data = extracted_data['module_name']
                                print(f"  Set module name: {extracted_data['module_name']}")
                            
                            if extracted_data.get('enrichment'):
                                module.enrichment_activities.data = extracted_data['enrichment']
                                print(f"  Set enrichment: {extracted_data['enrichment'][:50]}...")
                            
                            # Populate session data
                            sessions_data = extracted_data.get('sessions', [])
                            for j, session_data in enumerate(sessions_data[:7]):  # Max 7 sessions
                                if j < len(module.sessions):
                                    print(f"    Session {j+1}: focus='{session_data.get('focus', '')[:30]}...', objectives='{session_data.get('objectives', '')[:30]}...'")
                                    module.sessions[j].focus.data = session_data.get('focus', '')
                                    module.sessions[j].objectives.data = session_data.get('objectives', '')
                                    module.sessions[j].materials.data = session_data.get('materials', '')
                                    module.sessions[j].teacher_prep.data = session_data.get('teacher_prep', '')
                                    module.sessions[j].assessments.data = session_data.get('assessments', '')
                            
                            extracted_count += 1
                            
                        except Exception as e:
                            print(f"Error processing PDF for module {i+1}: {e}")
                            flash(f'Error processing PDF for module {i+1}: {str(e)}', 'warning')
                
                if extracted_count > 0:
                    flash(f'Data extracted from {extracted_count} PDF(s) successfully! Review and edit the data below.', 'success')
                else:
                    flash('No valid PDFs found to extract data from.', 'warning')
                
            except Exception as e:
                print(f"Error during extraction: {e}")
                flash(f'Error extracting data: {str(e)}', 'error')
                
            # Return to form with populated data
            return render_template('create_horizontal_lesson_plan.html', form=form)
            
        else:  # action == 'generate' or default
            # Generate the document
            try:
                print("Attempting to generate Horizontal Lesson Plan...")
                doc_path, filename = generate_horizontal_lesson_plan(form)
                
                print(f"Horizontal Lesson Plan generated at: {doc_path}")
                
                # Save document info to database
                doc_record = GeneratedDocument(
                    user_id=current_user.id,
                    document_type='horizontal_lesson_plan',
                    filename=filename,
                    file_path=doc_path,
                    module_acronym=None,  # This form doesn't have a single module acronym
                    file_size=os.path.getsize(doc_path)
                )
                db.session.add(doc_record)
                db.session.commit()
                
                flash('Horizontal Lesson Plan generated successfully!', 'success')
                return redirect(url_for('my_documents'))
            except Exception as e:
                print(f"Error generating Horizontal Lesson Plan: {e}")
                flash(f'Error generating Horizontal Lesson Plan: {str(e)}', 'error')
    
    return render_template('create_horizontal_lesson_plan.html', form=form)

@app.route('/load-moduleactivity-draft/<int:draft_id>')
@login_required
def load_moduleactivity_draft(draft_id):
    """Load module activity sheet draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='moduleactivity').first()
    
    if not draft:
        flash('Draft not found', 'error')
        return redirect(url_for('create_module_activity_sheet'))
    
    try:
        # Create form and populate with draft data
        form = ModuleActivitySheetForm()
        form_data = draft.form_data
        
        # Populate form fields
        form.module_acronym.data = form_data.get('module_acronym', '')
        
        # Populate session data
        sessions_data = form_data.get('sessions', [])
        session_dict = {session['session_number']: session for session in sessions_data}
        
        for i in range(1, 8):
            if i in session_dict:
                session_data = session_dict[i]
                getattr(form, f'session{i}_activity').data = session_data.get('activity', '')
                getattr(form, f'session{i}_is_pba').data = session_data.get('is_pba', False)
        
        flash(f'Draft "{draft.title}" loaded successfully!', 'success')
        return render_template('create_moduleActivitySheet.html', form=form, draft_id=draft.id)
        
    except Exception as e:
        print(f"Error loading module activity draft: {e}")
        flash(f'Error loading draft: {str(e)}', 'error')
        return redirect(url_for('create_module_activity_sheet'))

@app.route('/delete-moduleactivity-draft/<int:draft_id>', methods=['POST'])
@login_required
def delete_moduleactivity_draft(draft_id):
    """Delete module activity sheet draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='moduleactivity').first()
    
    if not draft:
        flash('Draft not found', 'error')
    else:
        db.session.delete(draft)
        db.session.commit()
        flash('Draft deleted successfully!', 'success')
    
    return redirect(url_for('drafts'))

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
    
    try:
        # Load the temporary template
        doc = DocxTemplate(temp_template_path)
        
        # Create a subdocument to hold all dynamic content
        subdoc = doc.new_subdoc()
        
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
            
            elif field_type == 'table':
                # Extract table configuration
                table_title = (field_data.get('table_title') or '').strip()
                table_rows = int(field_data.get('table_rows', 3))
                table_cols = int(field_data.get('table_cols', 3))
                
                # Add table title if provided
                if table_title:
                    p = subdoc.add_paragraph(table_title)
                    for run in p.runs:
                        run.font.name = 'Segoe UI'
                        run.font.size = Pt(12)
                        run.font.bold = True
                    p.paragraph_format.space_after = Pt(6)
                
                # Create the table
                table = subdoc.add_table(rows=table_rows, cols=table_cols)
                table.style = 'Table Grid'  # Use built-in table style with borders
                
                # Populate table cells with data
                for row_idx in range(table_rows):
                    for col_idx in range(table_cols):
                        cell_key = f'table_cell_{row_idx}_{col_idx}'
                        cell_value = (field_data.get(cell_key) or '').strip()
                        
                        cell = table.cell(row_idx, col_idx)
                        cell.text = cell_value
                        
                        # Format cell content
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                run.font.name = 'Segoe UI'
                                run.font.size = Pt(11)
                                # Make header row bold
                                if row_idx == 0:
                                    run.font.bold = True
                
                # Add spacing after table
                subdoc.add_paragraph().paragraph_format.space_after = Pt(12)
            
            # Note: Image field type removed from frontend
            
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
            'learningobjective5': escape_xml(form.learningobjective5.data) if form.learningobjective5.data else '',
            'learningobjective6': escape_xml(form.learningobjective6.data) if form.learningobjective6.data else '',
            
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
    master_template_path = 'templates/docx_templates/module_ak_master.docx'
    working_template_path = 'templates/docx_templates/module_ak.docx'
    
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
            
            # Handle both form data structure (when coming from form submission)
            # and autosave data structure (when coming from draft loading)
            questions = []
            
            if 'questions' in session_data and isinstance(session_data['questions'], list):
                # Autosave/draft structure: questions as array
                questions = session_data['questions']
                print(f"🔍 RCA Session {i+1}: Using autosave structure with {len(questions)} questions")
            else:
                # Form submission structure: individual question objects
                questions = session_data.get('questions', [])
                print(f"🔍 RCA Session {i+1}: Using form structure with {len(questions)} questions")
            
            # Add research question (first question)
            if len(questions) > 0 and questions[0].get('question_text'):
                session_obj['research_question'] = {
                    'text': escape_xml(questions[0]['question_text']),
                    'choice': [
                        escape_xml(questions[0].get('choice_a', '')),
                        escape_xml(questions[0].get('choice_b', '')),
                        escape_xml(questions[0].get('choice_c', '')),
                        escape_xml(questions[0].get('choice_d', ''))
                    ],
                    'correct_answer': questions[0].get('correct_answer', '').upper()
                }
                print(f"🔍   Research question: {questions[0]['question_text'][:50]}...")
            
            # Add challenge question (second question)
            if len(questions) > 1 and questions[1].get('question_text'):
                session_obj['challenge_question'] = {
                    'text': escape_xml(questions[1]['question_text']),
                    'choice': [
                        escape_xml(questions[1].get('choice_a', '')),
                        escape_xml(questions[1].get('choice_b', '')),
                        escape_xml(questions[1].get('choice_c', '')),
                        escape_xml(questions[1].get('choice_d', ''))
                    ],
                    'correct_answer': questions[1].get('correct_answer', '').upper()
                }
                print(f"🔍   Challenge question: {questions[1]['question_text'][:50]}...")
            
            # Add application question (third question)
            if len(questions) > 2 and questions[2].get('question_text'):
                session_obj['application_question'] = {
                    'text': escape_xml(questions[2]['question_text']),
                    'choice': [
                        escape_xml(questions[2].get('choice_a', '')),
                        escape_xml(questions[2].get('choice_b', '')),
                        escape_xml(questions[2].get('choice_c', '')),
                        escape_xml(questions[2].get('choice_d', ''))
                    ],
                    'correct_answer': questions[2].get('correct_answer', '').upper()
                }
                print(f"🔍   Application question: {questions[2]['question_text'][:50]}...")
            
            # Only add sessions that have at least one question
            if any(key in session_obj for key in ['research_question', 'challenge_question', 'application_question']):
                rca_sessions_data.append(session_obj)
                print(f"🔍 Added RCA Session {i+1} with {len([k for k in ['research_question', 'challenge_question', 'application_question'] if k in session_obj])} questions")
        
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
        
        # 5. Enrichment Activities & Worksheet Answer Keys - REMOVED FOR SIMPLIFICATION
        # These complex sections have been moved to separate "Academic Worksheet Builder" template
        
        # Create empty subdocuments for template compatibility
        enrichment_subdoc = doc.new_subdoc()
        worksheet_keys_subdoc = doc.new_subdoc()
        
        # Skip complex enrichment and worksheet processing - moved to separate template

        # Build the complete context (simplified - no enrichment or worksheet sections)
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
        
        # Render the document
        print("Rendering Module Answer Key document...")
        doc.render(context)
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"Module Answer Key {escape_xml(form.module_acronym.data).replace(' ', '_')}.docx"
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


def generate_module_answer_key2(form):
    """Generate a Module Answer Key 2.0 using docxtpl - streamlined version without complex sections"""
    # Use the dedicated Module Answer Key 2.0 template (same Jinja syntax, no enrichment/worksheet sections)
    master_template_path = 'templates/docx_templates/module_answer_key2_master.docx'
    working_template_path = 'templates/docx_templates/module_answer_key2.docx'
    
    print(f"🔍 Looking for Module Answer Key 2.0 master template at: {master_template_path}")
    
    # Check if master template exists
    if not os.path.exists(master_template_path):
        raise FileNotFoundError("Module Answer Key 2.0 master DOCX template not found. Please create the master template first.")
    
    # PROTECTION: Verify master template integrity before proceeding
    master_stat = os.stat(master_template_path)
    print(f"🔍 Master template size: {master_stat.st_size} bytes, modified: {datetime.fromtimestamp(master_stat.st_mtime)}")
    
    # Always copy from master to working template before processing
    print("🔍 Copying fresh Module Answer Key 2.0 template from master...")
    try:
        shutil.copy2(master_template_path, working_template_path)
        print(f"✓ Successfully copied master to working template")
    except Exception as e:
        raise Exception(f"Failed to copy master template: {e}")
    
    print("🔍 Loading Module Answer Key 2.0 working template...")
    
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
        print(f"🔍 Loading DocxTemplate from temporary file: {temp_template_path}")
        doc = DocxTemplate(temp_template_path)
        
        # Prepare context data matching the template structure (simplified version)
        
        # 1. Pre-test questions - Fixed to match template expectation of {{ question.question }}
        pretest_questions_data = []
        for question_data in form.pretest_questions.data:
            if question_data.get('question_text'):
                pretest_questions_data.append({
                    'question': escape_xml(question_data['question_text']),  # Template uses {{ question.question }}
                    'choice': [
                        escape_xml(question_data.get('choice_a', '')),
                        escape_xml(question_data.get('choice_b', '')),
                        escape_xml(question_data.get('choice_c', '')),
                        escape_xml(question_data.get('choice_d', ''))
                    ],
                    'correct_answer': question_data.get('correct_answer', '').upper()
                })
        
        # 2. RCA sessions (sessions 2-5, each with 3 questions)
        rca_sessions_data = []
        for i, session_data in enumerate(form.rca_sessions.data):
            session_obj = {
                'session_number': i + 2,  # Sessions 2-5
            }
            
            # Handle both form data structure and autosave data structure
            questions = []
            
            if 'questions' in session_data and isinstance(session_data['questions'], list):
                # Autosave/draft structure: questions as array
                questions = session_data['questions']
                print(f"🔍 RCA Session {i+1}: Using autosave structure with {len(questions)} questions")
            else:
                # Form submission structure: individual question objects
                questions = session_data.get('questions', [])
                print(f"🔍 RCA Session {i+1}: Using form structure with {len(questions)} questions")
            
            # Add research question (first question)
            if len(questions) > 0 and questions[0].get('question_text'):
                session_obj['research_question'] = {
                    'text': escape_xml(questions[0]['question_text']),
                    'choice': [
                        escape_xml(questions[0].get('choice_a', '')),
                        escape_xml(questions[0].get('choice_b', '')),
                        escape_xml(questions[0].get('choice_c', '')),
                        escape_xml(questions[0].get('choice_d', ''))
                    ],
                    'correct_answer': questions[0].get('correct_answer', '').upper()
                }
                print(f"🔍   Research question: {questions[0]['question_text'][:50]}...")
            
            # Add challenge question (second question)
            if len(questions) > 1 and questions[1].get('question_text'):
                session_obj['challenge_question'] = {
                    'text': escape_xml(questions[1]['question_text']),
                    'choice': [
                        escape_xml(questions[1].get('choice_a', '')),
                        escape_xml(questions[1].get('choice_b', '')),
                        escape_xml(questions[1].get('choice_c', '')),
                        escape_xml(questions[1].get('choice_d', ''))
                    ],
                    'correct_answer': questions[1].get('correct_answer', '').upper()
                }
                print(f"🔍   Challenge question: {questions[1]['question_text'][:50]}...")
            
            # Add application question (third question)
            if len(questions) > 2 and questions[2].get('question_text'):
                session_obj['application_question'] = {
                    'text': escape_xml(questions[2]['question_text']),
                    'choice': [
                        escape_xml(questions[2].get('choice_a', '')),
                        escape_xml(questions[2].get('choice_b', '')),
                        escape_xml(questions[2].get('choice_c', '')),
                        escape_xml(questions[2].get('choice_d', ''))
                    ],
                    'correct_answer': questions[2].get('correct_answer', '').upper()
                }
                print(f"🔍   Application question: {questions[2]['question_text'][:50]}...")
            
            # Only add sessions that have at least one question
            if any(key in session_obj for key in ['research_question', 'challenge_question', 'application_question']):
                rca_sessions_data.append(session_obj)
                print(f"🔍 Added RCA Session {i+1} with {len([k for k in ['research_question', 'challenge_question', 'application_question'] if k in session_obj])} questions")
        
        # 3. Post-test questions - Fixed to match template expectation of {{ question.question }}
        posttest_questions_data = []
        for question_data in form.posttest_questions.data:
            if question_data.get('question_text'):
                posttest_questions_data.append({
                    'question': escape_xml(question_data['question_text']),  # Template uses {{ question.question }}
                    'choice': [
                        escape_xml(question_data.get('choice_a', '')),
                        escape_xml(question_data.get('choice_b', '')),
                        escape_xml(question_data.get('choice_c', '')),
                        escape_xml(question_data.get('choice_d', ''))
                    ],
                    'correct_answer': question_data.get('correct_answer', '').upper()
                })
        
        # 4. Performance Based Assessments (3 sessions, numbered 1-3)
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
        
        # 5. Vocabulary
        vocabulary_data = []
        for term_data in form.vocabulary.data:
            if term_data.get('term'):
                vocabulary_data.append({
                    'term': escape_xml(term_data['term']),
                    'definition': escape_xml(term_data.get('definition', ''))
                })
        
        # 6. Student Portfolio Checklist
        portfolio_checklist_data = []
        for item_data in form.portfolio_checklist.data:
            if item_data.get('product'):
                portfolio_checklist_data.append({
                    'product': escape_xml(item_data['product']),
                    'session_number': escape_xml(item_data.get('session_number', ''))
                })
        
        # Build the complete context (simplified - no enrichment or worksheet sections)
        context = {
            'module_acronym': escape_xml(form.module_acronym.data),
            'pretest_questions': pretest_questions_data,
            'rca_sessions': rca_sessions_data,
            'posttest_questions': posttest_questions_data,
            'pba_sessions': pba_sessions_data,
            'vocabulary': vocabulary_data,
            'portfolio_checklist': portfolio_checklist_data
        }
        
        print(f"🔍 Module Answer Key 2.0 context data prepared")
        print(f"🔍 Number of pre-test questions: {len(pretest_questions_data)}")
        print(f"🔍 Number of RCA sessions: {len(rca_sessions_data)}")
        print(f"🔍 Number of post-test questions: {len(posttest_questions_data)}")
        print(f"🔍 Number of PBA sessions: {len(pba_sessions_data)}")
        print(f"🔍 Number of vocabulary terms: {len(vocabulary_data)}")
        print(f"🔍 Number of portfolio checklist items: {len(portfolio_checklist_data)}")
        
        # Debug: Print first few items to verify structure
        if vocabulary_data:
            print(f"🔍 First vocabulary item: {vocabulary_data[0]}")
        if portfolio_checklist_data:
            print(f"🔍 First portfolio item: {portfolio_checklist_data[0]}")
        
        # Render the document
        print("🔍 Rendering Module Answer Key 2.0 document...")
        try:
            doc.render(context)
        except Exception as template_error:
            print(f"🚨 Template rendering error: {str(template_error)}")
            print(f"🔍 This suggests a Jinja2 syntax error in the DOCX template file")
            print("🔍 Check the module_answer_key2_master.docx file for missing {% endfor %} tags")
            raise Exception("DOCX template syntax error: " + str(template_error) + ". Please check the module_answer_key2_master.docx template for missing {% endfor %} tags in loops.")
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"Module Answer Key 2.0 {escape_xml(form.module_acronym.data).replace(' ', '_')}_v2.0.docx"
        output_path = os.path.join(output_dir, filename)
        
        print(f"🔍 Saving Module Answer Key 2.0 document to: {output_path}")
        doc.save(output_path)
        
        print("✅ Module Answer Key 2.0 document saved successfully!")
        
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

def extract_pdf_text(pdf_file):
    """Extract text from uploaded PDF file"""
    try:
        # Reset file pointer to beginning
        pdf_file.seek(0)
        
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from all pages
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return None

def extract_session_data_from_text(text):
    """Extract session data from the Session Notes PDF with improved accuracy"""
    extracted_data = {
        'module_name': '',
        'enrichment': '',
        'sessions': []
    }
    
    try:
        # Clean up the text while preserving line breaks for structure
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s*\n\s*', '\n', text)  # Clean up line breaks
        
        # Extract module name - try multiple strategies
        module_name = extract_module_name_advanced(text)
        if module_name:
            extracted_data['module_name'] = module_name
        
        # Split text by sessions using the exact pattern "Session [number]-"
        session_splits = re.split(r'Session\s*(\d+)\s*-', text, flags=re.IGNORECASE)
        
        # Process each session (skip index 0 which is content before first session)
        for i in range(1, len(session_splits), 2):
            if i + 1 < len(session_splits):
                session_num = int(session_splits[i])
                if session_num <= 7:  # Only process sessions 1-7
                    session_content = session_splits[i + 1]
                    
                    # Stop at the next session or enrichments section, but be more careful about boundaries
                    # Look for the start of the next session, but make sure it's actually a session header
                    next_session_match = re.search(r'(?:\n|^)\s*Session\s*\d+\s*-', session_content, re.IGNORECASE)
                    enrichment_match = re.search(r'(?:\n|^)\s*Enrichment', session_content, re.IGNORECASE)
                    
                    if next_session_match:
                        session_content = session_content[:next_session_match.start()]
                    elif enrichment_match:
                        session_content = session_content[:enrichment_match.start()]
                    
                    # Debug output for session content
                    print(f"DEBUG: Processing Session {session_num}, content length: {len(session_content)}")
                    if 'Performance' in session_content:
                        perf_index = session_content.lower().find('performance')
                        print(f"DEBUG: 'Performance' found at position {perf_index} in session content")
                        print(f"DEBUG: Text around Performance: '{session_content[max(0, perf_index-50):perf_index+150]}'")
                    else:
                        print(f"DEBUG: 'Performance' NOT found in session content")
                    
                    session_data = extract_session_fields_improved(session_content)
                    extracted_data['sessions'].append(session_data)
        
        # Extract enrichment activities (everything after "Enrichments")
        enrichment_match = re.search(r'Enrichments?\s*(.*?)(?=\Z)', text, re.IGNORECASE | re.DOTALL)
        if enrichment_match:
            enrichment_text = enrichment_match.group(1).strip()
            # Clean up the enrichment text
            enrichment_text = re.sub(r'^\d+\.?\s*', '', enrichment_text, flags=re.MULTILINE)  # Remove numbering
            extracted_data['enrichment'] = clean_text(enrichment_text)
    
    except Exception as e:
        print(f"Error extracting session data: {e}")
    
    return extracted_data

def extract_module_name_advanced(text):
    """Advanced module name extraction using multiple strategies"""
    
    # Strategy 1: Look for text immediately after "Session Notes" 
    match = re.search(r'Session\s+Notes\s+([^\n\r]+)', text, re.IGNORECASE)
    if match:
        potential_name = match.group(1).strip()
        potential_name = remove_header_artifacts(potential_name)
        if potential_name and len(potential_name) > 3 and len(potential_name) < 50:
            return potential_name
    
    # Strategy 2: Look for text before "Session Notes"
    match = re.search(r'([^\n\r]+)\s+Session\s+Notes', text, re.IGNORECASE)
    if match:
        potential_name = match.group(1).strip()
        potential_name = remove_header_artifacts(potential_name)
        if potential_name and len(potential_name) > 3 and len(potential_name) < 50:
            return potential_name
    
    # Strategy 3: Look at the very beginning, skip common artifacts
    lines = text.split('\n')[:15]  # Check first 15 lines
    
    for line in lines:
        line = line.strip()
        # Skip obvious artifacts but look for substantial content
        if (line and 
            not re.search(r'Session\s+Notes', line, re.IGNORECASE) and
            not re.search(r'star\s*ACADEMY', line, re.IGNORECASE) and
            not re.search(r'NOLA\s+EDUCATION', line, re.IGNORECASE) and
            not re.search(r'www\.', line, re.IGNORECASE) and
            not re.search(r'Session\s+\d+', line, re.IGNORECASE) and
            not re.search(r'Focus:', line, re.IGNORECASE) and
            not re.search(r'Objectives:', line, re.IGNORECASE) and
            len(line) > 3 and len(line) < 50):
            
            # Clean up the line
            clean_line = remove_header_artifacts(line)
            clean_line = re.sub(r'[^\w\s&\'-]', '', clean_line).strip()
            
            # Check if it looks like a valid module name
            if (clean_line and 
                len(clean_line) > 3 and 
                not clean_line.lower() in ['session', 'notes', 'page', 'may', 'be', 'photocopied']):
                return clean_line
    
    # Strategy 4: Look for common module name patterns in the text
    common_patterns = [
        r'\b(Organism\s+Reproduction)\b',
        r'\b(Animals?)\b(?!\s+having)',  # "Animals" but not "animals having"
        r'\b(Plants?)\b(?!\s+reproduce)',
        r'\b(Chemistry)\b',
        r'\b(Physics)\b',
        r'\b(Biology)\b',
        r'\b(Environmental?\s+Science)\b',
        r'\b(Earth\s+Science)\b',
        r'\b(Sports?\s+Statistics)\b',
    ]
    
    for pattern in common_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def extract_session_fields_improved(session_text):
    """Extract individual fields from a session text block with improved accuracy"""
    session_data = {
        'focus': '',
        'objectives': '',
        'materials': '',
        'teacher_prep': '',
        'assessments': ''
    }
    
    # More precise patterns based on the actual document structure
    field_patterns = {
        'focus': [
            r'Focus:\s*(.*?)(?=\s*Objectives:)',
            r'Focus:\s*(.*?)(?=\s*(?:Objectives|Materials|Teacher|Performance))',
        ],
        'objectives': [
            r'Objectives:\s*(.*?)(?=\s*Materials:)',
            r'Objectives:\s*(.*?)(?=\s*(?:Materials|Teacher|Performance))',
        ],
        'materials': [
            r'Materials:\s*(.*?)(?=\s*Teacher\s*Preparations?:)',
            r'Materials:\s*(.*?)(?=\s*(?:Teacher|Performance))',
        ],
        'teacher_prep': [
            r'Teacher\s*Preparations?:\s*(.*?)(?=\s*Performance\s*(?:Based\s*)?(?:Assessment\s*)?Questions?:)',
            r'Teacher\s*Preparations?:\s*(.*?)(?=\s*(?:Performance|Assessment))',
        ],
        'assessments': [
            r'Performance\s*Assessment\s*Questions?\s*:?\s*(.*?)(?=\s*(?:Session\s*\d+|Enrichments?|$))',
            r'Performance\s*Based\s*Assessment\s*Questions?\s*:?\s*(.*?)(?=\s*(?:Session\s*\d+|Enrichments?|$))',
            r'Performance\s*(?:Based\s*)?(?:Assessment\s*)?Questions?\s*:?\s*(.*?)(?=\s*(?:Session\s*\d+|Enrichments?|$))',
            r'Assessment\s*Questions?\s*:?\s*(.*?)(?=\s*(?:Session\s*\d+|Enrichments?|$))',
            r'PBA\s*:?\s*(.*?)(?=\s*(?:Session\s*\d+|Enrichments?|$))',
        ]
    }
    
    # Extract each field using the patterns
    for field, patterns in field_patterns.items():
        extracted = False
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, session_text, re.IGNORECASE | re.DOTALL)
            if match:
                extracted_text = match.group(1).strip()
                
                # Debug output for assessments
                if field == 'assessments':
                    print(f"DEBUG: Assessments found with pattern {i+1}: '{extracted_text[:100]}...'")
                
                # Clean up the extracted text based on field type
                if field == 'focus':
                    session_data[field] = clean_focus_text(extracted_text)
                elif field == 'objectives':
                    session_data[field] = clean_objectives_text(extracted_text)
                elif field == 'teacher_prep':
                    session_data[field] = clean_teacher_prep_text(extracted_text)
                elif field == 'assessments':
                    session_data[field] = clean_assessment_text(extracted_text)
                else:
                    session_data[field] = clean_text(extracted_text)
                extracted = True
                break
        
        # Debug output for failed extractions
        if not extracted and field == 'assessments':
            print(f"DEBUG: No assessments found. Session text sample: '{session_text[:200]}...'")
        
        # If no data was extracted for teacher_prep or assessments, set to N/A
        if not extracted:
            if field in ['teacher_prep', 'assessments']:
                session_data[field] = 'N/A'
    
    return session_data

def clean_focus_text(text):
    """Clean session focus text with proper title case"""
    if not text:
        return ''
    
    # Remove header/footer artifacts first
    text = remove_header_artifacts(text)
    
    # Basic cleanup
    text = clean_text(text)
    
    # Apply title case while preserving acronyms and special terms
    words = text.split()
    title_words = []
    
    for word in words:
        # Keep short words like &, and, or lowercase unless at start
        if word.lower() in ['&', 'and', 'or', 'the', 'of', 'in', 'on', 'at', 'to', 'for', 'with'] and title_words:
            title_words.append(word.lower())
        else:
            # Capitalize first letter of each word
            title_words.append(word.capitalize())
    
    return ' '.join(title_words)

def remove_header_artifacts(text):
    """Remove common header/footer artifacts from PDF text"""
    if not text:
        return text
    
    # List of common header/footer patterns to remove
    artifacts = [
        r'Nola\s+Education,?\s*Llc',
        r'www\.staracademyprogram\.com',
        r'This\s+Page\s+May\s+Be\s+Photocopied\s+for\s+Use\s+Only\s+Within\s+the',
        r'star\s*ACADEMY',
        r'Session\s+Notes\s+Animals',
        r'NOLA\s+EDUCATION,?\s*LLC',
        r'⎢.*?\.com',
        r'www\..*?\.com',
        r'This\s+page\s+may\s+be\s+photocopied.*?Star\s+Academy',
    ]
    
    # Remove each artifact pattern
    for pattern in artifacts:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def clean_objectives_text(text):
    """Clean objectives text and ensure proper punctuation"""
    if not text:
        return ''
    
    # Handle "N/A" case
    if re.match(r'^\s*n/?a\s*$', text, re.IGNORECASE):
        return 'N/A'
    
    # Remove header artifacts first
    text = remove_header_artifacts(text)
    
    # Basic cleanup
    text = clean_text(text)
    
    # Split into sentences (by common patterns)
    sentences = re.split(r'(?<=[.!?])\s+|(?<=[a-z])\s+(?=[A-Z])', text)
    
    cleaned_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:
            # Ensure sentence ends with a period if it doesn't have punctuation
            if not re.search(r'[.!?]$', sentence):
                sentence += '.'
            cleaned_sentences.append(sentence)
    
    return ' '.join(cleaned_sentences)

def clean_teacher_prep_text(text):
    """Clean teacher preparation text and ensure proper punctuation"""
    if not text:
        return 'N/A'
    
    # Handle "N/A" case
    if re.match(r'^\s*n/?a\s*$', text, re.IGNORECASE):
        return 'N/A'
    
    # Basic cleanup
    text = clean_text(text)
    
    # Ensure it ends with a period if it doesn't have punctuation
    if text and not re.search(r'[.!?]$', text):
        text += '.'
    
    return text if text else 'N/A'

def clean_assessment_text(text):
    """Clean assessment text while preserving list structure"""
    if not text:
        return 'N/A'
    
    # Handle "N/A" case
    if re.match(r'^\s*n/?a\s*$', text, re.IGNORECASE):
        return 'N/A'
    
    # Remove any "Enrichments" text that might have leaked in
    text = re.sub(r'\s*Enrichments?\.?\s*.*$', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Clean up but preserve numbered lists
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Fix common PDF extraction issues
    text = fix_pdf_text_issues(text)
    
    # If it contains numbered items, format them nicely and add punctuation
    if re.search(r'\d+\.', text):
        # Split by numbers and rejoin with proper formatting
        parts = re.split(r'(\d+\.)', text)
        formatted_parts = []
        for i, part in enumerate(parts):
            if re.match(r'\d+\.', part):
                formatted_parts.append(f"\n{part}")
            elif part.strip():
                sentence = part.strip()
                
                # Fix spacing before punctuation
                sentence = re.sub(r'\s+([.!?])', r'\1', sentence)
                
                # Add period if missing
                if not re.search(r'[.!?]$', sentence):
                    sentence += '.'
                formatted_parts.append(f" {sentence}")
        text = ''.join(formatted_parts).strip()
    else:
        # Single sentence - fix spacing and add period if missing
        text = re.sub(r'\s+([.!?])', r'\1', text)
        if not re.search(r'[.!?]$', text):
            text += '.'
    
    return text if text else 'N/A'

def fix_pdf_text_issues(text):
    """Fix common PDF text extraction issues"""
    if not text:
        return text
    
    # Fix broken words (common PDF extraction issues)
    text = re.sub(r'cephalizatio\s*n', 'cephalization', text, flags=re.IGNORECASE)
    text = re.sub(r'segmentatio\s*n', 'segmentation', text, flags=re.IGNORECASE)
    text = re.sub(r'classificatio\s*n', 'classification', text, flags=re.IGNORECASE)
    text = re.sub(r'organizatio\s*n', 'organization', text, flags=re.IGNORECASE)
    text = re.sub(r'observatio\s*n', 'observation', text, flags=re.IGNORECASE)
    
    # Fix spacing issues around punctuation
    text = re.sub(r'\s+([.!?,:;])', r'\1', text)
    
    return text

def clean_text(text):
    """Clean and normalize extracted text"""
    if not text:
        return ''
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove common PDF artifacts
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    return text

def generate_horizontal_lesson_plan(form):
    """Generate a horizontal lesson plan using docxtpl"""
    # Use the horizontal lesson plan master template
    master_template_path = 'templates/docx_templates/horizontal_lesson_plan_master.docx'
    
    print(f"Looking for horizontal lesson plan master template at: {master_template_path}")
    
    # Check if master template exists
    if not os.path.exists(master_template_path):
        raise FileNotFoundError("Horizontal Lesson Plan master DOCX template not found. Please create the master template first.")
    
    # Create a temporary copy of the master template
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        shutil.copy2(master_template_path, temp_file.name)
        temp_template_path = temp_file.name
    
    try:
        # Load the temporary template
        doc = DocxTemplate(temp_template_path)
        
        # Initialize the context with basic fields matching your template exactly
        context = {
            'school': {
                'name': escape_xml(form.school_name.data)
            },
            'teacher': {
                'name': escape_xml(form.teacher_name.data)
            },
            'term': escape_xml(form.term.data)
        }
        
        # Process each module using your template's flat naming convention
        for i, module in enumerate(form.modules):
            module_num = i + 1  # m1, m2, m3, m4, m5
            
            if module.module_name.data or any(session.focus.data or session.objectives.data 
                                           for session in module.sessions):
                
                # Add module name: {{ m1.name }}, {{ m2.name }}, etc.
                context[f'm{module_num}'] = {
                    'name': escape_xml(module.module_name.data or f"Module {module_num}"),
                    'enrichment': escape_xml(module.enrichment_activities.data or '')
                }
                
                # Process sessions for this module: {{ m1.s1.focus }}, {{ m1.s2.focus }}, etc.
                for j, session in enumerate(module.sessions):
                    session_num = j + 1  # s1, s2, s3, s4, s5, s6, s7
                    
                    # Create session data with your template's field names
                    session_data = {
                        'focus': escape_xml(session.focus.data or ''),
                        'objectives': escape_xml(session.objectives.data or ''),
                        'materials': escape_xml(session.materials.data or ''),
                        'prep': escape_xml(session.teacher_prep.data or ''),  # 'prep' not 'teacher_prep'
                        'pba': escape_xml(session.assessments.data or '')    # 'pba' not 'assessments'
                    }
                    
                    # Add session to module: context['m1']['s1'] = session_data
                    context[f'm{module_num}'][f's{session_num}'] = session_data
        
        print(f"Horizontal Lesson Plan context prepared")
        # Count modules with data by checking for m1, m2, m3, m4, m5 keys
        module_count = sum(1 for key in context.keys() if key.startswith('m') and key[1:].isdigit())
        print(f"Number of modules with data: {module_count}")
        
        # Render the document
        print("Rendering horizontal lesson plan document...")
        doc.render(context)
        
        # Save to output directory
        output_dir = 'generated_docs'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"Horizontal Lesson Plan {escape_xml(form.school_name.data).replace(' ', '_')} {escape_xml(form.teacher_name.data).replace(' ', '_')}_v2.0.docx"
        output_path = os.path.join(output_dir, filename)
        
        print(f"Saving horizontal lesson plan document to: {output_path}")
        doc.save(output_path)
        
        print("Horizontal lesson plan document saved successfully!")
        return output_path, filename
        
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_template_path)
        except:
            pass  # Ignore cleanup errors

@app.route('/debug/db-status')
def debug_db_status():
    """Debug route to check database status - DEVELOPMENT ONLY"""
    # SECURITY: Only allow in development
    if app.config.get('IS_PRODUCTION', False):
        return "Debug routes disabled in production", 403
    
    try:
        # Don't call db.create_all() - just check existing tables
        total_users = User.query.count()
        admin_count = User.query.filter_by(is_admin=True).count()
        
        # Test database connection without modifications
        test_query = db.session.execute(db.text('SELECT 1')).scalar()
        
        return f"""
        <h1>Database Status - OK</h1>
        <ul>
        <li>Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')[:50]}...</li>
        <li>Total users: {total_users}</li>
        <li>Admin users: {admin_count}</li>
        <li>Database connection: {test_query}</li>
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

@app.route('/migrate-db')
def migrate_db():
    """Safely migrate database - DEVELOPMENT ONLY"""
    # SECURITY: Only allow in development
    if app.config.get('IS_PRODUCTION', False):
        return "Debug routes disabled in production", 403
    
    try:
        # Only create missing tables (safe operation) - don't drop existing ones
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
        <p><a href="/debug/db-status">Check Database Status</a></p>
        """

@app.route('/create-admin-simple', methods=['GET', 'POST'])
def create_admin_simple():
    """Simple admin creation with better error handling - DEVELOPMENT ONLY"""
    # SECURITY: Only allow in development or when no admin exists
    if app.config.get('IS_PRODUCTION', False):
        # In production, only allow if no admin exists
        existing_admin = User.query.filter_by(is_admin=True).first()
        if existing_admin:
            return "Admin creation disabled - admin already exists", 403
    
    try:
        # Don't call db.create_all() - use migrations instead
        # Tables should already exist via flask db upgrade
        
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
    
    return redirect(url_for('drafts'))

@app.route('/download/<int:doc_id>')
@login_required
def download_document(doc_id):
    """Download a generated document with improved error handling"""
    try:
        document = GeneratedDocument.query.filter_by(id=doc_id, user_id=current_user.id).first()
        
        if not document:
            print(f"⚠️  Download attempt for non-existent document ID: {doc_id} by user: {current_user.id}")
            flash('Document not found. It may have been removed or you may not have permission to access it.', 'error')
            return redirect(url_for('my_documents'))
        
        # Enhanced file existence check
        if not document.file_path:
            print(f"❌ Document {doc_id} has no file path")
            flash(f'Document "{document.filename}" has no file path. Please contact support.', 'error')
            # Remove the broken record
            db.session.delete(document)
            db.session.commit()
            return redirect(url_for('my_documents'))
        
        if not os.path.exists(document.file_path):
            print(f"❌ File not found on disk: {document.file_path}")
            flash(f'The file for "{document.filename}" is no longer available. The document record has been removed.', 'warning')
            # Remove the broken record
            db.session.delete(document)
            db.session.commit()
            return redirect(url_for('my_documents'))
        
        # Verify file is readable
        try:
            file_size = os.path.getsize(document.file_path)
            if file_size == 0:
                print(f"❌ File is empty: {document.file_path}")
                flash(f'The file for "{document.filename}" appears to be corrupted (0 bytes).', 'error')
                return redirect(url_for('my_documents'))
        except OSError as e:
            print(f"❌ Cannot access file: {document.file_path}, error: {e}")
            flash(f'Cannot access the file for "{document.filename}". Please try again later.', 'error')
            return redirect(url_for('my_documents'))
        
        # Track download
        document.increment_download()
        db.session.commit()
        
        # Activity logging
        ActivityLog.log_activity('document_downloaded', current_user.id, 
                                {'document_type': document.document_type, 'filename': document.filename}, 
                                request)
        db.session.commit()
        
        print(f"✅ Successful download: {document.filename} by user {current_user.id}")
        
        # Return file for download
        return send_file(document.file_path, as_attachment=True, download_name=document.filename)
        
    except Exception as e:
        print(f"🚨 Download error for doc_id {doc_id}: {str(e)}")
        flash('An unexpected error occurred while downloading the document. Please try again or contact support.', 'error')
        return redirect(url_for('my_documents'))

@app.route('/my-documents')
@login_required
def my_documents():
    """List user's generated documents"""
    documents = GeneratedDocument.query.filter_by(
        user_id=current_user.id
    ).order_by(GeneratedDocument.created_at.desc()).all()
    
    return render_template('my_documents.html', documents=documents)

# Routes for vocabulary draft management (moved here to avoid conflicts)
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

@app.route('/drafts')
@login_required
def drafts():
    """List all user's drafts (all document types)"""
    drafts = FormDraft.query.filter_by(
        user_id=current_user.id,
        is_current=True
    ).order_by(FormDraft.updated_at.desc()).all()
    
    return render_template('drafts.html', drafts=drafts)

@app.route('/delete-document/<int:doc_id>', methods=['POST'])
@login_required
def delete_document(doc_id):
    """Delete a generated document"""
    document = GeneratedDocument.query.filter_by(id=doc_id, user_id=current_user.id).first()
    
    if not document:
        flash('Document not found', 'error')
        return redirect(url_for('my_documents'))
    
    try:
        # Delete the physical file if it exists
        if document.file_path and os.path.exists(document.file_path):
            os.remove(document.file_path)
            print(f"✓ Deleted file: {document.file_path}")
        
        # Store filename for success message
        filename = document.filename
        
        # Delete the database record
        db.session.delete(document)
        db.session.commit()
        
        flash(f'Document "{filename}" removed successfully!', 'success')
        
    except Exception as e:
        print(f"Error deleting document: {e}")
        flash(f'Error removing document: {str(e)}', 'error')
    
    return redirect(url_for('my_documents'))

@app.route('/autosave-test-draft', methods=['POST'])
@login_required
def autosave_test_draft():
    """AJAX endpoint for autosaving test draft"""
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Prepare form data for JSON storage
        form_data = {
            'module_acronym': data.get('module_acronym', ''),
            'test_type': data.get('test_type', 'pre'),
            'questions': []
        }
        
        # Process test questions
        questions_data = data.get('questions', [])
        for question_data in questions_data:
            question_text = question_data.get('question_text', '').strip()
            choice_a = question_data.get('choice_a', '').strip()
            choice_b = question_data.get('choice_b', '').strip()
            choice_c = question_data.get('choice_c', '').strip()
            choice_d = question_data.get('choice_d', '').strip()
            
            # Only include questions with some content
            if question_text or choice_a or choice_b or choice_c or choice_d:
                form_data['questions'].append({
                    'question_text': question_text,
                    'choice_a': choice_a,
                    'choice_b': choice_b,
                    'choice_c': choice_c,
                    'choice_d': choice_d
                })
        
        # Check if this is updating an existing draft
        draft_id = data.get('draft_id')
        if draft_id:
            # Update existing draft
            draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='test').first()
            if draft:
                draft.form_data = form_data
                draft.updated_at = datetime.utcnow()
                # Update title if module acronym or test type changed
                test_type_display = "Pre-Test" if form_data['test_type'] == 'pre' else "Post-Test"
                if form_data['module_acronym']:
                    draft.title = f"{test_type_display} Worksheet - {form_data['module_acronym']}"
                    draft.module_acronym = form_data['module_acronym']
            else:
                return jsonify({'success': False, 'error': 'Draft not found'})
        else:
            # Create new draft
            test_type_display = "Pre-Test" if form_data['test_type'] == 'pre' else "Post-Test"
            title = f"{test_type_display} Worksheet - {form_data['module_acronym']}" if form_data['module_acronym'] else f"{test_type_display} Worksheet - Untitled"
            draft = FormDraft(
                user_id=current_user.id,
                form_type='test',
                title=title,
                module_acronym=form_data['module_acronym'],
                form_data=form_data
            )
            db.session.add(draft)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'draft_id': draft.id,
            'message': 'Draft saved automatically',
            'timestamp': datetime.utcnow().strftime('%I:%M:%S %p')
        })
        
    except Exception as e:
        print(f"Error in test autosave: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/load-test-draft/<int:draft_id>')
@login_required
def load_test_draft(draft_id):
    """Load test worksheet draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='test').first()
    
    if not draft:
        flash('Draft not found', 'error')
        return redirect(url_for('create_test'))
    
    try:
        # Create form and populate with draft data
        form = TestWorksheetForm()
        form_data = draft.form_data
        
        # Populate form fields
        form.module_acronym.data = form_data.get('module_acronym', '')
        form.test_type.data = form_data.get('test_type', 'pre')
        
        # Populate test questions
        questions_data = form_data.get('questions', [])
        for i, question_data in enumerate(questions_data):
            if i < len(form.questions):
                form.questions[i].question_text.data = question_data.get('question_text', '')
                form.questions[i].choice_a.data = question_data.get('choice_a', '')
                form.questions[i].choice_b.data = question_data.get('choice_b', '')
                form.questions[i].choice_c.data = question_data.get('choice_c', '')
                form.questions[i].choice_d.data = question_data.get('choice_d', '')
        
        flash(f'Draft "{draft.title}" loaded successfully!', 'success')
        return render_template('create_test.html', form=form, draft_id=draft.id)
        
    except Exception as e:
        print(f"Error loading test draft: {e}")
        flash(f'Error loading draft: {str(e)}', 'error')
        return redirect(url_for('create_test'))

@app.route('/delete-test-draft/<int:draft_id>', methods=['POST'])
@login_required
def delete_test_draft(draft_id):
    """Delete test worksheet draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='test').first()
    
    if not draft:
        flash('Draft not found', 'error')
    else:
        db.session.delete(draft)
        db.session.commit()
        flash('Draft deleted successfully!', 'success')
    
    return redirect(url_for('drafts'))

@app.route('/load-pba-draft/<int:draft_id>')
@login_required
def load_pba_draft(draft_id):
    """Load PBA worksheet draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='pba').first()
    
    if not draft:
        flash('Draft not found', 'error')
        return redirect(url_for('create_pba'))
    
    try:
        # Create form and populate with draft data
        form = PBAWorksheetForm()
        form_data = draft.form_data
        
        # Populate basic fields
        form.module_acronym.data = form_data.get('module_acronym', '')
        form.session_number.data = form_data.get('session_number', '')
        form.section_header.data = form_data.get('section_header', '')
        
        # Populate assessment fields
        assessments_data = form_data.get('assessments', [])
        for i, assessment_data in enumerate(assessments_data):
            if i < len(form.assessments):
                form.assessments[i].assessment.data = assessment_data.get('assessment', '')
        
        flash(f'Draft "{draft.title}" loaded successfully!', 'success')
        return render_template('create_pba.html', form=form, draft_id=draft.id)
        
    except Exception as e:
        print(f"Error loading PBA draft: {e}")
        flash(f'Error loading draft: {str(e)}', 'error')
        return redirect(url_for('create_pba'))

@app.route('/delete-pba-draft/<int:draft_id>', methods=['POST'])
@login_required
def delete_pba_draft(draft_id):
    """Delete PBA worksheet draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='pba').first()
    
    if not draft:
        flash('Draft not found', 'error')
    else:
        db.session.delete(draft)
        db.session.commit()
        flash('Draft deleted successfully!', 'success')
    
    return redirect(url_for('drafts'))

@app.route('/autosave-pba-draft', methods=['POST'])
@login_required
def autosave_pba_draft():
    """AJAX endpoint for autosaving PBA draft"""
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Prepare form data for JSON storage
        form_data = {
            'module_acronym': data.get('module_acronym', ''),
            'session_number': data.get('session_number', ''),
            'section_header': data.get('section_header', ''),
            'assessments': []
        }
        
        # Process assessment fields
        assessments_data = data.get('assessments', [])
        for assessment_data in assessments_data:
            assessment_text = assessment_data.get('assessment', '').strip()
            # Only include non-empty assessments
            if assessment_text:
                form_data['assessments'].append({
                    'assessment': assessment_text
                })
        
        # Check if this is updating an existing draft
        draft_id = data.get('draft_id')
        if draft_id:
            # Update existing draft
            draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='pba').first()
            if draft:
                draft.form_data = form_data
                draft.updated_at = datetime.utcnow()
                # Update title based on form data
                if form_data['module_acronym'] or form_data['session_number']:
                    draft.title = f"PBA Worksheet - {form_data['module_acronym']} Session {form_data['session_number']}"
                    draft.module_acronym = form_data['module_acronym']
            else:
                return jsonify({'success': False, 'error': 'Draft not found'})
        else:
            # Create new draft
            title_parts = []
            if form_data['module_acronym']:
                title_parts.append(form_data['module_acronym'])
            if form_data['session_number']:
                title_parts.append(f"Session {form_data['session_number']}")
            
            title = f"PBA Worksheet - {' '.join(title_parts)}" if title_parts else "PBA Worksheet - Untitled"
            
            draft = FormDraft(
                user_id=current_user.id,
                form_type='pba',
                title=title,
                module_acronym=form_data['module_acronym'],
                form_data=form_data
            )
            db.session.add(draft)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'draft_id': draft.id,
            'message': 'Draft saved automatically',
            'timestamp': datetime.utcnow().strftime('%I:%M:%S %p')
        })
        
    except Exception as e:
        print(f"Error in PBA autosave: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/autosave-generic-draft', methods=['POST'])
@login_required  
def autosave_generic_draft():
    """AJAX endpoint for autosaving generic worksheet draft"""
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Prepare form data for JSON storage
        form_data = {
            'module_acronym': data.get('module_acronym', ''),
            'dynamic_fields': data.get('dynamic_fields', [])
        }
        
        # Check if this is updating an existing draft
        draft_id = data.get('draft_id')
        if draft_id:
            # Update existing draft
            draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='generic').first()
            if draft:
                draft.form_data = form_data
                draft.updated_at = datetime.utcnow()
                # Update title based on form data
                if form_data['module_acronym']:
                    draft.title = f"Generic Worksheet - {form_data['module_acronym']}"
                    draft.module_acronym = form_data['module_acronym']
            else:
                return jsonify({'success': False, 'error': 'Draft not found'})
        else:
            # Create new draft
            title = f"Generic Worksheet - {form_data['module_acronym']}" if form_data['module_acronym'] else "Generic Worksheet - Untitled"
            draft = FormDraft(
                user_id=current_user.id,
                form_type='generic',
                title=title,
                module_acronym=form_data['module_acronym'],
                form_data=form_data
            )
            db.session.add(draft)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'draft_id': draft.id,
            'message': 'Draft saved automatically',
            'timestamp': datetime.utcnow().strftime('%I:%M:%S %p')
        })
        
    except Exception as e:
        print(f"Error in generic autosave: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/autosave-moduleactivity-draft', methods=['POST'])
@login_required
def autosave_moduleactivity_draft():
    """AJAX endpoint for autosaving module activity sheet draft"""
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Prepare form data for JSON storage
        form_data = {
            'module_acronym': data.get('module_acronym', ''),
            'sessions': []
        }
        
        # Process session data (7 sessions)
        for i in range(1, 8):
            session_activity = data.get(f'session{i}_activity', '').strip()
            session_is_pba = data.get(f'session{i}_is_pba', False)
            
            if session_activity or session_is_pba:
                form_data['sessions'].append({
                    'session_number': i,
                    'activity': session_activity,
                    'is_pba': session_is_pba
                })
        
        # Check if this is updating an existing draft
        draft_id = data.get('draft_id')
        if draft_id:
            # Update existing draft
            draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='moduleactivity').first()
            if draft:
                draft.form_data = form_data
                draft.updated_at = datetime.utcnow()
                # Update title based on form data
                if form_data['module_acronym']:
                    draft.title = f"Module Activity Sheet - {form_data['module_acronym']}"
                    draft.module_acronym = form_data['module_acronym']
            else:
                return jsonify({'success': False, 'error': 'Draft not found'})
        else:
            # Create new draft
            title = f"Module Activity Sheet - {form_data['module_acronym']}" if form_data['module_acronym'] else "Module Activity Sheet - Untitled"
            draft = FormDraft(
                user_id=current_user.id,
                form_type='moduleactivity',
                title=title,
                module_acronym=form_data['module_acronym'],
                form_data=form_data
            )
            db.session.add(draft)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'draft_id': draft.id,
            'message': 'Draft saved automatically',
            'timestamp': datetime.utcnow().strftime('%I:%M:%S %p')
        })
        
    except Exception as e:
        print(f"Error in module activity autosave: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/autosave-moduleguide-draft', methods=['POST'])
@login_required
def autosave_moduleguide_draft():
    """AJAX endpoint for autosaving module guide draft"""
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Prepare form data for JSON storage
        form_data = {
            'module_acronym': data.get('module_acronym', ''),
            'teachertips_statement': data.get('teachertips_statement', ''),
            'standards': [],
            'vocab_terms': [],
            'careers': [],
            'sessions': [],
            'enrichment_activities': [],
            'locally_sourced_materials': [],
            'maintenance_items': [],
            'assembly_instructions': [],
            'recommended_websites': []
        }
        
        # Process standards
        standards_data = data.get('standards', [])
        for standard in standards_data:
            # Check if standard is a valid dictionary (not None)
            if standard and isinstance(standard, dict):
                if standard.get('standard'):
                    form_data['standards'].append({
                        'standard': standard['standard']
                    })
        
        # Process vocabulary terms
        vocab_data = data.get('vocab_terms', [])
        for term in vocab_data:
            # Check if term is a valid dictionary (not None)
            if term and isinstance(term, dict):
                if term.get('term'):
                    form_data['vocab_terms'].append({
                        'term': term['term']
                    })
        
        # Process careers
        careers_data = data.get('careers', [])
        for career in careers_data:
            # Check if career is a valid dictionary (not None)
            if career and isinstance(career, dict):
                if career.get('career'):
                    form_data['careers'].append({
                        'career': career['career']
                    })
        
        # Process sessions (7 sessions with complex structure)
        sessions_data = data.get('sessions', [])
        for session in sessions_data:
            # Check if session is a valid dictionary (not None)
            if session and isinstance(session, dict):
                if session.get('focus') or session.get('goals') or session.get('materials') or session.get('preparations') or session.get('assessments'):
                    session_data = {
                        'focus': session.get('focus', ''),
                        'goals': [goal for goal in session.get('goals', []) if goal],
                        'materials': [material for material in session.get('materials', []) if material],
                        'preparations': [prep for prep in session.get('preparations', []) if prep],
                        'assessments': [assessment for assessment in session.get('assessments', []) if assessment]
                    }
                    form_data['sessions'].append(session_data)
        
        # Process enrichment activities
        enrichment_data = data.get('enrichment_activities', [])
        for activity in enrichment_data:
            # Check if activity is a valid dictionary (not None)
            if activity and isinstance(activity, dict):
                if activity.get('activity'):
                    form_data['enrichment_activities'].append({
                        'activity': activity['activity']
                    })
        
        # Process locally sourced materials
        materials_data = data.get('locally_sourced_materials', [])
        for material in materials_data:
            # Check if material is a valid dictionary (not None)
            if material and isinstance(material, dict):
                if material.get('material'):
                    form_data['locally_sourced_materials'].append({
                        'material': material['material']
                    })
        
        # Process maintenance items
        maintenance_data = data.get('maintenance_items', [])
        for item in maintenance_data:
            # Check if item is a valid dictionary (not None)
            if item and isinstance(item, dict):
                if item.get('item'):
                    form_data['maintenance_items'].append({
                        'item': item['item']
                    })
        
        # Process assembly instructions
        assembly_data = data.get('assembly_instructions', [])
        for instruction in assembly_data:
            # Check if instruction is a valid dictionary (not None)
            if instruction and isinstance(instruction, dict):
                if instruction.get('instruction'):
                    form_data['assembly_instructions'].append({
                        'instruction': instruction['instruction']
                    })
        
        # Process recommended websites
        websites_data = data.get('recommended_websites', [])
        for website in websites_data:
            # Check if website is a valid dictionary (not None)
            if website and isinstance(website, dict):
                if website.get('title') or website.get('url'):
                    form_data['recommended_websites'].append({
                        'title': website.get('title', ''),
                        'url': website.get('url', '')
                    })
        
        # Check if this is updating an existing draft
        draft_id = data.get('draft_id')
        if draft_id:
            # Update existing draft
            draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='moduleguide').first()
            if draft:
                draft.form_data = form_data
                draft.updated_at = datetime.utcnow()
                # Update title based on form data
                if form_data['module_acronym']:
                    draft.title = f"Module Guide - {form_data['module_acronym']}"
                    draft.module_acronym = form_data['module_acronym']
            else:
                return jsonify({'success': False, 'error': 'Draft not found'})
        else:
            # Create new draft
            title = f"Module Guide - {form_data['module_acronym']}" if form_data['module_acronym'] else "Module Guide - Untitled"
            draft = FormDraft(
                user_id=current_user.id,
                form_type='moduleguide',
                title=title,
                module_acronym=form_data['module_acronym'],
                form_data=form_data
            )
            db.session.add(draft)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'draft_id': draft.id,
            'message': 'Draft saved automatically',
            'timestamp': datetime.utcnow().strftime('%I:%M:%S %p')
        })
        
    except Exception as e:
        print(f"Error in module guide autosave: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/load-moduleguide-draft/<int:draft_id>')
@login_required
def load_moduleguide_draft(draft_id):
    """Load module guide draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='moduleguide').first()
    
    if not draft:
        flash('Draft not found', 'error')
        return redirect(url_for('create_module_guide'))
    
    try:
        # Create form and populate with draft data
        form = ModuleGuideForm()
        form_data = draft.form_data
        
        # Populate basic fields
        form.module_acronym.data = form_data.get('module_acronym', '')
        form.teachertips_statement.data = form_data.get('teachertips_statement', '')
        
        # Populate standards
        standards_data = form_data.get('standards', [])
        for i, standard_data in enumerate(standards_data):
            if i < len(form.standards):
                form.standards[i].standard.data = standard_data.get('standard', '')
        
        # Populate vocabulary terms
        vocab_data = form_data.get('vocab_terms', [])
        for i, vocab_item in enumerate(vocab_data):
            if i < len(form.vocab_terms):
                form.vocab_terms[i].term.data = vocab_item.get('term', '')
        
        # Populate careers
        careers_data = form_data.get('careers', [])
        for i, career_data in enumerate(careers_data):
            if i < len(form.careers):
                form.careers[i].career.data = career_data.get('career', '')
        
        # Populate sessions (complex nested structure)
        sessions_data = form_data.get('sessions', [])
        for i, session_data in enumerate(sessions_data):
            if i < len(form.sessions):
                session_form = form.sessions[i]
                session_form.focus.data = session_data.get('focus', '')
                
                # Populate goals
                goals = session_data.get('goals', [])
                for j, goal in enumerate(goals):
                    if j < len(session_form.goals):
                        session_form.goals[j].goal.data = goal
                
                # Populate materials (15 material fields)
                materials = session_data.get('materials', [])
                for j, material in enumerate(materials):
                    if j < 15:  # 15 material fields
                        material_field = getattr(session_form, f'material{j+1}')
                        material_field.data = material
                
                # Populate preparations
                preparations = session_data.get('preparations', [])
                for j, prep in enumerate(preparations):
                    if j < len(session_form.preparations):
                        session_form.preparations[j].prep.data = prep
                
                # Populate assessments
                assessments = session_data.get('assessments', [])
                for j, assessment in enumerate(assessments):
                    if j < len(session_form.assessments):
                        session_form.assessments[j].assessment.data = assessment
        
        # Populate enrichment activities
        enrichment_data = form_data.get('enrichment_activities', [])
        for i, activity_data in enumerate(enrichment_data):
            if i < len(form.enrichment_activities):
                form.enrichment_activities[i].activity.data = activity_data.get('activity', '')
        
        # Populate locally sourced materials
        materials_data = form_data.get('locally_sourced_materials', [])
        for i, material_data in enumerate(materials_data):
            if i < len(form.locally_sourced_materials):
                form.locally_sourced_materials[i].material.data = material_data.get('material', '')
        
        # Populate maintenance items
        maintenance_data = form_data.get('maintenance_items', [])
        for i, item_data in enumerate(maintenance_data):
            if i < len(form.maintenance_items):
                form.maintenance_items[i].item.data = item_data.get('item', '')
        
        # Populate assembly instructions
        assembly_data = form_data.get('assembly_instructions', [])
        for i, instruction_data in enumerate(assembly_data):
            if i < len(form.assembly_instructions):
                form.assembly_instructions[i].instruction.data = instruction_data.get('instruction', '')
        
        # Populate recommended websites
        websites_data = form_data.get('recommended_websites', [])
        for i, website_data in enumerate(websites_data):
            if i < len(form.recommended_websites):
                form.recommended_websites[i].title.data = website_data.get('title', '')
                form.recommended_websites[i].url.data = website_data.get('url', '')
        
        flash(f'Draft "{draft.title}" loaded successfully!', 'success')
        return render_template('create_moduleGuide.html', form=form, draft_id=draft.id)
        
    except Exception as e:
        print(f"Error loading module guide draft: {e}")
        flash(f'Error loading draft: {str(e)}', 'error')
        return redirect(url_for('create_module_guide'))

@app.route('/delete-moduleguide-draft/<int:draft_id>', methods=['POST'])
@login_required
def delete_moduleguide_draft(draft_id):
    """Delete module guide draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='moduleguide').first()
    
    if not draft:
        flash('Draft not found', 'error')
    else:
        db.session.delete(draft)
        db.session.commit()
        flash('Draft deleted successfully!', 'success')
    
    return redirect(url_for('drafts'))

@app.route('/autosave-moduleanswerkey-draft', methods=['POST'])
@login_required
def autosave_moduleanswerkey_draft():
    """AJAX endpoint for autosaving module answer key draft"""
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Prepare form data for JSON storage
        form_data = {
            'module_acronym': data.get('module_acronym', ''),
            'pretest_questions': [],
            'rca_sessions': [],
            'posttest_questions': [],
            'pba_sessions': [],
            'vocabulary': [],
            'portfolio_checklist': [],
            'enrichment_dynamic_content': data.get('enrichment_dynamic_content', []),
            'worksheet_answer_keys': data.get('worksheet_answer_keys', [])
        }
        
        # Process pre-test questions
        pretest_data = data.get('pretest_questions', [])
        for question in pretest_data:
            # Check if question is a valid dictionary (not None)
            if question and isinstance(question, dict):
                if question.get('question_text') or question.get('choice_a') or question.get('choice_b') or question.get('choice_c') or question.get('choice_d'):
                    form_data['pretest_questions'].append({
                        'question_text': question.get('question_text', ''),
                        'choice_a': question.get('choice_a', ''),
                        'choice_b': question.get('choice_b', ''),
                        'choice_c': question.get('choice_c', ''),
                        'choice_d': question.get('choice_d', ''),
                        'correct_answer': question.get('correct_answer', '')
                    })
        
        # Process RCA sessions (4 sessions with 3 questions each)
        rca_data = data.get('rca_sessions', [])
        for session in rca_data:
            # Check if session is a valid dictionary (not None)
            if session and isinstance(session, dict):
                questions = []
                for question in session.get('questions', []):
                    # Check if question is a valid dictionary (not None)
                    if question and isinstance(question, dict):
                        if question.get('question_text') or question.get('choice_a'):
                            questions.append({
                                'question_text': question.get('question_text', ''),
                                'choice_a': question.get('choice_a', ''),
                                'choice_b': question.get('choice_b', ''),
                                'choice_c': question.get('choice_c', ''),
                                'choice_d': question.get('choice_d', ''),
                                'correct_answer': question.get('correct_answer', '')
                            })
                
                if questions:
                    form_data['rca_sessions'].append({
                        'session_number': session.get('session_number', ''),
                        'questions': questions
                    })
        
        # Process post-test questions
        posttest_data = data.get('posttest_questions', [])
        for question in posttest_data:
            # Check if question is a valid dictionary (not None)
            if question and isinstance(question, dict):
                if question.get('question_text') or question.get('choice_a') or question.get('choice_b') or question.get('choice_c') or question.get('choice_d'):
                    form_data['posttest_questions'].append({
                        'question_text': question.get('question_text', ''),
                        'choice_a': question.get('choice_a', ''),
                        'choice_b': question.get('choice_b', ''),
                        'choice_c': question.get('choice_c', ''),
                        'choice_d': question.get('choice_d', ''),
                        'correct_answer': question.get('correct_answer', '')
                    })
        
        # Process PBA sessions
        pba_data = data.get('pba_sessions', [])
        for session in pba_data:
            # Check if session is a valid dictionary (not None)
            if session and isinstance(session, dict):
                questions = []
                for question in session.get('assessment_questions', []):
                    # Check if question is a valid dictionary (not None)
                    if question and isinstance(question, dict):
                        if question.get('question') or question.get('correct_answer'):
                            questions.append({
                                'question': question.get('question', ''),
                                'correct_answer': question.get('correct_answer', '')
                            })
                
                if session.get('session_number') or session.get('activity_name') or questions:
                    form_data['pba_sessions'].append({
                        'session_number': session.get('session_number', ''),
                        'activity_name': session.get('activity_name', ''),
                        'assessment_questions': questions
                    })
        
        # Process vocabulary terms
        vocab_data = data.get('vocabulary', [])
        for term in vocab_data:
            # Check if term is a valid dictionary (not None)
            if term and isinstance(term, dict):
                if term.get('term') or term.get('definition'):
                    form_data['vocabulary'].append({
                        'term': term.get('term', ''),
                        'definition': term.get('definition', '')
                    })
        
        # Process portfolio checklist
        portfolio_data = data.get('portfolio_checklist', [])
        for item in portfolio_data:
            # Check if item is a valid dictionary (not None)
            if item and isinstance(item, dict):
                if item.get('product') or item.get('session_number'):
                    form_data['portfolio_checklist'].append({
                        'product': item.get('product', ''),
                        'session_number': item.get('session_number', '')
                    })
        
        # Check if this is updating an existing draft
        draft_id = data.get('draft_id')
        if draft_id:
            # Update existing draft
            draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='moduleanswerkey').first()
            if draft:
                draft.form_data = form_data
                draft.updated_at = datetime.utcnow()
                # Update title based on form data
                if form_data['module_acronym']:
                    draft.title = f"Module Answer Key - {form_data['module_acronym']}"
                    draft.module_acronym = form_data['module_acronym']
            else:
                return jsonify({'success': False, 'error': 'Draft not found'})
        else:
            # Create new draft
            title = f"Module Answer Key - {form_data['module_acronym']}" if form_data['module_acronym'] else "Module Answer Key - Untitled"
            draft = FormDraft(
                user_id=current_user.id,
                form_type='moduleanswerkey',
                title=title,
                module_acronym=form_data['module_acronym'],
                form_data=form_data
            )
            db.session.add(draft)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'draft_id': draft.id,
            'message': 'Draft saved automatically',
            'timestamp': datetime.utcnow().strftime('%I:%M:%S %p')
        })
        
    except Exception as e:
        print(f"Error in module answer key autosave: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/load-moduleanswerkey-draft/<int:draft_id>')
@login_required
def load_moduleanswerkey_draft(draft_id):
    """Load module answer key draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='moduleanswerkey').first()
    
    if not draft:
        flash('Draft not found', 'error')
        return redirect(url_for('create_module_answer_key'))
    
    try:
        # Create form and populate with draft data
        form = ModuleAnswerKeyForm()
        form_data = draft.form_data
        
        # Populate basic fields
        form.module_acronym.data = form_data.get('module_acronym', '')
        
        # Populate pre-test questions
        pretest_data = form_data.get('pretest_questions', [])
        for i, question_data in enumerate(pretest_data):
            if i < len(form.pretest_questions):
                form.pretest_questions[i].question_text.data = question_data.get('question_text', '')
                form.pretest_questions[i].choice_a.data = question_data.get('choice_a', '')
                form.pretest_questions[i].choice_b.data = question_data.get('choice_b', '')
                form.pretest_questions[i].choice_c.data = question_data.get('choice_c', '')
                form.pretest_questions[i].choice_d.data = question_data.get('choice_d', '')
                # Clean correct_answer to ensure it's valid
                correct_answer = question_data.get('correct_answer', '').strip().upper()
                form.pretest_questions[i].correct_answer.data = correct_answer if correct_answer in ['A', 'B', 'C', 'D'] else ''
        
        # Populate RCA sessions
        rca_data = form_data.get('rca_sessions', [])
        print(f"🔍 RCA sessions data: {len(rca_data)} sessions found")
        for i, session_data in enumerate(rca_data):
            print(f"🔍 RCA session {i+1}: {len(session_data.get('questions', []))} questions")
            if i < len(form.rca_sessions):
                questions = session_data.get('questions', [])
                for j, question_data in enumerate(questions):
                    print(f"🔍 RCA session {i+1}, question {j+1}: {question_data.get('question_text', '')[:50]}...")
                    if j < len(form.rca_sessions[i].questions):
                        form.rca_sessions[i].questions[j].question_text.data = question_data.get('question_text', '')
                        form.rca_sessions[i].questions[j].choice_a.data = question_data.get('choice_a', '')
                        form.rca_sessions[i].questions[j].choice_b.data = question_data.get('choice_b', '')
                        form.rca_sessions[i].questions[j].choice_c.data = question_data.get('choice_c', '')
                        form.rca_sessions[i].questions[j].choice_d.data = question_data.get('choice_d', '')
                        # Clean correct_answer to ensure it's valid
                        correct_answer = question_data.get('correct_answer', '').strip().upper()
                        form.rca_sessions[i].questions[j].correct_answer.data = correct_answer if correct_answer in ['A', 'B', 'C', 'D'] else ''
        
        # Populate post-test questions
        posttest_data = form_data.get('posttest_questions', [])
        for i, question_data in enumerate(posttest_data):
            if i < len(form.posttest_questions):
                form.posttest_questions[i].question_text.data = question_data.get('question_text', '')
                form.posttest_questions[i].choice_a.data = question_data.get('choice_a', '')
                form.posttest_questions[i].choice_b.data = question_data.get('choice_b', '')
                form.posttest_questions[i].choice_c.data = question_data.get('choice_c', '')
                form.posttest_questions[i].choice_d.data = question_data.get('choice_d', '')
                # Clean correct_answer to ensure it's valid
                correct_answer = question_data.get('correct_answer', '').strip().upper()
                form.posttest_questions[i].correct_answer.data = correct_answer if correct_answer in ['A', 'B', 'C', 'D'] else ''
        
        # Populate PBA sessions
        pba_data = form_data.get('pba_sessions', [])
        print(f"🔍 PBA sessions data: {len(pba_data)} sessions found")
        for i, session_data in enumerate(pba_data):
            print(f"🔍 PBA session {i+1}: {len(session_data.get('assessment_questions', []))} questions")
            if i < len(form.pba_sessions):
                form.pba_sessions[i].session_number.data = session_data.get('session_number', '')
                form.pba_sessions[i].activity_name.data = session_data.get('activity_name', '')
                
                questions = session_data.get('assessment_questions', [])
                for j, question_data in enumerate(questions):
                    print(f"🔍 PBA session {i+1}, question {j+1}: {question_data.get('question', '')[:50]}...")
                    if j < len(form.pba_sessions[i].assessment_questions):
                        form.pba_sessions[i].assessment_questions[j].question.data = question_data.get('question', '')
                        form.pba_sessions[i].assessment_questions[j].correct_answer.data = question_data.get('correct_answer', '')
        
        # Populate vocabulary
        vocab_data = form_data.get('vocabulary', [])
        for i, term_data in enumerate(vocab_data):
            if i < len(form.vocabulary):
                form.vocabulary[i].term.data = term_data.get('term', '')
                form.vocabulary[i].definition.data = term_data.get('definition', '')
        
        # Populate portfolio checklist
        portfolio_data = form_data.get('portfolio_checklist', [])
        print(f"🔍 Portfolio checklist data: {len(portfolio_data)} items found")
        print(f"🔍 Raw portfolio data: {portfolio_data}")
        print(f"🔍 Form portfolio_checklist length: {len(form.portfolio_checklist)}")
        
        for i, item_data in enumerate(portfolio_data):
            print(f"🔍 Portfolio item {i+1}: {item_data}")
            if i < len(form.portfolio_checklist):
                print(f"🔍 Setting portfolio_checklist[{i}].product = '{item_data.get('product', '')}'")
                print(f"🔍 Setting portfolio_checklist[{i}].session_number = '{item_data.get('session_number', '')}'")
                form.portfolio_checklist[i].product.data = item_data.get('product', '')
                form.portfolio_checklist[i].session_number.data = item_data.get('session_number', '')
            else:
                print(f"🔍 Skipping item {i+1} - index {i} >= form length {len(form.portfolio_checklist)}")
        
        # Pass dynamic fields data to template for JavaScript reconstruction
        enrichment_data = form_data.get('enrichment_dynamic_content', [])
        worksheet_data = form_data.get('worksheet_answer_keys', [])
        
        # Debug logging
        print(f"🔍 Module Answer Key draft {draft.id} data keys: {list(form_data.keys())}")
        print(f"🔍 Enrichment data: {enrichment_data}")
        print(f"🔍 Worksheet data: {worksheet_data}")
        
        flash(f'Draft "{draft.title}" loaded successfully!', 'success')
        return render_template('create_moduleAnswerKey.html', form=form, draft_id=draft.id, 
                             draft_data=form_data, enrichment_dynamic_content=enrichment_data, 
                             worksheet_answer_keys=worksheet_data, portfolio_checklist_data=portfolio_data)
        
    except Exception as e:
        print(f"Error loading module answer key draft: {e}")
        flash(f'Error loading draft: {str(e)}', 'error')
        return redirect(url_for('create_module_answer_key'))

@app.route('/delete-moduleanswerkey-draft/<int:draft_id>', methods=['POST'])
@login_required
def delete_moduleanswerkey_draft(draft_id):
    """Delete module answer key draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='moduleanswerkey').first()
    
    if not draft:
        flash('Draft not found', 'error')
    else:
        db.session.delete(draft)
        db.session.commit()
        flash('Draft deleted successfully!', 'success')
    
    return redirect(url_for('drafts'))

# ===== MODULE ANSWER KEY 2.0 DRAFT MANAGEMENT ROUTES =====

@app.route('/autosave-module-answer-key2-draft', methods=['POST'])
@login_required
def autosave_module_answer_key2_draft():
    """AJAX endpoint for autosaving Module Answer Key 2.0 draft with enhanced reliability"""
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Prepare form data for JSON storage with explicit validation
        form_data = {
            'module_acronym': data.get('module_acronym', ''),
            'pretest_questions': [],
            'rca_sessions': [],
            'posttest_questions': [],
            'pba_sessions': [],
            'vocabulary': [],
            'portfolio_checklist': []
        }
        
        # Process pre-test questions with index validation
        pretest_questions = data.get('pretest_questions', [])
        for i, question in enumerate(pretest_questions):
            if question and any(question.get(key, '') for key in ['question_text', 'choice_a', 'choice_b', 'choice_c', 'choice_d', 'correct_answer']):
                form_data['pretest_questions'].append({
                    'question_text': question.get('question_text', ''),
                    'choice_a': question.get('choice_a', ''),
                    'choice_b': question.get('choice_b', ''),
                    'choice_c': question.get('choice_c', ''),
                    'choice_d': question.get('choice_d', ''),
                    'correct_answer': question.get('correct_answer', '').upper() if question.get('correct_answer') else ''
                })
        
        # Process RCA sessions with nested question validation
        rca_sessions = data.get('rca_sessions', [])
        for session in rca_sessions:
            if session:
                questions = []
                for question in session.get('questions', []):
                    if question and any(question.get(key, '') for key in ['question_text', 'choice_a', 'choice_b', 'choice_c', 'choice_d', 'correct_answer']):
                        questions.append({
                            'question_text': question.get('question_text', ''),
                            'choice_a': question.get('choice_a', ''),
                            'choice_b': question.get('choice_b', ''),
                            'choice_c': question.get('choice_c', ''),
                            'choice_d': question.get('choice_d', ''),
                            'correct_answer': question.get('correct_answer', '').upper() if question.get('correct_answer') else ''
                        })
                if questions:  # Only add session if it has questions
                    form_data['rca_sessions'].append({'questions': questions})
        
        # Process post-test questions with index validation
        posttest_questions = data.get('posttest_questions', [])
        for i, question in enumerate(posttest_questions):
            if question and any(question.get(key, '') for key in ['question_text', 'choice_a', 'choice_b', 'choice_c', 'choice_d', 'correct_answer']):
                form_data['posttest_questions'].append({
                    'question_text': question.get('question_text', ''),
                    'choice_a': question.get('choice_a', ''),
                    'choice_b': question.get('choice_b', ''),
                    'choice_c': question.get('choice_c', ''),
                    'choice_d': question.get('choice_d', ''),
                    'correct_answer': question.get('correct_answer', '').upper() if question.get('correct_answer') else ''
                })
        
        # Process PBA sessions with validation
        pba_sessions = data.get('pba_sessions', [])
        for session in pba_sessions:
            if session and (session.get('session_number') or session.get('activity_name') or session.get('assessment_questions')):
                assessment_questions = []
                for question in session.get('assessment_questions', []):
                    if question and (question.get('question') or question.get('correct_answer')):
                        assessment_questions.append({
                            'question': question.get('question', ''),
                            'correct_answer': question.get('correct_answer', '')
                        })
                form_data['pba_sessions'].append({
                    'session_number': session.get('session_number', ''),
                    'activity_name': session.get('activity_name', ''),
                    'assessment_questions': assessment_questions
                })
        
        # Process vocabulary with validation
        vocabulary = data.get('vocabulary', [])
        for term in vocabulary:
            if term and (term.get('term') or term.get('definition')):
                form_data['vocabulary'].append({
                    'term': term.get('term', ''),
                    'definition': term.get('definition', '')
                })
        
        # Process portfolio checklist with validation
        portfolio_checklist = data.get('portfolio_checklist', [])
        for item in portfolio_checklist:
            if item and (item.get('product') or item.get('session_number')):
                form_data['portfolio_checklist'].append({
                    'product': item.get('product', ''),
                    'session_number': item.get('session_number', '')
                })
        
        # Create title from module acronym
        module_acronym = form_data.get('module_acronym', 'Untitled')
        title = f"Module Answer Key 2.0 - {module_acronym}" if module_acronym else "Module Answer Key 2.0 - Untitled"
        
        # Check if user already has a draft for this form type
        existing_draft = FormDraft.query.filter_by(
            user_id=current_user.id, 
            form_type='module_answer_key2',
            is_current=True
        ).first()
        
        if existing_draft:
            # Update existing draft
            existing_draft.form_data = form_data
            existing_draft.title = title
            existing_draft.module_acronym = module_acronym
            existing_draft.updated_at = datetime.utcnow()
            print(f"🔍 Updated existing Module Answer Key 2.0 draft {existing_draft.id}")
        else:
            # Create new draft
            new_draft = FormDraft(
                user_id=current_user.id,
                form_type='module_answer_key2',
                title=title,
                module_acronym=module_acronym,
                form_data=form_data,
                is_current=True
            )
            db.session.add(new_draft)
            print(f"🔍 Created new Module Answer Key 2.0 draft")
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Draft saved successfully'})
        
    except Exception as e:
        print(f"🔍 Error autosaving Module Answer Key 2.0 draft: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/load-module-answer-key2-draft/<int:draft_id>')
@login_required
def load_module_answer_key2_draft(draft_id):
    """Load Module Answer Key 2.0 draft"""
    try:
        # Get the draft
        draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='module_answer_key2').first()
        
        if not draft:
            flash('Draft not found', 'error')
            return redirect(url_for('create_module_answer_key2'))
        
        # Create form and load data
        form = ModuleAnswerKey2Form()
        form_data = draft.form_data
        
        # Load data into form with enhanced error handling
        success = load_module_answer_key2_draft_into_form(form, current_user.id)
        
        if not success:
            flash('Error loading draft data', 'error')
            return redirect(url_for('create_module_answer_key2'))
        
        print(f"🔍 Module Answer Key 2.0 draft {draft.id} loaded successfully")
        flash(f'Draft "{draft.title}" loaded successfully!', 'success')
        return render_template('create_module_answer_key2.html', form=form, draft_id=draft.id)
        
    except Exception as e:
        print(f"Error loading Module Answer Key 2.0 draft: {e}")
        flash(f'Error loading draft: {str(e)}', 'error')
        return redirect(url_for('create_module_answer_key2'))

@app.route('/delete-module-answer-key2-draft/<int:draft_id>', methods=['POST'])
@login_required
def delete_module_answer_key2_draft(draft_id):
    """Delete Module Answer Key 2.0 draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='module_answer_key2').first()
    
    if not draft:
        flash('Draft not found', 'error')
    else:
        db.session.delete(draft)
        db.session.commit()
        flash('Module Answer Key 2.0 draft deleted successfully!', 'success')
    
    return redirect(url_for('drafts'))

@app.route('/autosave-familybriefing-draft', methods=['POST'])
@login_required
def autosave_familybriefing_draft():
    """AJAX endpoint for autosaving family briefing draft"""
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Prepare form data for JSON storage
        form_data = {
            'module_name': data.get('module_name', ''),
            'introsentence': data.get('introsentence', ''),
            'learningobjective1': data.get('learningobjective1', ''),
            'learningobjective2': data.get('learningobjective2', ''),
            'learningobjective3': data.get('learningobjective3', ''),
            'learningobjective4': data.get('learningobjective4', ''),
            'learningobjective5': data.get('learningobjective5', ''),
            'learningobjective6': data.get('learningobjective6', ''),
            'activityname1': data.get('activityname1', ''),
            'activityname2': data.get('activityname2', ''),
            'activityname3': data.get('activityname3', ''),
            'activityname4': data.get('activityname4', ''),
            'activityname5': data.get('activityname5', ''),
            'activityname6': data.get('activityname6', ''),
            'activityname7': data.get('activityname7', ''),
            'term1': data.get('term1', ''),
            'term2': data.get('term2', ''),
            'term3': data.get('term3', ''),
            'term4': data.get('term4', ''),
            'term5': data.get('term5', ''),
            'term6': data.get('term6', ''),
            'term7': data.get('term7', ''),
            'term8': data.get('term8', ''),
            'term9': data.get('term9', ''),
            'term10': data.get('term10', ''),
            'term11': data.get('term11', ''),
            'term12': data.get('term12', ''),
            'term13': data.get('term13', ''),
            'term14': data.get('term14', ''),
            'term15': data.get('term15', ''),
            'term16': data.get('term16', ''),
            'term17': data.get('term17', ''),
            'term18': data.get('term18', ''),
            'term19': data.get('term19', ''),
            'term20': data.get('term20', ''),
            'term21': data.get('term21', ''),
            'keyconcept1_name': data.get('keyconcept1_name', ''),
            'keyconcept1_explanation': data.get('keyconcept1_explanation', ''),
            'keyconcept2_name': data.get('keyconcept2_name', ''),
            'keyconcept2_explanation': data.get('keyconcept2_explanation', ''),
            'keyconcept3_name': data.get('keyconcept3_name', ''),
            'keyconcept3_explanation': data.get('keyconcept3_explanation', '')
        }
        
        # Check if this is updating an existing draft
        draft_id = data.get('draft_id')
        if draft_id:
            # Update existing draft
            draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='familybriefing').first()
            if draft:
                draft.form_data = form_data
                draft.updated_at = datetime.utcnow()
                # Update title based on form data
                if form_data['module_name']:
                    draft.title = f"Family Briefing - {form_data['module_name']}"
                    draft.module_acronym = form_data['module_name']
            else:
                return jsonify({'success': False, 'error': 'Draft not found'})
        else:
            # Create new draft
            title = f"Family Briefing - {form_data['module_name']}" if form_data['module_name'] else "Family Briefing - Untitled"
            draft = FormDraft(
                user_id=current_user.id,
                form_type='familybriefing',
                title=title,
                module_acronym=form_data['module_name'],
                form_data=form_data
            )
            db.session.add(draft)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'draft_id': draft.id,
            'message': 'Draft saved automatically',
            'timestamp': datetime.utcnow().strftime('%I:%M:%S %p')
        })
        
    except Exception as e:
        print(f"Error in family briefing autosave: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/autosave-rca-draft', methods=['POST'])
@login_required
def autosave_rca_draft():
    """AJAX endpoint for autosaving RCA worksheet draft"""
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Prepare form data for JSON storage
        form_data = {
            'module_acronym': data.get('module_acronym', ''),
            'session_number': data.get('session_number', ''),
            'questions': []
        }
        
        # Process RCA questions (Research, Challenge, Application)
        questions_data = data.get('questions', [])
        for question_data in questions_data:
            question_text = question_data.get('question_text', '').strip()
            choice_a = question_data.get('choice_a', '').strip()
            choice_b = question_data.get('choice_b', '').strip()
            choice_c = question_data.get('choice_c', '').strip()
            choice_d = question_data.get('choice_d', '').strip()
            
            # Only include questions with some content
            if question_text or choice_a or choice_b or choice_c or choice_d:
                form_data['questions'].append({
                    'question_text': question_text,
                    'choice_a': choice_a,
                    'choice_b': choice_b,
                    'choice_c': choice_c,
                    'choice_d': choice_d
                })
        
        # Check if this is updating an existing draft
        draft_id = data.get('draft_id')
        if draft_id:
            # Update existing draft
            draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='rca').first()
            if draft:
                draft.form_data = form_data
                draft.updated_at = datetime.utcnow()
                # Update title based on form data
                if form_data['module_acronym'] or form_data['session_number']:
                    draft.title = f"RCA Worksheet - {form_data['module_acronym']} Session {form_data['session_number']}"
                    draft.module_acronym = form_data['module_acronym']
            else:
                return jsonify({'success': False, 'error': 'Draft not found'})
        else:
            # Create new draft
            title_parts = []
            if form_data['module_acronym']:
                title_parts.append(form_data['module_acronym'])
            if form_data['session_number']:
                title_parts.append(f"Session {form_data['session_number']}")
            
            title = f"RCA Worksheet - {' '.join(title_parts)}" if title_parts else "RCA Worksheet - Untitled"
            
            draft = FormDraft(
                user_id=current_user.id,
                form_type='rca',
                title=title,
                module_acronym=form_data['module_acronym'],
                form_data=form_data
            )
            db.session.add(draft)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'draft_id': draft.id,
            'message': 'Draft saved automatically',
            'timestamp': datetime.utcnow().strftime('%I:%M:%S %p')
        })
        
    except Exception as e:
        print(f"Error in RCA autosave: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Missing Load/Delete Draft Routes - CRITICAL FIX
@app.route('/load-familybriefing-draft/<int:draft_id>')
@login_required
def load_familybriefing_draft(draft_id):
    """Load family briefing draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='familybriefing').first()
    
    if not draft:
        flash('Draft not found', 'error')
        return redirect(url_for('create_familybriefing'))
    
    try:
        # Create form and populate with draft data
        form = FamilyBriefingForm()
        form_data = draft.form_data
        
        # Populate all form fields
        form.module_name.data = form_data.get('module_name', '')
        form.introsentence.data = form_data.get('introsentence', '')
        form.learningobjective1.data = form_data.get('learningobjective1', '')
        form.learningobjective2.data = form_data.get('learningobjective2', '')
        form.learningobjective3.data = form_data.get('learningobjective3', '')
        form.learningobjective4.data = form_data.get('learningobjective4', '')
        form.learningobjective5.data = form_data.get('learningobjective5', '')
        form.learningobjective6.data = form_data.get('learningobjective6', '')
        form.activityname1.data = form_data.get('activityname1', '')
        form.activityname2.data = form_data.get('activityname2', '')
        form.activityname3.data = form_data.get('activityname3', '')
        form.activityname4.data = form_data.get('activityname4', '')
        form.activityname5.data = form_data.get('activityname5', '')
        form.activityname6.data = form_data.get('activityname6', '')
        form.activityname7.data = form_data.get('activityname7', '')
        form.term1.data = form_data.get('term1', '')
        form.term2.data = form_data.get('term2', '')
        form.term3.data = form_data.get('term3', '')
        form.term4.data = form_data.get('term4', '')
        form.term5.data = form_data.get('term5', '')
        form.term6.data = form_data.get('term6', '')
        form.term7.data = form_data.get('term7', '')
        form.term8.data = form_data.get('term8', '')
        form.term9.data = form_data.get('term9', '')
        form.term10.data = form_data.get('term10', '')
        form.term11.data = form_data.get('term11', '')
        form.term12.data = form_data.get('term12', '')
        form.term13.data = form_data.get('term13', '')
        form.term14.data = form_data.get('term14', '')
        form.term15.data = form_data.get('term15', '')
        form.term16.data = form_data.get('term16', '')
        form.term17.data = form_data.get('term17', '')
        form.term18.data = form_data.get('term18', '')
        form.term19.data = form_data.get('term19', '')
        form.term20.data = form_data.get('term20', '')
        form.term21.data = form_data.get('term21', '')
        form.keyconcept1_name.data = form_data.get('keyconcept1_name', '')
        form.keyconcept1_explanation.data = form_data.get('keyconcept1_explanation', '')
        form.keyconcept2_name.data = form_data.get('keyconcept2_name', '')
        form.keyconcept2_explanation.data = form_data.get('keyconcept2_explanation', '')
        form.keyconcept3_name.data = form_data.get('keyconcept3_name', '')
        form.keyconcept3_explanation.data = form_data.get('keyconcept3_explanation', '')
        
        flash(f'Draft "{draft.title}" loaded successfully!', 'success')
        return render_template('create_familybriefing.html', form=form, draft_id=draft.id)
        
    except Exception as e:
        print(f"Error loading family briefing draft: {e}")
        flash(f'Error loading draft: {str(e)}', 'error')
        return redirect(url_for('create_familybriefing'))

@app.route('/delete-familybriefing-draft/<int:draft_id>', methods=['POST'])
@login_required
def delete_familybriefing_draft(draft_id):
    """Delete family briefing draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='familybriefing').first()
    
    if not draft:
        flash('Draft not found', 'error')
    else:
        db.session.delete(draft)
        db.session.commit()
        flash('Draft deleted successfully!', 'success')
    
    return redirect(url_for('drafts'))

@app.route('/load-rca-draft/<int:draft_id>')
@login_required
def load_rca_draft(draft_id):
    """Load RCA worksheet draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='rca').first()
    
    if not draft:
        flash('Draft not found', 'error')
        return redirect(url_for('create_rca'))
    
    try:
        # Create form and populate with draft data
        form = RCAWorksheetForm()
        form_data = draft.form_data
        
        # Populate form fields
        form.module_acronym.data = form_data.get('module_acronym', '')
        form.session_number.data = form_data.get('session_number', '')
        
        # Populate questions
        questions_data = form_data.get('questions', [])
        for i, question_data in enumerate(questions_data):
            if i < len(form.questions):
                form.questions[i].question_text.data = question_data.get('question_text', '')
                form.questions[i].choice_a.data = question_data.get('choice_a', '')
                form.questions[i].choice_b.data = question_data.get('choice_b', '')
                form.questions[i].choice_c.data = question_data.get('choice_c', '')
                form.questions[i].choice_d.data = question_data.get('choice_d', '')
        
        flash(f'Draft "{draft.title}" loaded successfully!', 'success')
        return render_template('create_rca.html', form=form, draft_id=draft.id)
        
    except Exception as e:
        print(f"Error loading RCA draft: {e}")
        flash(f'Error loading draft: {str(e)}', 'error')
        return redirect(url_for('create_rca'))

@app.route('/delete-rca-draft/<int:draft_id>', methods=['POST'])
@login_required
def delete_rca_draft(draft_id):
    """Delete RCA worksheet draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='rca').first()
    
    if not draft:
        flash('Draft not found', 'error')
    else:
        db.session.delete(draft)
        db.session.commit()
        flash('Draft deleted successfully!', 'success')
    
    return redirect(url_for('drafts'))

@app.route('/load-generic-draft/<int:draft_id>')
@login_required
def load_generic_draft(draft_id):
    """Load generic worksheet draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='generic').first()
    
    if not draft:
        flash('Draft not found', 'error')
        return redirect(url_for('create_generic'))
    
    try:
        # Create form and populate with draft data
        form = GenericWorksheetForm()
        form_data = draft.form_data
        
        # Populate basic fields
        form.module_acronym.data = form_data.get('module_acronym', '')
        form.worksheet_title.data = form_data.get('worksheet_title', '')
        
        # Pass dynamic fields data to template for JavaScript reconstruction
        dynamic_fields_data = form_data.get('dynamic_fields', [])
        
        flash(f'Draft "{draft.title}" loaded successfully!', 'success')
        return render_template('create_generic.html', form=form, draft_id=draft.id, 
                             draft_data=form_data, dynamic_fields_data=dynamic_fields_data)
        
    except Exception as e:
        print(f"Error loading generic draft: {e}")
        flash(f'Error loading draft: {str(e)}', 'error')
        return redirect(url_for('create_generic'))

@app.route('/delete-generic-draft/<int:draft_id>', methods=['POST'])
@login_required
def delete_generic_draft(draft_id):
    """Delete generic worksheet draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='generic').first()
    
    if not draft:
        flash('Draft not found', 'error')
    else:
        db.session.delete(draft)
        db.session.commit()
        flash('Draft deleted successfully!', 'success')
    
    return redirect(url_for('drafts'))

# ===== HORIZONTAL LESSON PLAN DRAFT ROUTES =====

@app.route('/autosave-horizontal-lesson-plan-draft', methods=['POST'])
@login_required
def autosave_horizontal_lesson_plan_draft():
    """AJAX endpoint for autosaving horizontal lesson plan draft"""
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Prepare form data for JSON storage
        form_data = {
            'school_name': data.get('school_name', ''),
            'teacher_name': data.get('teacher_name', ''),
            'term': data.get('term', ''),
            'modules': data.get('modules', [])
        }
        
        # Check if this is updating an existing draft
        draft_id = data.get('draft_id')
        if draft_id:
            # Update existing draft
            draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='horizontal_lesson_plan').first()
            if draft:
                draft.form_data = form_data
                draft.updated_at = datetime.utcnow()
                # Update title if school name changed
                if form_data['school_name']:
                    draft.title = f"Horizontal Lesson Plan - {form_data['school_name']}"
            else:
                return jsonify({'success': False, 'error': 'Draft not found'})
        else:
            # Create new draft
            title = f"Horizontal Lesson Plan - {form_data['school_name']}" if form_data['school_name'] else "Horizontal Lesson Plan - Untitled"
            draft = FormDraft(
                user_id=current_user.id,
                form_type='horizontal_lesson_plan',
                title=title,
                form_data=form_data
            )
            db.session.add(draft)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'draft_id': draft.id,
            'message': 'Draft saved automatically',
            'timestamp': datetime.utcnow().strftime('%I:%M:%S %p')
        })
        
    except Exception as e:
        print(f"Error in autosave: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/load-horizontal-lesson-plan-draft/<int:draft_id>')
@login_required
def load_horizontal_lesson_plan_draft(draft_id):
    """Load horizontal lesson plan draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='horizontal_lesson_plan').first()
    
    if not draft:
        flash('Draft not found', 'error')
        return redirect(url_for('create_horizontal_lesson_plan'))
    
    try:
        # Create form and populate with draft data
        form = HorizontalLessonPlanForm()
        form_data = draft.form_data
        
        # Populate basic fields
        form.school_name.data = form_data.get('school_name', '')
        form.teacher_name.data = form_data.get('teacher_name', '')
        form.term.data = form_data.get('term', '')
        
        # Populate modules
        modules_data = form_data.get('modules', [])
        for i, module_data in enumerate(modules_data):
            if i < len(form.modules):
                form.modules[i].module_name.data = module_data.get('module_name', '')
                form.modules[i].enrichment_activities.data = module_data.get('enrichment_activities', '')
                
                # Populate sessions
                sessions_data = module_data.get('sessions', [])
                for j, session_data in enumerate(sessions_data):
                    if j < len(form.modules[i].sessions):
                        form.modules[i].sessions[j].focus.data = session_data.get('focus', '')
                        form.modules[i].sessions[j].objectives.data = session_data.get('objectives', '')
                        form.modules[i].sessions[j].materials.data = session_data.get('materials', '')
                        form.modules[i].sessions[j].teacher_prep.data = session_data.get('teacher_prep', '')
                        form.modules[i].sessions[j].assessments.data = session_data.get('assessments', '')
        
        flash(f'Draft "{draft.title}" loaded successfully!', 'success')
        return render_template('create_horizontal_lesson_plan.html', form=form, draft_id=draft.id)
        
    except Exception as e:
        print(f"Error loading horizontal lesson plan draft: {e}")
        flash(f'Error loading draft: {str(e)}', 'error')
        return redirect(url_for('create_horizontal_lesson_plan'))

@app.route('/delete-horizontal-lesson-plan-draft/<int:draft_id>', methods=['POST'])
@login_required
def delete_horizontal_lesson_plan_draft(draft_id):
    """Delete horizontal lesson plan draft"""
    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id, form_type='horizontal_lesson_plan').first()
    
    if not draft:
        flash('Draft not found', 'error')
    else:
        db.session.delete(draft)
        db.session.commit()
        flash('Draft deleted successfully!', 'success')
    
    return redirect(url_for('drafts'))

if __name__ == '__main__':
    # Create default admin if none exists (for development/initial setup)
    with app.app_context():
        try:
            # Check if any admin exists
            if not User.query.filter_by(is_admin=True).first():
                # Create default admin
                default_admin = User(
                    email='admin@nola.docs',
                    username='admin',
                    first_name='Admin',
                    last_name='User',
                    is_admin=True,
                    is_active=True
                )
                default_admin.set_password('admin123')  # Change this password!
                
                db.session.add(default_admin)
                db.session.commit()
                print("✅ Default admin created: admin@nola.docs / admin123")
        except Exception as e:
            print(f"Note: {e}")
    
    app.run(debug=True) 