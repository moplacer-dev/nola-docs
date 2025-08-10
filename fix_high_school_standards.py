#!/usr/bin/env python3
"""
Fix High School NGSS standards that were incorrectly classified as middle school grades.
High School standards should either be moved to a separate grade level or removed from 
middle school grade assignments.
"""

from models import db, Standard
from app import app

def fix_high_school_standards():
    """Fix high school standards classification"""
    
    print("🔧 FIXING HIGH SCHOOL STANDARDS")
    print("=" * 35)
    
    with app.app_context():
        # Find all HS standards that are currently assigned to MS grades
        hs_standards = Standard.query.filter(
            Standard.framework == 'NGSS',
            Standard.code.like('HS-%'),
            Standard.grade_level.in_([7, 8])
        ).all()
        
        print(f"📊 Found {len(hs_standards)} HS standards assigned to MS grades")
        
        if not hs_standards:
            print("✅ No HS standards need fixing")
            return True
        
        # Show what we found
        for std in hs_standards:
            print(f"  {std.code} (currently grade {std.grade_level})")
        
        # Set them to grade_level = None or a specific HS grade
        # For now, let's set them to None to remove them from MS grades
        updated_count = 0
        
        for standard in hs_standards:
            print(f"  🔄 {standard.code}: Grade {standard.grade_level} -> Grade None (HS)")
            standard.grade_level = None
            # Optionally, we could set a specific HS grade like standard.grade_level = 9
            updated_count += 1
        
        try:
            db.session.commit()
            print(f"\\n✅ FIXED {updated_count} HIGH SCHOOL STANDARDS")
            
            # Verify the fix
            final_counts = {
                'MS_Grade_7': Standard.query.filter_by(framework='NGSS', grade_level=7).count(),
                'MS_Grade_8': Standard.query.filter_by(framework='NGSS', grade_level=8).count(),
                'HS_None': Standard.query.filter(
                    Standard.framework == 'NGSS',
                    Standard.code.like('HS-%'),
                    Standard.grade_level.is_(None)
                ).count(),
                'MS_None': Standard.query.filter(
                    Standard.framework == 'NGSS',
                    Standard.code.like('MS-%'),
                    Standard.grade_level.is_(None)
                ).count()
            }
            
            print(f"\\n📊 FINAL VERIFICATION:")
            print(f"  - MS Grade 7: {final_counts['MS_Grade_7']} standards")
            print(f"  - MS Grade 8: {final_counts['MS_Grade_8']} standards")
            print(f"  - HS ungraded: {final_counts['HS_None']} standards")
            print(f"  - MS ungraded: {final_counts['MS_None']} standards")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during fix: {e}")
            return False

def generate_final_summary():
    """Generate a final summary of the NGSS separation work"""
    
    print("\\n📋 FINAL SUMMARY")
    print("=" * 20)
    
    with app.app_context():
        # Get comprehensive counts
        all_ngss = Standard.query.filter_by(framework='NGSS').all()
        
        ms_grade_7 = [s for s in all_ngss if s.grade_level == 7 and s.code.startswith('MS-')]
        ms_grade_8 = [s for s in all_ngss if s.grade_level == 8 and s.code.startswith('MS-')]
        hs_ungraded = [s for s in all_ngss if s.grade_level is None and s.code.startswith('HS-')]
        ms_ungraded = [s for s in all_ngss if s.grade_level is None and s.code.startswith('MS-')]
        
        print(f"🎯 NGSS STANDARDS ORGANIZATION:")
        print(f"  📚 MS Grade 7: {len(ms_grade_7)} standards")
        print(f"  📚 MS Grade 8: {len(ms_grade_8)} standards")
        print(f"  🎓 HS Ungraded: {len(hs_ungraded)} standards")
        print(f"  ❓ MS Ungraded: {len(ms_ungraded)} standards")
        
        # Show samples
        if ms_grade_7:
            print(f"\\n📝 Grade 7 samples: {[s.code for s in ms_grade_7[:5]]}")
        if ms_grade_8:
            print(f"📝 Grade 8 samples: {[s.code for s in ms_grade_8[:5]]}")
        if hs_ungraded:
            print(f"📝 HS samples: {[s.code for s in hs_ungraded[:5]]}")
        if ms_ungraded:
            print(f"⚠️  MS ungraded: {[s.code for s in ms_ungraded]}")
        
        # Module mapping summary
        from models import ModuleStandardMapping
        
        grade_7_mappings = db.session.query(ModuleStandardMapping).join(Standard).filter(
            Standard.framework == 'NGSS',
            Standard.grade_level == 7
        ).count()
        
        grade_8_mappings = db.session.query(ModuleStandardMapping).join(Standard).filter(
            Standard.framework == 'NGSS',
            Standard.grade_level == 8
        ).count()
        
        print(f"\\n🔗 MODULE MAPPINGS:")
        print(f"  - Grade 7 NGSS mappings: {grade_7_mappings}")
        print(f"  - Grade 8 NGSS mappings: {grade_8_mappings}")
        print(f"  - Total NGSS mappings: {grade_7_mappings + grade_8_mappings}")

if __name__ == '__main__':
    if fix_high_school_standards():
        generate_final_summary()
        print("\\n🎉 All NGSS grade separation work completed!")