#!/usr/bin/env python3
"""
SHELL-ONLY HLP SETUP
Run this directly in Render shell - NO MIGRATIONS NEEDED
"""
import os
from sqlalchemy import text

print("🚀 Shell HLP Setup - Starting...")

try:
    from app import app, db
    from models import LessonPlanModule, LessonPlanSession, LessonPlanEnrichment
    
    with app.app_context():
        
        print("📊 Creating HLP tables directly...")
        
        # Create tables with raw SQL - no migrations needed
        db.engine.execute(text("""
        CREATE TABLE IF NOT EXISTS lesson_plan_modules (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            subject VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        db.engine.execute(text("""
        CREATE TABLE IF NOT EXISTS lesson_plan_sessions (
            id SERIAL PRIMARY KEY,
            module_id INTEGER NOT NULL REFERENCES lesson_plan_modules(id),
            session_number INTEGER NOT NULL,
            focus TEXT,
            objectives TEXT,
            materials TEXT,
            teacher_preparations TEXT,
            performance_assessment_questions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        db.engine.execute(text("""
        CREATE TABLE IF NOT EXISTS lesson_plan_enrichments (
            id SERIAL PRIMARY KEY,
            module_id INTEGER NOT NULL REFERENCES lesson_plan_modules(id),
            enrichment_number INTEGER NOT NULL,
            title VARCHAR(200),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        db.session.commit()
        print("✅ Tables created!")
        
        print("📊 Clearing existing data...")
        db.engine.execute(text("DELETE FROM lesson_plan_enrichments"))
        db.engine.execute(text("DELETE FROM lesson_plan_sessions"))
        db.engine.execute(text("DELETE FROM lesson_plan_modules"))
        db.session.commit()
        
        print("📊 Adding sample data...")
        
        # Add Weather module
        db.engine.execute(text("""
        INSERT INTO lesson_plan_modules (name, subject) 
        VALUES ('Weather v1.1', 'Science')
        """))
        db.session.commit()
        
        # Get module ID
        result = db.engine.execute(text("SELECT id FROM lesson_plan_modules WHERE name = 'Weather v1.1'"))
        module_id = result.fetchone()[0]
        
        # Add session
        db.engine.execute(text("""
        INSERT INTO lesson_plan_sessions 
        (module_id, session_number, focus, objectives, materials, teacher_preparations, performance_assessment_questions)
        VALUES (:module_id, 1, 
        'Layers of the Atmosphere; Weather Measurement',
        '• Define weather and climate.
• Learn the composition and layers of the atmosphere.  
• Use a computerized weather station to measure weather conditions.',
        'Weather Monitor',
        'Ensure the Weather Station has been operational for 24 hours prior to the start of Session 1.',
        '1. The student can define the troposphere, including its locations and thickness.')
        """), {'module_id': module_id})
        
        # Add enrichments
        enrichments = [
            (1, 'Dew Point Calculation', 'Using information learned about dew point, calculate dew point when given temperature and humidity.'),
            (2, 'Temperature Conversion', 'Convert temperatures from Celsius to Fahrenheit and Fahrenheit to Celsius.'),
            (3, 'Temperature Equivalence', 'Answer the following question: At what temperature in Celsius would be the same as the temperature in Fahrenheit?'),
            (4, 'Relative Humidity Calculation', 'After learning about relative humidity, calculate relative humidity with the given temperature and water content.')
        ]
        
        for enrich_num, title, desc in enrichments:
            db.engine.execute(text("""
            INSERT INTO lesson_plan_enrichments 
            (module_id, enrichment_number, title, description)
            VALUES (:module_id, :enrich_num, :title, :desc)
            """), {'module_id': module_id, 'enrich_num': enrich_num, 'title': title, 'desc': desc})
        
        db.session.commit()
        
        # Count records
        modules = db.engine.execute(text("SELECT COUNT(*) FROM lesson_plan_modules")).fetchone()[0]
        sessions = db.engine.execute(text("SELECT COUNT(*) FROM lesson_plan_sessions")).fetchone()[0]
        enrichments = db.engine.execute(text("SELECT COUNT(*) FROM lesson_plan_enrichments")).fetchone()[0]
        
        print(f"\n🎉 HLP SETUP COMPLETE!")
        print(f"✅ {modules} modules")
        print(f"✅ {sessions} sessions") 
        print(f"✅ {enrichments} enrichments")
        print("\n🚀 Feature is now live at: /create-horizontal-lesson-plan-streamlined")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()