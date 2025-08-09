#!/usr/bin/env python3
"""
Simplified data loading script that works with the existing Flask app
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.abspath('.'))

# Set Flask app environment variable
os.environ['FLASK_APP'] = 'app.py'

# Import after setting environment
from flask import Flask
from models import db, State, Standard, Module, ModuleStandardMapping
import pandas as pd

# Create Flask app context manually
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/nola_docs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def simple_load():
    with app.app_context():
        print("🚀 Loading correlation report data...")
        
        # Load a few sample states
        print("Loading states...")
        sample_states = [('LA', 'Louisiana'), ('TX', 'Texas'), ('CA', 'California')]
        for code, name in sample_states:
            existing = State.query.filter_by(code=code).first()
            if not existing:
                state = State(code=code, name=name)
                db.session.add(state)
        db.session.commit()
        print(f"✅ Loaded {len(sample_states)} states")
        
        # Load standards from first sheet only to test
        standards_path = 'data/standards/CC and NGSS Standards.xlsx'
        if os.path.exists(standards_path):
            print("Loading sample standards...")
            try:
                df = pd.read_excel(standards_path, sheet_name='MS Math')  # Test with just one sheet
                count = 0
                
                for _, row in df.head(5).iterrows():  # Just load first 5 standards as test
                    try:
                        code = str(row['CCSS']).strip()
                        description = str(row['Standard - Performance Expectation']).strip()
                        
                        if pd.isna(row['CCSS']) or code == 'nan':
                            continue
                        
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
                            count += 1
                    except Exception as e:
                        print(f"Error processing standard: {e}")
                        continue
                
                db.session.commit()
                print(f"✅ Loaded {count} sample standards")
                
            except Exception as e:
                print(f"Error loading standards: {e}")
        
        # Load sample modules
        modules_path = 'data/modules/Modules and Standards Matrix.xlsx'
        if os.path.exists(modules_path):
            print("Loading sample modules...")
            try:
                df = pd.read_excel(modules_path, sheet_name='7th Grade Math')
                
                # Get first few module names from columns
                sample_modules = []
                for col in list(df.columns[2:7]):  # Just first 5 modules as test
                    if col and not pd.isna(col):
                        clean_name = str(col).strip()
                        import re
                        clean_name = re.sub(r'\s*\(\d+\)\s*$', '', clean_name).strip()
                        if clean_name:
                            sample_modules.append(clean_name)
                
                count = 0
                for module_name in sample_modules:
                    existing = Module.query.filter_by(title=module_name, subject='Math').first()
                    if not existing:
                        module = Module(
                            title=module_name,
                            subject='Math',
                            description=f'Math module from Star Academy'
                        )
                        db.session.add(module)
                        count += 1
                
                db.session.commit()
                print(f"✅ Loaded {count} sample modules")
                
            except Exception as e:
                print(f"Error loading modules: {e}")
        
        print("🎉 Sample data loading complete!")
        print("\nData loaded:")
        print(f"  States: {State.query.count()}")
        print(f"  Standards: {Standard.query.count()}")
        print(f"  Modules: {Module.query.count()}")
        print(f"  Mappings: {ModuleStandardMapping.query.count()}")

if __name__ == '__main__':
    simple_load()