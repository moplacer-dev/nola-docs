# NGSS Grade Separation - Deployment Instructions

## Overview
This document outlines how to deploy the NGSS grade separation changes from your local development environment to production (Render).

## Current Status
✅ **Local Development**: NGSS standards successfully separated into 7th and 8th grade
✅ **Deployment Script**: Created and tested
🔄 **Production**: Ready to deploy

## Deployment Steps

### Method 1: Direct Script Execution (Recommended)

1. **Commit and Push Changes**
   ```bash
   git add .
   git commit -m "Add NGSS grade separation deployment script"
   git push origin main
   ```

2. **Deploy on Render**
   - Wait for automatic deployment to complete
   - Open Render Dashboard → Your Web Service
   - Click "Shell" tab to open terminal

3. **Run Deployment Script**
   ```bash
   python deploy_ngss_separation.py
   ```

4. **Verify Success**
   The script will show output like:
   ```
   ✅ NGSS SEPARATION COMPLETED:
     - Grade 7 updated: 31
     - Grade 8 updated: 27
     - HS standards fixed: 18
   
   🎉 SUCCESS: All MS NGSS standards now have grade assignments!
   ```

### Method 2: Manual Migration (Alternative)

If the script method fails, you can run SQL directly:

1. **Open Render Shell**
2. **Run Python Shell**
   ```bash
   python -c "
   from models import db, Standard
   from app import app
   
   with app.app_context():
       # Your SQL updates here
       db.session.execute('UPDATE standards SET grade_level = 7 WHERE framework = \"NGSS\" AND code IN (\"MS-PS1-1\", \"MS-PS1-2\", ...)')
       db.session.commit()
   "
   ```

## Verification

After deployment, verify the changes:

### Check Standards Count
```python
python -c "
from models import db, Standard
from app import app

with app.app_context():
    grade_7 = Standard.query.filter_by(framework='NGSS', grade_level=7).count()
    grade_8 = Standard.query.filter_by(framework='NGSS', grade_level=8).count()
    print(f'Grade 7: {grade_7}, Grade 8: {grade_8}')
"
```

**Expected Result**: `Grade 7: 31, Grade 8: 27`

### Test Correlation Reports
1. Generate a 7th grade science correlation report
2. Verify it shows ~31 NGSS standards (not 76)
3. Generate an 8th grade science correlation report  
4. Verify it shows ~27 NGSS standards (not 76)

## Files Included

### Deployment Files
- `deploy_ngss_separation.py` - Main deployment script
- `DEPLOYMENT_INSTRUCTIONS.md` - This file

### Development/Testing Files (Optional)
- `separate_ngss_grades.py` - Initial separation script
- `complete_ngss_separation.py` - Complete classification script
- `update_module_mappings.py` - Module mapping updates
- `fix_high_school_standards.py` - HS standards cleanup
- `test_correlation_reports.py` - Verification tests
- `NGSS_SEPARATION_SUMMARY.md` - Complete project summary

### Reference Documents
- `data/standards/NGSS 7th and 8th Grade Standards.md` - Grade classifications
- `data/modules/Louisiana Department of Education Grade 7 & 8 Science.csv` - Module alignments

## Rollback Plan

If something goes wrong, you can rollback:

```python
python -c "
from models import db, Standard
from app import app

with app.app_context():
    # Reset all NGSS to grade_level = None
    standards = Standard.query.filter_by(framework='NGSS').all()
    for std in standards:
        std.grade_level = None
    db.session.commit()
    print('NGSS standards reset to grade_level = None')
"
```

## Expected Impact

**Before Deployment:**
- Science correlation reports show all 76 NGSS standards
- No grade-specific filtering possible

**After Deployment:**
- 7th grade science reports show 31 relevant NGSS standards
- 8th grade science reports show 27 relevant NGSS standards
- Proper grade-specific correlation alignment
- 18 High School standards moved out of middle school grades

## Support

If you encounter any issues during deployment:
1. Check the script output for error messages
2. Verify database connection is working
3. Use the verification commands above to check current state
4. Refer to `NGSS_SEPARATION_SUMMARY.md` for detailed technical information

## Security Notes

- The deployment script includes safety checks
- It won't duplicate work if already applied
- All changes are reversible
- No data loss will occur