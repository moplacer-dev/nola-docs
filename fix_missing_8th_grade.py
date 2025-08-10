#!/usr/bin/env python3
"""
Fix missing Math 8th Grade standards on production
"""

import click
from flask.cli import with_appcontext
from models import db, Standard
import pandas as pd
import os

@click.command()
@with_appcontext
def fix_missing_8th_grade():
    """Add the missing Math 8th Grade standards"""
    print("🔧 FIXING MISSING MATH 8TH GRADE STANDARDS")
    print("=" * 50)
    
    # Check current state
    math_8_before = Standard.query.filter_by(subject='MATH', grade_level=8).count()
    print(f"Math 8th Grade standards before: {math_8_before}")
    
    standards_path = 'data/standards/CC and NGSS Standards.xlsx'
    if not os.path.exists(standards_path):
        print(f"❌ Standards file not found: {standards_path}")
        return
    
    try:
        excel_file = pd.ExcelFile(standards_path)
        print(f"📋 Available sheets: {excel_file.sheet_names}")
        
        # Look for Middle School Math sheet (contains both 7th and 8th grade)
        target_sheet = None
        for sheet_name in excel_file.sheet_names:
            if 'MS Math' in sheet_name or 'Middle School Math' in sheet_name:
                target_sheet = sheet_name
                break
        
        if not target_sheet:
            # Fallback to any Math sheet
            for sheet_name in excel_file.sheet_names:
                if 'Math' in sheet_name:
                    target_sheet = sheet_name
                    break
        
        if not target_sheet:
            print("❌ No Math sheet found")
            print("Available sheets:", excel_file.sheet_names)
            return
        
        print(f"📖 Processing sheet: {target_sheet}")
        df = pd.read_excel(standards_path, sheet_name=target_sheet)
        
        # Show the structure
        print(f"📊 Sheet columns: {list(df.columns)}")
        print(f"📊 Sheet rows: {len(df)}")
        
        # Look for CCSS column and description column
        code_col = None
        desc_col = None
        
        for col in df.columns:
            if 'CCSS' in str(col) or 'Code' in str(col):
                code_col = col
            elif 'Standard' in str(col) or 'Description' in str(col) or 'Performance' in str(col):
                desc_col = col
        
        if not code_col or not desc_col:
            print(f"❌ Could not identify code column ({code_col}) or description column ({desc_col})")
            print("Available columns:", list(df.columns))
            return
        
        print(f"✅ Using code column: {code_col}")
        print(f"✅ Using description column: {desc_col}")
        
        # Process the standards
        added_count = 0
        for _, row in df.iterrows():
            code = str(row[code_col]).strip()
            description = str(row[desc_col]).strip()
            
            # Skip empty rows
            if pd.isna(row[code_col]) or code == 'nan' or not code:
                continue
            
            # Look for 8th grade standards (8.xxx format)
            if not code.startswith('8.'):
                continue
            
            # Check if this standard already exists
            existing = Standard.query.filter_by(
                framework='CCSS-M',
                code=code
            ).first()
            
            if existing:
                print(f"⚠️  Standard {code} already exists, skipping")
                continue
            
            # Add the new standard
            new_standard = Standard(
                framework='CCSS-M',
                subject='MATH',
                grade_level=8,  # This is the key fix!
                code=code,
                description=description
            )
            
            db.session.add(new_standard)
            added_count += 1
            print(f"➕ Added: {code}")
        
        # Commit changes
        db.session.commit()
        
        # Check results
        math_8_after = Standard.query.filter_by(subject='MATH', grade_level=8).count()
        print(f"\n✅ RESULTS:")
        print(f"  Math 8th Grade standards before: {math_8_before}")
        print(f"  Math 8th Grade standards after: {math_8_after}")
        print(f"  New standards added: {added_count}")
        
        if math_8_after > math_8_before:
            print("🎉 SUCCESS: 8th Grade Math standards added!")
        else:
            print("❌ No new standards were added")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.session.rollback()
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_missing_8th_grade()