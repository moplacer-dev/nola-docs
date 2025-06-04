# Phase 2 Technical Reference Guide
*NOLA Docs Save/Load Implementation Patterns*

## 📚 Overview

This document captures proven technical patterns, troubleshooting solutions, and implementation details for NOLA Docs Phase 2 save/load functionality. Use this as a reference when extending save/load to additional document types.

---

## 🎯 Phase 2A: Vocabulary Worksheets (COMPLETED ✅)

### Implementation Summary
- **Status:** Live in Production
- **Deployment:** December 2024  
- **Features:** Complete save/load/download workflow
- **User Workflow:** Create → Save Draft → Load Draft → Generate → Download

---

## 🔧 Core Technical Patterns

### Pattern 1: Unified Form Route Architecture

**❌ WRONG APPROACH (Causes "Method Not Allowed" errors):**
```python
# DON'T DO THIS - Separate routes cause conflicts
@app.route('/create-vocabulary', methods=['GET', 'POST'])
def create_vocabulary():
    # Only handles generation
    
@app.route('/save-vocabulary-draft', methods=['POST'])  # ❌ CONFLICT
def save_vocabulary_draft():
    # Separate save route
```

**✅ CORRECT APPROACH (Unified handling):**
```python
@app.route('/create-vocabulary', methods=['GET', 'POST'])
@login_required
def create_vocabulary():
    form = VocabularyWorksheetForm()
    
    if request.method == 'POST':
        # KEY: Detect which action was requested
        action = request.form.get('action', 'generate')
        
        if form.validate_on_submit():
            if action == 'save_draft':
                # Handle draft saving
                form_data = {
                    'module_acronym': form.module_acronym.data,
                    'words': [{'word': word.word.data} for word in form.words if word.word.data]
                }
                
                draft_id = request.form.get('draft_id')
                if draft_id:
                    # Update existing draft
                    draft = FormDraft.query.filter_by(id=draft_id, user_id=current_user.id).first()
                    draft.form_data = form_data
                    draft.updated_at = datetime.utcnow()
                else:
                    # Create new draft
                    title = f"Vocabulary Worksheet - {form.module_acronym.data}"
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
                
            else:  # action == 'generate' or default
                # Handle document generation
                doc_path, filename = generate_vocabulary_worksheet(form)
                
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
                
                return redirect(url_for('download_document', doc_id=doc_record.id))
        else:
            if action == 'save_draft':
                flash('Please fix form errors before saving', 'error')
    
    return render_template('create_vocabulary.html', form=form)
```

**Key Benefits:**
- ✅ Eliminates routing conflicts
- ✅ Single source of truth for form processing
- ✅ Clear action-based logic flow
- ✅ Easier to maintain and debug

### Pattern 2: Template Form Structure

**✅ CORRECT TEMPLATE PATTERN:**
```html
<form method="POST" id="vocab-form">
    {{ form.hidden_tag() }}
    
    <!-- Form fields -->
    <div class="mb-8">
        {{ form.module_acronym.label() }}
        {{ form.module_acronym() }}
        <!-- More fields... -->
    </div>

    <!-- Form Actions -->
    <div class="flex justify-between items-center space-x-4">
        <!-- Left side - Navigation -->
        <div class="flex space-x-3">
            <a href="/vocabulary-drafts">📝 My Drafts</a>
            <a href="/my-documents">📄 My Documents</a>
        </div>
        
        <!-- Right side - Actions -->
        <div class="flex space-x-3">
            <a href="/" class="bg-gray-200 text-gray-700 px-6 py-3 rounded-md">Cancel</a>
            
            <!-- KEY: Both buttons submit to same route with different action values -->
            <button type="submit" name="action" value="save_draft" 
                    class="bg-green-600 text-white px-6 py-3 rounded-md">
                💾 Save Draft
            </button>
            
            <button type="submit" name="action" value="generate" 
                    class="bg-blue-600 text-white px-6 py-3 rounded-md">
                Generate Worksheet
            </button>
        </div>
    </div>
    
    <!-- Hidden field for draft tracking -->
    {% if draft_id %}
        <input type="hidden" name="draft_id" value="{{ draft_id }}">
    {% endif %}
</form>
```

**❌ WRONG APPROACH (Causes routing conflicts):**
```html
<!-- DON'T DO THIS -->
<button type="submit" name="action" value="save_draft" 
        formaction="/save-vocabulary-draft">  <!-- ❌ Separate route -->
    💾 Save Draft
</button>
```

### Pattern 3: Draft Management Routes

**Complete route set for each document type:**

```python
@app.route('/vocabulary-drafts')
@login_required
def vocabulary_drafts():
    """List user's vocabulary worksheet drafts"""
    drafts = FormDraft.query.filter_by(
        user_id=current_user.id, 
        form_type='vocabulary',  # KEY: Filter by document type
        is_current=True
    ).order_by(FormDraft.updated_at.desc()).all()
    
    return render_template('vocabulary_drafts.html', drafts=drafts)

@app.route('/load-vocabulary-draft/<int:draft_id>')
@login_required
def load_vocabulary_draft(draft_id):
    """Load vocabulary worksheet draft"""
    draft = FormDraft.query.filter_by(
        id=draft_id, 
        user_id=current_user.id,  # KEY: Security check
        form_type='vocabulary'
    ).first()
    
    if not draft:
        flash('Draft not found', 'error')
        return redirect(url_for('create_vocabulary'))
    
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

@app.route('/delete-vocabulary-draft/<int:draft_id>', methods=['POST'])
@login_required
def delete_vocabulary_draft(draft_id):
    """Delete vocabulary worksheet draft"""
    draft = FormDraft.query.filter_by(
        id=draft_id, 
        user_id=current_user.id,  # KEY: Security check
        form_type='vocabulary'
    ).first()
    
    if not draft:
        flash('Draft not found', 'error')
    else:
        db.session.delete(draft)
        db.session.commit()
        flash('Draft deleted successfully!', 'success')
    
    return redirect(url_for('vocabulary_drafts'))
```

### Pattern 4: Document Download System

```python
@app.route('/download/<int:doc_id>')
@login_required
def download_document(doc_id):
    """Download a generated document"""
    document = GeneratedDocument.query.filter_by(
        id=doc_id, 
        user_id=current_user.id  # KEY: Security check
    ).first()
    
    if not document:
        flash('Document not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if file exists
    if not os.path.exists(document.file_path):
        flash('Document file not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Track download analytics
    document.increment_download()
    db.session.commit()
    
    # Activity logging
    ActivityLog.log_activity('document_downloaded', current_user.id, 
                            {'document_type': document.document_type, 'filename': document.filename}, 
                            request)
    db.session.commit()
    
    # Return file for download
    return send_file(document.file_path, as_attachment=True, download_name=document.filename)
```

---

## 🐛 Troubleshooting Guide

### Issue 1: "Method Not Allowed" Error

**Problem:** Users get HTTP 405 error when clicking "Generate Worksheet"

**Root Cause:** Form routing conflicts between separate save and generate routes

**Solution:** Use unified form route pattern (Pattern 1 above)

**Symptoms:**
- ✅ Save Draft works
- ❌ Generate button gives "Method Not Allowed"  
- ❌ Form submits to wrong route

**Fix:**
1. Remove separate `/save-[type]-draft` routes
2. Use single route with action parameter detection
3. Update template buttons to use `name="action" value="[action]"`

### Issue 2: Database Migration Issues After Deployment

**Problem:** Authentication fails after deploying Phase 2 code

**Root Cause:** New database models not created in production

**Solution:** Create database migration routes

```python
@app.route('/migrate-db')
def migrate_db():
    """Safely migrate database - add missing tables only"""
    try:
        with app.app_context():
            db.create_all()  # Safe - only creates missing tables
        
        total_users = User.query.count()
        return f"Migration complete. {total_users} users preserved."
    except Exception as e:
        return f"Migration error: {str(e)}"
```

**Prevention:**
- Always include migration routes in Phase 2 deployments
- Test migration on staging before production
- Keep database schema additions backward-compatible

### Issue 3: Draft Data Not Loading Properly

**Problem:** Saved drafts don't populate form fields correctly

**Root Cause:** JSON structure mismatch between save and load

**Solution:** Standardize form data structure

```python
# SAVE: Consistent structure
form_data = {
    'module_acronym': form.module_acronym.data,
    'words': [{'word': word.word.data} for word in form.words if word.word.data]
}

# LOAD: Match the structure exactly
form.module_acronym.data = form_data.get('module_acronym', '')
words_data = form_data.get('words', [])
for i, word_data in enumerate(words_data):
    if i < len(form.words):
        form.words[i].word.data = word_data.get('word', '')
```

### Issue 4: File Download Issues

**Problem:** Generated files not downloading properly

**Root Cause:** File path or permission issues

**Solution:** 
```python
# Check file exists before download
if not os.path.exists(document.file_path):
    flash('Document file not found', 'error')
    return redirect(url_for('dashboard'))

# Use proper download headers
return send_file(document.file_path, as_attachment=True, download_name=document.filename)
```

---

## 📋 Implementation Checklist

### For Each New Document Type:

**Backend Implementation:**
- [ ] Update `create_[type]` route with unified form handling
- [ ] Add draft management routes (`/[type]-drafts`, `/load-[type]-draft`, `/delete-[type]-draft`)
- [ ] Create form data JSON structure
- [ ] Update `models.py` with new `form_type` value
- [ ] Test database migration

**Frontend Implementation:**
- [ ] Update form template with save/load buttons
- [ ] Create `[type]_drafts.html` template
- [ ] Add navigation links to templates
- [ ] Update dashboard with new document type
- [ ] Test complete user workflow

**Testing Checklist:**
- [ ] Save draft functionality
- [ ] Load draft functionality  
- [ ] Generate document functionality
- [ ] Download document functionality
- [ ] Draft management (edit/delete)
- [ ] User isolation (can't access other users' drafts)
- [ ] Error handling and validation

---

## 🚀 Next Phase Guidelines

### Phase 2B: PBA Worksheets
- **Priority:** High (user requested)
- **Complexity:** Medium (similar to vocabulary)
- **Estimated Time:** 1-2 days using patterns

### Phase 2C: Test Worksheets  
- **Priority:** High (frequently used)
- **Complexity:** Medium (pre/post test variants)
- **Estimated Time:** 1-2 days using patterns

### Phase 2D: Generic Worksheets
- **Priority:** Medium (power user feature)
- **Complexity:** High (dynamic fields, images)
- **Estimated Time:** 2-3 days using patterns

### Phase 2E: Family Briefings
- **Priority:** Medium (less frequent use)
- **Complexity:** Low (simple form structure)
- **Estimated Time:** 1 day using patterns

---

## 💡 Lessons Learned

1. **Always use unified form routes** - Prevents routing conflicts
2. **Test database migrations early** - Production deployment gotcha
3. **Standardize JSON structures** - Makes debugging easier
4. **Include comprehensive error handling** - Better user experience
5. **Document patterns immediately** - Speeds up next implementations
6. **Test complete workflows** - Don't just test individual features

---

## 📞 Support

If you encounter issues implementing these patterns:
1. Check the troubleshooting guide above
2. Review the vocabulary worksheet implementation as reference
3. Test each component individually before integration
4. Use the checklist to ensure nothing is missed

*Last Updated: June 2025* 