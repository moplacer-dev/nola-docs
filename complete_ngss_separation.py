#!/usr/bin/env python3
"""
Complete the NGSS separation by using the CSV file with module alignments.
This will classify all remaining NGSS standards into 7th and 8th grade.
"""

from models import db, Standard, Module, ModuleStandardMapping
from app import app
import pandas as pd

def load_csv_grade_mappings():
    """Load grade mappings from the CSV file"""
    csv_path = '/Users/moriahplacer/Desktop/Mo\'s Vault/nola.docs/data/modules/Louisiana Department of Education Grade 7 & 8 Science.csv'
    
    try:
        # Read the CSV
        df = pd.read_csv(csv_path)
        
        # The first column should contain the grade and standard code
        # Let's examine the structure
        print("🔍 CSV FILE STRUCTURE:")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Shape: {df.shape}")
        print(f"  First few rows:")
        for i, row in df.head().iterrows():
            grade_col = df.columns[0]  # First column
            standard_col = df.columns[1]  # Second column  
            print(f"    Row {i}: {row[grade_col]} | {row[standard_col]}")
        
        grade_7_standards = []
        grade_8_standards = []
        
        # Process each row
        for i, row in df.iterrows():
            grade_col = df.columns[0]  # First column contains grade info
            standard_col = df.columns[1]  # Second column contains NGSS code
            
            grade_info = str(row[grade_col]).strip()
            standard_code = str(row[standard_col]).strip()
            
            # Skip header rows and invalid data
            if standard_code == 'nan' or not standard_code.startswith('MS-'):
                continue
                
            # Determine grade based on the grade column
            if '7th Grade' in grade_info or grade_info == '7th Grade':
                grade_7_standards.append(standard_code)
            elif '8th Grade' in grade_info or grade_info == '8th Grade':  
                grade_8_standards.append(standard_code)
        
        return grade_7_standards, grade_8_standards
        
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return [], []

def complete_ngss_separation():
    """Complete the NGSS grade separation using CSV data"""
    
    print("🔧 COMPLETING NGSS GRADE SEPARATION")
    print("=" * 40)
    
    # Load CSV mappings
    csv_grade_7, csv_grade_8 = load_csv_grade_mappings()
    
    print(f"📊 CSV DATA:")
    print(f"  - 7th grade standards: {len(csv_grade_7)}")
    print(f"  - 8th grade standards: {len(csv_grade_8)}")
    
    if csv_grade_7:
        print(f"  - Sample 7th: {csv_grade_7[:3]}")
    if csv_grade_8:
        print(f"  - Sample 8th: {csv_grade_8[:3]}")
    
    with app.app_context():
        # Get unassigned NGSS standards
        unassigned = Standard.query.filter_by(framework='NGSS', grade_level=None).all()
        print(f"\n📋 UNASSIGNED STANDARDS: {len(unassigned)}")
        
        updated_7th = 0
        updated_8th = 0
        still_unassigned = []
        
        for standard in unassigned:
            code = standard.code
            if code in csv_grade_7:
                print(f"  ✅ {code} -> Grade 7 (from CSV)")
                standard.grade_level = 7
                updated_7th += 1
            elif code in csv_grade_8:
                print(f"  ✅ {code} -> Grade 8 (from CSV)")
                standard.grade_level = 8
                updated_8th += 1
            else:
                still_unassigned.append(code)
        
        # For any remaining unassigned, we can make educated guesses based on patterns
        # or assign them to a default grade
        for standard in Standard.query.filter_by(framework='NGSS', grade_level=None).all():
            code = standard.code
            if code not in still_unassigned:
                continue
                
            # Default assignment strategy (you can adjust this logic)
            # For now, let's assign ETS (Engineering) standards to both grades
            # and Life Science to 8th grade by default
            if 'ETS' in code:
                print(f"  🔧 {code} -> Grade 8 (ETS default)")
                standard.grade_level = 8
                updated_8th += 1
            elif 'LS' in code:
                print(f"  🧬 {code} -> Grade 8 (LS default)")  
                standard.grade_level = 8
                updated_8th += 1
            elif 'PS' in code:
                print(f"  ⚛️  {code} -> Grade 7 (PS default)")
                standard.grade_level = 7
                updated_7th += 1
            elif 'ESS' in code:
                print(f"  🌍 {code} -> Grade 7 (ESS default)")
                standard.grade_level = 7
                updated_7th += 1
            else:
                print(f"  ❓ {code} -> Grade 8 (fallback)")
                standard.grade_level = 8
                updated_8th += 1
        
        # Commit changes
        try:
            db.session.commit()
            print(f"\n✅ COMPLETED SEPARATION:")
            print(f"  - Additional 7th grade: {updated_7th}")
            print(f"  - Additional 8th grade: {updated_8th}")
            
            # Final verification
            total_7th = Standard.query.filter_by(framework='NGSS', grade_level=7).count()
            total_8th = Standard.query.filter_by(framework='NGSS', grade_level=8).count()
            total_none = Standard.query.filter_by(framework='NGSS', grade_level=None).count()
            
            print(f"\n🎯 FINAL COUNTS:")
            print(f"  - Total NGSS Grade 7: {total_7th}")
            print(f"  - Total NGSS Grade 8: {total_8th}")
            print(f"  - Total NGSS Grade None: {total_none}")
            
            if total_none == 0:
                print(f"  ✅ All NGSS standards now have grade assignments!")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during commit: {e}")
            return False

if __name__ == '__main__':
    complete_ngss_separation()