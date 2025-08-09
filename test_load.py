#!/usr/bin/env python3
"""
Test data loading script using absolute database path
"""

import os
import sys
import pandas as pd

# Add current directory to path so we can import models
sys.path.insert(0, os.path.abspath('.'))

from flask import Flask
from models import db, State, Standard, Module, ModuleStandardMapping

# Create Flask app with absolute database path
app = Flask(__name__)
db_path = os.path.abspath('instance/nola_docs.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def test_load():
    with app.app_context():
        print("🧪 Testing correlation report data loading...")
        print(f"📁 Using database: {db_path}")
        
        # Check if database exists
        if not os.path.exists(db_path):
            print(f"❌ Database not found at {db_path}")
            print("Please run the Flask app first to create the database.")
            return
        
        # Test 1: Load sample states
        print("\n1️⃣ Loading sample states...")
        sample_states = [
            ('LA', 'Louisiana'), ('TX', 'Texas'), ('CA', 'California'), 
            ('NY', 'New York'), ('FL', 'Florida')
        ]
        
        states_added = 0
        for code, name in sample_states:
            existing = State.query.filter_by(code=code).first()
            if not existing:
                state = State(code=code, name=name)
                db.session.add(state)
                states_added += 1
        
        db.session.commit()
        print(f"✅ Added {states_added} new states (Total: {State.query.count()})")
        
        # Test 2: Load sample standards from one sheet
        print("\n2️⃣ Loading sample standards...")
        standards_path = 'data/standards/CC and NGSS Standards.xlsx'
        
        if not os.path.exists(standards_path):
            print(f"❌ Standards file not found: {standards_path}")
            return
        
        try:
            # Load just MS Math standards as a test
            df = pd.read_excel(standards_path, sheet_name='MS Math')
            print(f"📊 Found {len(df)} standards in MS Math sheet")
            
            standards_added = 0
            for _, row in df.head(10).iterrows():  # Load first 10 as test
                try:
                    code = str(row['CCSS']).strip()
                    description = str(row['Standard - Performance Expectation']).strip()
                    
                    # Skip empty rows
                    if pd.isna(row['CCSS']) or code == 'nan' or code == '':
                        continue
                    
                    # Check if already exists
                    existing = Standard.query.filter_by(code=code).first()
                    if not existing:
                        standard = Standard(
                            code=code,
                            description=description[:500],  # Truncate if too long
                            subject='Math',
                            grade_level='7th Grade',
                            standard_type='CCSS'
                        )
                        db.session.add(standard)
                        standards_added += 1
                        
                except Exception as e:
                    print(f"   ⚠️ Error processing standard: {e}")
                    continue
            
            db.session.commit()
            print(f"✅ Added {standards_added} new standards (Total: {Standard.query.count()})")
            
        except Exception as e:
            print(f"❌ Error loading standards: {e}")
        
        # Test 3: Load sample modules
        print("\n3️⃣ Loading sample modules...")
        modules_path = 'data/modules/Modules and Standards Matrix.xlsx'
        
        if not os.path.exists(modules_path):
            print(f"❌ Modules file not found: {modules_path}")
            return
        
        try:
            excel_file = pd.ExcelFile(modules_path)
            
            # Load modules from ALL sheets
            sheet_mapping = {
                '7th Grade Math': 'Math',
                '8th Grade Math': 'Math', 
                'MS Science': 'Science'
            }
            
            modules_added = 0
            all_modules = set()
            
            for sheet_name, subject in sheet_mapping.items():
                if sheet_name in excel_file.sheet_names:
                    print(f"    Processing {sheet_name}...")
                    df = pd.read_excel(modules_path, sheet_name=sheet_name)
                    
                    # Get ALL module names from column headers (skip first 2 columns)
                    module_columns = df.columns[2:]  # ALL modules, not just first 5
                    
                    for col in module_columns:
                        if col and not pd.isna(col) and col != 'Unnamed: 1':
                            # Clean up module name
                            clean_name = str(col).strip()
                            # Remove trailing numbers in parentheses like '(16)'
                            import re
                            clean_name = re.sub(r'\s*\(\d+\)\s*$', '', clean_name).strip()
                            
                            if clean_name:
                                all_modules.add((clean_name, subject))
            
            # Create Module records for all unique modules
            for module_title, subject in all_modules:
                # Check if already exists
                existing = Module.query.filter_by(title=module_title, subject=subject).first()
                if not existing:
                    module = Module(
                        title=module_title,
                        subject=subject,
                        description=f'{subject} module from Star Academy'
                    )
                    db.session.add(module)
                    modules_added += 1
            
            db.session.commit()
            print(f"✅ Added {modules_added} new modules (Total: {Module.query.count()})")
            
        except Exception as e:
            print(f"❌ Error loading modules: {e}")
        
        # Test 4: Create sample mappings
        print("\n4️⃣ Creating sample mappings...")
        
        try:
            df = pd.read_excel(modules_path, sheet_name='7th Grade Math')
            
            # Get first few standards and modules for testing
            sample_standards = Standard.query.filter_by(subject='Math', grade_level='7th Grade').limit(3).all()
            sample_modules = Module.query.filter_by(subject='Math').limit(3).all()
            
            mappings_added = 0
            for standard in sample_standards:
                for module in sample_modules:
                    # Check if mapping already exists
                    existing = ModuleStandardMapping.query.filter_by(
                        module_id=module.id,
                        standard_id=standard.id,
                        grade_level='7th Grade'
                    ).first()
                    
                    if not existing:
                        mapping = ModuleStandardMapping(
                            module_id=module.id,
                            standard_id=standard.id,
                            grade_level='7th Grade'
                        )
                        db.session.add(mapping)
                        mappings_added += 1
            
            db.session.commit()
            print(f"✅ Added {mappings_added} new mappings (Total: {ModuleStandardMapping.query.count()})")
            
        except Exception as e:
            print(f"❌ Error creating mappings: {e}")
        
        # Summary
        print("\n📋 SUMMARY:")
        print(f"  🏛️  States: {State.query.count()}")
        print(f"  📚 Standards: {Standard.query.count()}")
        print(f"  📖 Modules: {Module.query.count()}")
        print(f"  🔗 Mappings: {ModuleStandardMapping.query.count()}")
        
        print("\n🎉 Test data loading complete!")
        print("\n🌐 Next steps:")
        print("1. Start the Flask app: python app.py")
        print("2. Visit: http://localhost:5000/create-correlation-report")
        print("3. Test the correlation report generation")

if __name__ == '__main__':
    test_load()