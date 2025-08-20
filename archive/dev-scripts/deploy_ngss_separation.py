#!/usr/bin/env python3
"""
Deployment script to separate NGSS standards into 7th and 8th grade levels.
This can be run directly on Render via their shell.

IMPORTANT: This script also fixes app.py correlation functions to use the new grade levels.
Make sure the updated app.py is deployed before running this script!

Usage on Render:
1. Deploy updated code (including app.py fixes)
2. Open Render shell for your web service  
3. Run: python deploy_ngss_separation.py
"""

import os
import sys

def check_environment():
    """Check if we're in production and can access the database"""
    try:
        from models import db, Standard
        from app import app
        
        with app.app_context():
            # Test database connection
            count = Standard.query.count()
            print(f"✅ Database connected - {count} total standards")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_current_state():
    """Check if NGSS separation is already applied"""
    from models import db, Standard
    from app import app
    
    with app.app_context():
        ngss_7th = Standard.query.filter_by(framework='NGSS', grade_level=7).count()
        ngss_8th = Standard.query.filter_by(framework='NGSS', grade_level=8).count()
        ngss_none_ms = Standard.query.filter(
            Standard.framework == 'NGSS',
            Standard.code.like('MS-%'),
            Standard.grade_level.is_(None)
        ).count()
        
        print(f"📊 CURRENT NGSS STATE:")
        print(f"  - Grade 7: {ngss_7th} standards")
        print(f"  - Grade 8: {ngss_8th} standards")
        print(f"  - MS ungraded: {ngss_none_ms} standards")
        
        # If we have proper separation, skip
        if ngss_7th > 20 and ngss_8th > 20 and ngss_none_ms == 0:
            print("✅ NGSS separation already applied!")
            return True
        
        return False

def apply_ngss_separation():
    """Apply the NGSS grade separation"""
    from models import db, Standard
    from app import app
    
    print("🔧 APPLYING NGSS GRADE SEPARATION")
    print("=" * 40)
    
    # Grade 7 NGSS standards (from documentation)
    grade_7_standards = [
        'MS-ESS1-4', 'MS-ESS3-3', 'MS-ESS3-4', 'MS-ESS3-5',
        'MS-LS1-2', 'MS-LS1-3', 'MS-LS1-5', 'MS-LS1-7', 'MS-LS3-1', 'MS-LS3-2',
        'MS-PS1-1', 'MS-PS1-2'
    ]
    
    # Grade 8 NGSS standards (from documentation) 
    grade_8_standards = [
        'MS-ESS1-1', 'MS-ESS1-2', 'MS-ESS1-3',
        'MS-LS1-4', 'MS-LS4-1', 'MS-LS4-2', 'MS-LS4-3', 'MS-LS4-4', 'MS-LS4-5', 'MS-LS4-6',
        'MS-PS2-1', 'MS-PS2-2', 'MS-PS2-4', 'MS-PS3-1', 'MS-PS4-1'
    ]
    
    # Additional classifications based on subject patterns
    additional_grade_7 = [
        # Physical Science defaults to grade 7
        'MS-PS1-3', 'MS-PS1-4', 'MS-PS1-5', 'MS-PS1-6', 'MS-PS2-3', 'MS-PS2-5',
        'MS-PS3-2', 'MS-PS3-3', 'MS-PS3-4', 'MS-PS3-5', 'MS-PS4-2',
        # Earth & Space Science defaults to grade 7
        'MS-ESS2-1', 'MSS-ESS2-2', 'MS-ESS2-3', 'MS-ESS2-4', 'MS-ESS2-5', 'MS-ESS2-6', 
        'MS-ESS3-1', 'MS-ESS3-2'
    ]
    
    additional_grade_8 = [
        # Life Science defaults to grade 8
        'MS-LS1-1', 'MS-LS1-6', 'MS-LS1-8', 'MS-LS2-1', 'MS-LS2-2', 'MS-LS2-3', 
        'MS-LS2-4', 'MS-LS2-5',
        # Engineering standards to grade 8
        'MS-ETS1-1', 'MS-ETS1-2', 'MS-ETS1-3', 'MS-ETS1-4'
    ]
    
    all_grade_7 = grade_7_standards + additional_grade_7
    all_grade_8 = grade_8_standards + additional_grade_8
    
    with app.app_context():
        updated_7th = 0
        updated_8th = 0
        
        # Update Grade 7 standards
        print(f"🎯 Updating 7th grade standards...")
        for code in all_grade_7:
            standards = Standard.query.filter_by(framework='NGSS', code=code).all()
            for standard in standards:
                if standard.code.startswith('MS-'):  # Only MS standards
                    print(f"  ✅ {code} -> Grade 7")
                    standard.grade_level = 7
                    updated_7th += 1
        
        # Update Grade 8 standards  
        print(f"\\n🎯 Updating 8th grade standards...")
        for code in all_grade_8:
            standards = Standard.query.filter_by(framework='NGSS', code=code).all()
            for standard in standards:
                if standard.code.startswith('MS-'):  # Only MS standards
                    print(f"  ✅ {code} -> Grade 8")
                    standard.grade_level = 8
                    updated_8th += 1
        
        # Move High School standards out of middle school grades
        print(f"\\n🎓 Fixing High School standards...")
        hs_standards = Standard.query.filter(
            Standard.framework == 'NGSS',
            Standard.code.like('HS-%'),
            Standard.grade_level.in_([7, 8])
        ).all()
        
        hs_fixed = 0
        for standard in hs_standards:
            print(f"  🔄 {standard.code}: Grade {standard.grade_level} -> Grade None (HS)")
            standard.grade_level = None
            hs_fixed += 1
        
        # Commit changes
        try:
            db.session.commit()
            print(f"\\n✅ NGSS SEPARATION COMPLETED:")
            print(f"  - Grade 7 updated: {updated_7th}")
            print(f"  - Grade 8 updated: {updated_8th}")
            print(f"  - HS standards fixed: {hs_fixed}")
            
            # Verify final state
            final_7th = Standard.query.filter_by(framework='NGSS', grade_level=7).count()
            final_8th = Standard.query.filter_by(framework='NGSS', grade_level=8).count()
            final_ms_none = Standard.query.filter(
                Standard.framework == 'NGSS',
                Standard.code.like('MS-%'),
                Standard.grade_level.is_(None)
            ).count()
            
            print(f"\\n📊 FINAL VERIFICATION:")
            print(f"  - NGSS Grade 7: {final_7th}")
            print(f"  - NGSS Grade 8: {final_8th}")
            print(f"  - MS Ungraded: {final_ms_none}")
            
            if final_ms_none == 0:
                print("\\n🎉 SUCCESS: All MS NGSS standards now have grade assignments!")
                return True
            else:
                print("\\n⚠️  Some MS standards still ungraded")
                return False
            
        except Exception as e:
            db.session.rollback()
            print(f"\\n❌ ERROR during commit: {e}")
            return False

def main():
    """Main deployment function"""
    print("🚀 NGSS GRADE SEPARATION DEPLOYMENT")
    print("=" * 45)
    
    # Check environment
    if not check_environment():
        print("❌ Environment check failed")
        sys.exit(1)
    
    # Check if already applied
    if check_current_state():
        print("\\n✅ No action needed - separation already applied")
        sys.exit(0)
    
    # Apply separation
    success = apply_ngss_separation()
    
    if success:
        print("\\n🎉 DEPLOYMENT SUCCESSFUL!")
        print("\\nCorrelation reports will now show grade-specific NGSS standards:")
        print("  - 7th Grade Science: ~31 NGSS standards")
        print("  - 8th Grade Science: ~27 NGSS standards")
    else:
        print("\\n💥 DEPLOYMENT FAILED!")
        sys.exit(1)

if __name__ == '__main__':
    main()