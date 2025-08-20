#!/usr/bin/env python3
"""
Test that correlation reports now properly separate 7th and 8th grade NGSS standards.
"""

from models import db, Standard, Module, ModuleStandardMapping
from app import app

def test_correlation_reports():
    """Test correlation report functionality with grade-separated NGSS"""
    
    print("🧪 TESTING CORRELATION REPORTS")
    print("=" * 35)
    
    with app.app_context():
        
        # Test 1: Science Grade 7 Report
        print("📊 SCIENCE GRADE 7 CORRELATION:")
        grade_7_ngss = Standard.query.filter_by(
            framework='NGSS', 
            subject='SCIENCE',
            grade_level=7
        ).all()
        
        print(f"  - Total 7th grade NGSS standards: {len(grade_7_ngss)}")
        
        # Get modules mapped to these standards
        mapped_modules_7 = db.session.query(Module.title)\
            .join(ModuleStandardMapping)\
            .join(Standard)\
            .filter(
                Standard.framework == 'NGSS',
                Standard.grade_level == 7,
                Module.subject == 'SCIENCE'
            ).distinct().all()
        
        print(f"  - Modules with 7th grade NGSS mappings: {len(mapped_modules_7)}")
        if mapped_modules_7:
            for module in mapped_modules_7[:5]:  # Show first 5
                print(f"    • {module[0]}")
            if len(mapped_modules_7) > 5:
                print(f"    ... and {len(mapped_modules_7) - 5} more")
        
        # Test 2: Science Grade 8 Report  
        print(f"\\n📊 SCIENCE GRADE 8 CORRELATION:")
        grade_8_ngss = Standard.query.filter_by(
            framework='NGSS',
            subject='SCIENCE', 
            grade_level=8
        ).all()
        
        print(f"  - Total 8th grade NGSS standards: {len(grade_8_ngss)}")
        
        # Get modules mapped to these standards
        mapped_modules_8 = db.session.query(Module.title)\
            .join(ModuleStandardMapping)\
            .join(Standard)\
            .filter(
                Standard.framework == 'NGSS',
                Standard.grade_level == 8,
                Module.subject == 'SCIENCE'
            ).distinct().all()
        
        print(f"  - Modules with 8th grade NGSS mappings: {len(mapped_modules_8)}")
        if mapped_modules_8:
            for module in mapped_modules_8[:5]:  # Show first 5
                print(f"    • {module[0]}")
            if len(mapped_modules_8) > 5:
                print(f"    ... and {len(mapped_modules_8) - 5} more")
        
        # Test 3: Verify no overlap issues
        print(f"\\n🔍 OVERLAP ANALYSIS:")
        
        # Check if any modules appear in both grades (this might be expected for some)
        modules_7_set = {m[0] for m in mapped_modules_7}
        modules_8_set = {m[0] for m in mapped_modules_8}
        
        overlap = modules_7_set.intersection(modules_8_set)
        grade_7_only = modules_7_set - modules_8_set
        grade_8_only = modules_8_set - modules_7_set
        
        print(f"  - Modules in both grades: {len(overlap)}")
        print(f"  - Grade 7 only: {len(grade_7_only)}")
        print(f"  - Grade 8 only: {len(grade_8_only)}")
        
        if overlap:
            print(f"  - Cross-grade modules: {list(overlap)[:5]}...")
        
        # Test 4: Sample detailed mapping for one module
        if mapped_modules_7:
            sample_module = mapped_modules_7[0][0]
            print(f"\\n📋 SAMPLE MODULE ANALYSIS: '{sample_module}'")
            
            module_standards = db.session.query(Standard.code, Standard.grade_level)\
                .join(ModuleStandardMapping)\
                .join(Module)\
                .filter(
                    Module.title == sample_module,
                    Standard.framework == 'NGSS'
                ).all()
            
            grade_counts = {}
            for code, grade in module_standards:
                if grade not in grade_counts:
                    grade_counts[grade] = []
                grade_counts[grade].append(code)
            
            for grade, codes in grade_counts.items():
                print(f"    Grade {grade}: {len(codes)} standards")
                print(f"      Examples: {codes[:3]}")
        
        # Test 5: Generate summary statistics
        print(f"\\n📈 SUMMARY STATISTICS:")
        
        total_ngss_ms = len(grade_7_ngss) + len(grade_8_ngss)
        total_mappings = db.session.query(ModuleStandardMapping.standard_id)\
            .join(Standard)\
            .filter(
                Standard.framework == 'NGSS',
                Standard.grade_level.in_([7, 8])
            ).count()
        
        print(f"  - Total MS NGSS standards: {total_ngss_ms}")
        print(f"  - Total MS NGSS mappings: {total_mappings}")
        print(f"  - Average mappings per standard: {total_mappings/total_ngss_ms:.1f}")
        
        # Success indicators
        success_indicators = [
            ("7th grade has standards", len(grade_7_ngss) > 0),
            ("8th grade has standards", len(grade_8_ngss) > 0),  
            ("7th grade has module mappings", len(mapped_modules_7) > 0),
            ("8th grade has module mappings", len(mapped_modules_8) > 0),
            ("No unassigned MS standards", len(Standard.query.filter(
                Standard.framework == 'NGSS',
                Standard.code.like('MS-%'),
                Standard.grade_level.is_(None)
            ).all()) == 0)
        ]
        
        print(f"\\n✅ SUCCESS INDICATORS:")
        all_pass = True
        for indicator, passed in success_indicators:
            status = "✅" if passed else "❌"
            print(f"  {status} {indicator}")
            if not passed:
                all_pass = False
        
        if all_pass:
            print(f"\\n🎉 ALL TESTS PASSED! Correlation reports should now work correctly.")
        else:
            print(f"\\n⚠️  Some issues detected. Review the results above.")
            
        return all_pass

if __name__ == '__main__':
    test_correlation_reports()