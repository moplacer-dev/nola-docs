🚀 Streamlined Horizontal Lesson Plan Implementation Roadmap

  Perfect approach! Here's the complete implementation plan:

  Phase 1: Database Foundation

  1.1 Database Schema (PostgreSQL Compatible)

  # Add to models.py
  class LessonPlanModule(db.Model):
      """Streamlined lesson plan modules - pre-populated with all session 
  data"""
      __tablename__ = 'lesson_plan_modules'

      id = db.Column(db.Integer, primary_key=True)
      name = db.Column(db.String(200), nullable=False, index=True)  # 
  "Environmental Math (ENVM)"
      subject = db.Column(db.String(20), nullable=False, index=True)  # 
  "Math", "Science"
      grade_level = db.Column(db.Integer, nullable=True, index=True)  # 7, 
  8, or NULL for multi-grade
      enrichment_activities = db.Column(db.Text)  # Pre-populated enrichment
   text
      active = db.Column(db.Boolean, default=True)
      created_at = db.Column(db.DateTime, default=datetime.utcnow)

      # Relationships
      sessions = db.relationship('LessonPlanSession', backref='module',
  lazy='dynamic',
                                 cascade='all, delete-orphan',
  order_by='LessonPlanSession.session_number')

      def __repr__(self):
          return f'<LessonPlanModule {self.name}>'

  class LessonPlanSession(db.Model):
      """Pre-populated session data - 7 sessions per module"""
      __tablename__ = 'lesson_plan_sessions'

      id = db.Column(db.Integer, primary_key=True)
      module_id = db.Column(db.Integer,
  db.ForeignKey('lesson_plan_modules.id'), nullable=False)
      session_number = db.Column(db.Integer, nullable=False)  # 1-7
      focus = db.Column(db.Text)
      objectives = db.Column(db.Text)
      materials = db.Column(db.Text)
      teacher_prep = db.Column(db.Text)
      assessments = db.Column(db.Text)
      created_at = db.Column(db.DateTime, default=datetime.utcnow)

      __table_args__ = (
          db.UniqueConstraint('module_id', 'session_number',
  name='uq_module_session'),
          db.Index('ix_module_sessions', 'module_id', 'session_number'),
      )

      def __repr__(self):
          return f'<LessonPlanSession Module:{self.module_id} 
  Session:{self.session_number}>'

  1.2 Create Migration

  # Local command to run:
  flask db migrate -m "Add streamlined lesson plan models for 
  database-driven horizontal lesson plans"
  flask db upgrade

  Phase 2: Data Population Strategy

  2.1 Data Loading Script

  # create_lesson_plan_data.py - extract from existing PDFs or manual entry
  def load_lesson_plan_modules():
      """Load lesson plan modules and sessions from existing data sources"""
      # Extract from existing generated documents or create sample data
      # Pattern similar to correlation report data loading

      modules_data = [
          {
              'name': 'Environmental Math (ENVM)',
              'subject': 'Math',
              'grade_level': 8,
              'enrichment_activities': 'Students will explore real-world 
  environmental applications...',
              'sessions': [
                  {
                      'session_number': 1,
                      'focus': 'Introduction to Environmental Mathematics',
                      'objectives': 'Students will understand the connection
   between mathematics and environmental science...',
                      'materials': 'Calculators, environmental data sheets, 
  graphing paper...',
                      'teacher_prep': 'Review environmental math concepts, 
  prepare data sets...',
                      'assessments': 'Formative: Exit ticket with one 
  environmental math problem...'
                  },
                  # ... 6 more sessions
              ]
          },
          # Add more modules...
      ]

  Phase 3: Backend Implementation

  3.1 API Endpoint for Module Selection

  # Add to app.py
  @app.route('/api/lesson-plan-modules')
  @login_required
  def get_lesson_plan_modules_api():
      """API endpoint to get all lesson plan modules (similar to correlation
   report)"""
      try:
          modules = LessonPlanModule.query.filter_by(active=True).order_by(L
  essonPlanModule.name).all()
          module_data = []

          for module in modules:
              module_data.append({
                  'id': module.id,
                  'name': module.name,
                  'subject': module.subject,
                  'grade_level': module.grade_level,
                  'session_count': module.sessions.count()
              })

          return jsonify({'modules': module_data})
      except Exception as e:
          return jsonify({'error': str(e)}), 500

  3.2 Streamlined Form Class

  # Add to app.py
  class StreamlinedHorizontalLessonPlanForm(FlaskForm):
      # Basic Information (simplified)
      school_name = StringField('School Name',
                               validators=[DataRequired(), Length(min=1,
  max=200)],
                               render_kw={"placeholder": "e.g., Jefferson 
  Elementary School"})

      teacher_name = StringField('Teacher Name',
                                validators=[DataRequired(), Length(min=1,
  max=100)],
                                render_kw={"placeholder": "e.g., Ms. 
  Johnson"})

      # School year auto-populated to 2025-2026 (user can edit if needed)
      school_year = StringField('School Year',
                               validators=[DataRequired(), Length(min=1,
  max=20)],
                               default='2025-2026')

      # Module selection (similar to correlation report)
      selected_modules = SelectMultipleField('Selected Modules (up to 5)',
                                            validators=[DataRequired()],
                                            coerce=int)

      submit = SubmitField('Generate Horizontal Lesson Plan')

      def validate_selected_modules(self, field):
          """Ensure max 5 modules selected"""
          if len(field.data) > 5:
              raise ValidationError('Please select no more than 5 modules.')

  3.3 Main Route Handler

  # Add to app.py
  @app.route('/create-horizontal-lesson-plan-streamlined', methods=['GET', 
  'POST'])
  @login_required
  def create_streamlined_horizontal_lesson_plan():
      """Streamlined horizontal lesson plan creation - database driven"""
      form = StreamlinedHorizontalLessonPlanForm()

      if request.method == 'POST':
          # Manual form handling (like correlation report pattern)
          school_name = request.form.get('school_name')
          teacher_name = request.form.get('teacher_name')
          school_year = request.form.get('school_year', '2025-2026')
          selected_modules = request.form.getlist('selected_modules')

          # Basic validation
          if not school_name or not teacher_name or not selected_modules:
              flash('Please fill in all fields and select at least one 
  module.', 'error')
          elif len(selected_modules) > 5:
              flash('Please select no more than 5 modules.', 'error')
          else:
              try:
                  # Generate the document using database-driven approach
                  doc_path = generate_streamlined_horizontal_lesson_plan(
                      school_name=school_name,
                      teacher_name=teacher_name,
                      school_year=school_year,
                      module_ids=[int(mid) for mid in selected_modules]
                  )

                  # Save document record
                  doc_record = GeneratedDocument(
                      user_id=current_user.id,
                      document_type='horizontal_lesson_plan_streamlined',
                      filename=os.path.basename(doc_path),
                      file_path=doc_path,
                      file_size=os.path.getsize(doc_path)
                  )
                  db.session.add(doc_record)
                  db.session.commit()

                  flash('Streamlined Horizontal Lesson Plan generated 
  successfully!', 'success')
                  return redirect(url_for('my_documents'))

              except Exception as e:
                  flash(f'Error generating document: {str(e)}', 'error')

      return
  render_template('create_horizontal_lesson_plan_streamlined.html',
  form=form)

  Phase 4: Document Generation Logic

  4.1 Table Generation Function

  # Add to app.py
  def generate_streamlined_horizontal_lesson_plan(school_name, teacher_name,
   school_year, module_ids):
      """Generate horizontal lesson plan document from database-driven 
  modules"""

      # Load selected modules with sessions
      modules =
  LessonPlanModule.query.filter(LessonPlanModule.id.in_(module_ids)).all()

      if not modules:
          raise ValueError("No valid modules found for selected IDs")

      # Create context for template (similar to correlation report)
      context = {
          'school_name': school_name,
          'teacher_name': teacher_name,
          'school_year': school_year,
          'modules': []
      }

      # Build modules data with sessions
      for module in modules:
          sessions =
  module.sessions.order_by(LessonPlanSession.session_number).all()

          module_data = {
              'name': module.name,
              'enrichment_activities': module.enrichment_activities,
              'sessions': [
                  {
                      'session_number': session.session_number,
                      'focus': session.focus,
                      'objectives': session.objectives,
                      'materials': session.materials,
                      'teacher_prep': session.teacher_prep,
                      'assessments': session.assessments
                  }
                  for session in sessions
              ]
          }
          context['modules'].append(module_data)

      # Generate table using similar approach to correlation report
      hlp_table = create_horizontal_lesson_plan_table(context)
      context['hlp'] = {'table': hlp_table}

      # Use docx template generation
      template_path =
  'templates/docx_templates/horizontal_lesson_plan_streamlined_master.docx'
      timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
      filename = f"Horizontal_Lesson_Plan_{school_name.replace(' ', 
  '_')}_{timestamp}.docx"
      output_path = os.path.join('generated_docs', filename)

      doc = DocxTemplate(template_path)
      doc.render(context)
      doc.save(output_path)

      return output_path

  Phase 5: Integration & Testing

  5.1 Add to Navigation

  <!-- Add to templates/index.html -->
  <a href="/create-horizontal-lesson-plan-streamlined" 
     class="bg-purple-600 text-white px-4 py-3 rounded-lg 
  hover:bg-purple-700 transition-colors text-center">
      🚀 Horizontal Lesson Plan (New)
  </a>

  5.2 Local Testing Checklist

  - Migration runs successfully
  - Data loads correctly
  - API endpoint returns modules
  - Form validation works
  - Document generation works
  - Template renders correctly

  Phase 6: Production Deployment

  6.1 GitHub & Render Deployment

  # Deployment sequence:
  1. Push to GitHub
  2. Render auto-deploys
  3. Run migration: flask db upgrade
  4. Load data: python create_lesson_plan_data.py
  5. Test production functionality

  6.2 Production Data Strategy

  - Create production-ready data loading script
  - Ensure data is consistent and high-quality
  - Set up data backup/restore procedures

  Key Benefits of This Approach

  ✅ User Experience: 2 fields + module selection vs 235 manual fields✅
  Consistency: All content comes from curated database✅ Scalability: Easy
  to add new modules without code changes✅ Maintainability: Single source
  of truth for all lesson content✅ Performance: No complex form processing,
   just database queries✅ Proven Pattern: Reuses successful correlation
  report architecture
