#!/usr/bin/env python3
"""
Production data loader for Render deployment
Loads FULL correlation report data from Excel files (same as local setup)
"""

import click
from flask.cli import with_appcontext
from models import db, State, Standard, Module, ModuleStandardMapping
import pandas as pd
import os
import re

@click.command()
@with_appcontext
def load_production_data():
    """Load FULL correlation report data into production database"""
    print("🚀 Loading FULL production data for correlation reports...")
    print("This includes all states, standards, modules, and mappings from Excel files")
    
    try:
        load_states()
        load_standards()
        load_modules() 
        load_module_standard_mappings()
        
        # Final summary
        print("\n🎉 FULL production data loading complete!")
        print("\nFinal counts:")
        print(f"  States: {State.query.count()}")
        print(f"  Standards: {Standard.query.count()}")
        print(f"  Modules: {Module.query.count()}")
        print(f"  Mappings: {ModuleStandardMapping.query.count()}")
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        db.session.rollback()
        raise

def load_states():
    """Load all 50 US states data"""
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
    
    print("Loading states...")
    state_count = 0
    for code, name in states_data:
        existing = State.query.filter_by(code=code).first()
        if not existing:
            state = State(code=code, name=name)
            db.session.add(state)
            state_count += 1
    
    db.session.commit()
    print(f"✅ Added {state_count} new states (Total: {State.query.count()})")

def load_standards():
    """Load CCSS and NGSS standards from Excel files"""
    
    standards_path = 'data/standards/CC and NGSS Standards.xlsx'
    if not os.path.exists(standards_path):
        print(f"⚠️  Standards file not found: {standards_path}")
        print("⚠️  Skipping standards loading")
        return
    
    print(f"Loading standards from {standards_path}...")
    
    try:
        excel_file = pd.ExcelFile(standards_path)
        
        # Process each sheet based on the structure we found
        sheet_mapping = {
            'MS Science ': {'subject': 'SCIENCE', 'grade_level': None, 'framework': 'NGSS', 'code_col': 'NGSS', 'desc_col': 'Standard - Performance Expectation'},
            'MS Math': {'subject': 'MATH', 'grade_level': 7, 'framework': 'CCSS-M', 'code_col': 'CCSS', 'desc_col': 'Standard - Performance Expectation'},
            'HS Math': {'subject': 'MATH', 'grade_level': 8, 'framework': 'CCSS-M', 'code_col': 'CCSS', 'desc_col': 'Standard - Performance Expectation'},
        }
        
        total_standards = 0
        for sheet_name, config in sheet_mapping.items():
            if sheet_name in excel_file.sheet_names:
                print(f"  Processing sheet: {sheet_name}")
                df = pd.read_excel(standards_path, sheet_name=sheet_name)
                
                count = 0
                for _, row in df.iterrows():
                    try:
                        code = str(row[config['code_col']]).strip()
                        description = str(row[config['desc_col']]).strip()
                        
                        # Skip empty rows
                        if pd.isna(row[config['code_col']]) or code == 'nan' or code == '':
                            continue
                        
                        # Clean up description
                        description = description.replace('\n', ' ').strip()
                        if len(description) > 500:  # Truncate if too long
                            description = description[:497] + "..."
                        
                        # Check if already exists
                        existing = Standard.query.filter_by(framework=config['framework'], code=code).first()
                        if not existing:
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
        print(f"✅ Total standards added: {total_standards} (Total: {Standard.query.count()})")
        
    except Exception as e:
        print(f"⚠️  Error reading standards file: {e}")

def load_modules():
    """Load Star Academy modules from Excel file"""
    modules_path = 'data/modules/Modules and Standards Matrix.xlsx'
    
    if not os.path.exists(modules_path):
        print(f"⚠️  Modules file not found: {modules_path}")
        print("⚠️  Skipping modules loading")
        return
    
    print(f"Loading modules from {modules_path}...")
    
    try:
        excel_file = pd.ExcelFile(modules_path)
        
        # Extract unique modules from the matrix sheets
        modules_set = set()
        
        sheet_mapping = {
            '7th Grade Math': {'subject': 'MATH', 'grade_level': 7},
            '8th Grade Math': {'subject': 'MATH', 'grade_level': 8}, 
            'MS Science': {'subject': 'SCIENCE', 'grade_level': None}
        }
        
        for sheet_name, config in sheet_mapping.items():
            if sheet_name in excel_file.sheet_names:
                print(f"  Processing sheet: {sheet_name}")
                df = pd.read_excel(modules_path, sheet_name=sheet_name)
                
                # Get module names from column headers (skip first 2 columns which are standards)
                module_columns = df.columns[2:]  # Skip 'CCSS/NGSS' and 'Unnamed: 1' columns
                
                for module_name in module_columns:
                    if module_name and module_name != 'Unnamed: 1' and not pd.isna(module_name):
                        # Clean up module name
                        clean_name = str(module_name).strip()
                        # Remove trailing numbers in parentheses like '(16)'
                        clean_name = re.sub(r'\s*\(\d+\)\s*$', '', clean_name).strip()
                        
                        if clean_name:
                            modules_set.add((clean_name, config['subject'], config['grade_level']))
        
        # Create Module records
        module_count = 0
        for module_title, subject, grade_level in modules_set:
            # Check if module already exists
            existing = Module.query.filter_by(title=module_title, subject=subject, grade_level=grade_level).first()
            if not existing:
                module = Module(
                    title=module_title,
                    subject=subject,
                    grade_level=grade_level,
                    active=True
                )
                db.session.add(module)
                module_count += 1
        
        db.session.commit()
        print(f"✅ Added {module_count} new modules (Total: {Module.query.count()})")
        
    except Exception as e:
        print(f"⚠️  Error reading modules file: {e}")

def load_module_standard_mappings():
    """Load module-to-standard mappings from Excel file"""
    mappings_path = 'data/modules/Modules and Standards Matrix.xlsx'
    
    if not os.path.exists(mappings_path):
        print(f"⚠️  Mappings file not found: {mappings_path}")
        print("⚠️  Skipping mappings loading")
        return
    
    print(f"Loading module-standard mappings from {mappings_path}...")
    
    try:
        excel_file = pd.ExcelFile(mappings_path)
        
        sheet_mapping = {
            '7th Grade Math': {'subject': 'MATH', 'grade_level': 7, 'standard_col': 'CCSS', 'framework': 'CCSS-M'},
            '8th Grade Math': {'subject': 'MATH', 'grade_level': 8, 'standard_col': 'CCSS', 'framework': 'CCSS-M'},
            'MS Science': {'subject': 'SCIENCE', 'grade_level': None, 'standard_col': 'NGSS (MS)', 'framework': 'NGSS'}
        }
        
        total_mappings = 0
        
        for sheet_name, config in sheet_mapping.items():
            if sheet_name not in excel_file.sheet_names:
                continue
                
            print(f"  Processing mappings from sheet: {sheet_name}")
            df = pd.read_excel(mappings_path, sheet_name=sheet_name)
            
            # Get module columns (skip first 2)
            module_columns = df.columns[2:]
            
            sheet_mappings = 0
            for _, row in df.iterrows():
                standard_code = str(row[config['standard_col']]).strip() if config['standard_col'] in row else ""
                
                if pd.isna(row.get(config['standard_col'])) or standard_code == 'nan' or not standard_code:
                    continue
                
                # Find the standard in database
                standard = Standard.query.filter_by(framework=config['framework'], code=standard_code).first()
                if not standard:
                    continue
                
                # Check each module column for this standard
                for module_col in module_columns:
                    if module_col == 'Unnamed: 1' or pd.isna(module_col):
                        continue
                        
                    cell_value = row.get(module_col)
                    if pd.isna(cell_value) or str(cell_value).strip() == '':
                        continue
                    
                    # Clean module name
                    clean_module_name = str(module_col).strip()
                    clean_module_name = re.sub(r'\s*\(\d+\)\s*$', '', clean_module_name).strip()
                    
                    # Find the module in database
                    module = Module.query.filter_by(
                        title=clean_module_name, 
                        subject=config['subject'],
                        grade_level=config['grade_level']
                    ).first()
                    
                    if module:
                        # Check if mapping already exists
                        existing = ModuleStandardMapping.query.filter_by(
                            module_id=module.id, 
                            standard_id=standard.id
                        ).first()
                        
                        if not existing:
                            mapping = ModuleStandardMapping(
                                module_id=module.id,
                                standard_id=standard.id,
                                source='EXCEL_MATRIX'
                            )
                            db.session.add(mapping)
                            sheet_mappings += 1
            
            print(f"  ✅ Added {sheet_mappings} mappings from {sheet_name}")
            total_mappings += sheet_mappings
        
        db.session.commit()
        print(f"✅ Total mappings added: {total_mappings} (Total: {ModuleStandardMapping.query.count()})")
        
    except Exception as e:
        print(f"⚠️  Error creating mappings: {e}")

if __name__ == '__main__':
    # This allows the script to be run directly for testing
    from app import app
    with app.app_context():
        load_production_data()