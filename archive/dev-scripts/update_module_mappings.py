#!/usr/bin/env python3
"""
Update module mappings for NGSS standards using the Louisiana Department CSV data.
This will replace existing module mappings with the updated grade-specific alignments.
"""

from models import db, Standard, Module, ModuleStandardMapping
from app import app
import pandas as pd
import numpy as np

def load_csv_module_mappings():
    """Load module mappings from the CSV file"""
    csv_path = '/Users/moriahplacer/Desktop/Mo\'s Vault/nola.docs/data/modules/Louisiana Department of Education Grade 7 & 8 Science.csv'
    
    mappings = {'7th Grade': {}, '8th Grade': {}}
    
    try:
        # Read the CSV
        df = pd.read_csv(csv_path)
        print(f"📊 CSV loaded: {df.shape[0]} rows, {df.shape[1]} columns")
        
        # Process each row
        current_grade = None
        
        for idx, row in df.iterrows():
            # Check if this row indicates a grade level
            grade_col = df.columns[0]  # First column contains grade info
            if pd.notna(row[grade_col]):
                grade_info = str(row[grade_col]).strip()
                if 'Grade' in grade_info:
                    current_grade = grade_info
                    print(f"📚 Processing {current_grade}")
                    continue
            
            # Get the NGSS standard code from second column
            if len(df.columns) < 2:
                continue
                
            standard_col = df.columns[1]
            standard_code = str(row[standard_col]).strip()
            
            # Skip if not a valid NGSS code
            if standard_code == 'nan' or not (standard_code.startswith('MS-') or standard_code.startswith('HS-')):
                continue
                
            if current_grade not in mappings:
                mappings[current_grade] = {}
                
            mappings[current_grade][standard_code] = {}
            
            # Process each module column (starting from column 3)
            for col_idx in range(3, len(df.columns)):
                col_name = df.columns[col_idx]
                cell_value = row.iloc[col_idx]
                
                # Skip empty or non-numeric cells, or columns that look like headers
                if pd.isna(cell_value) or col_name.startswith('Unnamed'):
                    continue
                    
                # Clean up module name (remove numbers in parentheses)
                module_name = col_name.strip()
                if '(' in module_name and ')' in module_name:
                    # Remove the (number) pattern at the end
                    module_name = module_name.split('(')[0].strip()
                
                # Only include if there's a mapping indicator (x, number, etc.)
                if (isinstance(cell_value, str) and 'x' in str(cell_value).lower()) or \
                   (isinstance(cell_value, (int, float)) and cell_value > 0):
                    
                    if standard_code not in mappings[current_grade]:
                        mappings[current_grade][standard_code] = {}
                    mappings[current_grade][standard_code][module_name] = True
        
        # Print summary
        for grade, standards in mappings.items():
            if standards:
                print(f"  {grade}: {len(standards)} standards mapped")
                # Show some examples
                for std_code, modules in list(standards.items())[:3]:
                    print(f"    {std_code} -> {len(modules)} modules")
        
        return mappings
        
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return {}

def update_module_mappings():
    """Update module mappings based on CSV data"""
    
    print("🔄 UPDATING MODULE MAPPINGS")
    print("=" * 35)
    
    # Load CSV mappings
    csv_mappings = load_csv_module_mappings()
    
    if not csv_mappings:
        print("❌ No CSV mappings loaded")
        return False
    
    with app.app_context():
        # First, let's see what modules exist
        all_modules = Module.query.filter_by(subject='SCIENCE').all()
        print(f"\\n📋 EXISTING SCIENCE MODULES: {len(all_modules)}")
        
        module_map = {}
        for module in all_modules:
            # Create a mapping of simplified names to modules
            clean_name = module.title.strip()
            module_map[clean_name] = module
        
        print(f"   Module mapping created for {len(module_map)} modules")
        
        # Process each grade
        total_mappings_added = 0
        modules_not_found = set()
        standards_not_found = set()
        
        for grade, standards_dict in csv_mappings.items():
            if not standards_dict:
                continue
                
            print(f"\\n🎯 Processing {grade}...")
            grade_num = 7 if '7th' in grade else 8
            
            for standard_code, modules_dict in standards_dict.items():
                # Find the standard in database
                standard = Standard.query.filter_by(framework='NGSS', code=standard_code).first()
                if not standard:
                    standards_not_found.add(standard_code)
                    continue
                
                # Process each module for this standard
                for module_name in modules_dict.keys():
                    # Try to find matching module
                    module = None
                    
                    # Direct match first
                    if module_name in module_map:
                        module = module_map[module_name]
                    else:
                        # Try fuzzy matching
                        for db_module_name, db_module in module_map.items():
                            if module_name.lower() in db_module_name.lower() or \
                               db_module_name.lower() in module_name.lower():
                                module = db_module
                                break
                    
                    if not module:
                        modules_not_found.add(module_name)
                        continue
                    
                    # Check if mapping already exists
                    existing_mapping = ModuleStandardMapping.query.filter_by(
                        module_id=module.id,
                        standard_id=standard.id
                    ).first()
                    
                    if not existing_mapping:
                        # Create new mapping
                        mapping = ModuleStandardMapping(
                            module_id=module.id,
                            standard_id=standard.id,
                            source='CSV_GRADE_SPECIFIC'
                        )
                        db.session.add(mapping)
                        total_mappings_added += 1
        
        # Commit changes
        try:
            db.session.commit()
            print(f"\\n✅ MAPPING UPDATE COMPLETE:")
            print(f"  - New mappings added: {total_mappings_added}")
            print(f"  - Standards not found: {len(standards_not_found)}")
            print(f"  - Modules not found: {len(modules_not_found)}")
            
            if standards_not_found:
                print(f"  - Missing standards: {list(standards_not_found)[:5]}...")
            
            if modules_not_found:
                print(f"  - Missing modules: {list(modules_not_found)[:5]}...")
            
            # Summary of current state
            total_ngss_mappings = ModuleStandardMapping.query.join(Standard).filter(
                Standard.framework == 'NGSS'
            ).count()
            
            print(f"\\n📊 CURRENT STATE:")
            print(f"  - Total NGSS mappings: {total_ngss_mappings}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during commit: {e}")
            return False

def verify_grade_separation():
    """Verify that the grade separation worked correctly"""
    
    print("\\n🔍 VERIFYING GRADE SEPARATION")
    print("=" * 35)
    
    with app.app_context():
        # Check final counts
        ngss_7th = Standard.query.filter_by(framework='NGSS', grade_level=7).all()
        ngss_8th = Standard.query.filter_by(framework='NGSS', grade_level=8).all()
        ngss_none = Standard.query.filter_by(framework='NGSS', grade_level=None).all()
        
        print(f"📊 FINAL NGSS COUNTS:")
        print(f"  - Grade 7: {len(ngss_7th)} standards")
        print(f"  - Grade 8: {len(ngss_8th)} standards") 
        print(f"  - Grade None: {len(ngss_none)} standards")
        
        # Show samples from each grade
        if ngss_7th:
            print(f"\\n📚 Grade 7 Sample:")
            for std in ngss_7th[:5]:
                print(f"  - {std.code}")
                
        if ngss_8th:
            print(f"\\n📚 Grade 8 Sample:")
            for std in ngss_8th[:5]:
                print(f"  - {std.code}")
        
        # Check for any issues with High School standards
        hs_standards = [s for s in ngss_7th + ngss_8th if s.code.startswith('HS-')]
        if hs_standards:
            print(f"\\n⚠️  HIGH SCHOOL STANDARDS FOUND:")
            print(f"   These should probably be moved to high school grade levels:")
            for std in hs_standards[:5]:
                print(f"  - {std.code} (currently grade {std.grade_level})")

if __name__ == '__main__':
    print("🚀 Starting module mapping update process...")
    
    # First verify our grade separation
    verify_grade_separation()
    
    # Then update the mappings
    if update_module_mappings():
        print("\\n🎉 Module mapping update completed successfully!")
    else:
        print("\\n💥 Module mapping update failed!")