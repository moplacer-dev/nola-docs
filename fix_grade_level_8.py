#!/usr/bin/env python3
"""
Fix 8th grade standards that are incorrectly labeled as grade_level=7
"""

import click
from flask.cli import with_appcontext
from models import db, Standard

@click.command()
@with_appcontext
def fix_grade_level_8():
    """Fix standards starting with '8.' to have grade_level=8"""
    print("🔧 FIXING GRADE LEVEL FOR 8TH GRADE STANDARDS")
    print("=" * 50)
    
    # Find all standards that start with '8.' but aren't grade_level=8
    misclassified = Standard.query.filter(
        Standard.subject == 'MATH',
        Standard.code.like('8.%'),
        Standard.grade_level != 8
    ).all()
    
    print(f"📊 Found {len(misclassified)} standards to fix")
    
    if not misclassified:
        print("✅ No standards need fixing!")
        return
    
    # Show what we're about to fix
    print("🔍 Standards to update:")
    for std in misclassified[:10]:  # Show first 10
        print(f"  {std.code}: grade_level {std.grade_level} -> 8")
    
    if len(misclassified) > 10:
        print(f"  ... and {len(misclassified) - 10} more")
    
    # Confirm before proceeding
    try:
        # Update all at once using SQL
        updated_count = db.session.query(Standard).filter(
            Standard.subject == 'MATH',
            Standard.code.like('8.%'),
            Standard.grade_level != 8
        ).update({Standard.grade_level: 8})
        
        db.session.commit()
        
        print(f"✅ Updated {updated_count} standards to grade_level=8")
        
        # Verify the fix
        remaining_issues = Standard.query.filter(
            Standard.subject == 'MATH',
            Standard.code.like('8.%'),
            Standard.grade_level != 8
        ).count()
        
        grade_8_count = Standard.query.filter_by(
            subject='MATH',
            grade_level=8
        ).count()
        
        print(f"📊 Results:")
        print(f"  Math 8th grade standards now: {grade_8_count}")
        print(f"  Remaining misclassified: {remaining_issues}")
        
        if remaining_issues == 0:
            print("🎉 SUCCESS: All 8th grade standards fixed!")
        else:
            print(f"⚠️  {remaining_issues} standards still need attention")
            
    except Exception as e:
        print(f"❌ Error during update: {e}")
        db.session.rollback()
        raise

if __name__ == '__main__':
    fix_grade_level_8()