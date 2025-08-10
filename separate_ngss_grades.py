#!/usr/bin/env python3
"""
Script to separate NGSS standards into 7th and 8th grade based on the provided document.
This addresses the issue where all NGSS standards are currently stored with grade_level=None.
"""

from models import db, Standard, Module, ModuleStandardMapping
from app import app
import pandas as pd

# Grade 7 NGSS standards from the document
GRADE_7_STANDARDS = [
    # Earth & Space Science (ESS)
    'MS-ESS1-4', 'MS-ESS2-2', 'MS-ESS3-3', 'MS-ESS3-4', 'MS-ESS3-5',
    # Life Science (LS)
    'MS-LS1-2', 'MS-LS1-3', 'MS-LS1-5', 'MS-LS1-7', 'MS-LS3-1', 'MS-LS3-2',
    # Physical Science (PS)
    'MS-PS1-1', 'MS-PS1-2'
]

# Grade 8 NGSS standards from the document
GRADE_8_STANDARDS = [
    # Earth & Space Science (ESS)
    'MS-ESS1-1', 'MS-ESS1-2', 'MS-ESS1-3',
    # Life Science (LS)
    'MS-LS1-4', 'MS-LS4-1', 'MS-LS4-2', 'MS-LS4-3', 'MS-LS4-4', 'MS-LS4-5', 'MS-LS4-6',
    # Physical Science (PS)
    'MS-PS2-1', 'MS-PS2-2', 'MS-PS2-4', 'MS-PS3-1', 'MS-PS4-1'
]

def separate_ngss_standards():
    """Update NGSS standards to have proper grade levels"""
    
    print("🔧 SEPARATING NGSS STANDARDS INTO 7TH AND 8TH GRADE")
    print("=" * 55)
    
    with app.app_context():
        # Get all current NGSS standards
        ngss_standards = Standard.query.filter_by(framework='NGSS').all()
        print(f"📊 Found {len(ngss_standards)} NGSS standards currently in database")
        
        # Count by current grade level
        grade_none = [s for s in ngss_standards if s.grade_level is None]
        print(f"  - Grade None: {len(grade_none)}")
        
        updated_7th = 0
        updated_8th = 0
        not_found = []
        
        # Update 7th grade standards
        print(f"\n🎯 Updating 7th grade standards...")
        for code in GRADE_7_STANDARDS:
            standard = Standard.query.filter_by(framework='NGSS', code=code).first()
            if standard:
                print(f"  ✅ {code} -> Grade 7")
                standard.grade_level = 7
                updated_7th += 1
            else:
                print(f"  ❌ {code} not found in database")
                not_found.append(code)
        
        # Update 8th grade standards
        print(f"\n🎯 Updating 8th grade standards...")
        for code in GRADE_8_STANDARDS:
            standard = Standard.query.filter_by(framework='NGSS', code=code).first()
            if standard:
                print(f"  ✅ {code} -> Grade 8")
                standard.grade_level = 8
                updated_8th += 1
            else:
                print(f"  ❌ {code} not found in database")
                not_found.append(code)
        
        # Commit the changes
        try:
            db.session.commit()
            print(f"\n✅ SUCCESSFULLY UPDATED STANDARDS:")
            print(f"  - 7th grade: {updated_7th} standards")
            print(f"  - 8th grade: {updated_8th} standards")
            print(f"  - Not found: {len(not_found)} standards")
            
            if not_found:
                print(f"  - Missing codes: {not_found}")
            
            # Verify the changes
            print(f"\n🔍 VERIFICATION:")
            grade_7_count = Standard.query.filter_by(framework='NGSS', grade_level=7).count()
            grade_8_count = Standard.query.filter_by(framework='NGSS', grade_level=8).count()
            grade_none_count = Standard.query.filter_by(framework='NGSS', grade_level=None).count()
            
            print(f"  - NGSS Grade 7: {grade_7_count} standards")
            print(f"  - NGSS Grade 8: {grade_8_count} standards")
            print(f"  - NGSS Grade None: {grade_none_count} standards")
            
            # Check if any standards are still unassigned
            if grade_none_count > 0:
                unassigned = Standard.query.filter_by(framework='NGSS', grade_level=None).all()
                print(f"\n⚠️  UNASSIGNED STANDARDS:")
                for std in unassigned[:10]:  # Show first 10
                    print(f"    {std.code}")
                if len(unassigned) > 10:
                    print(f"    ... and {len(unassigned) - 10} more")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERROR during database update: {e}")
            return False
    
    return True

def check_module_mappings():
    """Check what module mappings might need updating"""
    
    print(f"\n🔍 CHECKING MODULE MAPPINGS")
    print("=" * 30)
    
    with app.app_context():
        # Find modules that map to NGSS standards
        ngss_mappings = db.session.query(ModuleStandardMapping, Standard, Module)\
            .join(Standard)\
            .join(Module)\
            .filter(Standard.framework == 'NGSS')\
            .all()
        
        if not ngss_mappings:
            print("  No module mappings found for NGSS standards")
            return
        
        print(f"  Found {len(ngss_mappings)} module-to-NGSS mappings")
        
        # Group by module
        module_mappings = {}
        for mapping, standard, module in ngss_mappings:
            if module.title not in module_mappings:
                module_mappings[module.title] = {
                    'module': module,
                    'standards': [],
                    'grade_levels': set()
                }
            module_mappings[module.title]['standards'].append(standard.code)
            if standard.grade_level:
                module_mappings[module.title]['grade_levels'].add(standard.grade_level)
        
        print(f"\n📋 MODULES WITH NGSS MAPPINGS:")
        for title, data in module_mappings.items():
            module = data['module']
            standards = data['standards']
            grade_levels = data['grade_levels']
            
            print(f"\n  🎓 {title}")
            print(f"    Module grade: {module.grade_level}")
            print(f"    Standard grades: {sorted(grade_levels) if grade_levels else 'None'}")
            print(f"    Standards count: {len(standards)}")
            print(f"    Sample standards: {standards[:3]}")
            
            # Flag potential issues
            if len(grade_levels) > 1:
                print(f"    ⚠️  Module maps to multiple grade levels: {sorted(grade_levels)}")
            elif module.grade_level and grade_levels and module.grade_level not in grade_levels:
                print(f"    ⚠️  Module grade ({module.grade_level}) doesn't match standard grades ({sorted(grade_levels)})")

if __name__ == '__main__':
    print("Starting NGSS grade separation process...")
    
    # First, separate the standards
    if separate_ngss_standards():
        # Then check the module mappings
        check_module_mappings()
        print(f"\n🎉 NGSS grade separation completed!")
    else:
        print(f"\n💥 NGSS grade separation failed!")