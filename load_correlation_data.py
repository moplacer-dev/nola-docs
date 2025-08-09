#!/usr/bin/env python3
"""
Data loading script for Correlation Report feature
Run this script after placing your Excel files in the data/ directory

Expected file structure:
- data/standards/ccss.xlsx
- data/standards/ngss.xlsx  
- data/modules/modules_standards_matrix.xlsx

Usage:
    python load_correlation_data.py
"""

import pandas as pd
import os
from flask import Flask
from models import db, State, Standard, Module, ModuleStandardMapping

# Create Flask app for database context
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instance/nola_docs.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def load_states():
    """Load US states data"""
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
    for code, name in states_data:
        state = State.query.filter_by(code=code).first()
        if not state:
            state = State(code=code, name=name)
            db.session.add(state)
    
    db.session.commit()
    print(f"✅ Loaded {len(states_data)} states")

def load_standards():
    """Load CCSS and NGSS standards from Excel files"""
    
    standards_path = 'data/standards/CC and NGSS Standards.xlsx'
    if not os.path.exists(standards_path):
        print(f"⚠️  Standards file not found: {standards_path}")
        return
    
    print(f"Loading standards from {standards_path}...")
    
    try:
        excel_file = pd.ExcelFile(standards_path)
        
        # Process each sheet based on the structure we found
        sheet_mapping = {
            'MS Science ': {'subject': 'Science', 'grade': '7th Grade', 'type': 'NGSS', 'code_col': 'NGSS', 'desc_col': 'Standard - Performance Expectation'},
            'MS Math': {'subject': 'Math', 'grade': '7th Grade', 'type': 'CCSS', 'code_col': 'CCSS', 'desc_col': 'Standard - Performance Expectation'},
            'HS Math': {'subject': 'Math', 'grade': '8th Grade', 'type': 'CCSS', 'code_col': 'CCSS', 'desc_col': 'Standard - Performance Expectation'},
            'HS Science': {'subject': 'Science', 'grade': '8th Grade', 'type': 'NGSS', 'code_col': 'NGSS', 'desc_col': 'Standard - Performance Expectation'},
        }
        
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
                        
                        standard = Standard(
                            code=code,
                            description=description,
                            subject=config['subject'],
                            grade_level=config['grade'],
                            standard_type=config['type']
                        )
                        db.session.add(standard)
                        count += 1
                    except Exception as e:
                        print(f"    ⚠️  Error processing row: {e}")
                        continue
                
                print(f"  ✅ Loaded {count} standards from {sheet_name}")
        
        db.session.commit()
        
    except Exception as e:
        print(f"⚠️  Error reading standards file: {e}")

def load_modules():
    """Load Star Academy modules from Excel file"""
    modules_path = 'data/modules/Modules and Standards Matrix.xlsx'
    
    if not os.path.exists(modules_path):
        print(f"⚠️  Modules file not found: {modules_path}")
        return
    
    print(f"Loading modules from {modules_path}...")
    
    try:
        excel_file = pd.ExcelFile(modules_path)
        
        # Extract unique modules from the matrix sheets
        modules_set = set()
        
        sheet_mapping = {
            '7th Grade Math': 'Math',
            '8th Grade Math': 'Math', 
            'MS Science': 'Science'
        }
        
        for sheet_name, subject in sheet_mapping.items():
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
                        import re
                        clean_name = re.sub(r'\s*\(\d+\)\s*$', '', clean_name).strip()
                        
                        if clean_name:
                            modules_set.add((clean_name, subject))
        
        # Create Module records
        count = 0
        for module_title, subject in modules_set:
            # Check if module already exists
            existing = Module.query.filter_by(title=module_title, subject=subject).first()
            if not existing:
                module = Module(
                    title=module_title,
                    subject=subject,
                    description=f"{subject} module from Star Academy"
                )
                db.session.add(module)
                count += 1
        
        db.session.commit()
        print(f"✅ Loaded {count} unique modules")
        
    except Exception as e:
        print(f"⚠️  Error reading modules file: {e}")

def load_module_standard_mappings():
    """Load module-to-standard mappings from Excel file"""
    mappings_path = 'data/modules/Modules and Standards Matrix.xlsx'
    
    if not os.path.exists(mappings_path):
        print(f"⚠️  Mappings file not found: {mappings_path}")
        return
    
    print(f"Loading module-standard mappings from {mappings_path}...")
    
    try:
        excel_file = pd.ExcelFile(mappings_path)
        
        sheet_mapping = {
            '7th Grade Math': {'subject': 'Math', 'grade': '7th Grade', 'standard_col': 'CCSS'},
            '8th Grade Math': {'subject': 'Math', 'grade': '8th Grade', 'standard_col': 'CCSS'},
            'MS Science': {'subject': 'Science', 'grade': '7th Grade', 'standard_col': 'NGSS (MS)'}
        }
        
        total_mappings = 0
        
        for sheet_name, config in sheet_mapping.items():
            if sheet_name not in excel_file.sheet_names:
                continue
                
            print(f"  Processing mappings from sheet: {sheet_name}")
            df = pd.read_excel(mappings_path, sheet_name=sheet_name)
            
            # Get module columns (skip standards columns)
            module_columns = []
            for col in df.columns[2:]:  # Skip first 2 columns 
                if col and not pd.isna(col) and col != 'Unnamed: 1':
                    clean_name = str(col).strip()
                    # Remove trailing numbers in parentheses
                    import re
                    clean_name = re.sub(r'\s*\(\d+\)\s*$', '', clean_name).strip()
                    if clean_name:
                        module_columns.append((col, clean_name))
            
            sheet_mappings = 0
            
            # Process each row (each standard)
            for _, row in df.iterrows():
                try:
                    standard_code = str(row[config['standard_col']]).strip()
                    
                    # Skip empty rows
                    if pd.isna(row[config['standard_col']]) or standard_code == 'nan' or standard_code == '':
                        continue
                    
                    # Find the standard in database
                    standard = Standard.query.filter_by(
                        code=standard_code,
                        subject=config['subject'],
                        grade_level=config['grade']
                    ).first()
                    
                    if not standard:
                        print(f"    ⚠️  Standard not found: {standard_code}")
                        continue
                    
                    # Check each module column for 'x' marks
                    for original_col, clean_module_name in module_columns:
                        cell_value = str(row[original_col]).strip().lower()
                        
                        if cell_value == 'x':
                            # Find the module in database
                            module = Module.query.filter_by(
                                title=clean_module_name,
                                subject=config['subject']
                            ).first()
                            
                            if not module:
                                print(f"    ⚠️  Module not found: {clean_module_name}")
                                continue
                            
                            # Check if mapping already exists
                            existing = ModuleStandardMapping.query.filter_by(
                                module_id=module.id,
                                standard_id=standard.id,
                                grade_level=config['grade']
                            ).first()
                            
                            if not existing:
                                mapping = ModuleStandardMapping(
                                    module_id=module.id,
                                    standard_id=standard.id,
                                    grade_level=config['grade']
                                )
                                db.session.add(mapping)
                                sheet_mappings += 1
                                
                except Exception as e:
                    print(f"    ⚠️  Error processing mapping row: {e}")
                    continue
            
            print(f"  ✅ Created {sheet_mappings} mappings from {sheet_name}")
            total_mappings += sheet_mappings
        
        db.session.commit()
        print(f"✅ Total mappings created: {total_mappings}")
        
    except Exception as e:
        print(f"⚠️  Error reading mappings file: {e}")

def main():
    """Main loading function"""
    print("🚀 Starting data loading for Correlation Report feature...")
    
    with app.app_context():
        # Load in order (states first, then standards, then modules, then mappings)
        load_states()
        load_standards()
        load_modules()
        load_module_standard_mappings()
    
    print("🎉 Data loading complete!")
    print("\nNext steps:")
    print("1. Verify data was loaded correctly by checking the database")
    print("2. Test the correlation report feature in the web interface")
    print("3. Upload your docx template to templates/docx_templates/correlation_report_master.docx")

if __name__ == '__main__':
    main()