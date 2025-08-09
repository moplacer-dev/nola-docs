#!/usr/bin/env python3
"""
Test script for correlation table generation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, generate_correlation_report_document, Module, Standard
from flask import Flask
import tempfile

def test_correlation_generation():
    """Test correlation table generation with exact specifications"""
    
    with app.app_context():
        print("=== Testing 8th Grade Math with 5 modules ===")
        
        # Get first 5 math modules  
        math_modules = Module.query.filter_by(subject='Math').limit(5).all()
        math_module_ids = [str(m.id) for m in math_modules]
        
        print(f"Selected modules: {[m.title for m in math_modules]}")
        
        if math_modules:
            try:
                doc_path = generate_correlation_report_document(
                    state='LA',
                    grade_level='8th Grade', 
                    subject='Math',
                    selected_module_ids=math_module_ids
                )
                print(f"✅ Math document generated: {doc_path}")
            except Exception as e:
                print(f"❌ Error generating Math document: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ No Math modules found")
        
        print("\n=== Testing 8th Grade Science with 10 modules ===")
        
        # Get first 10 science modules
        science_modules = Module.query.filter_by(subject='Science').limit(10).all()
        science_module_ids = [str(m.id) for m in science_modules]
        
        print(f"Selected modules: {[m.title for m in science_modules]}")
        
        if science_modules:
            try:
                doc_path = generate_correlation_report_document(
                    state='LA',
                    grade_level='8th Grade',
                    subject='Science', 
                    selected_module_ids=science_module_ids
                )
                print(f"✅ Science document generated: {doc_path}")
            except Exception as e:
                print(f"❌ Error generating Science document: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ No Science modules found")
        
        # Print some debug info
        print("\n=== Database Status ===")
        total_modules = Module.query.count()
        total_standards = Standard.query.count()
        math_standards = Standard.query.filter_by(subject='Math').count()
        science_standards = Standard.query.filter_by(subject='Science').count()
        
        print(f"Total modules: {total_modules}")
        print(f"Total standards: {total_standards}")
        print(f"Math standards: {math_standards}")  
        print(f"Science standards: {science_standards}")

if __name__ == '__main__':
    test_correlation_generation()