#!/usr/bin/env python3
"""
Complete Data Verification Script
================================

This script provides a comprehensive analysis of what should be loaded vs what was actually loaded.
Run this to get 100% certainty about your data accuracy.
"""

import pandas as pd
import os
import sys
from collections import defaultdict
from flask import Flask
from models import db, Standard, Module, ModuleStandardMapping

def create_app():
    """Create Flask app with database configuration"""
    app = Flask(__name__)
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        database_url = 'sqlite:///instance/nola_docs.db'
    
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app

def analyze_expected_data():
    """Analyze what SHOULD be in the database based on Excel files"""
    print("🔍 ANALYZING EXPECTED DATA FROM EXCEL FILES")
    print("=" * 60)
    
    standards_file = 'data/standards/CC and NGSS Standards.xlsx'
    matrix_file = 'data/modules/Modules and Standards Matrix (updated).xlsx'
    
    expected = {
        'standards': {'math': {}, 'science': {}},
        'modules': {'7_math': [], '8_math': [], '7_science': [], '8_science': []},
        'mappings': {'7_math': {}, '8_math': {}, '7_science': {}, '8_science': {}}
    }
    
    # Check files exist
    if not os.path.exists(standards_file):
        print(f"❌ Standards file missing: {standards_file}")
        return None
    
    if not os.path.exists(matrix_file):
        print(f"❌ Matrix file missing: {matrix_file}")
        return None
    
    print(f"✅ Both files found")
    
    # Analyze standards file
    print(f"\n📋 STANDARDS FILE ANALYSIS:")
    
    # Math standards
    ms_math = pd.read_excel(standards_file, sheet_name='MS Math')
    math_standards = []
    for _, row in ms_math.iterrows():
        if pd.notna(row['CCSS']) and pd.notna(row['Standard - Performance Expectation']):
            code = str(row['CCSS']).strip()
            desc = str(row['Standard - Performance Expectation']).strip()
            
            # Determine grade
            grade = None
            if '.' in code:
                grade_part = code.split('.')[0]
                if grade_part.isdigit():
                    grade = int(grade_part)
                elif grade_part.startswith('7'):
                    grade = 7
                elif grade_part.startswith('8'):
                    grade = 8
            
            math_standards.append({'code': code, 'desc': desc, 'grade': grade})
            expected['standards']['math'][code] = {'desc': desc, 'grade': grade}
    
    print(f"   Math standards: {len(math_standards)}")
    print(f"   Grade 7: {len([s for s in math_standards if s['grade'] == 7])}")
    print(f"   Grade 8: {len([s for s in math_standards if s['grade'] == 8])}")
    print(f"   No grade: {len([s for s in math_standards if s['grade'] is None])}")
    
    # Science standards
    ms_sci = pd.read_excel(standards_file, sheet_name='MS Science ')
    science_standards = []
    for _, row in ms_sci.iterrows():
        if pd.notna(row['NGSS']) and pd.notna(row['Standard - Performance Expectation']):
            code = str(row['NGSS']).strip()
            desc = str(row['Standard - Performance Expectation']).strip()
            science_standards.append({'code': code, 'desc': desc})
            expected['standards']['science'][code] = {'desc': desc}
    
    print(f"   Science standards: {len(science_standards)}")
    
    # Check for the problematic standards
    problem_standards = ['MS-PS4-3', 'MS-ESS2-2', 'MSS-ESS2-2']
    for std in problem_standards:
        if std in expected['standards']['science']:
            print(f"   ✅ Found: {std}")
        else:
            print(f"   ❌ Missing: {std}")
    
    # Analyze matrix file
    print(f"\n📊 MATRIX FILE ANALYSIS:")
    
    sheets_info = [
        ('7th Grade Math', '7_math', 'CCSS', 'MATH'),
        ('8th Grade Math', '8_math', 'CCSS', 'MATH'),
        ('7th Grade Science', '7_science', 'NGSS (MS)', 'SCIENCE'),
        ('8th Grade Science', '8_science', 'NGSS (MS)', 'SCIENCE')
    ]
    
    total_expected_modules = 0
    total_expected_mappings = 0
    
    for sheet_name, key, std_col, subject in sheets_info:
        print(f"\n   {sheet_name}:")
        
        df = pd.read_excel(matrix_file, sheet_name=sheet_name)
        
        # Get standards in this sheet
        sheet_standards = df[std_col].dropna().tolist()
        print(f"     Standards in sheet: {len(sheet_standards)}")
        
        # Check for problem standards
        for std in problem_standards:
            if std in sheet_standards:
                print(f"     ✅ Matrix has: {std}")
        
        # Get modules (exclude first column which is standards)
        module_columns = [col for col in df.columns[1:] if col.strip()]
        active_modules = []
        
        for mod_col in module_columns:
            clean_name = str(mod_col).strip().replace('\xa0', '').replace('  ', ' ')
            
            # Skip inactive modules marked with (0)
            if '(0)' in clean_name:
                continue
                
            active_modules.append(clean_name)
            expected['modules'][key].append(clean_name)
            
            # Count mappings for this module
            mappings_for_module = 0
            mapping_details = []
            for _, row in df.iterrows():
                standard = row[std_col]
                marker = row[mod_col]
                
                if pd.notna(standard) and pd.notna(marker) and str(marker).strip().lower() == 'x':
                    mappings_for_module += 1
                    mapping_details.append(str(standard).strip())
            
            if mappings_for_module > 0:
                expected['mappings'][key][clean_name] = mapping_details
                total_expected_mappings += mappings_for_module
        
        print(f"     Active modules: {len(active_modules)}")
        print(f"     Modules with mappings: {len([m for m in active_modules if m in expected['mappings'][key]])}")
        total_expected_modules += len(active_modules)
    
    print(f"\n📊 EXPECTED TOTALS:")
    print(f"   Standards: Math={len(expected['standards']['math'])}, Science={len(expected['standards']['science'])}")
    print(f"   Modules: {total_expected_modules}")
    print(f"   Mappings: {total_expected_mappings}")
    
    return expected

def analyze_actual_data(app):
    """Analyze what's ACTUALLY in the database"""
    print(f"\n🗄️  ANALYZING ACTUAL DATABASE DATA")
    print("=" * 60)
    
    with app.app_context():
        # Standards
        standards = Standard.query.all()
        math_standards = [s for s in standards if s.subject == 'MATH']
        science_standards = [s for s in standards if s.subject == 'SCIENCE']
        
        print(f"📋 ACTUAL STANDARDS:")
        print(f"   Total: {len(standards)}")
        print(f"   Math: {len(math_standards)}")
        print(f"   Science: {len(science_standards)}")
        
        # Grade breakdown
        math_7 = [s for s in math_standards if s.grade_level == 7]
        math_8 = [s for s in math_standards if s.grade_level == 8]
        sci_7 = [s for s in science_standards if s.grade_level == 7]  
        sci_8 = [s for s in science_standards if s.grade_level == 8]
        sci_none = [s for s in science_standards if s.grade_level is None]
        
        print(f"   Math Grade 7: {len(math_7)}")
        print(f"   Math Grade 8: {len(math_8)}")
        print(f"   Science Grade 7: {len(sci_7)}")
        print(f"   Science Grade 8: {len(sci_8)}")
        print(f"   Science No Grade: {len(sci_none)}")
        
        # Check for problem standards
        problem_standards = ['MS-PS4-3', 'MS-ESS2-2', 'MSS-ESS2-2']
        for std in problem_standards:
            found = Standard.query.filter_by(code=std).first()
            if found:
                print(f"   ✅ DB has: {std} (grade: {found.grade_level})")
            else:
                print(f"   ❌ DB missing: {std}")
        
        # Modules
        modules = Module.query.all()
        math_modules = [m for m in modules if m.subject == 'MATH']
        science_modules = [m for m in modules if m.subject == 'SCIENCE']
        
        print(f"\n📊 ACTUAL MODULES:")
        print(f"   Total: {len(modules)}")
        print(f"   Math: {len(math_modules)}")
        print(f"   Science: {len(science_modules)}")
        
        # Grade breakdown
        math_7_mods = [m for m in math_modules if m.grade_level == 7]
        math_8_mods = [m for m in math_modules if m.grade_level == 8]
        sci_7_mods = [m for m in science_modules if m.grade_level == 7]
        sci_8_mods = [m for m in science_modules if m.grade_level == 8]
        
        print(f"   Math Grade 7: {len(math_7_mods)}")
        print(f"   Math Grade 8: {len(math_8_mods)}")
        print(f"   Science Grade 7: {len(sci_7_mods)}")
        print(f"   Science Grade 8: {len(sci_8_mods)}")
        
        # Mappings
        mappings = ModuleStandardMapping.query.all()
        print(f"\n🔗 ACTUAL MAPPINGS:")
        print(f"   Total: {len(mappings)}")
        
        return {
            'standards': {'total': len(standards), 'math': len(math_standards), 'science': len(science_standards)},
            'modules': {'total': len(modules), 'math': len(math_modules), 'science': len(science_modules)},
            'mappings': len(mappings)
        }

def compare_expected_vs_actual(expected, actual):
    """Compare expected vs actual and highlight discrepancies"""
    print(f"\n⚖️  EXPECTED VS ACTUAL COMPARISON")
    print("=" * 60)
    
    # Standards comparison
    exp_math_standards = len(expected['standards']['math'])
    exp_science_standards = len(expected['standards']['science'])
    exp_total_standards = exp_math_standards + exp_science_standards
    
    print(f"📋 STANDARDS:")
    print(f"   Expected: {exp_total_standards} (Math: {exp_math_standards}, Science: {exp_science_standards})")
    print(f"   Actual:   {actual['standards']['total']} (Math: {actual['standards']['math']}, Science: {actual['standards']['science']})")
    
    std_diff = actual['standards']['total'] - exp_total_standards
    if std_diff == 0:
        print(f"   ✅ PERFECT MATCH")
    else:
        print(f"   {'📈' if std_diff > 0 else '📉'} Difference: {std_diff:+d}")
    
    # Modules comparison
    exp_total_modules = sum(len(modules) for modules in expected['modules'].values())
    
    print(f"\n📊 MODULES:")
    print(f"   Expected: {exp_total_modules}")
    print(f"   Actual:   {actual['modules']['total']}")
    
    mod_diff = actual['modules']['total'] - exp_total_modules
    if mod_diff == 0:
        print(f"   ✅ PERFECT MATCH")
    else:
        print(f"   {'📈' if mod_diff > 0 else '📉'} Difference: {mod_diff:+d}")
        
        if mod_diff < 0:
            print(f"   ❌ MISSING {abs(mod_diff)} MODULES - This is the problem!")
    
    # Mappings comparison  
    exp_total_mappings = sum(len(mappings) for mappings in expected['mappings'].values())
    
    print(f"\n🔗 MAPPINGS:")
    print(f"   Expected: {exp_total_mappings}")
    print(f"   Actual:   {actual['mappings']}")
    
    map_diff = actual['mappings'] - exp_total_mappings
    if map_diff == 0:
        print(f"   ✅ PERFECT MATCH")
    else:
        print(f"   {'📈' if map_diff > 0 else '📉'} Difference: {map_diff:+d}")

def detailed_module_analysis(expected):
    """Show exactly which modules should exist"""
    print(f"\n🔍 DETAILED MODULE BREAKDOWN")
    print("=" * 60)
    
    for key, modules in expected['modules'].items():
        grade, subject = key.split('_')
        grade_display = f"{grade}th Grade"
        subject_display = subject.title()
        
        print(f"\n{subject_display} {grade_display}: {len(modules)} modules")
        for i, module in enumerate(sorted(modules), 1):
            mappings_count = len(expected['mappings'][key].get(module, []))
            print(f"   {i:2d}. {module} ({mappings_count} standards)")

def main():
    print("🔍 COMPLETE DATA VERIFICATION")
    print("=" * 80)
    
    # Analyze expected data from Excel
    expected = analyze_expected_data()
    if not expected:
        print("❌ Cannot proceed - missing Excel files")
        return
    
    # Analyze actual data from database
    app = create_app()
    actual = analyze_actual_data(app)
    
    # Compare
    compare_expected_vs_actual(expected, actual)
    
    # Detailed breakdown
    detailed_module_analysis(expected)
    
    print(f"\n🎯 CONCLUSION:")
    exp_total_modules = sum(len(modules) for modules in expected['modules'].values())
    if actual['modules']['total'] == exp_total_modules:
        print("✅ Your database is 100% accurate!")
    else:
        diff = actual['modules']['total'] - exp_total_modules
        print(f"❌ You're missing {abs(diff)} modules from the database")
        print("   This explains why your correlation reports aren't showing all data")
        print("   The rebuild script had issues loading some modules")

if __name__ == '__main__':
    main()