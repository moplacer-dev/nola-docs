#!/usr/bin/env python3
"""Smoke test for template instance consistency"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from docxtpl import DocxTemplate
from app import set_cell_text, shade_cell

def smoke_test():
    """Test minimal subdoc injection with single template instance"""
    
    TEMPLATE_PATH = "templates/docx_templates/correlation_report_master.docx"
    
    if not os.path.exists(TEMPLATE_PATH):
        print(f"❌ Template not found: {TEMPLATE_PATH}")
        return
    
    print("=== Smoke Test: Single Template Instance ===")
    
    try:
        # 1) Create ONE template instance
        tpl = DocxTemplate(TEMPLATE_PATH)
        print(f"✓ SMOKE tpl id: {id(tpl)}")
        
        # 2) Build minimal subdoc FROM THIS EXACT INSTANCE
        mini = tpl.new_subdoc()
        tbl = mini.add_table(rows=2, cols=2)
        
        # Use safe helper functions
        set_cell_text(tbl.rows[0].cells[0], "Standard", "Rockwell", 8, True)
        set_cell_text(tbl.rows[0].cells[1], "Module A", "Rockwell", 8, True)
        set_cell_text(tbl.rows[1].cells[0], "8.NS.A.1", "Arial", 8, False)
        set_cell_text(tbl.rows[1].cells[1], "X", "Arial", 8, True)
        shade_cell(tbl.rows[1].cells[1], "8DC593")
        
        print("✓ Minimal table created with safe helpers")
        
        # 3) Render WITH THIS SAME INSTANCE
        context = {"correlation_table": mini}
        tpl.render(context)
        print(f"✓ Rendered with tpl id: {id(tpl)}")
        
        # 4) Save
        os.makedirs("generated_docs", exist_ok=True)
        output_path = "generated_docs/SMOKE_OK.docx"
        tpl.save(output_path)
        print(f"✓ Saved: {output_path}")
        
        # Check file size
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"✓ File exists, size: {size} bytes")
            if size > 30000:
                print("🎉 SMOKE TEST PASSED!")
                print("   If this file opens in Word, then subdoc plumbing + placeholder are fine.")
                print("   If it doesn't open, the placeholder might be in a weird object.")
            else:
                print("⚠️  File size seems too small")
        
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    smoke_test()