#!/usr/bin/env python3
"""
Script to safely fix the ModuleAnswerKeyForm by:
1. Removing the problematic field definitions
2. Adding safety checks for missing fields
"""

import re

def fix_app_py():
    """Apply systematic fixes to app.py"""
    
    # Read the file
    with open('app.py', 'r') as f:
        content = f.read()
    
    # 1. Remove the problematic field definitions
    lines = content.split('\n')
    
    # Find and remove the enrichment_dynamic_content line
    for i, line in enumerate(lines):
        if 'enrichment_dynamic_content = FieldList(FormField(DynamicFieldForm)' in line:
            lines[i] = '    # enrichment_dynamic_content field removed - moved to separate template'
            print(f"✅ Removed enrichment_dynamic_content field at line {i+1}")
            break
    
    # Find and remove the worksheet_answer_keys line
    for i, line in enumerate(lines):
        if 'worksheet_answer_keys = FieldList(FormField(WorksheetAnswerKeyForm)' in line:
            lines[i] = '    # worksheet_answer_keys field removed - moved to separate template'
            print(f"✅ Removed worksheet_answer_keys field at line {i+1}")
            break
    
    # 2. Add safety checks for field access
    content = '\n'.join(lines)
    
    # Replace form.enrichment_dynamic_content.data with safe access
    content = re.sub(
        r'form\.enrichment_dynamic_content\.data',
        'getattr(form, "enrichment_dynamic_content", type("MockField", (), {"data": []})).data',
        content
    )
    
    # Replace form.worksheet_answer_keys.data with safe access
    content = re.sub(
        r'form\.worksheet_answer_keys\.data',
        'getattr(form, "worksheet_answer_keys", type("MockField", (), {"data": []})).data',
        content
    )
    
    # 3. Remove template context variables
    content = re.sub(
        r"'enrichment_dynamic_content': enrichment_subdoc,",
        "'enrichment_dynamic_content': doc.new_subdoc(),  # Empty - moved to separate template",
        content
    )
    
    content = re.sub(
        r"'worksheet_answer_keys': worksheet_keys_subdoc",
        "'worksheet_answer_keys': doc.new_subdoc()  # Empty - moved to separate template",
        content
    )
    
    # 4. Fix autosave references
    content = re.sub(
        r"'enrichment_dynamic_content': data\.get\('enrichment_dynamic_content', \[\]\),",
        "# 'enrichment_dynamic_content': [],  # Removed - moved to separate template",
        content
    )
    
    content = re.sub(
        r"'worksheet_answer_keys': data\.get\('worksheet_answer_keys', \[\]\)",
        "# 'worksheet_answer_keys': []  # Removed - moved to separate template",
        content
    )
    
    # Write the fixed content
    with open('app.py', 'w') as f:
        f.write(content)
    
    print("✅ Applied all fixes to app.py")

if __name__ == '__main__':
    fix_app_py() 