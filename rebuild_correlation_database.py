#!/usr/bin/env python3
"""
Clean Database Rebuild Script for Correlation Data
=================================================

This script completely rebuilds the correlation database tables with fresh data.
It works with both local SQLite and Render PostgreSQL databases.

WHAT THIS SCRIPT DOES:
1. Backs up existing data (optional)
2. Clears correlation tables (standards, modules, mappings)
3. Loads fresh data from your Excel files
4. Preserves non-correlation data (users, drafts, etc.)

FILES REQUIRED:
- data/standards/CC and NGSS Standards.xlsx
- data/modules/Modules and Standards Matrix (updated).xlsx

Usage:
    python rebuild_correlation_database.py [--backup] [--dry-run]
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
    
    # Use DATABASE_URL environment variable (works for both local and Render)
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Fallback to local SQLite
        database_url = 'sqlite:///instance/nola_docs.db'
    
    # Fix PostgreSQL URL format if needed (Render compatibility)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app

def backup_existing_data(app):
    """Create backup of existing correlation data"""
    print("Creating backup of existing data...")
    
    with app.app_context():
        backup_data = {
            'standards': [],
            'modules': [],
            'mappings': []
        }
        
        # Backup standards
        standards = Standard.query.all()
        for std in standards:
            backup_data['standards'].append({
                'framework': std.framework,
                'subject': std.subject,
                'grade_band': std.grade_band,
                'grade_level': std.grade_level,
                'code': std.code,
                'description': std.description
            })
        
        # Backup modules
        modules = Module.query.all()
        for mod in modules:
            backup_data['modules'].append({
                'title': mod.title,
                'subject': mod.subject,
                'grade_level': mod.grade_level,
                'active': mod.active
            })
        
        # Backup mappings
        mappings = ModuleStandardMapping.query.all()
        for mapping in mappings:
            backup_data['mappings'].append({
                'module_id': mapping.module_id,
                'standard_id': mapping.standard_id,
                'source': mapping.source
            })
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'correlation_backup_{timestamp}.json'
        
        import json
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        print(f"✅ Backup saved to: {backup_file}")
        print(f"   Standards: {len(backup_data['standards'])}")
        print(f"   Modules: {len(backup_data['modules'])}")
        print(f"   Mappings: {len(backup_data['mappings'])}")

def clear_correlation_tables(app):
    """Clear only correlation-related tables"""
    print("Clearing correlation tables...")
    
    with app.app_context():
        # Clear in correct order (foreign key constraints)
        ModuleStandardMapping.query.delete()
        Standard.query.delete()
        Module.query.delete()
        
        # Note: We keep States table as it's foundational
        print("✅ Cleared ModuleStandardMapping, Standard, and Module tables")

def load_states_data(app):
    """Load US states data"""
    print("Loading states data...")
    
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
            # Only add if doesn't exist
            existing = State.query.filter_by(code=code).first()
            if not existing:
                state = State(code=code, name=name)
                db.session.add(state)
                states_loaded += 1
        
        print(f"✅ Loaded {states_loaded} new states")

def load_standards_data(app, standards_file):
    """Load standards from Excel file"""
    print("Loading standards data...")
    
    if not os.path.exists(standards_file):
        raise FileNotFoundError(f"Standards file not found: {standards_file}")
    
    with app.app_context():
        total_loaded = 0
        
        # Load Math Standards (7th and 8th grade)
        print("  Loading Math standards...")
        ms_math = pd.read_excel(standards_file, sheet_name='MS Math')
        
        for _, row in ms_math.iterrows():
            code = row['CCSS']
            description = row['Standard - Performance Expectation']
            
            if pd.isna(code) or pd.isna(description):
                continue
            
            # Extract grade from code (7.RP.A.1 -> grade 7)
            grade_level = None
            if '.' in str(code):
                grade_part = str(code).split('.')[0]
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
                code=str(code).strip(),
                description=str(description).strip()
            )
            db.session.add(standard)
            total_loaded += 1
        
        # Load Science Standards (7th and 8th grade will be assigned via matrix)
        print("  Loading Science standards...")
        ms_sci = pd.read_excel(standards_file, sheet_name='MS Science ')
        
        for _, row in ms_sci.iterrows():
            code = row['NGSS']
            description = row['Standard - Performance Expectation']
            
            if pd.isna(code) or pd.isna(description):
                continue
            
            # We'll assign grade_level when processing the matrix
            standard = Standard(
                framework='NGSS',
                subject='SCIENCE',
                grade_band='MS',
                grade_level=None,  # Will be updated from matrix
                code=str(code).strip(),
                description=str(description).strip()
            )
            db.session.add(standard)
            total_loaded += 1
        
        print(f"✅ Loaded {total_loaded} standards")

def load_modules_and_mappings(app, matrix_file):
    """Load modules and their standard mappings from Excel file"""
    print("Loading modules and mappings...")
    
    if not os.path.exists(matrix_file):
        raise FileNotFoundError(f"Matrix file not found: {matrix_file}")
    
    with app.app_context():
        total_modules = 0
        total_mappings = 0
        
        # Process each grade/subject combination
        sheets = [
            ('7th Grade Math', 7, 'MATH', 'CCSS'),
            ('8th Grade Math', 8, 'MATH', 'CCSS'),
            ('7th Grade Science', 7, 'SCIENCE', 'NGSS (MS)'),
            ('8th Grade Science', 8, 'SCIENCE', 'NGSS (MS)')
        ]
        
        for sheet_name, grade, subject, std_column in sheets:
            print(f"  Processing {sheet_name}...")
            
            df = pd.read_excel(matrix_file, sheet_name=sheet_name)
            
            # Get module columns (all except first which is standards)
            module_columns = [col for col in df.columns[1:] if col.strip()]
            
            # Process each module
            for module_col in module_columns:
                # Clean module name (remove trailing spaces/special chars)
                module_title = str(module_col).strip().replace('\xa0', '').replace('  ', ' ')
                
                # Skip modules with (0) which seem to be inactive
                if '(0)' in module_title:
                    continue
                
                # Create or get module
                existing_module = Module.query.filter_by(
                    title=module_title, 
                    subject=subject, 
                    grade_level=grade
                ).first()
                
                if not existing_module:
                    module = Module(
                        title=module_title,
                        subject=subject,
                        grade_level=grade,
                        active=True
                    )
                    db.session.add(module)
                    db.session.flush()  # Get ID
                    total_modules += 1
                else:
                    module = existing_module
                
                # Process standards for this module
                for _, row in df.iterrows():
                    standard_code = row[std_column]
                    module_marker = row[module_col]
                    
                    if pd.isna(standard_code) or pd.isna(module_marker):
                        continue
                    
                    if str(module_marker).strip().lower() == 'x':
                        # Find the standard
                        framework = 'CCSS-M' if subject == 'MATH' else 'NGSS'
                        standard = Standard.query.filter_by(
                            framework=framework,
                            code=str(standard_code).strip()
                        ).first()
                        
                        if standard:
                            # Update standard grade_level if it's None (for science)
                            if standard.grade_level is None:
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
                                    source='MATRIX_V2'
                                )
                                db.session.add(mapping)
                                total_mappings += 1
                        else:
                            print(f"    Warning: Standard not found: {standard_code}")
        
        print(f"✅ Loaded {total_modules} modules and {total_mappings} mappings")

def verify_data_integrity(app):
    """Verify the loaded data integrity"""
    print("Verifying data integrity...")
    
    with app.app_context():
        # Check counts
        standards_count = Standard.query.count()
        modules_count = Module.query.count()
        mappings_count = ModuleStandardMapping.query.count()
        states_count = State.query.count()
        
        print(f"  States: {states_count}")
        print(f"  Standards: {standards_count}")
        print(f"  Modules: {modules_count}")
        print(f"  Mappings: {mappings_count}")
        
        # Check grade level assignments
        math_7th = Standard.query.filter_by(framework='CCSS-M', grade_level=7).count()
        math_8th = Standard.query.filter_by(framework='CCSS-M', grade_level=8).count()
        sci_7th = Standard.query.filter_by(framework='NGSS', grade_level=7).count()
        sci_8th = Standard.query.filter_by(framework='NGSS', grade_level=8).count()
        
        print(f"  Math 7th grade: {math_7th} standards")
        print(f"  Math 8th grade: {math_8th} standards")
        print(f"  Science 7th grade: {sci_7th} standards")
        print(f"  Science 8th grade: {sci_8th} standards")
        
        # Check for orphaned records
        orphaned_mappings = db.session.execute("""
            SELECT COUNT(*) FROM module_standard_mappings m
            LEFT JOIN modules mod ON m.module_id = mod.id
            LEFT JOIN standards std ON m.standard_id = std.id
            WHERE mod.id IS NULL OR std.id IS NULL
        """).scalar()
        
        if orphaned_mappings > 0:
            print(f"  ⚠️  Warning: {orphaned_mappings} orphaned mappings found")
        else:
            print("  ✅ No orphaned mappings")
        
        print("✅ Data integrity check complete")

def main():
    parser = argparse.ArgumentParser(description='Rebuild correlation database')
    parser.add_argument('--backup', action='store_true', 
                       help='Create backup before clearing data')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    # File paths
    standards_file = 'data/standards/CC and NGSS Standards.xlsx'
    matrix_file = 'data/modules/Modules and Standards Matrix (updated).xlsx'
    
    # Verify files exist
    if not os.path.exists(standards_file):
        print(f"❌ Standards file not found: {standards_file}")
        sys.exit(1)
    
    if not os.path.exists(matrix_file):
        print(f"❌ Matrix file not found: {matrix_file}")
        sys.exit(1)
    
    print("🚀 Starting Correlation Database Rebuild")
    print("=" * 50)
    print(f"Standards file: {standards_file}")
    print(f"Matrix file: {matrix_file}")
    print(f"Backup: {'Yes' if args.backup else 'No'}")
    print(f"Dry run: {'Yes' if args.dry_run else 'No'}")
    print()
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        print("This would:")
        print("1. Create backup (if requested)")
        print("2. Clear correlation tables")
        print("3. Load states data")
        print("4. Load standards from Excel")
        print("5. Load modules and mappings from Excel")
        print("6. Verify data integrity")
        return
    
    # Confirm before proceeding
    if not args.dry_run:
        response = input("This will completely rebuild correlation data. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return
    
    # Create Flask app
    app = create_app()
    
    try:
        # Create tables if they don't exist
        with app.app_context():
            db.create_all()
        
        # Step 1: Backup (optional)
        if args.backup:
            backup_existing_data(app)
        
        # Step 2: Clear correlation tables
        clear_correlation_tables(app)
        
        # Step 3: Load states
        load_states_data(app)
        
        # Step 4: Load standards
        load_standards_data(app, standards_file)
        
        # Step 5: Load modules and mappings
        load_modules_and_mappings(app, matrix_file)
        
        # Step 6: Commit all changes
        with app.app_context():
            db.session.commit()
            print("✅ All changes committed to database")
        
        # Step 7: Verify integrity
        verify_data_integrity(app)
        
        print()
        print("🎉 Database rebuild completed successfully!")
        print("Your correlation reports should now work with the updated data.")
        
    except Exception as e:
        print(f"❌ Error during rebuild: {e}")
        import traceback
        traceback.print_exc()
        
        # Rollback on error
        with app.app_context():
            db.session.rollback()
        
        sys.exit(1)

if __name__ == '__main__':
    main()