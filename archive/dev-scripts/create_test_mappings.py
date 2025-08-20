#!/usr/bin/env python3
"""
Create some test mappings so we can see X marks in the correlation table
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.abspath('.'))

from flask import Flask
from models import db, Standard, Module, ModuleStandardMapping

# Create Flask app with absolute database path
app = Flask(__name__)
db_path = os.path.abspath('instance/nola_docs.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def create_test_mappings():
    with app.app_context():
        print("🔗 Creating test mappings for correlation report...")
        
        # Get some 8th Grade Math standards and Math modules
        standards = Standard.query.filter_by(subject='Math', grade_level='8th Grade').limit(10).all()
        modules = Module.query.filter_by(subject='Math').limit(5).all()
        
        print(f"Found {len(standards)} standards and {len(modules)} modules")
        
        if not standards or not modules:
            print("❌ Need both standards and modules to create mappings")
            return
        
        # Create some test mappings (each module covers some standards)
        mappings_created = 0
        
        for module in modules:
            # Each module will cover 3-5 random standards
            import random
            num_standards = random.randint(3, min(5, len(standards)))
            covered_standards = random.sample(standards, num_standards)
            
            for standard in covered_standards:
                # Check if mapping already exists
                existing = ModuleStandardMapping.query.filter_by(
                    module_id=module.id,
                    standard_id=standard.id,
                    grade_level='8th Grade'
                ).first()
                
                if not existing:
                    mapping = ModuleStandardMapping(
                        module_id=module.id,
                        standard_id=standard.id,
                        grade_level='8th Grade'
                    )
                    db.session.add(mapping)
                    mappings_created += 1
        
        db.session.commit()
        print(f"✅ Created {mappings_created} test mappings")
        print(f"📊 Total mappings in database: {ModuleStandardMapping.query.count()}")
        
        # Show what we created
        print("\n📋 Sample mappings:")
        sample_mappings = ModuleStandardMapping.query.join(Standard).join(Module).filter(
            Standard.subject == 'Math',
            Standard.grade_level == '8th Grade'
        ).limit(5).all()
        
        for mapping in sample_mappings:
            print(f"  • {mapping.module.title} covers {mapping.standard.code}")

if __name__ == '__main__':
    create_test_mappings()