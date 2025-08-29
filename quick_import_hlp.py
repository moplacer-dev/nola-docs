#!/usr/bin/env python3
"""
Quick HLP data import that uses the main app's database connection.
This will work immediately in production without waiting for deployment.
"""

import csv
import os

def import_hlp_data():
    """Import HLP data using the main app context."""
    from app import app, db
    from models import LessonPlanModule, LessonPlanSession, LessonPlanEnrichment
    
    with app.app_context():
        print("🚀 Importing HLP data...")
        
        # Clear existing data (optional - remove if you want to append)
        print("Clearing existing HLP data...")
        LessonPlanEnrichment.query.delete()
        LessonPlanSession.query.delete()
        LessonPlanModule.query.delete()
        db.session.commit()
        
        # Import sessions
        sessions_file = 'data/hlp/star_academy_sessions.csv'
        modules_created = {}
        sessions_imported = 0
        
        if os.path.exists(sessions_file):
            print(f"Importing sessions from {sessions_file}...")
            
            with open(sessions_file, 'r', encoding='utf-8') as file:
                # Skip first line which is just "star_academy_sessions" 
                next(file)
                reader = csv.DictReader(file)
                
                for row in reader:
                    module_name = row['Module'].strip()
                    
                    # Create module if it doesn't exist
                    if module_name not in modules_created:
                        existing_module = LessonPlanModule.query.filter_by(name=module_name).first()
                        if not existing_module:
                            module = LessonPlanModule(name=module_name, subject='Science')
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
        
        # Import enrichments
        enrichments_file = 'data/hlp/star_academy_enrichments.csv'
        enrichments_imported = 0
        
        if os.path.exists(enrichments_file):
            print(f"Importing enrichments from {enrichments_file}...")
            
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
        
        # Summary
        print("\n=== Import Summary ===")
        print(f"Modules: {LessonPlanModule.query.count()}")
        print(f"Sessions: {LessonPlanSession.query.count()}")
        print(f"Enrichments: {LessonPlanEnrichment.query.count()}")
        
        print("\n✅ HLP data import completed successfully!")

if __name__ == '__main__':
    import_hlp_data()