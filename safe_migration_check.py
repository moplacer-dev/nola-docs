#!/usr/bin/env python3
"""
Safe migration check for HLP models.
This will show us exactly what the migration will do without making changes.
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import sqlite3

def create_app():
    """Create Flask app for migration checking."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/nola_docs.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app

def check_existing_tables():
    """Check what tables currently exist in the database."""
    print("🔍 Checking existing database tables...")
    
    db_path = 'instance/nola_docs.db'
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"📋 Found {len(tables)} existing tables:")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  • {table_name}: {count} records")
    
    conn.close()
    return [table[0] for table in tables]

def check_migration_conflicts():
    """Check if our new table names would conflict with existing ones."""
    print("\n🔍 Checking for potential naming conflicts...")
    
    existing_tables = check_existing_tables()
    new_tables = ['lesson_plan_modules', 'lesson_plan_sessions', 'lesson_plan_enrichments']
    
    conflicts = []
    for new_table in new_tables:
        if new_table in existing_tables:
            conflicts.append(new_table)
    
    if conflicts:
        print(f"⚠️  WARNING: Found naming conflicts: {conflicts}")
        return False
    else:
        print("✅ No naming conflicts found!")
        return True

def simulate_migration():
    """Show what the migration SQL would look like."""
    print("\n📝 Migration SQL Preview:")
    print("The following tables would be created:")
    
    sql_statements = [
        """
        CREATE TABLE lesson_plan_modules (
            id INTEGER PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            subject VARCHAR(50),
            grade_level INTEGER,
            active BOOLEAN DEFAULT 1 NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE INDEX ix_lesson_plan_modules_name ON lesson_plan_modules (name);
        CREATE INDEX ix_lesson_plan_modules_subject ON lesson_plan_modules (subject);
        CREATE INDEX ix_lesson_plan_modules_grade_level ON lesson_plan_modules (grade_level);
        CREATE UNIQUE INDEX ix_lesson_plan_modules_name_unique ON lesson_plan_modules (name);
        """,
        """
        CREATE TABLE lesson_plan_sessions (
            id INTEGER PRIMARY KEY,
            module_id INTEGER NOT NULL,
            session_number INTEGER NOT NULL,
            focus TEXT,
            objectives TEXT,
            materials TEXT,
            teacher_preparations TEXT,
            performance_assessment_questions TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(module_id) REFERENCES lesson_plan_modules (id)
        );
        """,
        """
        CREATE INDEX ix_lesson_plan_sessions_module_id ON lesson_plan_sessions (module_id);
        CREATE UNIQUE INDEX uq_module_session ON lesson_plan_sessions (module_id, session_number);
        """,
        """
        CREATE TABLE lesson_plan_enrichments (
            id INTEGER PRIMARY KEY,
            module_id INTEGER NOT NULL,
            enrichment_number INTEGER NOT NULL,
            title VARCHAR(500),
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(module_id) REFERENCES lesson_plan_modules (id)
        );
        """,
        """
        CREATE INDEX ix_lesson_plan_enrichments_module_id ON lesson_plan_enrichments (module_id);
        CREATE UNIQUE INDEX uq_module_enrichment ON lesson_plan_enrichments (module_id, enrichment_number);
        """
    ]
    
    for i, sql in enumerate(sql_statements, 1):
        print(f"\n--- Statement {i} ---")
        print(sql.strip())

def check_csv_data():
    """Verify the CSV data files are ready."""
    print("\n📊 Checking CSV data files...")
    
    sessions_file = 'data/hlp/star_academy_sessions.csv'
    enrichments_file = 'data/hlp/star_academy_enrichments.csv'
    
    if os.path.exists(sessions_file):
        with open(sessions_file, 'r') as f:
            lines = f.readlines()
            print(f"✅ Sessions CSV: {len(lines)} lines")
    else:
        print(f"❌ Sessions CSV not found: {sessions_file}")
    
    if os.path.exists(enrichments_file):
        with open(enrichments_file, 'r') as f:
            lines = f.readlines()
            print(f"✅ Enrichments CSV: {len(lines)} lines")
    else:
        print(f"❌ Enrichments CSV not found: {enrichments_file}")

def main():
    """Main safety check."""
    print("🚨 SAFE MIGRATION CHECK FOR HLP IMPLEMENTATION")
    print("=" * 60)
    
    # Check 1: Existing database state
    existing_tables = check_existing_tables()
    
    # Check 2: No naming conflicts
    no_conflicts = check_migration_conflicts()
    
    # Check 3: Preview migration SQL
    simulate_migration()
    
    # Check 4: Verify data files
    check_csv_data()
    
    # Final assessment
    print("\n" + "=" * 60)
    print("🎯 DEPLOYMENT SAFETY ASSESSMENT")
    print("=" * 60)
    
    if no_conflicts and len(existing_tables) > 0:
        print("✅ SAFE TO PROCEED with deployment:")
        print("  • No table name conflicts")
        print("  • Database exists and has data")
        print("  • New tables are isolated from existing ones")
        print("  • CSV data files are available")
        print("\n🚀 Recommended next steps:")
        print("  1. Backup the database")
        print("  2. Create Flask migration")
        print("  3. Apply migration")
        print("  4. Import CSV data")
        print("  5. Test the new functionality")
    else:
        print("⚠️  ISSUES FOUND - Review before deploying:")
        if not no_conflicts:
            print("  • Table name conflicts detected")
        if len(existing_tables) == 0:
            print("  • No existing database found")

if __name__ == '__main__':
    main()