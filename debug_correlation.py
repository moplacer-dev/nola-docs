#!/usr/bin/env python3
"""
Debug script for correlation table issues
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, build_correlation_subdoc, Module, Standard
from docxtpl import DocxTemplate
import tempfile
import shutil

def debug_correlation_issues():
    """Debug all potential issues with correlation table"""
    
    with app.app_context():
        print("=== DEBUG: Checking template and subdoc injection ===")
        
        # 1. Check data availability
        math_modules = Module.query.filter_by(subject='Math').limit(3).all()
        title_set = [m.title for m in math_modules]
        print(f"✓ title_set: {title_set}")
        
        standards = Standard.query.filter_by(subject='Math', grade_level='8th Grade').limit(5).all()
        all_standards = [s.code for s in standards]
        print(f"✓ all_standards: {all_standards}")
        
        # Mock some data
        module_to_standards = {
            title_set[0]: {all_standards[0], all_standards[1]} if len(all_standards) > 1 else set(),
            title_set[1]: {all_standards[2]} if len(all_standards) > 2 else set(),
            title_set[2]: {all_standards[0], all_standards[3]} if len(all_standards) > 3 else set(),
        }
        print(f"✓ module_to_standards: {module_to_standards}")
        
        if not title_set or not all_standards:
            print("❌ ISSUE: Empty data lists!")
            return
        
        # 2. Load template and check
        template_path = 'templates/docx_templates/correlation_report_master.docx'
        print(f"✓ Template path: {template_path}")
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
            shutil.copy2(template_path, temp_file.name)
            temp_template_path = temp_file.name
        
        try:
            doc = DocxTemplate(temp_template_path)
            print(f"✓ Template loaded successfully")
            
            # 3. Test subdoc creation
            print("\n=== Testing subdoc creation ===")
            subdoc = build_correlation_subdoc(doc, title_set, all_standards, module_to_standards)
            print(f"✓ Subdoc created: {type(subdoc)}")
            print(f"✓ Subdoc is not None: {subdoc is not None}")
            
            # 4. Test different context keys
            test_contexts = [
                {'correlation_table': subdoc},
                {'dynamic_correlation_table': subdoc},
                {'correlation_content': subdoc}
            ]
            
            for i, context in enumerate(test_contexts):
                try:
                    print(f"\n=== Testing context key: {list(context.keys())[0]} ===")
                    
                    # Create a fresh copy for each test
                    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file2:
                        shutil.copy2(template_path, temp_file2.name)
                        temp_template_path2 = temp_file2.name
                    
                    doc2 = DocxTemplate(temp_template_path2)
                    subdoc2 = build_correlation_subdoc(doc2, title_set, all_standards, module_to_standards)
                    
                    context_key = list(context.keys())[0]
                    context[context_key] = subdoc2
                    
                    doc2.render(context)
                    
                    output_path = f"generated_docs/DEBUG_Context_{i+1}_{context_key}.docx"
                    doc2.save(output_path)
                    print(f"✓ Document saved with context '{context_key}': {output_path}")
                    
                    # Clean up
                    if os.path.exists(temp_template_path2):
                        os.unlink(temp_template_path2)
                        
                except Exception as e:
                    print(f"❌ Error with context '{list(context.keys())[0]}': {e}")
            
        except Exception as e:
            print(f"❌ Error loading template or creating subdoc: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if os.path.exists(temp_template_path):
                os.unlink(temp_template_path)
        
        print(f"\n=== Check generated_docs/ for DEBUG_Context_*.docx files ===")

if __name__ == '__main__':
    debug_correlation_issues()