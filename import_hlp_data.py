#!/usr/bin/env python3
"""
Import script for Streamlined Horizontal Lesson Plan (HLP) data.
Loads CSV data for Star Academy modules, sessions, and enrichments.
"""

import csv
import sys
import os
from flask import Flask
from models import db, LessonPlanModule, LessonPlanSession, LessonPlanEnrichment

def create_app():
    """Create Flask app for database operations."""
    app = Flask(__name__)
    
    # Use the same database configuration as the main app
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///instance/nola_docs.db')
    # Fix for Render PostgreSQL URL format
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def import_sessions_csv(file_path):
    """Import sessions data from CSV."""
    print(f"Importing sessions from {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        modules_created = {}
        sessions_imported = 0
        
        for row in reader:
            module_name = row['Module'].strip()
            
            # Create module if it doesn't exist
            if module_name not in modules_created:
                existing_module = LessonPlanModule.query.filter_by(name=module_name).first()
                if not existing_module:
                    module = LessonPlanModule(name=module_name)
                    db.session.add(module)
                    db.session.flush()  # Get the ID
                    modules_created[module_name] = module.id
                    print(f"Created module: {module_name}")
                else:
                    modules_created[module_name] = existing_module.id
                    print(f"Using existing module: {module_name}")
            
            # Create session
            session = LessonPlanSession(
                module_id=modules_created[module_name],
                session_number=int(row['Session']),
                focus=row['Focus'].strip() if row['Focus'] else None,
                objectives=row['Objectives'].strip() if row['Objectives'] else None,
                materials=row['Materials'].strip() if row['Materials'] else None,
                teacher_preparations=row['Teacher_Preparations'].strip() if row['Teacher_Preparations'] else None,
                performance_assessment_questions=row['Performance_Assessment_Questions'].strip() if row['Performance_Assessment_Questions'] else None
            )
            
            db.session.add(session)
            sessions_imported += 1
        
        db.session.commit()
        print(f"Successfully imported {sessions_imported} sessions for {len(modules_created)} modules.")
        return modules_created

def import_enrichments_csv(file_path, modules_created):
    """Import enrichments data from CSV."""
    print(f"Importing enrichments from {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        enrichments_imported = 0
        
        for row in reader:
            module_name = row['Module'].strip()
            
            # Find module ID
            if module_name not in modules_created:
                module = LessonPlanModule.query.filter_by(name=module_name).first()
                if not module:
                    print(f"Warning: Module '{module_name}' not found for enrichment")
                    continue
                modules_created[module_name] = module.id
            
            # Create enrichment
            enrichment = LessonPlanEnrichment(
                module_id=modules_created[module_name],
                enrichment_number=int(row['Enrichment_Number']),
                title=row['Title'].strip() if row['Title'] else None,
                description=row['Description'].strip() if row['Description'] else None
            )
            
            db.session.add(enrichment)
            enrichments_imported += 1
        
        db.session.commit()
        print(f"Successfully imported {enrichments_imported} enrichments.")

def main():
    """Main import function."""
    app = create_app()
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Clear existing data (optional - remove if you want to append)
        print("Clearing existing HLP data...")
        LessonPlanEnrichment.query.delete()
        LessonPlanSession.query.delete()
        LessonPlanModule.query.delete()
        db.session.commit()
        
        # Import data
        sessions_file = 'data/hlp/star_academy_sessions.csv'
        enrichments_file = 'data/hlp/star_academy_enrichments.csv'
        
        if not os.path.exists(sessions_file):
            print(f"Error: Sessions file not found at {sessions_file}")
            sys.exit(1)
        
        if not os.path.exists(enrichments_file):
            print(f"Error: Enrichments file not found at {enrichments_file}")
            sys.exit(1)
        
        # Import sessions first (creates modules)
        modules_created = import_sessions_csv(sessions_file)
        
        # Import enrichments
        import_enrichments_csv(enrichments_file, modules_created)
        
        print("\n=== Import Summary ===")
        print(f"Modules: {LessonPlanModule.query.count()}")
        print(f"Sessions: {LessonPlanSession.query.count()}")
        print(f"Enrichments: {LessonPlanEnrichment.query.count()}")
        
        print("\n=== Available Modules ===")
        for module in LessonPlanModule.query.all():
            session_count = module.sessions.count()
            enrichment_count = module.enrichments.count()
            print(f"- {module.name}: {session_count} sessions, {enrichment_count} enrichments")

if __name__ == '__main__':
    main()