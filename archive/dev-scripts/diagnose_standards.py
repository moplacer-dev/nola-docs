#!/usr/bin/env python3
"""
Diagnose the standards data structure to understand the missing 8th grade issue
"""

import click
from flask.cli import with_appcontext
from models import db, Standard
import pandas as pd
import os

@click.command()
@with_appcontext
def diagnose_standards():
    """Diagnose what's wrong with the standards data"""
    print("🔍 DIAGNOSING STANDARDS DATA STRUCTURE")
    print("=" * 50)
    
    # Check what we have in the database
    print("📊 Current Database Standards:")
    all_standards = Standard.query.filter_by(subject='MATH').all()
    
    grade_7_codes = []
    grade_8_codes = []
    grade_none_codes = []
    
    for std in all_standards:
        if std.grade_level == 7:
            grade_7_codes.append(std.code)
        elif std.grade_level == 8:
            grade_8_codes.append(std.code)
        elif std.grade_level is None:
            grade_none_codes.append(std.code)
    
    print(f"  Grade 7 standards: {len(grade_7_codes)}")
    if grade_7_codes:
        print(f"    Sample: {grade_7_codes[:5]}")
    
    print(f"  Grade 8 standards: {len(grade_8_codes)}")
    if grade_8_codes:
        print(f"    Sample: {grade_8_codes[:5]}")
    
    print(f"  Grade None standards: {len(grade_none_codes)}")
    if grade_none_codes:
        print(f"    Sample: {grade_none_codes[:5]}")
    
    # Check what should be 8th grade (starts with 8.)
    should_be_8th = []
    for std in all_standards:
        if std.code.startswith('8.'):
            should_be_8th.append((std.code, std.grade_level))
    
    print(f"\n🎯 Standards that START with '8.' (should be 8th grade): {len(should_be_8th)}")
    for code, grade in should_be_8th[:10]:  # Show first 10
        print(f"    {code} -> Currently grade_level: {grade}")
    
    # Check the Excel file
    standards_path = 'data/standards/CC and NGSS Standards.xlsx'
    if os.path.exists(standards_path):
        print(f"\n📋 Excel File Analysis:")
        excel_file = pd.ExcelFile(standards_path)
        
        for sheet_name in excel_file.sheet_names:
            if 'Math' in sheet_name:
                print(f"\n📖 Sheet: {sheet_name}")
                df = pd.read_excel(standards_path, sheet_name=sheet_name)
                print(f"  Columns: {list(df.columns)}")
                print(f"  Rows: {len(df)}")
                
                # Find the CCSS column
                code_col = None
                for col in df.columns:
                    if 'CCSS' in str(col):
                        code_col = col
                        break
                
                if code_col:
                    codes = df[code_col].dropna().astype(str).tolist()
                    grade_7_in_excel = [c for c in codes if c.startswith('7.')]
                    grade_8_in_excel = [c for c in codes if c.startswith('8.')]
                    
                    print(f"  7th grade codes (7.xxx): {len(grade_7_in_excel)}")
                    print(f"  8th grade codes (8.xxx): {len(grade_8_in_excel)}")
                    
                    if grade_8_in_excel:
                        print(f"    Sample 8th grade: {grade_8_in_excel[:5]}")
    
    # Recommended fix
    print(f"\n💡 DIAGNOSIS:")
    if should_be_8th:
        print(f"  ✅ Found {len(should_be_8th)} standards that should be 8th grade")
        
        # Check if they're misclassified as grade 7
        misclassified = [code for code, grade in should_be_8th if grade != 8]
        if misclassified:
            print(f"  🔧 {len(misclassified)} standards need grade_level corrected to 8")
            print(f"     Examples: {misclassified[:5]}")
        else:
            print("  ✅ All 8.xxx standards are correctly marked as grade 8")
    else:
        print("  ❌ No 8th grade standards found - they may be missing entirely")

if __name__ == '__main__':
    diagnose_standards()