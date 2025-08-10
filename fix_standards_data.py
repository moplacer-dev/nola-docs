#!/usr/bin/env python3
"""
EMERGENCY FIX: Reload standards with correct grade mappings
"""

import click
from flask.cli import with_appcontext
from models import db, Standard, ModuleStandardMapping
import pandas as pd
import os

@click.command()
@with_appcontext
def fix_standards_data():
    """Fix the standards data with correct grade mappings"""
    print("🚨 EMERGENCY FIX: Loading standards with correct grade mappings...")
    
    standards_path = 'data/standards/CC and NGSS Standards.xlsx'
    if not os.path.exists(standards_path):
        print(f"⚠️  Standards file not found: {standards_path}")
        return
    
    try:
        excel_file = pd.ExcelFile(standards_path)
        
        # CORRECTED sheet mapping based on local database structure
        sheet_mapping = {
            'MS Science ': {'subject': 'SCIENCE', 'grade_level': None, 'framework': 'NGSS', 'code_col': 'NGSS', 'desc_col': 'Standard - Performance Expectation'},
            'MS Math': {'subject': 'MATH', 'grade_level': 7, 'framework': 'CCSS-M', 'code_col': 'CCSS', 'desc_col': 'Standard - Performance Expectation'},
            'HS Math': {'subject': 'MATH', 'grade_level': None, 'framework': 'CCSS-M', 'code_col': 'CCSS', 'desc_col': 'Standard - Performance Expectation'},  # NULL, not 8!
        }
        
        # Check if there's an 8th grade math sheet we missed
        print(f"Available sheets: {excel_file.sheet_names}")
        
        # Look for any sheet that might contain 8th grade math standards
        for sheet_name in excel_file.sheet_names:
            if '8' in sheet_name and 'Math' in sheet_name:
                print(f"Found potential 8th grade sheet: {sheet_name}")
                # Add it to mapping
                sheet_mapping[sheet_name] = {
                    'subject': 'MATH', 'grade_level': 8, 'framework': 'CCSS-M', 
                    'code_col': 'CCSS', 'desc_col': 'Standard - Performance Expectation'
                }
        
        total_standards = 0
        for sheet_name, config in sheet_mapping.items():
            if sheet_name in excel_file.sheet_names:
                print(f"  Processing sheet: {sheet_name} -> Grade {config['grade_level']}")
                df = pd.read_excel(standards_path, sheet_name=sheet_name)
                
                count = 0
                for _, row in df.iterrows():
                    try:
                        code = str(row[config['code_col']]).strip()
                        description = str(row[config['desc_col']]).strip()
                        
                        if pd.isna(row[config['code_col']]) or code == 'nan' or code == '':
                            continue
                        
                        description = description.replace('\n', ' ').strip()
                        if len(description) > 500:
                            description = description[:497] + "..."
                        
                        standard = Standard(
                            framework=config['framework'],
                            subject=config['subject'],
                            grade_level=config['grade_level'],
                            code=code,
                            description=description
                        )
                        db.session.add(standard)
                        count += 1
                    except Exception as e:
                        print(f"    ⚠️  Error processing row: {e}")
                        continue
                
                print(f"  ✅ Added {count} standards from {sheet_name}")
                total_standards += count
        
        db.session.commit()
        print(f"✅ Total standards added: {total_standards}")
        
        # Show final breakdown
        print("\nFinal standards breakdown:")
        for subject in ['MATH', 'SCIENCE']:
            for grade in [7, 8, None]:
                count = Standard.query.filter_by(subject=subject, grade_level=grade).count()
                if count > 0:
                    grade_label = str(grade) if grade else 'NULL'
                    print(f"  {subject} Grade {grade_label}: {count}")
                    
        print(f"\nTotal: {Standard.query.count()}")
        
    except Exception as e:
        print(f"⚠️  Error: {e}")
        db.session.rollback()

if __name__ == '__main__':
    from app import app
    with app.app_context():
        fix_standards_data()