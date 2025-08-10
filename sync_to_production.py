#!/usr/bin/env python3
"""
Sync local SQLite data to production PostgreSQL
This script helps transfer your working local data to the production environment
"""

import click
from flask.cli import with_appcontext
from models import db, State, Standard, Module, ModuleStandardMapping
import json
import os

@click.command()
@with_appcontext  
def sync_to_production():
    """Export local data that can be imported to production"""
    print("📦 EXPORTING LOCAL DATA FOR PRODUCTION SYNC")
    print("=" * 50)
    
    # Create export directory
    export_dir = "production_data_export"
    os.makedirs(export_dir, exist_ok=True)
    
    # Export states
    states = State.query.all()
    states_data = [{"code": s.code, "name": s.name} for s in states]
    with open(f"{export_dir}/states.json", "w") as f:
        json.dump(states_data, f, indent=2)
    print(f"✅ Exported {len(states_data)} states")
    
    # Export standards
    standards = Standard.query.all()
    standards_data = []
    for s in standards:
        standards_data.append({
            "framework": s.framework,
            "subject": s.subject,
            "grade_band": s.grade_band,
            "grade_level": s.grade_level,
            "code": s.code,
            "description": s.description
        })
    with open(f"{export_dir}/standards.json", "w") as f:
        json.dump(standards_data, f, indent=2)
    print(f"✅ Exported {len(standards_data)} standards")
    
    # Export modules
    modules = Module.query.all()
    modules_data = []
    for m in modules:
        modules_data.append({
            "title": m.title,
            "subject": m.subject,
            "grade_level": m.grade_level,
            "active": m.active
        })
    with open(f"{export_dir}/modules.json", "w") as f:
        json.dump(modules_data, f, indent=2)
    print(f"✅ Exported {len(modules_data)} modules")
    
    # Export mappings (with module titles and standard codes for easier import)
    mappings = (db.session.query(Module.title, Module.subject, Module.grade_level, 
                                Standard.code, Standard.framework, ModuleStandardMapping.source)
                .join(ModuleStandardMapping, Module.id==ModuleStandardMapping.module_id)
                .join(Standard, Standard.id==ModuleStandardMapping.standard_id)
                .all())
    
    mappings_data = []
    for mod_title, mod_subject, mod_grade, std_code, std_framework, source in mappings:
        mappings_data.append({
            "module_title": mod_title,
            "module_subject": mod_subject, 
            "module_grade_level": mod_grade,
            "standard_code": std_code,
            "standard_framework": std_framework,
            "source": source
        })
    
    with open(f"{export_dir}/mappings.json", "w") as f:
        json.dump(mappings_data, f, indent=2)
    print(f"✅ Exported {len(mappings_data)} mappings")
    
    # Create import script
    import_script = f'''#!/usr/bin/env python3
"""
Import script for production environment
Run this on your production server with: python import_production_data.py
"""

import json
import os
from app import app, db, State, Standard, Module, ModuleStandardMapping

def import_production_data():
    with app.app_context():
        print("🚀 IMPORTING DATA TO PRODUCTION DATABASE")
        
        try:
            # Clear existing data (careful!)
            print("🧹 Clearing existing correlation data...")
            ModuleStandardMapping.query.delete()
            Module.query.delete()
            Standard.query.delete()
            State.query.delete()
            db.session.commit()
            
            # Import states
            with open("states.json", "r") as f:
                states_data = json.load(f)
            for state_data in states_data:
                state = State(**state_data)
                db.session.add(state)
            db.session.commit()
            print(f"✅ Imported {{len(states_data)}} states")
            
            # Import standards
            with open("standards.json", "r") as f:
                standards_data = json.load(f)
            for std_data in standards_data:
                standard = Standard(**std_data)
                db.session.add(standard)
            db.session.commit()
            print(f"✅ Imported {{len(standards_data)}} standards")
            
            # Import modules
            with open("modules.json", "r") as f:
                modules_data = json.load(f)
            for mod_data in modules_data:
                module = Module(**mod_data)
                db.session.add(module)
            db.session.commit()
            print(f"✅ Imported {{len(modules_data)}} modules")
            
            # Import mappings
            with open("mappings.json", "r") as f:
                mappings_data = json.load(f)
            
            imported_mappings = 0
            for mapping_data in mappings_data:
                # Find module and standard by their identifiers
                module = Module.query.filter_by(
                    title=mapping_data["module_title"],
                    subject=mapping_data["module_subject"],
                    grade_level=mapping_data["module_grade_level"]
                ).first()
                
                standard = Standard.query.filter_by(
                    code=mapping_data["standard_code"],
                    framework=mapping_data["standard_framework"]
                ).first()
                
                if module and standard:
                    # Check if mapping already exists
                    existing = ModuleStandardMapping.query.filter_by(
                        module_id=module.id,
                        standard_id=standard.id
                    ).first()
                    
                    if not existing:
                        mapping = ModuleStandardMapping(
                            module_id=module.id,
                            standard_id=standard.id,
                            source=mapping_data["source"]
                        )
                        db.session.add(mapping)
                        imported_mappings += 1
            
            db.session.commit()
            print(f"✅ Imported {{imported_mappings}} mappings")
            
            print("\\n🎉 DATA IMPORT COMPLETE!")
            print(f"  States: {{State.query.count()}}")
            print(f"  Standards: {{Standard.query.count()}}")
            print(f"  Modules: {{Module.query.count()}}")
            print(f"  Mappings: {{ModuleStandardMapping.query.count()}}")
            
        except Exception as e:
            print(f"❌ Import failed: {{e}}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    import_production_data()
'''
    
    with open(f"{export_dir}/import_production_data.py", "w") as f:
        f.write(import_script)
    print(f"✅ Created import script")
    
    print(f"\n📁 All data exported to: {export_dir}/")
    print("📋 To sync to production:")
    print("1. Upload the export directory to your production server")
    print("2. Run: python import_production_data.py")
    print("3. Verify with: flask verify-production-data")

if __name__ == "__main__":
    sync_to_production()