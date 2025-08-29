#!/usr/bin/env python3
"""
Test script for Streamlined Horizontal Lesson Plan (HLP) implementation.
Creates tables manually and tests basic functionality.
"""

import csv
import sys
import os
from flask import Flask
from sqlalchemy import text

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, LessonPlanModule, LessonPlanSession, LessonPlanEnrichment

def create_app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_hlp.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def create_tables_manually():
    """Create the HLP tables manually using raw SQL."""
    print("Creating tables manually...")
    
    # Create lesson_plan_modules table
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS lesson_plan_modules (
            id INTEGER PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            subject VARCHAR(50),
            grade_level INTEGER,
            active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create lesson_plan_sessions table
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS lesson_plan_sessions (
            id INTEGER PRIMARY KEY,
            module_id INTEGER NOT NULL,
            session_number INTEGER NOT NULL,
            focus TEXT,
            objectives TEXT,
            materials TEXT,
            teacher_preparations TEXT,
            performance_assessment_questions TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (module_id) REFERENCES lesson_plan_modules (id)
        )
    """))
    
    # Create lesson_plan_enrichments table
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS lesson_plan_enrichments (
            id INTEGER PRIMARY KEY,
            module_id INTEGER NOT NULL,
            enrichment_number INTEGER NOT NULL,
            title VARCHAR(500),
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (module_id) REFERENCES lesson_plan_enrichments (id)
        )
    """))
    
    db.session.commit()
    print("Tables created successfully!")

def import_test_data():
    """Import test data from CSV files."""
    print("Importing test data...")
    
    sessions_file = 'data/hlp/star_academy_sessions.csv'
    enrichments_file = 'data/hlp/star_academy_enrichments.csv'
    
    if not os.path.exists(sessions_file):
        print(f"Warning: Sessions file not found at {sessions_file}")
        return
    
    modules_created = {}
    sessions_imported = 0
    
    # Import sessions
    with open(sessions_file, 'r', encoding='utf-8') as file:
        # Skip first line which is just "star_academy_sessions" 
        next(file)
        reader = csv.DictReader(file)
        
        for row in reader:
            module_name = row['Module'].strip()
            
            # Create module if it doesn't exist
            if module_name not in modules_created:
                # Check if module already exists in database
                existing_module = db.session.execute(text(
                    "SELECT id FROM lesson_plan_modules WHERE name = :name"
                ), {'name': module_name}).fetchone()
                
                if not existing_module:
                    # Insert new module
                    result = db.session.execute(text("""
                        INSERT INTO lesson_plan_modules (name, subject, active) 
                        VALUES (:name, :subject, 1)
                    """), {'name': module_name, 'subject': 'Science'})
                    module_id = result.lastrowid
                    modules_created[module_name] = module_id
                    print(f"Created module: {module_name}")
                else:
                    modules_created[module_name] = existing_module[0]
                    print(f"Using existing module: {module_name}")
            
            # Insert session
            db.session.execute(text("""
                INSERT INTO lesson_plan_sessions 
                (module_id, session_number, focus, objectives, materials, teacher_preparations, performance_assessment_questions) 
                VALUES (:module_id, :session_number, :focus, :objectives, :materials, :teacher_prep, :assessment)
            """), {
                'module_id': modules_created[module_name],
                'session_number': int(row['Session']),
                'focus': row['Focus'].strip() if row['Focus'] else None,
                'objectives': row['Objectives'].strip() if row['Objectives'] else None,
                'materials': row['Materials'].strip() if row['Materials'] else None,
                'teacher_prep': row['Teacher_Preparations'].strip() if row['Teacher_Preparations'] else None,
                'assessment': row['Performance_Assessment_Questions'].strip() if row['Performance_Assessment_Questions'] else None
            })
            sessions_imported += 1
    
    db.session.commit()
    print(f"Imported {sessions_imported} sessions for {len(modules_created)} modules")
    
    # Import enrichments if file exists
    if os.path.exists(enrichments_file):
        enrichments_imported = 0
        
        with open(enrichments_file, 'r', encoding='utf-8') as file:
            # Check if first line is a header like "Module,Enrichment_Number,..."
            first_line = file.readline().strip()
            if not first_line.startswith('Module,'):
                # Skip the first line if it's not the real header
                pass
            else:
                # Go back to start if first line is the real header
                file.seek(0)
            reader = csv.DictReader(file)
            
            for row in reader:
                module_name = row['Module'].strip()
                
                if module_name not in modules_created:
                    existing_module = db.session.execute(text(
                        "SELECT id FROM lesson_plan_modules WHERE name = :name"
                    ), {'name': module_name}).fetchone()
                    
                    if existing_module:
                        modules_created[module_name] = existing_module[0]
                    else:
                        print(f"Warning: Module '{module_name}' not found for enrichment")
                        continue
                
                # Insert enrichment
                db.session.execute(text("""
                    INSERT INTO lesson_plan_enrichments 
                    (module_id, enrichment_number, title, description) 
                    VALUES (:module_id, :enrichment_number, :title, :description)
                """), {
                    'module_id': modules_created[module_name],
                    'enrichment_number': int(row['Enrichment_Number']),
                    'title': row['Title'].strip() if row['Title'] else None,
                    'description': row['Description'].strip() if row['Description'] else None
                })
                enrichments_imported += 1
        
        db.session.commit()
        print(f"Imported {enrichments_imported} enrichments")

def test_data_retrieval():
    """Test that we can retrieve data properly."""
    print("\n=== Testing Data Retrieval ===")
    
    # Get module count
    module_count = db.session.execute(text("SELECT COUNT(*) FROM lesson_plan_modules")).fetchone()[0]
    print(f"Modules in database: {module_count}")
    
    # Get session count
    session_count = db.session.execute(text("SELECT COUNT(*) FROM lesson_plan_sessions")).fetchone()[0]
    print(f"Sessions in database: {session_count}")
    
    # Get enrichment count
    enrichment_count = db.session.execute(text("SELECT COUNT(*) FROM lesson_plan_enrichments")).fetchone()[0]
    print(f"Enrichments in database: {enrichment_count}")
    
    # Show sample data
    print("\n=== Sample Module Data ===")
    modules = db.session.execute(text("SELECT id, name FROM lesson_plan_modules LIMIT 3")).fetchall()
    for module in modules:
        print(f"Module {module[0]}: {module[1]}")
        
        # Get sessions for this module
        sessions = db.session.execute(text(
            "SELECT session_number, focus FROM lesson_plan_sessions WHERE module_id = :id ORDER BY session_number"
        ), {'id': module[0]}).fetchall()
        
        for session in sessions:
            print(f"  Session {session[0]}: {session[1][:50]}...")

def test_table_generation():
    """Test the table generation function."""
    print("\n=== Testing Table Generation ===")
    
    try:
        # Get first module ID
        module_row = db.session.execute(text("SELECT id FROM lesson_plan_modules LIMIT 1")).fetchone()
        if not module_row:
            print("No modules found for testing table generation")
            return
        
        module_id = module_row[0]
        print(f"Testing table generation for module ID: {module_id}")
        
        # Import the table creation function
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from app import create_hlp_table
        
        # Test table generation
        table_doc = create_hlp_table([module_id])
        print("Table generation successful!")
        
        # Save test document
        test_filename = "test_hlp_table.docx"
        table_doc.save(test_filename)
        print(f"Test table saved as: {test_filename}")
        
    except Exception as e:
        print(f"Error testing table generation: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main test function."""
    print("🚀 Testing Streamlined HLP Implementation")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Create tables
            create_tables_manually()
            
            # Import data
            import_test_data()
            
            # Test data retrieval
            test_data_retrieval()
            
            # Test table generation
            test_table_generation()
            
            print("\n✅ All tests completed successfully!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    main()