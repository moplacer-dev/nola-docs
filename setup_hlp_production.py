#!/usr/bin/env python3
"""
Simple production setup for HLP tables.
Run this in production to create tables and import data.
"""
import csv
import os

print("🚀 Setting up HLP feature in production...")

# Step 1: Create tables
try:
    from app import app, db
    from models import LessonPlanModule, LessonPlanSession, LessonPlanEnrichment
    
    with app.app_context():
        print("Creating HLP tables...")
        db.create_all()
        print("✅ Tables created!")
        
        # Step 2: Import data
        print("Importing HLP data...")
        
        # Clear existing data
        LessonPlanEnrichment.query.delete()
        LessonPlanSession.query.delete()
        LessonPlanModule.query.delete()
        db.session.commit()
        
        # Import sessions
        sessions_file = 'data/hlp/star_academy_sessions.csv'
        modules_created = {}
        sessions_imported = 0
        
        if os.path.exists(sessions_file):
            with open(sessions_file, 'r', encoding='utf-8') as file:
                next(file)  # Skip first line
                reader = csv.DictReader(file)
                
                for row in reader:
                    module_name = row['Module'].strip()
                    
                    # Create module
                    if module_name not in modules_created:
                        module = LessonPlanModule(name=module_name, subject='Science')
                        db.session.add(module)
                        db.session.flush()
                        modules_created[module_name] = module.id
                    
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
                print(f"✅ Imported {sessions_imported} sessions for {len(modules_created)} modules")
        
        # Import enrichments
        enrichments_file = 'data/hlp/star_academy_enrichments.csv'
        enrichments_imported = 0
        
        if os.path.exists(enrichments_file):
            with open(enrichments_file, 'r', encoding='utf-8') as file:
                first_line = file.readline().strip()
                if not first_line.startswith('Module,'):
                    pass
                else:
                    file.seek(0)
                reader = csv.DictReader(file)
                
                for row in reader:
                    module_name = row['Module'].strip()
                    
                    if module_name not in modules_created:
                        module = LessonPlanModule.query.filter_by(name=module_name).first()
                        if module:
                            modules_created[module_name] = module.id
                        else:
                            continue
                    
                    enrichment = LessonPlanEnrichment(
                        module_id=modules_created[module_name],
                        enrichment_number=int(row['Enrichment_Number']),
                        title=row['Title'].strip() if row['Title'] else None,
                        description=row['Description'].strip() if row['Description'] else None
                    )
                    db.session.add(enrichment)
                    enrichments_imported += 1
                
                db.session.commit()
                print(f"✅ Imported {enrichments_imported} enrichments")
        
        print("\n🎉 HLP SETUP COMPLETE!")
        print(f"✅ {LessonPlanModule.query.count()} modules")
        print(f"✅ {LessonPlanSession.query.count()} sessions") 
        print(f"✅ {LessonPlanEnrichment.query.count()} enrichments")
        print("\n🚀 Feature is now live at: /create-horizontal-lesson-plan-streamlined")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()