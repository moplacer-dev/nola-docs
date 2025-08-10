#!/usr/bin/env python3
"""
Production Data Verification Script
Run this to check if the production database has the required data for correlation reports
"""

import click
from flask.cli import with_appcontext
from models import db, State, Standard, Module, ModuleStandardMapping

@click.command()
@with_appcontext
def verify_production_data():
    """Verify that production database has all required data for correlation reports"""
    print("🔍 VERIFYING PRODUCTION DATA FOR CORRELATION REPORTS")
    print("=" * 60)
    
    # Check basic counts
    states_count = State.query.count()
    standards_count = Standard.query.count()
    modules_count = Module.query.count()
    mappings_count = ModuleStandardMapping.query.count()
    
    print(f"📊 Basic Counts:")
    print(f"  States: {states_count}")
    print(f"  Standards: {standards_count}")
    print(f"  Modules: {modules_count}")
    print(f"  Mappings: {mappings_count}")
    
    # Check critical data for correlation reports
    print(f"\n🎯 Critical Data Checks:")
    
    # Test Math 8th Grade standards directly
    math_8_standards = Standard.query.filter_by(framework='CCSS-M', subject='MATH', grade_level=8).all()
    print(f"  Math 8th Grade Standards: {len(math_8_standards)}")
    
    # Test Math 8th Grade modules and mappings
    math_8_modules = Module.query.filter_by(subject='MATH', grade_level=8).all()
    print(f"  Math 8th Grade Modules: {len(math_8_modules)}")
    
    # Test Science standards (typically grade_level=None)
    science_standards = Standard.query.filter_by(framework='NGSS', subject='SCIENCE', grade_level=None).all()
    print(f"  Science Standards: {len(science_standards)}")
    
    # Test Science modules 
    science_modules = Module.query.filter_by(subject='SCIENCE').all()
    print(f"  Science Modules: {len(science_modules)}")
    
    # Check grade level distribution
    print(f"\n📈 Grade Level Distribution:")
    
    # Standards by grade
    print("  Standards:")
    for grade in [7, 8, None]:
        math_count = Standard.query.filter_by(subject='MATH', grade_level=grade).count()
        science_count = Standard.query.filter_by(subject='SCIENCE', grade_level=grade).count()
        print(f"    Grade {grade}: Math={math_count}, Science={science_count}")
    
    # Modules by grade  
    print("  Modules:")
    for grade in [7, 8, None]:
        math_count = Module.query.filter_by(subject='MATH', grade_level=grade).count()
        science_count = Module.query.filter_by(subject='SCIENCE', grade_level=grade).count()
        print(f"    Grade {grade}: Math={math_count}, Science={science_count}")
    
    # Sample data verification
    print(f"\n🔬 Sample Data:")
    
    # Show some actual standards
    print("  Sample Standards:")
    for std in Standard.query.limit(5).all():
        print(f"    {std.framework} | {std.subject} | Grade {std.grade_level} | {std.code}")
    
    # Show some actual modules
    print("  Sample Modules:")
    for mod in Module.query.limit(5).all():
        print(f"    {mod.title} | {mod.subject} | Grade {mod.grade_level}")
    
    # Show some mappings
    print("  Sample Mappings:")
    mappings = (db.session.query(Module.title, Standard.code)
                .join(ModuleStandardMapping, Module.id==ModuleStandardMapping.module_id)
                .join(Standard, Standard.id==ModuleStandardMapping.standard_id)
                .limit(5).all())
    for mod_title, std_code in mappings:
        print(f"    {mod_title} -> {std_code}")
    
    # Final assessment
    print(f"\n✅ ASSESSMENT:")
    issues = []
    
    if states_count < 50:
        issues.append(f"Missing states data (have {states_count}, need 50)")
    if standards_count < 100:
        issues.append(f"Insufficient standards data (have {standards_count})")
    if modules_count < 50:
        issues.append(f"Insufficient modules data (have {modules_count})")
    if mappings_count < 500:
        issues.append(f"Insufficient mapping data (have {mappings_count})")
    if len(math_8_standards) == 0:
        issues.append("No Math 8th Grade standards found")
    if len(math_8_modules) == 0:
        issues.append("No Math 8th Grade modules found")
    
    if issues:
        print("❌ ISSUES FOUND:")
        for issue in issues:
            print(f"   • {issue}")
        print("\n🚨 ACTION REQUIRED: Run data loading commands")
        print("   flask load-production-data")
        print("   flask fix-standards-data")
    else:
        print("✅ All data looks good for correlation reports!")
    
    return len(issues) == 0

if __name__ == '__main__':
    verify_production_data()