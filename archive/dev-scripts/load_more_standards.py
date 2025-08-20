#!/usr/bin/env python3
"""
Load more standards and create realistic mappings for better testing
"""

import os
import sys
import pandas as pd

# Add current directory to path
sys.path.insert(0, os.path.abspath('.'))

from flask import Flask
from models import db, State, Standard, Module, ModuleStandardMapping

# Create Flask app with absolute database path
app = Flask(__name__)
db_path = os.path.abspath('instance/nola_docs.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def load_more_data():
    with app.app_context():
        print("📚 Loading more standards for better testing...")
        
        # Load more standards from each sheet
        standards_path = 'data/standards/CC and NGSS Standards.xlsx'
        if not os.path.exists(standards_path):
            print(f"❌ Standards file not found: {standards_path}")
            return
        
        try:
            sheet_mapping = {
                'MS Science ': {'subject': 'Science', 'grade': '7th Grade', 'type': 'NGSS', 'code_col': 'NGSS', 'desc_col': 'Standard - Performance Expectation'},
                'MS Math': {'subject': 'Math', 'grade': '7th Grade', 'type': 'CCSS', 'code_col': 'CCSS', 'desc_col': 'Standard - Performance Expectation'},
                'HS Math': {'subject': 'Math', 'grade': '8th Grade', 'type': 'CCSS', 'code_col': 'CCSS', 'desc_col': 'Standard - Performance Expectation'},
                'HS Science': {'subject': 'Science', 'grade': '8th Grade', 'type': 'NGSS', 'code_col': 'NGSS', 'desc_col': 'Standard - Performance Expectation'},
            }
            
            total_added = 0
            
            for sheet_name, config in sheet_mapping.items():
                try:
                    df = pd.read_excel(standards_path, sheet_name=sheet_name)
                    print(f"  Processing {sheet_name} ({len(df)} standards)...")
                    
                    count = 0
                    for _, row in df.iterrows():  # Load ALL standards, not just first 10
                        try:
                            code = str(row[config['code_col']]).strip()
                            description = str(row[config['desc_col']]).strip()
                            
                            # Skip empty rows
                            if pd.isna(row[config['code_col']]) or code == 'nan' or code == '':
                                continue
                            
                            # Check if already exists
                            existing = Standard.query.filter_by(code=code).first()
                            if not existing:
                                # Clean up description
                                description = description.replace('\n', ' ').strip()
                                
                                standard = Standard(
                                    code=code,
                                    description=description[:500],  # Truncate if too long
                                    subject=config['subject'],
                                    grade_level=config['grade'],
                                    standard_type=config['type']
                                )
                                db.session.add(standard)
                                count += 1
                                
                        except Exception as e:
                            print(f"    ⚠️ Error processing standard: {e}")
                            continue
                    
                    print(f"    ✅ Added {count} new standards from {sheet_name}")
                    total_added += count
                    
                except Exception as e:
                    print(f"    ❌ Error processing sheet {sheet_name}: {e}")
            
            db.session.commit()
            print(f"✅ Total standards added: {total_added}")
            print(f"📊 Total standards in database: {Standard.query.count()}")
            
        except Exception as e:
            print(f"❌ Error loading standards: {e}")

if __name__ == '__main__':
    load_more_data()