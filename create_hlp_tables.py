#!/usr/bin/env python3
"""
Direct table creation for HLP models.
This bypasses migration issues by creating tables directly.
"""

def create_hlp_tables():
    """Create HLP tables directly using the main app."""
    from app import app, db
    from models import LessonPlanModule, LessonPlanSession, LessonPlanEnrichment
    
    with app.app_context():
        try:
            print("🚀 Creating HLP tables directly...")
            
            # Check if tables already exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            hlp_tables = ['lesson_plan_modules', 'lesson_plan_sessions', 'lesson_plan_enrichments']
            
            for table_name in hlp_tables:
                if table_name in existing_tables:
                    print(f"✅ Table '{table_name}' already exists")
                else:
                    print(f"📝 Table '{table_name}' needs to be created")
            
            # Create all tables (this is safe - won't recreate existing ones)
            db.create_all()
            
            print("✅ HLP tables are ready!")
            
            # Verify tables exist
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            for table_name in hlp_tables:
                if table_name in existing_tables:
                    print(f"✓ Verified: {table_name}")
                else:
                    print(f"❌ Missing: {table_name}")
            
            print("\n🎯 Now you can import data with:")
            print("python quick_import_hlp.py")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    create_hlp_tables()