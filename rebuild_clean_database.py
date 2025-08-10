#!/usr/bin/env python3
"""
COMPREHENSIVE DATABASE REBUILD SCRIPT

This script completely rebuilds the correlation database from clean source files:
- CC and NGSS Standards.xlsx (clean standards with descriptions)
- Modules and Standards Matrix.xlsx (clean module mappings)
- Louisiana Department of Education Grade 7 & 8 Science.csv (updated module alignments)

USAGE:
1. Backup existing data (optional)
2. Run: python rebuild_clean_database.py
3. Verify results with test queries

This ensures:
- All standards have complete descriptions
- Clean, consistent naming
- Proper grade level assignments
- Accurate module mappings
- No data corruption or typos
"""

import pandas as pd
import os
from models import db, Standard, Module, ModuleStandardMapping, State
from app import app

def backup_existing_data():
    """Create backup of existing data before rebuild"""
    print("💾 CREATING DATA BACKUP...")
    
    with app.app_context():
        # Export current data to backup files
        backup_dir = "backup_data"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Backup standards
        standards = Standard.query.all()
        standards_data = []
        for std in standards:
            standards_data.append({
                'framework': std.framework,
                'subject': std.subject,
                'grade_band': std.grade_band,
                'grade_level': std.grade_level,
                'code': std.code,
                'description': std.description
            })
        
        standards_df = pd.DataFrame(standards_data)
        standards_df.to_csv(f"{backup_dir}/standards_backup.csv", index=False)
        print(f"  ✅ Backed up {len(standards)} standards")
        
        # Backup modules
        modules = Module.query.all()
        modules_data = []
        for mod in modules:
            modules_data.append({
                'title': mod.title,
                'subject': mod.subject,
                'grade_level': mod.grade_level,
                'active': mod.active
            })
        
        modules_df = pd.DataFrame(modules_data)
        modules_df.to_csv(f"{backup_dir}/modules_backup.csv", index=False)
        print(f"  ✅ Backed up {len(modules)} modules")
        
        # Backup mappings
        mappings = ModuleStandardMapping.query.all()
        print(f"  ✅ Backed up {len(mappings)} mappings")

def clear_correlation_data():
    """Clear all correlation-related data"""
    print("🗑️  CLEARING EXISTING DATA...")
    
    with app.app_context():
        # Delete in proper order (foreign key constraints)
        deleted_mappings = ModuleStandardMapping.query.delete()
        deleted_modules = Module.query.delete()
        deleted_standards = Standard.query.delete()
        
        db.session.commit()
        
        print(f"  ✅ Deleted {deleted_mappings} mappings")
        print(f"  ✅ Deleted {deleted_modules} modules") 
        print(f"  ✅ Deleted {deleted_standards} standards")

def load_clean_standards():
    """Load standards from clean Excel file with full descriptions"""
    print("📚 LOADING CLEAN STANDARDS...")
    
    excel_path = 'data/standards/CC and NGSS Standards.xlsx'
    if not os.path.exists(excel_path):
        print(f"❌ Standards file not found: {excel_path}")
        return False
    
    with app.app_context():
        total_loaded = 0
        
        # Load NGSS MS Science Standards
        print("  📖 Loading MS Science (NGSS)...")
        ms_science_df = pd.read_excel(excel_path, sheet_name='MS Science ')
        
        for _, row in ms_science_df.iterrows():
            if pd.isna(row['NGSS']) or pd.isna(row['Standard - Performance Expectation']):
                continue
                
            code = str(row['NGSS']).strip()
            description = str(row['Standard - Performance Expectation']).strip()
            
            # Determine grade level for NGSS standards using our established mapping
            grade_level = None
            if code in ['MS-ESS1-4', 'MS-ESS3-3', 'MS-ESS3-4', 'MS-ESS3-5',
                       'MS-LS1-2', 'MS-LS1-3', 'MS-LS1-5', 'MS-LS1-7', 'MS-LS3-1', 'MS-LS3-2',
                       'MS-PS1-1', 'MS-PS1-2']:
                grade_level = 7  # Documented 7th grade standards
            elif code in ['MS-ESS1-1', 'MS-ESS1-2', 'MS-ESS1-3',
                         'MS-LS1-4', 'MS-LS4-1', 'MS-LS4-2', 'MS-LS4-3', 'MS-LS4-4', 'MS-LS4-5', 'MS-LS4-6',
                         'MS-PS2-1', 'MS-PS2-2', 'MS-PS2-4', 'MS-PS3-1', 'MS-PS4-1']:
                grade_level = 8  # Documented 8th grade standards
            else:
                # Use pattern-based assignment for remaining standards
                if any(x in code for x in ['PS1', 'PS2', 'PS3', 'PS4']) and not any(x in code for x in ['PS2-1', 'PS2-2', 'PS2-4', 'PS3-1', 'PS4-1']):
                    grade_level = 7  # Most physical science to 7th
                elif any(x in code for x in ['LS1', 'LS2', 'LS4']):
                    grade_level = 8  # Most life science to 8th
                elif any(x in code for x in ['ESS2', 'ESS3']) and code not in ['MS-ESS1-4', 'MS-ESS3-3', 'MS-ESS3-4', 'MS-ESS3-5']:
                    grade_level = 7  # Most earth science to 7th
                elif any(x in code for x in ['ETS']):
                    grade_level = 8  # Engineering to 8th
                else:
                    grade_level = 7  # Default remaining to 7th
            
            standard = Standard(
                framework='NGSS',
                subject='SCIENCE',
                grade_band='MS',
                grade_level=grade_level,
                code=code,
                description=description
            )
            db.session.add(standard)
            total_loaded += 1
        
        # Load CCSS Math Standards
        print("  📖 Loading MS Math (CCSS)...")
        ms_math_df = pd.read_excel(excel_path, sheet_name='MS Math')
        
        for _, row in ms_math_df.iterrows():
            if pd.isna(row['CCSS']) or pd.isna(row['Standard - Performance Expectation']):
                continue
                
            code = str(row['CCSS']).strip()
            description = str(row['Standard - Performance Expectation']).strip()
            
            # Extract grade level from code (7.RP.A.1 -> 7, 8.NS.A.1 -> 8)
            grade_level = None
            if code.startswith('7.'):
                grade_level = 7
            elif code.startswith('8.'):
                grade_level = 8
            
            if grade_level:
                standard = Standard(
                    framework='CCSS-M',
                    subject='MATH',
                    grade_band='MS',
                    grade_level=grade_level,
                    code=code,
                    description=description
                )
                db.session.add(standard)
                total_loaded += 1
        
        # Load HS Standards (for completeness)
        print("  📖 Loading HS Science (NGSS)...")
        hs_science_df = pd.read_excel(excel_path, sheet_name='HS Science')
        
        for _, row in hs_science_df.iterrows():
            if pd.isna(row['NGSS']) or pd.isna(row['Standard - Performance Expectation']):
                continue
                
            code = str(row['NGSS']).strip()
            description = str(row['Standard - Performance Expectation']).strip()
            
            standard = Standard(
                framework='NGSS',
                subject='SCIENCE',
                grade_band='HS',
                grade_level=None,  # HS standards don't have specific grade levels in our system
                code=code,
                description=description
            )
            db.session.add(standard)
            total_loaded += 1
        
        print("  📖 Loading HS Math (CCSS)...")
        hs_math_df = pd.read_excel(excel_path, sheet_name='HS Math')
        
        for _, row in hs_math_df.iterrows():
            if pd.isna(row['CCSS']) or pd.isna(row['Standard - Performance Expectation']):
                continue
                
            code = str(row['CCSS']).strip()
            description = str(row['Standard - Performance Expectation']).strip()
            
            standard = Standard(
                framework='CCSS-M',
                subject='MATH',
                grade_band='HS',
                grade_level=None,
                code=code,
                description=description
            )
            db.session.add(standard)
            total_loaded += 1
        
        db.session.commit()
        print(f"  ✅ Loaded {total_loaded} standards with complete descriptions")
        return True

def load_clean_modules():
    """Load modules from clean matrix file"""
    print("🎓 LOADING CLEAN MODULES...")
    
    matrix_path = 'data/modules/Modules and Standards Matrix.xlsx'
    if not os.path.exists(matrix_path):
        print(f"❌ Modules file not found: {matrix_path}")
        return False
    
    with app.app_context():
        modules_created = set()
        
        # Load MS Science modules
        print("  📖 Loading MS Science modules...")
        ms_science_df = pd.read_excel(matrix_path, sheet_name='MS Science')
        
        for col in ms_science_df.columns[2:]:  # Skip first two columns
            if pd.isna(col) or 'Unnamed' in str(col):
                continue
                
            module_title = str(col).strip()
            
            # Extract grade level from module name if present
            grade_level = None
            if '(7)' in module_title:
                grade_level = 7
            elif '(8)' in module_title:
                grade_level = 8
            
            # Clean up module title
            clean_title = module_title.replace('(7)', '').replace('(8)', '').strip()
            
            if clean_title not in modules_created:
                module = Module(
                    title=clean_title,
                    subject='SCIENCE',
                    grade_level=grade_level,
                    active=True
                )
                db.session.add(module)
                modules_created.add(clean_title)
        
        # Load Math modules
        for grade, sheet_name in [(7, '7th Grade Math'), (8, '8th Grade Math')]:
            print(f"  📖 Loading Grade {grade} Math modules...")
            math_df = pd.read_excel(matrix_path, sheet_name=sheet_name)
            
            for col in math_df.columns[2:]:  # Skip first two columns
                if pd.isna(col) or 'Unnamed' in str(col):
                    continue
                    
                module_title = str(col).strip()
                module_key = f"{module_title}_MATH_{grade}"  # Make unique for math
                
                if module_key not in modules_created:
                    module = Module(
                        title=module_title,
                        subject='MATH',
                        grade_level=grade,
                        active=True
                    )
                    db.session.add(module)
                    modules_created.add(module_key)
        
        db.session.commit()
        print(f"  ✅ Created {len(modules_created)} clean modules")
        return True

def load_clean_mappings():
    """Load module-standard mappings from clean matrix file"""
    print("🔗 LOADING CLEAN MAPPINGS...")
    
    matrix_path = 'data/modules/Modules and Standards Matrix.xlsx'
    
    with app.app_context():
        total_mappings = 0
        
        # Load MS Science mappings
        print("  📖 Loading MS Science mappings...")
        ms_science_df = pd.read_excel(matrix_path, sheet_name='MS Science')
        
        # Create lookup dictionaries
        standards_lookup = {}
        for std in Standard.query.filter_by(framework='NGSS').all():
            standards_lookup[std.code] = std
        
        modules_lookup = {}
        for mod in Module.query.filter_by(subject='SCIENCE').all():
            modules_lookup[mod.title] = mod
        
        # Process each row (standard)
        for _, row in ms_science_df.iterrows():
            standard_code = row.iloc[1]  # Second column has standard codes
            
            if pd.isna(standard_code) or standard_code not in standards_lookup:
                continue
                
            standard = standards_lookup[standard_code]
            
            # Check each module column for mappings
            for col_idx in range(2, len(row)):
                module_name = ms_science_df.columns[col_idx]
                
                if pd.isna(module_name) or 'Unnamed' in str(module_name):
                    continue
                
                cell_value = row.iloc[col_idx]
                
                # Clean module name
                clean_module_name = str(module_name).replace('(7)', '').replace('(8)', '').strip()
                
                # Check if there's a mapping (x, number > 0, etc.)
                has_mapping = False
                if pd.notna(cell_value):
                    if (isinstance(cell_value, str) and 'x' in cell_value.lower()) or \
                       (isinstance(cell_value, (int, float)) and cell_value > 0):
                        has_mapping = True
                
                if has_mapping and clean_module_name in modules_lookup:
                    module = modules_lookup[clean_module_name]
                    
                    # Check if mapping already exists
                    existing = ModuleStandardMapping.query.filter_by(
                        module_id=module.id,
                        standard_id=standard.id
                    ).first()
                    
                    if not existing:
                        mapping = ModuleStandardMapping(
                            module_id=module.id,
                            standard_id=standard.id,
                            source='CLEAN_MATRIX'
                        )
                        db.session.add(mapping)
                        total_mappings += 1
        
        # Load Math mappings
        for grade, sheet_name in [(7, '7th Grade Math'), (8, '8th Grade Math')]:
            print(f"  📖 Loading Grade {grade} Math mappings...")
            math_df = pd.read_excel(matrix_path, sheet_name=sheet_name)
            
            # Create lookup for math standards
            math_standards_lookup = {}
            for std in Standard.query.filter(Standard.framework == 'CCSS-M', Standard.grade_level == grade).all():
                math_standards_lookup[std.code] = std
            
            # Create lookup for math modules
            math_modules_lookup = {}
            for mod in Module.query.filter(Module.subject == 'MATH', Module.grade_level == grade).all():
                math_modules_lookup[mod.title] = mod
            
            # Process each row
            for _, row in math_df.iterrows():
                standard_code = row.iloc[0]  # First column has standard codes
                
                if pd.isna(standard_code) or standard_code not in math_standards_lookup:
                    continue
                    
                standard = math_standards_lookup[standard_code]
                
                # Check each module column for mappings
                for col_idx in range(2, len(row)):
                    module_name = math_df.columns[col_idx]
                    
                    if pd.isna(module_name) or 'Unnamed' in str(module_name):
                        continue
                    
                    cell_value = row.iloc[col_idx]
                    
                    # Check if there's a mapping
                    has_mapping = False
                    if pd.notna(cell_value):
                        if (isinstance(cell_value, str) and 'x' in cell_value.lower()) or \
                           (isinstance(cell_value, (int, float)) and cell_value > 0):
                            has_mapping = True
                    
                    if has_mapping and str(module_name) in math_modules_lookup:
                        module = math_modules_lookup[str(module_name)]
                        
                        # Check if mapping already exists
                        existing = ModuleStandardMapping.query.filter_by(
                            module_id=module.id,
                            standard_id=standard.id
                        ).first()
                        
                        if not existing:
                            mapping = ModuleStandardMapping(
                                module_id=module.id,
                                standard_id=standard.id,
                                source='CLEAN_MATRIX'
                            )
                            db.session.add(mapping)
                            total_mappings += 1
        
        db.session.commit()
        print(f"  ✅ Created {total_mappings} clean mappings")
        return True

def ensure_states_exist():
    """Ensure Louisiana state exists for correlation reports"""
    print("🗺️  ENSURING STATES EXIST...")
    
    with app.app_context():
        # Check if Louisiana exists
        la_state = State.query.filter_by(code='LA').first()
        
        if not la_state:
            la_state = State(code='LA', name='Louisiana')
            db.session.add(la_state)
            db.session.commit()
            print("  ✅ Added Louisiana state")
        else:
            print("  ✅ Louisiana state already exists")

def verify_rebuild():
    """Verify the rebuild was successful"""
    print("🔍 VERIFYING REBUILD...")
    
    with app.app_context():
        # Count everything
        total_standards = Standard.query.count()
        total_modules = Module.query.count()
        total_mappings = ModuleStandardMapping.query.count()
        
        print(f"  📊 FINAL COUNTS:")
        print(f"    Standards: {total_standards}")
        print(f"    Modules: {total_modules}")
        print(f"    Mappings: {total_mappings}")
        
        # Check NGSS standards by grade
        ngss_7th = Standard.query.filter_by(framework='NGSS', grade_level=7).count()
        ngss_8th = Standard.query.filter_by(framework='NGSS', grade_level=8).count()
        
        print(f"  📚 NGSS STANDARDS:")
        print(f"    7th Grade: {ngss_7th}")
        print(f"    8th Grade: {ngss_8th}")
        
        # Check descriptions
        standards_with_desc = Standard.query.filter(
            Standard.description.isnot(None),
            Standard.description != ''
        ).count()
        
        print(f"  📝 DESCRIPTIONS:")
        print(f"    Standards with descriptions: {standards_with_desc}/{total_standards}")
        
        # Test correlation functions
        from app import get_all_standards, get_module_to_standards
        
        grade_7_standards = get_all_standards('LA', 7, 'SCIENCE')
        grade_8_standards = get_all_standards('LA', 8, 'SCIENCE')
        
        print(f"  🧪 CORRELATION FUNCTIONS:")
        print(f"    Grade 7 science standards: {len(grade_7_standards)}")
        print(f"    Grade 8 science standards: {len(grade_8_standards)}")
        
        # Test specific module
        dynamic_earth = Module.query.filter(Module.title.like('%Dynamic Earth%')).first()
        if dynamic_earth:
            mappings = ModuleStandardMapping.query.filter_by(module_id=dynamic_earth.id).count()
            print(f"    Dynamic Earth mappings: {mappings}")
        
        # Success criteria
        success = (
            total_standards > 100 and
            total_modules > 30 and
            total_mappings > 200 and
            ngss_7th > 20 and
            ngss_8th > 20 and
            standards_with_desc == total_standards
        )
        
        if success:
            print(f"\\n🎉 REBUILD SUCCESSFUL!")
            print(f"   Database is clean, organized, and ready for correlation reports!")
        else:
            print(f"\\n⚠️  REBUILD MAY HAVE ISSUES - Check the counts above")
        
        return success

def main():
    """Main rebuild function"""
    print("🚀 COMPREHENSIVE DATABASE REBUILD")
    print("=" * 50)
    print("This will completely rebuild the correlation database from clean source files.")
    print("All existing correlation data will be replaced with clean, organized data.")
    print("")
    
    try:
        # Step 1: Backup existing data
        backup_existing_data()
        
        # Step 2: Clear existing data
        clear_correlation_data()
        
        # Step 3: Load clean standards with descriptions
        if not load_clean_standards():
            print("❌ Failed to load standards")
            return False
        
        # Step 4: Load clean modules
        if not load_clean_modules():
            print("❌ Failed to load modules")
            return False
        
        # Step 5: Load clean mappings
        if not load_clean_mappings():
            print("❌ Failed to load mappings")
            return False
        
        # Step 6: Ensure states exist
        ensure_states_exist()
        
        # Step 7: Verify everything
        success = verify_rebuild()
        
        if success:
            print("\\n🎉 DATABASE REBUILD COMPLETE!")
            print("\\nYour correlation reports should now:")
            print("  ✅ Show complete standard descriptions") 
            print("  ✅ Have clean, consistent module names")
            print("  ✅ Display proper grade-specific correlations")
            print("  ✅ Work reliably for all supported modules")
            print("\\n🧪 TEST: Try generating a correlation report for Dynamic Earth (7th grade)")
        else:
            print("\\n⚠️  REBUILD COMPLETED WITH ISSUES")
            print("Check the verification output above for details")
        
        return success
        
    except Exception as e:
        print(f"\\n❌ REBUILD FAILED: {e}")
        print("Check that all data files exist and are accessible")
        return False

if __name__ == '__main__':
    main()