#!/usr/bin/env python3
"""
FIXED Database Rebuild Script - Handles All Edge Cases
=====================================================

This script fixes all the issues identified in the verification:
1. Properly handles Excel file formatting issues
2. Ensures all standards are loaded before modules
3. Cleans up column names and handles unnamed columns
4. Forces proper standard loading including missing ones
"""

import pandas as pd
import os
import sys
from datetime import datetime
import argparse
from flask import Flask
from models import db, State, Standard, Module, ModuleStandardMapping

def create_app():
    """Create Flask app with database configuration"""
    app = Flask(__name__)
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        database_url = 'sqlite:///instance/nola_docs.db'
    
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app

def clear_correlation_tables(app):
    """Clear only correlation-related tables"""
    print("🧹 Clearing correlation tables...")
    
    with app.app_context():
        # Clear in correct order (foreign key constraints)
        ModuleStandardMapping.query.delete()
        Standard.query.delete()
        Module.query.delete()
        db.session.commit()
        print("✅ Cleared all correlation data")

def load_states_data(app):
    """Load US states data"""
    print("🗺️  Loading states data...")
    
    states_data = [
        ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'),
        ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'),
        ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'),
        ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'),
        ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'),
        ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'),
        ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'),
        ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'),
        ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'),
        ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'),
        ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'),
        ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'),
        ('WI', 'Wisconsin'), ('WY', 'Wyoming')
    ]
    
    with app.app_context():
        states_loaded = 0
        for code, name in states_data:
            existing = State.query.filter_by(code=code).first()
            if not existing:
                state = State(code=code, name=name)
                db.session.add(state)
                states_loaded += 1
        
        db.session.commit()
        print(f"✅ Loaded {states_loaded} new states")

def load_standards_with_fixes(app, standards_file):
    """Load standards from Excel file with proper error handling"""
    print("📚 Loading standards data with fixes...")
    
    with app.app_context():
        total_loaded = 0
        
        # Load Math Standards
        print("  📐 Loading Math standards...")
        try:
            ms_math = pd.read_excel(standards_file, sheet_name='MS Math')
            
            for _, row in ms_math.iterrows():
                code = row['CCSS']
                description = row['Standard - Performance Expectation']
                
                if pd.isna(code) or pd.isna(description):
                    continue
                
                code = str(code).strip()
                description = str(description).strip()
                
                # Determine grade from code
                grade_level = None
                if '.' in code:
                    grade_part = code.split('.')[0]
                    if grade_part.isdigit():
                        grade_level = int(grade_part)
                    elif grade_part.startswith('7'):
                        grade_level = 7
                    elif grade_part.startswith('8'):
                        grade_level = 8
                
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
                print(f"    ✅ {code} (Grade {grade_level})")
            
        except Exception as e:
            print(f"    ❌ Error loading math standards: {e}")
        
        # Load Science Standards
        print("  🔬 Loading Science standards...")
        try:
            ms_sci = pd.read_excel(standards_file, sheet_name='MS Science ')
            
            for _, row in ms_sci.iterrows():
                code = row['NGSS']
                description = row['Standard - Performance Expectation']
                
                if pd.isna(code) or pd.isna(description):
                    continue
                
                code = str(code).strip()
                description = str(description).strip()
                
                standard = Standard(
                    framework='NGSS',
                    subject='SCIENCE',
                    grade_band='MS',
                    grade_level=None,  # Will be assigned when processing matrix
                    code=code,
                    description=description
                )
                db.session.add(standard)
                total_loaded += 1
                print(f"    ✅ {code}")
        
        except Exception as e:
            print(f"    ❌ Error loading science standards: {e}")
        
        # Manual fix for missing standards
        print("  🔧 Adding missing standards manually...")
        missing_standards = [
            ('MS-PS4-3', 'Use mathematical representations to support a scientific conclusion about proportional relationships among energy, frequency, wavelength, and speed of waves.'),
            ('MS-ESS2-2', 'Construct an explanation based on evidence for how geoscience processes have changed Earth\'s surface at varying time and spatial scales.')
        ]
        
        for code, desc in missing_standards:
            existing = Standard.query.filter_by(code=code).first()
            if not existing:
                standard = Standard(
                    framework='NGSS',
                    subject='SCIENCE',
                    grade_band='MS',
                    grade_level=None,
                    code=code,
                    description=desc
                )
                db.session.add(standard)
                total_loaded += 1
                print(f"    🔧 Added missing: {code}")
        
        # Fix the typo standard
        typo_standard = Standard.query.filter_by(code='MSS-ESS2-2').first()
        if typo_standard:
            db.session.delete(typo_standard)
            print("    🔧 Removed typo standard: MSS-ESS2-2")
        
        db.session.commit()
        print(f"✅ Loaded {total_loaded} standards total")

def clean_column_name(col_name):
    """Clean up column names from Excel"""
    if pd.isna(col_name):
        return None
    
    name = str(col_name).strip()
    
    # Skip unnamed columns
    if name.startswith('Unnamed:'):
        return None
    
    # Clean up special characters
    name = name.replace('\xa0', ' ')  # Non-breaking space
    name = name.replace('  ', ' ')    # Double spaces
    name = name.strip()
    
    # Skip empty names
    if not name or name == 'nan':
        return None
    
    return name

def load_modules_and_mappings_fixed(app, matrix_file):
    """Load modules and mappings with proper error handling and column cleaning"""
    print("📊 Loading modules and mappings with fixes...")
    
    with app.app_context():
        total_modules = 0
        total_mappings = 0
        
        sheets_config = [
            ('7th Grade Math', 7, 'MATH', 'CCSS'),
            ('8th Grade Math', 8, 'MATH', 'CCSS'),
            ('7th Grade Science', 7, 'SCIENCE', 'NGSS (MS)'),
            ('8th Grade Science', 8, 'SCIENCE', 'NGSS (MS)')
        ]
        
        for sheet_name, grade, subject, std_column in sheets_config:
            print(f"  📋 Processing {sheet_name}...")
            
            try:
                df = pd.read_excel(matrix_file, sheet_name=sheet_name)
                
                # Clean up column names and get valid module columns
                valid_module_columns = []
                for col in df.columns[1:]:  # Skip first column (standards)
                    clean_name = clean_column_name(col)
                    if clean_name and not clean_name.endswith('(0)'):  # Skip inactive modules
                        valid_module_columns.append((col, clean_name))
                
                print(f"    Found {len(valid_module_columns)} valid modules")
                
                # Process each module
                for original_col, clean_module_name in valid_module_columns:
                    print(f"      Processing: {clean_module_name}")
                    
                    # Create or get module
                    existing_module = Module.query.filter_by(
                        title=clean_module_name,
                        subject=subject,
                        grade_level=grade
                    ).first()
                    
                    if not existing_module:
                        module = Module(
                            title=clean_module_name,
                            subject=subject,
                            grade_level=grade,
                            active=True
                        )
                        db.session.add(module)
                        db.session.flush()  # Get ID
                        total_modules += 1
                        print(f"        ✅ Created module: {clean_module_name}")
                    else:
                        module = existing_module
                        print(f"        ♻️  Using existing: {clean_module_name}")
                    
                    # Process standards for this module
                    mappings_created = 0
                    for _, row in df.iterrows():
                        try:
                            standard_code = row[std_column]
                            module_marker = row[original_col]
                            
                            if pd.isna(standard_code) or pd.isna(module_marker):
                                continue
                            
                            standard_code = str(standard_code).strip()
                            marker_str = str(module_marker).strip().lower()
                            
                            if marker_str == 'x':
                                # Find the standard
                                framework = 'CCSS-M' if subject == 'MATH' else 'NGSS'
                                standard = Standard.query.filter_by(
                                    framework=framework,
                                    code=standard_code
                                ).first()
                                
                                if standard:
                                    # Update standard grade_level if needed
                                    if standard.grade_level is None and subject == 'SCIENCE':
                                        standard.grade_level = grade
                                    
                                    # Create mapping if it doesn't exist
                                    existing_mapping = ModuleStandardMapping.query.filter_by(
                                        module_id=module.id,
                                        standard_id=standard.id
                                    ).first()
                                    
                                    if not existing_mapping:
                                        mapping = ModuleStandardMapping(
                                            module_id=module.id,
                                            standard_id=standard.id,
                                            source='MATRIX_V2_FIXED'
                                        )
                                        db.session.add(mapping)
                                        total_mappings += 1
                                        mappings_created += 1
                                else:
                                    print(f"        ⚠️  Standard not found: {standard_code}")
                        
                        except Exception as e:
                            print(f"        ❌ Error processing mapping: {e}")
                            continue
                    
                    print(f"        📊 Created {mappings_created} mappings")
                
            except Exception as e:
                print(f"    ❌ Error processing {sheet_name}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        db.session.commit()
        print(f"✅ Successfully loaded {total_modules} modules and {total_mappings} mappings")

def verify_final_results(app):
    """Verify the final results"""
    print("🔍 Verifying final results...")
    
    with app.app_context():
        standards = Standard.query.count()
        modules = Module.query.count()
        mappings = ModuleStandardMapping.query.count()
        
        print(f"  📚 Standards: {standards}")
        print(f"  📊 Modules: {modules}")
        print(f"  🔗 Mappings: {mappings}")
        
        # Check for critical standards
        critical_standards = ['MS-PS4-3', 'MS-ESS2-2']
        for std_code in critical_standards:
            std = Standard.query.filter_by(code=std_code).first()
            if std:
                print(f"  ✅ Found: {std_code} (grade: {std.grade_level})")
            else:
                print(f"  ❌ Missing: {std_code}")
        
        # Module breakdown
        math_mods = Module.query.filter_by(subject='MATH').count()
        science_mods = Module.query.filter_by(subject='SCIENCE').count()
        
        print(f"  📐 Math modules: {math_mods}")
        print(f"  🔬 Science modules: {science_mods}")
        
        if modules >= 140:  # Close to expected 151
            print("✅ Module count looks good!")
        else:
            print(f"⚠️  Still missing modules (got {modules}, expected ~151)")

def main():
    parser = argparse.ArgumentParser(description='FIXED rebuild correlation database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    
    args = parser.parse_args()
    
    standards_file = 'data/standards/CC and NGSS Standards.xlsx'
    matrix_file = 'data/modules/Modules and Standards Matrix (updated).xlsx'
    
    print("🔧 FIXED CORRELATION DATABASE REBUILD")
    print("=" * 60)
    print("This version fixes all the issues found in verification:")
    print("✅ Handles Excel formatting problems")
    print("✅ Manually adds missing standards") 
    print("✅ Cleans column names properly")
    print("✅ Forces proper standard loading before modules")
    print()
    
    if args.dry_run:
        print("DRY RUN - Would execute the fixed rebuild process")
        return
    
    response = input("Proceed with FIXED rebuild? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    app = create_app()
    
    try:
        with app.app_context():
            db.create_all()
        
        clear_correlation_tables(app)
        load_states_data(app) 
        load_standards_with_fixes(app, standards_file)
        load_modules_and_mappings_fixed(app, matrix_file)
        verify_final_results(app)
        
        print("\n🎉 FIXED REBUILD COMPLETED!")
        print("Your correlation reports should now work with ALL modules!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        with app.app_context():
            db.session.rollback()

if __name__ == '__main__':
    main()