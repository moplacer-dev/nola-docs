#!/usr/bin/env python3
"""
Production data loader for Render deployment
Loads sample data into the correlation report tables
"""

import click
from flask.cli import with_appcontext
from models import db, State, Standard, Module, ModuleStandardMapping

@click.command()
@with_appcontext
def load_production_data():
    """Load sample data for correlation reports into production database"""
    print("🚀 Loading production data for correlation reports...")
    
    try:
        # Load states
        print("Loading states...")
        sample_states = [
            ('LA', 'Louisiana'),
            ('TX', 'Texas'),
            ('FL', 'Florida'),
            ('CA', 'California'),
            ('NY', 'New York'),
            ('GA', 'Georgia'),
            ('NC', 'North Carolina'),
            ('VA', 'Virginia')
        ]
        
        state_count = 0
        for code, name in sample_states:
            existing = State.query.filter_by(code=code).first()
            if not existing:
                state = State(code=code, name=name)
                db.session.add(state)
                state_count += 1
        
        db.session.commit()
        print(f"✅ Added {state_count} new states")
        
        # Load sample standards
        print("Loading sample standards...")
        sample_standards = [
            ('CCSS-M', 'MATH', 7, '7.RP.A.1', 'Compute unit rates associated with ratios of fractions'),
            ('CCSS-M', 'MATH', 7, '7.RP.A.2', 'Recognize and represent proportional relationships between quantities'),
            ('CCSS-M', 'MATH', 7, '7.EE.A.1', 'Apply properties of operations as strategies to add, subtract, factor, and expand linear expressions'),
            ('CCSS-M', 'MATH', 8, '8.EE.A.1', 'Know and apply the properties of integer exponents to generate equivalent numerical expressions'),
            ('CCSS-M', 'MATH', 8, '8.EE.A.2', 'Use square root and cube root symbols to represent solutions to equations'),
            ('CCSS-M', 'MATH', 8, '8.F.A.1', 'Understand that a function is a rule that assigns to each input exactly one output'),
            ('NGSS', 'SCIENCE', 7, 'MS-LS1-1', 'Conduct an investigation to provide evidence that living things are made of cells'),
            ('NGSS', 'SCIENCE', 7, 'MS-LS1-2', 'Develop and use a model to describe the function of a cell as a whole'),
            ('NGSS', 'SCIENCE', 8, 'MS-PS1-1', 'Develop models to describe the atomic composition of simple molecules and extended structures'),
            ('NGSS', 'SCIENCE', 8, 'MS-ETS1-1', 'Define the criteria and constraints of a design problem'),
        ]
        
        standard_count = 0
        for framework, subject, grade, code, description in sample_standards:
            existing = Standard.query.filter_by(framework=framework, code=code).first()
            if not existing:
                standard = Standard(
                    framework=framework,
                    subject=subject,
                    grade_level=grade,
                    code=code,
                    description=description
                )
                db.session.add(standard)
                standard_count += 1
        
        db.session.commit()
        print(f"✅ Added {standard_count} new standards")
        
        # Load sample modules
        print("Loading sample modules...")
        sample_modules = [
            # 7th Grade Math
            ('Environmental Math', 'MATH', 7),
            ('Algebraic Thinking', 'MATH', 7),
            ('Proportional Reasoning', 'MATH', 7),
            ('Statistics and Probability', 'MATH', 7),
            # 8th Grade Math  
            ('Functions and Linear Equations', 'MATH', 8),
            ('Geometric Applications', 'MATH', 8),
            ('Exponential Thinking', 'MATH', 8),
            ('Data Analysis', 'MATH', 8),
            # 7th Grade Science
            ('Life Science Fundamentals', 'SCIENCE', 7),
            ('Cell Structure and Function', 'SCIENCE', 7),
            ('Genetics and Heredity', 'SCIENCE', 7),
            # 8th Grade Science
            ('Chemistry Basics', 'SCIENCE', 8),
            ('Physics Concepts', 'SCIENCE', 8),
            ('Engineering Design', 'SCIENCE', 8),
        ]
        
        module_count = 0
        for title, subject, grade in sample_modules:
            existing = Module.query.filter_by(title=title, subject=subject, grade_level=grade).first()
            if not existing:
                module = Module(
                    title=title,
                    subject=subject,
                    grade_level=grade,
                    active=True
                )
                db.session.add(module)
                module_count += 1
        
        db.session.commit()
        print(f"✅ Added {module_count} new modules")
        
        # Create sample mappings (modules to standards)
        print("Creating sample module-standard mappings...")
        mapping_count = 0
        
        # Get some modules and standards to create mappings
        env_math = Module.query.filter_by(title='Environmental Math').first()
        functions_math = Module.query.filter_by(title='Functions and Linear Equations').first()
        life_science = Module.query.filter_by(title='Life Science Fundamentals').first()
        
        math_7_standards = Standard.query.filter_by(subject='MATH', grade_level=7).all()
        math_8_standards = Standard.query.filter_by(subject='MATH', grade_level=8).all()
        science_7_standards = Standard.query.filter_by(subject='SCIENCE', grade_level=7).all()
        
        # Create some sample mappings
        sample_mappings = []
        if env_math and math_7_standards:
            for standard in math_7_standards[:2]:  # Map first 2 standards
                sample_mappings.append((env_math.id, standard.id))
        
        if functions_math and math_8_standards:
            for standard in math_8_standards[:2]:  # Map first 2 standards
                sample_mappings.append((functions_math.id, standard.id))
                
        if life_science and science_7_standards:
            for standard in science_7_standards[:2]:  # Map first 2 standards
                sample_mappings.append((life_science.id, standard.id))
        
        for module_id, standard_id in sample_mappings:
            existing = ModuleStandardMapping.query.filter_by(module_id=module_id, standard_id=standard_id).first()
            if not existing:
                mapping = ModuleStandardMapping(
                    module_id=module_id,
                    standard_id=standard_id,
                    source='SAMPLE_DATA'
                )
                db.session.add(mapping)
                mapping_count += 1
        
        db.session.commit()
        print(f"✅ Added {mapping_count} new mappings")
        
        # Final summary
        print("\n🎉 Production data loading complete!")
        print("\nFinal counts:")
        print(f"  States: {State.query.count()}")
        print(f"  Standards: {Standard.query.count()}")
        print(f"  Modules: {Module.query.count()}")
        print(f"  Mappings: {ModuleStandardMapping.query.count()}")
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        db.session.rollback()
        raise

if __name__ == '__main__':
    # This allows the script to be run directly for testing
    from app import app
    with app.app_context():
        load_production_data()