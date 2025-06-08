# NOLA Docs - Document Generator

A Flask-based web application for generating professional educational documents with locked-down formatting and user-controlled data input.

## 🎯 Project Overview

**Goal**: Build a form-based web app that lets users select document templates, fill out relevant forms, and generate perfectly formatted documents (DOCX/PDF) with strict formatting control.

**Key Principles**:
- ✅ Locked styling — no user formatting hacks
- ✅ Form-controlled logic — users input data, not format
- ✅ Server-side formatting control
- ✅ Automated output — perfect documents every time
- ✅ Scalable template system

## 🛠 Tech Stack

- **Backend**: Flask, WTForms, Flask-Login, SQLAlchemy
- **Frontend**: Tailwind CSS, Jinja2 Templates
- **Document Generation**: python-docx-template (docxtpl)
- **Authentication**: Flask-Login (planned)
- **Database**: SQLite (development)

## 📋 Current Status

### ✅ Completed Features
- [x] Basic Flask app structure
- [x] **Vocabulary Worksheet template** with master template protection
- [x] **PBA (Performance Based Assessment) Worksheet template** ⭐ **NEW**
- [x] **Post Test Worksheet template** with multiple choice questions ⭐ **NEW**
- [x] **Pre Test Worksheet template** (identical to post test) ⭐ **NEW**
- [x] **Generic Worksheet template** with dynamic form builder
- [x] **Family Briefing template** 👨‍👩‍👧‍👦 ⭐ **NEW**
- [x] **RCA (Research, Challenge & Application) Worksheet template** 🔬 ⭐ **NEW**
- [x] Form validation with WTForms
- [x] DOCX document generation with corruption protection
- [x] Clean Tailwind CSS styling
- [x] Dynamic form fields (vocabulary terms, assessments, multiple choice questions)
- [x] Error handling and debugging
- [x] **Master template protection system** 🛡️
- [x] **Module acronym-based file naming** 📁
- [x] **Template cleanup and organization** 🧹 **NEW**
- [x] **Comprehensive homepage with 8 worksheet types** 🏠 **NEW**
- [x] **Enhanced template integrity verification** 🔐 **NEW**
- [x] **Filesystem-level template protection** 🔒 **NEW**
- [x] **Automated backup system** 💾 **NEW**
- [x] **Module Guide** 📖
- [x] **Module Answer Key** 🔑

### 🔄 In Progress
- [x] Additional document templates ✅ **COMPLETED**
- [x] User authentication system ✅ **COMPLETED**
- [x] Admin dashboard ✅ **COMPLETED**
- [ ] Template management interface
- [x] Image upload support for Generic Worksheet ✅ **COMPLETED**

### ❌ Removed Features
- [x] ~~Notes Worksheet template~~ (Removed - only field required was in the header, but there can be no header/footer fields with python_docx_template)
- [x] ~~create_vocabulary_worksheet.html~~ (Removed - unused alternative implementation)
- [x] ~~create_notes.html~~ (Removed - no longer referenced in app.py)

## 🆕 Latest Updates (June 2, 2025)

### 📝 **Enhanced Module Answer Key with Nested Worksheet Structure**
- **Added Worksheet Grouping**: Restructured Module Answer Key form to organize worksheet answer keys in logical containers
- **Visual Organization**: Each worksheet now has its own titled container with dedicated "Add Field" functionality
- **Improved User Experience**: Clear hierarchy prevents confusion about which fields belong to which worksheet
- **Collapsible Interface**: Worksheet Answer Keys section now uses accordion UI like other sections
- **Flexible Structure**: Users can create multiple worksheet containers, each with custom titles and independent content
- **Better Form Flow**: 
  - Click "Add Worksheet Answer Key" → Creates new worksheet container
  - Each worksheet has its own "Add Field" button for section headers, questions, etc.
  - Visual separation between different worksheets
- **Same Document Output**: Final document format unchanged - improvement is purely organizational

**New Workflow Structure:**
```
📝 Module Answer Key
├── 📄 Worksheet Answer Key #1
│   ├── 📝 Title: "Chapter 3 Review"
│   ├── 📝 Section Header: "Basic Concepts" 
│   ├── ✅ Multiple Choice: "What is...?"
│   └── [Add Field] ← Independent field management
├── 📄 Worksheet Answer Key #2
│   ├── 📝 Title: "Lab Results"
│   ├── 📋 Instructions: "Complete all problems..."
│   └── [Add Field] ← Independent field management
└── 📄 [Add Worksheet Answer Key] ← Creates new containers
```

## 🆕 Previous Updates (May 31, 2025)

### 🖼️ **Image Upload for Generic Worksheets**
- **Added Full Support**: Generic worksheets can now include images alongside text content
- **Flexible Image Options**: Images displayed at optimal size with optional captions
- **Subdocument Implementation**: Uses docxtpl subdocuments to properly mix text and images
- **Automatic Cleanup**: Temporary image files are cleaned up after document generation
- **Security**: Server-side processing with file type validation (JPG, PNG, GIF only)
- **New Dependencies**: Added werkzeug for secure filename handling

### 📚 **New Family Briefing Document Template**
- **Added Full Support**: Complete form, route, and document generation for Family Briefing documents
- **Comprehensive Fields**: Module name, introduction, 4 learning objectives, 7 activities, 21 terms, and 3 key concepts with explanations
- **Simple Variable Structure**: Uses straightforward variable names for easy template mapping
- **Parent Communication**: Designed to communicate module information to parents and caregivers

### 🔧 **Pre/Post Test Template Improvements**
- **Array-Based Choice Structure**: Updated to use `question.choice[0]` through `question.choice[3]` format
- **Consistent Data Model**: Both pre-test and post-test now use identical array structures
- **Template Compatibility**: Backend converts form data to array format for cleaner template syntax
- **Enhanced Flexibility**: Easier to modify templates with standardized array indexing

### 🏠 **Homepage Enhancement**
- **Added Family Briefing Button**: New indigo-colored button linking to `/create-familybriefing`
- **7 Document Types**: Homepage now offers access to all available document generators

## 🆕 Previous Updates (May 28, 2025)

### 🛡️ **Enhanced Master Template Protection System**
- **Read-Only Protection**: All master templates are now filesystem-protected against accidental modification
- **Integrity Verification**: Real-time monitoring of master template modification times during processing
- **Timestamped Backups**: Automatic creation of dated backups before any operations
- **Enhanced Logging**: Detailed protection status and verification messages
- **Triple-Layer Protection**: Master → Working → Temporary file processing chain

### 🔧 **Jinja2 Template Syntax Improvements**
Based on `python-docx-template` documentation, resolved common issues:
- **Whitespace Control**: Proper use of `{%-` and `-%}` for eliminating extra spacing
- **Letter Restart Logic**: Dynamic letter assignment for multiple choice questions
- **Proper Delimiter Spacing**: Ensured spaces around all Jinja2 delimiters
- **Line Isolation**: `{%-` and `-%}` tags must be on separate lines

### 📊 **Template Status Verification**
Created comprehensive template verification system:
- **Size & Hash Verification**: SHA256 checksums for integrity verification
- **Modification Tracking**: Timestamp monitoring for unauthorized changes
- **Existence Validation**: Automated checking of all required master templates
- **Protection Status**: Real-time verification of read-only permissions

## 🎨 Available Worksheet Templates

### 1. **Vocabulary Worksheet** 📚
- **Purpose**: Generate vocabulary term worksheets
- **Fields**: Module acronym, vocabulary terms (up to 25)
- **File Format**: `Vocabulary WS_{Module}_Recaptured.docx`

### 2. **PBA (Performance Based Assessment) Worksheet** 🎯
- **Purpose**: Create performance-based assessment documents
- **Fields**: Module acronym, section header, 4 assessments
- **File Format**: `PBA_WS_{Module}_Recaptured.docx`

### 3. **Post Test Worksheet** ✅
- **Purpose**: Generate multiple choice post-tests
- **Fields**: Module acronym, multiple choice questions (up to 15)
- **File Format**: `Post_Test_WS_{Module}_Recaptured.docx`

### 4. **Pre Test Worksheet** 📝
- **Purpose**: Generate multiple choice pre-tests
- **Fields**: Module acronym, multiple choice questions (up to 15)
- **File Format**: `Pre_Test_WS_{Module}_Recaptured.docx`

### 5. **Generic Worksheet** ⚡
- **Purpose**: Dynamic worksheet builder with multiple field types
- **Fields**: Module acronym, worksheet title, unlimited dynamic fields
- **File Format**: `{Title} WS_{Module}_Recaptured.docx`

### 6. **Family Briefing** 👨‍👩‍👧‍👦
- **Purpose**: Communicate module information to parents and caregivers
- **Fields**: Module name, introduction, 4 learning objectives, 7 activities, 21 terms, 3 key concepts
- **File Format**: `{Module_Name}_Family_Briefing_Recaptured.docx`

### 7. **RCA (Research, Challenge & Application) Worksheet** 🔬
- **Purpose**: Create structured worksheets with research, challenge, and application questions
- **Fields**: Module acronym, session number, 3 multiple choice questions (1 Research, 1 Challenge, 1 Application)
- **File Format**: `RCA{SessionNumber}_WS_{Module}_Recaptured.docx`

### 8. **Module Guide** 📖
- **Purpose**: Comprehensive teacher guide with session notes, vocabulary, careers, and resources
- **Fields**: Module acronym, teacher tips overview, standards (6-10), vocabulary (25-30), careers (14-20), 7 detailed session notes, additional resources
- **File Format**: `{Module}_Module_Guide_Recaptured.docx`

### 9. **Module Answer Key** 🔑
- **Purpose**: Comprehensive answer key for all module assessments, vocabulary, and activities
- **Fields**: 
  - Pre-test questions (10 multiple choice with answers)
  - RCA sessions 2-5 (each with 3 questions: Research, Challenge, Application)
  - Post-test questions (10 multiple choice with answers)
  - Performance Based Assessments (4 sessions with activities and assessment questions)
  - Vocabulary (25-30 terms with definitions)
  - Student Portfolio Checklist (6+ products with session numbers)
  - Enrichment Activities (dynamic content builder)
  - **Worksheet Answer Keys** (🆕 **nested worksheet containers** - each worksheet can have its own title and independent dynamic content fields)
- **New Features**: 
  - 🆕 **Worksheet Grouping**: Organize answer keys in logical worksheet containers
  - 🆕 **Visual Hierarchy**: Clear separation between different worksheets with titled containers
  - 🆕 **Independent Field Management**: Each worksheet has its own "Add Field" functionality
  - 🆕 **Collapsible Interface**: Accordion-style UI for better organization
- **File Format**: `Module Answer Key {Module}_v2.0.docx`

## 🏠 Homepage Navigation

The homepage now features **10 worksheet creation buttons**:

1. **Learn More** (Blue) - About page
2. **Create Vocabulary Worksheet** (Green) - `/create-vocabulary`
3. **Create PBA Worksheet** (Purple) - `/create-pba`
4. **Create Pre Test Worksheet** (Yellow) - `/create-pretest`
5. **Create Post Test Worksheet** (Red) - `/create-posttest`
6. **Create Generic Worksheet** (Orange) - `/create-generic`
7. **Create Family Briefing** (Indigo) - `/create-familybriefing`
8. **Create RCA Worksheet** (Teal) - `/create-rca`
9. **Create Module Guide** (Cyan) - `/create-moduleGuide`
10. **Create Module Answer Key** (Pink) - `/create-moduleAnswerKey`

## 📝 DOCX Template Placeholder Guide

### Jinja2 Syntax for DOCX Templates (Updated Guide)

**Variables (Single Values):**
```
{{ variable_name }}           # Simple text replacement (note spaces!)
{{ module_acronym }}          # Module code (e.g., APHY, CHEM)
{{ section_header }}          # User-entered section title
```

**Loops (For Lists) - Enhanced Whitespace Control:**
```
{%- for item in items -%}

{{ loop.index }}. {{ item.field_name }}

{%- endfor -%}
```

**Multiple Choice with Dynamic Lettering:**
```
{%- for question in questions -%}

{{ loop.index }}. {{ question.question }}

{%- set choices = [question.choice_a, question.choice_b, question.choice_c, question.choice_d] -%}
{%- set letters = ['A', 'B', 'C', 'D'] -%}
{%- for choice in choices -%}
{%- if choice -%}
{{ letters[loop.index0] }}. {{ choice }}
{%- endif -%}
{%- endfor -%}

{%- endfor -%}
```

**Critical Jinja2 Rules for docxtpl:**
- ✅ **Always use spaces**: `{{ variable }}` not `{{variable}}`
- ✅ **Isolate whitespace control**: `{%-` and `-%}` must be on separate lines
- ✅ **Use `loop.index0`** for 0-based array indexing (A=0, B=1, C=2, D=3)
- ❌ **Don't use** `{%tr %}` unless you're inside a Word table
- ❌ **Avoid placeholders** in headers/footers (causes corruption)
- ✅ **Keep formatting simple** to prevent Word corruption

### Template Examples by Type

#### **Vocabulary Worksheet:**
```
{{ module_acronym }} - Vocabulary Worksheet

{%- for word in words -%}

{{ loop.index }}. {{ word.word }}

Definition: ________________________________

{%- endfor -%}
```

#### **PBA Worksheet:**
```
{{ section_header }}

{%- for assessment in assessments -%}

{{ loop.index }}. {{ assessment.assessment }}

Performance Criteria: _________________________

{%- endfor -%}
```

#### **Pre/Post Test Worksheets (Updated Array Syntax):**
```
{{ module_acronym }}
Pre-Test Worksheet (or Post-Test Worksheet)

{%p for question in questions %}
{{ loop.index }}. {{ question.question }}
    A. {{ question.choice[0] }}
    B. {{ question.choice[1] }}
    C. {{ question.choice[2] }}
    D. {{ question.choice[3] }}
{%p endfor %}
```

#### **Family Briefing:**
```
{{ module_name }} - Family Briefing

During this module, your child will {{ introsentence }}

Learning Objectives:
1. {{ learningobjective1 }}
2. {{ learningobjective2 }}
3. {{ learningobjective3 }}
4. {{ learningobjective4 }}

Session Activities:
• {{ activityname1 }}
• {{ activityname2 }}
... (up to activityname7)

Key Terminology: {{ term1 }}, {{ term2 }}, {{ term3 }}... (up to term21)

Key Concepts:
{{ keyconcept1 }}: {{ keyconcept1_explanation }}
{{ keyconcept2 }}: {{ keyconcept2_explanation }}
{{ keyconcept3 }}: {{ keyconcept3_explanation }}
```

#### **RCA (Research, Challenge & Application) Worksheet:**
```
{%p for question in questions %}
{% if loop.index == 1 %}
{{ loop.index }}. Research: {{ question.question }}
{% elif loop.index == 2 %}
{{ loop.index }}. Challenge: {{ question.question }}
{% elif loop.index == 3 %}
{{ loop.index }}. Application: {{ question.question }}
{% endif %}
    A. {{ question.choice[0] }}
    B. {{ question.choice[1] }}
    C. {{ question.choice[2] }}
    D. {{ question.choice[3] }}
{%p endfor %}
```

#### **Module Activity Sheet:**
```
{{ module_acronym }} - Module Activity Sheet

Session 1: Pre-Test
{% if session1.is_pba %}PBA: {% endif %}{{ session1.activity }}
Assessment Score: {% if session1.has_pba %}{% else %}N/A{% endif %}

Session 2: RCA
{% if session2.is_pba %}PBA: {% endif %}{{ session2.activity }}
Assessment Score: {% if session2.has_pba %}{% else %}N/A{% endif %}

... (repeats for all 7 sessions)
```

## 📁 File Naming Convention

Generated documents follow a consistent naming pattern:

**Current Formats**:
- **Vocabulary**: `Vocabulary WS_{Module}_Recaptured.docx`
- **PBA**: `PBA_WS_{Module}_Recaptured.docx`
- **Pre Test**: `Pre_Test_WS_{Module}_Recaptured.docx`
- **Post Test**: `Post_Test_WS_{Module}_Recaptured.docx`
- **Generic**: `{Title} WS_{Module}_Recaptured.docx`
- **Family Briefing**: `{Module_Name}_Family_Briefing_Recaptured.docx`
- **RCA**: `RCA{SessionNumber}_WS_{Module}_Recaptured.docx`
- **Module Guide**: `{Module}_Module_Guide_Recaptured.docx`
- **Module Answer Key**: `Module Answer Key {Module}_v2.0.docx`
- **Module Activity Sheet**: `Module Activity Sheet {Module}_v2.0.docx`

**Examples**:
- `Vocabulary WS_APHY_Recaptured.docx`
- `PBA_WS_CHEM_Recaptured.docx`
- `Pre_Test_WS_BIOE_Recaptured.docx`
- `Heat_Content WS_APHY_Recaptured.docx`
- `Introduction_to_Physics_Family_Briefing_Recaptured.docx`
- `RCA2_WS_SOUL_Recaptured.docx`
- `APHY_Module_Guide_Recaptured.docx`
- `Module Answer Key APHY_v2.0.docx`
- `Module Activity Sheet CHEM_v2.0.docx`

**Benefits**:
- ✅ **Descriptive prefixes** for easy identification
- ✅ **Module acronyms** for quick sorting (APHY, CHEM, BIOE)
- ✅ **"Recaptured" suffix** for version control
- ✅ **No spaces** in filenames (replaced with underscores)
- ✅ **Consistent "WS" identifier** across all templates

## 🔧 Development Setup

### Prerequisites
- Python 3.9+
- Virtual environment

### Installation
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Project Structure
```
nola.docs/
├── app.py                              # Main Flask application
├── requirements.txt                    # Python dependencies
├── templates/
│   ├── index.html                      # Homepage with 9 worksheet buttons
│   ├── about.html                      # About page
│   ├── create_vocabulary.html          # Vocabulary worksheet form
│   ├── create_pba.html                 # PBA worksheet form
│   ├── create_pretest.html             # Pre test worksheet form
│   ├── create_posttest.html            # Post test worksheet form
│   ├── create_generic.html             # Generic worksheet form
│   ├── create_familybriefing.html      # Family briefing form
│   ├── create_rca.html                 # RCA worksheet form
│   ├── create_moduleGuide.html         # Module Guide form
│   ├── create_moduleAnswerKey.html     # Module Answer Key form
│   ├── create_moduleActivitySheet.html # Module Activity Sheet form
│   └── docx_templates/
│       ├── vocabulary_worksheet_master.docx   # 🔒 Protected vocabulary template
│       ├── pba_worksheet_master.docx          # 🔒 Protected PBA template
│       ├── pre_test_worksheet_master.docx     # 🔒 Protected pre test template
│       ├── post_test_worksheet_master.docx    # 🔒 Protected post test template
│       ├── generic_worksheet_master.docx      # 🔒 Protected generic template
│       ├── family_briefing_master.docx        # 🔒 Protected family briefing template
│       ├── rca_worksheet_master.docx          # 🔒 Protected RCA template
│       ├── module_guide_master.docx           # 🔒 Protected Module Guide template
│       ├── module_answer_key_master.docx      # 🔒 Protected Module Answer Key template
│       ├── module_activity_sheet_master.docx  # 🔒 Protected Module Activity Sheet template
│       └── 1. backups/                # 💾 Timestamped template backups
├── generated_docs/                     # Output directory for generated documents
├── temp_uploads/                      # Temporary storage for uploaded images (auto-created)
└── venv/                              # Virtual environment
```

## 🐛 Common Issues & Solutions

### DOCX Template Formatting Issues

**Problem**: Extra letters (E, F, G, H) appearing after multiple choice options, or placeholders not replaced.

**Common Causes & Solutions**:

1. **Extra/Malformed Placeholders**
   - ❌ Check for: `{{question.choice_e}}` or similar extra placeholders
   - ❌ Broken placeholders split across formatting: `{{question.` and `choice_a}}`
   - ✅ **Solution**: Use only A, B, C, D choices and ensure placeholders are complete

2. **Word Formatting Issues**
   - ❌ Hidden formatting characters between placeholders
   - ❌ Placeholders split across different text runs in Word
   - ✅ **Solution**: Retype placeholders manually, avoid copy/paste

3. **Incorrect Loop Structure**
   - ❌ Using `{%tr %}` outside of tables
   - ❌ Missing `{% endfor %}` tags
   - ✅ **Solution**: Use simple `{% for %}...{% endfor %}` for lists

4. **Whitespace Issues (NEW)**
   - ❌ Missing whitespace control causing extra spacing between questions
   - ❌ Incorrect placement of `{%-` and `-%}` tags
   - ✅ **Solution**: Use proper whitespace control syntax with tags on separate lines

**Quick Debugging Steps**:
1. Test with minimal template (just basic placeholders)
2. Compare working templates (vocabulary/PBA) with problematic ones
3. Check Flask console for context data being passed
4. Recreate template from scratch if needed
5. **NEW**: Verify master template integrity with enhanced logging

### CSRF Token Errors with FieldList
**Problem**: `'dict' object has no attribute 'word'` or CSRF token missing errors.

**Solution**: Add `csrf = False` to nested form classes:
```python
class NestedForm(FlaskForm):
    class Meta:
        csrf = False
```

### Master Template Not Found or Corrupted
**Problem**: `FileNotFoundError: Master DOCX template not found` or template corruption.

**Solution**: The enhanced protection system now prevents this:
- ✅ **Read-only protection** prevents accidental modification
- ✅ **Automatic backups** available in `1. backups/` directory
- ✅ **Integrity verification** alerts you to any changes
- ✅ **Enhanced logging** shows exactly what's happening

## 🛡️ Enhanced Master Template Protection System

### Multi-Layer Protection Architecture

**Layer 1: Filesystem Protection**
- Master templates are set to read-only at the OS level
- Prevents accidental modification by any application
- Must be explicitly unlocked for editing

**Layer 2: Processing Isolation**
- Master → Working Copy → Temporary File → Processing
- Original masters never touched during document generation
- Automatic cleanup of temporary files

**Layer 3: Integrity Verification**
- SHA256 checksums for corruption detection
- Modification timestamp monitoring
- Real-time verification during processing

### How It Works
1. **Master Templates** (`*_master.docx`) - 🔒 Read-only protected originals
2. **Working Copies** - Fresh copies created from masters for each generation
3. **Temporary Files** - Processing happens on temporary copies
4. **Auto-cleanup** - Temporary files removed after generation
5. **Integrity Checks** - Continuous monitoring for unauthorized changes

### File Structure with Protection Status
```
templates/docx_templates/
├── vocabulary_worksheet_master.docx    # 🔒 Protected master
├── pba_worksheet_master.docx           # 🔒 Protected master
├── pre_test_worksheet_master.docx      # 🔒 Protected master
├── post_test_worksheet_master.docx     # 🔒 Protected master
├── generic_worksheet_master.docx       # 🔒 Protected master
├── family_briefing_master.docx         # 🔒 Protected master
├── vocabulary_worksheet.docx           # Working copy (auto-generated)
├── pba_worksheet.docx                  # Working copy (auto-generated)
├── pre_test_worksheet.docx             # Working copy (auto-generated)
├── post_test_worksheet.docx            # Working copy (auto-generated)
├── family_briefing.docx                # Working copy (auto-generated)
└── 1. backups/                        # 💾 Timestamped backups
    ├── pre_test_worksheet_master_backup_20250528_203049.docx
    ├── post_test_worksheet_master_backup_20250528_203049.docx
    ├── vocabulary_worksheet_master_backup_20250528_203049.docx
    ├── pba_worksheet_master_backup_20250528_203049.docx
    └── generic_worksheet_master_backup_20250528_203049.docx
```

### Protection Verification Logs
The system now provides detailed logging:
```
Master template size: 9231371 bytes, modified: 2025-05-28 20:05:21
✓ Successfully copied master to working template
✓ Created temporary template at: /tmp/tmpXXXXXX.docx
Loading DocxTemplate from temporary file: /tmp/tmpXXXXXX.docx
✓ Master template integrity verified - no accidental changes
✓ Cleaned up temporary file: /tmp/tmpXXXXXX.docx
```

## 🎯 Generic Worksheet Template

### Dynamic Form Builder
The Generic Worksheet template features a powerful dynamic form builder that allows users to create custom worksheets by adding different field types in any order:

**Available Field Types:**
- **📋 Section Header** - Bold headers to organize content
- **📝 Section Instructions** - Italicized instruction text
- **☑️ Multiple Choice** - Questions with up to 4 answer choices (A-D)
- **✏️ Fill in Blank** - Questions with blank lines for answers
- **📄 Text Entry** - Questions with multiple lines for longer responses
- **🖼️ Image** - Upload and embed images with captions ⭐ **NEW**

### Image Upload Feature ⭐ **NEW**

The Generic Worksheet now supports image uploads, allowing you to embed pictures directly into your worksheets:

**Features:**
- Upload images in JPG, PNG, or GIF format (max 16MB)
- Add optional captions below images
- Images are automatically embedded in the correct position

**Technical Implementation:**
- Uses **docxtpl subdocuments** to properly mix text and images
- Images are temporarily saved during processing then cleaned up
- Utilizes python-docx's `add_picture()` method for proper embedding
- Subdocument approach ensures compatibility with Word's formatting

**How It Works:**
1. Click "Add Field" and select "🖼️ Image"
2. Choose your image file
3. Optionally add a caption
4. The image will be embedded inline with your other content

**Important Notes:**
- Images are processed server-side for security
- Temporary image files are automatically cleaned up after generation
- The subdocument approach allows seamless mixing of text, questions, and images
- All Word styles are preserved when using subdocuments

### Technical Details: Subdocuments in docxtpl

When mixing complex content types (text, images, formatted paragraphs), docxtpl uses **subdocuments**:

```python
# Create a subdocument
subdoc = doc.new_subdoc()

# Add various content types
p = subdoc.add_paragraph("Section Header")
p.style = 'Heading 3'

# Add image
p = subdoc.add_paragraph()
run = p.add_run()
run.add_picture(image_path, width=Inches(4))

# Pass subdoc to template
context = {'dynamic_content': subdoc}
```

**Why Subdocuments?**
- **Simple variables** (`{{ var }}`) → For plain text replacement
- **RichText** (`{{r var }}`) → For text with character formatting (bold, italic, etc.)
- **Subdocuments** (`{{ var }}`) → For complex content including paragraphs, images, and mixed formatting

The Generic Worksheet uses subdocuments because it needs to:
- Mix different content types (headers, text, images)
- Apply paragraph-level styles (Heading 3, Normal, Caption)
- Embed images inline with other content
- Maintain proper Word document structure

This approach ensures maximum flexibility while maintaining document integrity and proper formatting.

## 🚀 Next Steps & Roadmap

### Immediate Next Steps (Priority Order)

1. **Template Content Optimization** 🔧
   - Apply enhanced Jinja2 syntax to all existing templates
   - Test whitespace control implementation
   - Verify dynamic letter assignment for multiple choice

2. **Add More Document Templates** 📝
   - Student Handout template
   - Student Assessment templates
   - SMN (Subject Matter Notes) handout template
   - Module Guide template
   - RCA worksheet template

3. **Improve User Experience** 🎨
   - Better form styling and layout
   - Progress indicators
   - Form auto-save
   - Live preview (stretch goal)

4. **Add File Download** 📥
   - Direct file download instead of just success message
   - File management (view/delete generated docs)

5. **User Authentication** 🔐
   - Flask-Login implementation
   - User roles (admin/user)
   - User-specific document history

### Future Enhancements

6. **Template Management System** 🗂
   - Upload new templates via web interface
   - Template versioning
   - Template categories

7. **Advanced Features** ⭐
   - PDF generation option
   - Bulk document generation
   - Document templates with images
   - Custom branding per user

## 🔍 Debugging Tips

### Enable Debug Mode
The app runs with `debug=True` by default, which provides:
- Automatic reloading on code changes
- Detailed error messages
- Interactive debugger in browser

### Enhanced Protection Logging
The system now provides comprehensive logging:
- Master template verification status
- File operation success/failure
- Integrity check results
- Cleanup confirmation

### Check Generated Documents
Generated documents are saved in `generated_docs/` directory with descriptive filenames.

### Form Validation Debugging
Add these debug prints to your route handlers:
```python
if request.method == 'POST':
    print(f"Form data: {request.form}")
    print(f"Form valid: {form.validate_on_submit()}")
    if form.errors:
        print(f"Form errors: {form.errors}")
```

### Context Data Debugging
Check what data is being passed to templates:
```python
print(f"Context data: {context}")
print(f"Number of items: {len(data_list)}")
```

### Template Integrity Verification
Monitor protection status:
```python
# Enhanced logging shows:
# - Master template size and modification time
# - Copy operation success
# - Temporary file creation
# - Integrity verification results
# - Cleanup confirmation
```

## 📚 Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [WTForms Documentation](https://wtforms.readthedocs.io/)
- [python-docx-template Documentation](https://docxtpl.readthedocs.io/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Jinja2 Template Documentation](https://jinja.palletsprojects.com/)

---

**Last Updated**: December 10, 2024  
**Version**: 6.0 - Module Activity Sheet 📊  
**Major Updates**: Added Module Activity Sheet template with PBA tracking for 7 sessions, now supporting 11 document types total