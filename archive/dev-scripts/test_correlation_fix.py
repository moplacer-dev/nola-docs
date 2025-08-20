#!/usr/bin/env python3
"""
Test that correlation reports now work correctly after fixing the grade_level filtering.
"""

from models import db, Standard, Module, ModuleStandardMapping
from app import app, get_all_standards, get_module_to_standards

def test_correlation_functions():
    """Test the correlation functions work with separated NGSS grades"""
    
    print("🧪 TESTING CORRELATION FUNCTIONS AFTER FIX")
    print("=" * 50)
    
    with app.app_context():
        
        # Test get_all_standards for 7th grade science
        print("📊 Testing get_all_standards()")
        
        grade_7_standards = get_all_standards('LA', 7, 'SCIENCE')
        print(f"  7th Grade Science Standards: {len(grade_7_standards)}")
        if grade_7_standards:
            print(f"    Examples: {grade_7_standards[:5]}")
        
        grade_8_standards = get_all_standards('LA', 8, 'SCIENCE')
        print(f"  8th Grade Science Standards: {len(grade_8_standards)}")
        if grade_8_standards:
            print(f"    Examples: {grade_8_standards[:5]}")
        
        # Test get_module_to_standards
        print(f"\\n📋 Testing get_module_to_standards()")
        
        grade_7_mappings = get_module_to_standards('SCIENCE', 7)
        print(f"  7th Grade Module Mappings: {len(grade_7_mappings)} modules")
        if grade_7_mappings:
            sample_modules = list(grade_7_mappings.keys())[:5]
            for module in sample_modules:
                print(f"    {module}: {len(grade_7_mappings[module])} standards")
        
        grade_8_mappings = get_module_to_standards('SCIENCE', 8)
        print(f"  8th Grade Module Mappings: {len(grade_8_mappings)} modules")
        if grade_8_mappings:
            sample_modules = list(grade_8_mappings.keys())[:5]
            for module in sample_modules:
                print(f"    {module}: {len(grade_8_mappings[module])} standards")
        
        # Test a specific correlation scenario
        print(f"\\n🎯 Testing Specific Correlation Scenario")
        
        # Get some science modules
        science_modules = Module.query.filter_by(subject='SCIENCE').limit(3).all()
        if science_modules:
            selected_module_ids = [str(m.id) for m in science_modules]
            print(f"  Selected modules: {[m.title for m in science_modules]}")
            
            # Test what the correlation report would show
            for grade in [7, 8]:
                standards = get_all_standards('LA', grade, 'SCIENCE') 
                mappings = get_module_to_standards('SCIENCE', grade)
                
                # Count modules that have mappings to selected modules
                relevant_modules = [m.title for m in science_modules if m.title in mappings]
                
                print(f"\\n  Grade {grade} Correlation Preview:")
                print(f"    Available standards: {len(standards)}")
                print(f"    Modules with mappings: {len(relevant_modules)}")
                if relevant_modules:
                    for module_title in relevant_modules:
                        mapped_standards = mappings.get(module_title, set())
                        print(f"      {module_title}: {len(mapped_standards)} mapped standards")
        
        # Success checks
        success_indicators = [
            ("Grade 7 has standards", len(grade_7_standards) > 0),
            ("Grade 8 has standards", len(grade_8_standards) > 0),
            ("Grade 7 has module mappings", len(grade_7_mappings) > 0),
            ("Grade 8 has module mappings", len(grade_8_mappings) > 0),
            ("Standards are different by grade", set(grade_7_standards) != set(grade_8_standards)),
        ]
        
        print(f"\\n✅ SUCCESS INDICATORS:")
        all_pass = True
        for indicator, passed in success_indicators:
            status = "✅" if passed else "❌"
            print(f"  {status} {indicator}")
            if not passed:
                all_pass = False
        
        if all_pass:
            print(f"\\n🎉 CORRELATION FUNCTIONS WORKING CORRECTLY!")
            print(f"\\n📋 Expected Results:")
            print(f"  - 7th grade reports will show {len(grade_7_standards)} NGSS standards")
            print(f"  - 8th grade reports will show {len(grade_8_standards)} NGSS standards") 
            print(f"  - Module correlations will be grade-specific")
        else:
            print(f"\\n⚠️  Some issues still remain")
            
        return all_pass

if __name__ == '__main__':
    test_correlation_functions()