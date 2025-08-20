#!/usr/bin/env python3
"""
Debug why correlation reports aren't showing science module mappings after NGSS separation.
"""

from models import db, Standard, Module, ModuleStandardMapping
from app import app

def debug_correlation_mappings():
    """Debug correlation report mapping issues"""
    
    print("🔍 DEBUGGING CORRELATION REPORT MAPPINGS")
    print("=" * 50)
    
    with app.app_context():
        
        # 1. Check what science modules exist
        print("📚 SCIENCE MODULES:")
        science_modules = Module.query.filter_by(subject='SCIENCE').all()
        print(f"  Total science modules: {len(science_modules)}")
        
        if science_modules:
            for module in science_modules[:10]:
                print(f"    • {module.title} (Grade: {module.grade_level})")
            if len(science_modules) > 10:
                print(f"    ... and {len(science_modules) - 10} more")
        else:
            print("  ❌ NO SCIENCE MODULES FOUND!")
            return
        
        # 2. Check NGSS standards
        print(f"\n🧬 NGSS STANDARDS:")
        ngss_standards = Standard.query.filter_by(framework='NGSS').all()
        print(f"  Total NGSS standards: {len(ngss_standards)}")
        
        grade_counts = {}
        for std in ngss_standards:
            grade = std.grade_level
            if grade not in grade_counts:
                grade_counts[grade] = 0
            grade_counts[grade] += 1
        
        for grade, count in sorted(grade_counts.items(), key=lambda x: x[0] or -1):
            print(f"    Grade {grade}: {count} standards")
        
        # 3. Check module-standard mappings
        print(f"\n🔗 MODULE-STANDARD MAPPINGS:")
        total_mappings = ModuleStandardMapping.query.count()
        print(f"  Total mappings: {total_mappings}")
        
        # NGSS mappings specifically
        ngss_mappings = db.session.query(ModuleStandardMapping)\
            .join(Standard)\
            .filter(Standard.framework == 'NGSS').count()
        print(f"  NGSS mappings: {ngss_mappings}")
        
        # Grade-specific NGSS mappings
        grade_7_mappings = db.session.query(ModuleStandardMapping)\
            .join(Standard)\
            .filter(Standard.framework == 'NGSS', Standard.grade_level == 7).count()
        
        grade_8_mappings = db.session.query(ModuleStandardMapping)\
            .join(Standard)\
            .filter(Standard.framework == 'NGSS', Standard.grade_level == 8).count()
        
        print(f"  Grade 7 NGSS mappings: {grade_7_mappings}")
        print(f"  Grade 8 NGSS mappings: {grade_8_mappings}")
        
        # 4. Check specific module examples
        print(f"\n📋 SAMPLE MODULE ANALYSIS:")
        
        # Pick a few common modules to analyze
        sample_modules = ['Food Science', 'Body Systems', 'Weather', 'Animals']
        
        for module_name in sample_modules:
            module = Module.query.filter(
                Module.title.like(f'%{module_name}%'),
                Module.subject == 'SCIENCE'
            ).first()
            
            if not module:
                print(f"  ❌ Module '{module_name}' not found")
                continue
            
            print(f"\\n  🎯 Module: {module.title}")
            print(f"     Module Grade: {module.grade_level}")
            
            # Get all standards mapped to this module
            mappings = db.session.query(ModuleStandardMapping, Standard)\
                .join(Standard)\
                .filter(ModuleStandardMapping.module_id == module.id)\
                .all()
            
            print(f"     Total mappings: {len(mappings)}")
            
            if mappings:
                # Group by standard framework and grade
                framework_counts = {}
                for mapping, standard in mappings:
                    key = f"{standard.framework}-Grade{standard.grade_level}"
                    if key not in framework_counts:
                        framework_counts[key] = []
                    framework_counts[key].append(standard.code)
                
                for key, codes in framework_counts.items():
                    print(f"       {key}: {len(codes)} standards")
                    print(f"         Examples: {codes[:3]}")
        
        # 5. Simulate correlation report query
        print(f"\\n🧪 SIMULATING CORRELATION REPORT QUERIES:")
        
        # Grade 7 Science Query
        print(f"\\n  📊 Grade 7 Science Correlation:")
        grade_7_query = db.session.query(Module.title, Standard.code)\
            .join(ModuleStandardMapping, Module.id == ModuleStandardMapping.module_id)\
            .join(Standard, ModuleStandardMapping.standard_id == Standard.id)\
            .filter(
                Module.subject == 'SCIENCE',
                Standard.framework == 'NGSS', 
                Standard.grade_level == 7
            )\
            .distinct()\
            .all()
        
        print(f"    Query results: {len(grade_7_query)} module-standard pairs")
        if grade_7_query:
            # Group by module
            modules_with_standards = {}
            for module_title, standard_code in grade_7_query:
                if module_title not in modules_with_standards:
                    modules_with_standards[module_title] = []
                modules_with_standards[module_title].append(standard_code)
            
            print(f"    Modules with Grade 7 standards: {len(modules_with_standards)}")
            for module, standards in list(modules_with_standards.items())[:5]:
                print(f"      • {module}: {len(standards)} standards")
        
        # Grade 8 Science Query
        print(f"\\n  📊 Grade 8 Science Correlation:")
        grade_8_query = db.session.query(Module.title, Standard.code)\
            .join(ModuleStandardMapping, Module.id == ModuleStandardMapping.module_id)\
            .join(Standard, ModuleStandardMapping.standard_id == Standard.id)\
            .filter(
                Module.subject == 'SCIENCE',
                Standard.framework == 'NGSS',
                Standard.grade_level == 8
            )\
            .distinct()\
            .all()
        
        print(f"    Query results: {len(grade_8_query)} module-standard pairs")
        if grade_8_query:
            # Group by module
            modules_with_standards = {}
            for module_title, standard_code in grade_8_query:
                if module_title not in modules_with_standards:
                    modules_with_standards[module_title] = []
                modules_with_standards[module_title].append(standard_code)
            
            print(f"    Modules with Grade 8 standards: {len(modules_with_standards)}")
            for module, standards in list(modules_with_standards.items())[:5]:
                print(f"      • {module}: {len(standards)} standards")
        
        # 6. Check for potential issues
        print(f"\\n⚠️  POTENTIAL ISSUES:")
        issues = []
        
        if len(science_modules) == 0:
            issues.append("No science modules found")
            
        if ngss_mappings == 0:
            issues.append("No NGSS mappings found")
            
        if grade_7_mappings == 0:
            issues.append("No Grade 7 NGSS mappings found")
            
        if grade_8_mappings == 0:
            issues.append("No Grade 8 NGSS mappings found")
            
        if len(grade_7_query) == 0:
            issues.append("Grade 7 correlation query returns no results")
            
        if len(grade_8_query) == 0:
            issues.append("Grade 8 correlation query returns no results")
        
        if issues:
            for issue in issues:
                print(f"    ❌ {issue}")
        else:
            print("    ✅ No obvious issues detected")
        
        # 7. Recommendations
        print(f"\\n💡 RECOMMENDATIONS:")
        
        if ngss_mappings == 0:
            print("    1. Module-standard mappings are missing - need to reload mapping data")
        elif grade_7_mappings == 0 or grade_8_mappings == 0:
            print("    2. Grade-specific mappings are missing - NGSS separation may have broken mappings")
        elif len(grade_7_query) == 0 or len(grade_8_query) == 0:
            print("    3. Correlation queries not working - check app logic")
        else:
            print("    ✅ Everything looks good - issue may be in the app interface")

if __name__ == '__main__':
    debug_correlation_mappings()