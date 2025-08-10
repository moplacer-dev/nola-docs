#!/usr/bin/env python3
"""
Quick diagnostic to check what's actually in the Excel files on the server
"""

import pandas as pd
import os

def check_files():
    standards_file = 'data/standards/CC and NGSS Standards.xlsx'
    matrix_file = 'data/modules/Modules and Standards Matrix (updated).xlsx'
    
    print("=== CHECKING EXCEL FILES ON SERVER ===")
    
    # Check if files exist
    print(f"Standards file exists: {os.path.exists(standards_file)}")
    print(f"Matrix file exists: {os.path.exists(matrix_file)}")
    
    if os.path.exists(standards_file):
        print(f"\n=== STANDARDS FILE ===")
        xl = pd.ExcelFile(standards_file)
        print(f"Sheets: {xl.sheet_names}")
        
        if 'MS Science ' in xl.sheet_names:
            ms_sci = pd.read_excel(standards_file, sheet_name='MS Science ')
            print(f"Science standards count: {len(ms_sci)}")
            
            # Check for the problematic ones
            codes = ms_sci['NGSS'].tolist()
            print(f"Has MS-PS4-3: {'MS-PS4-3' in codes}")
            print(f"Has MS-ESS2-2: {'MS-ESS2-2' in codes}")
            print(f"Has MSS-ESS2-2: {'MSS-ESS2-2' in codes}")
            
            print("First 5 science standards:")
            for i, code in enumerate(codes[:5]):
                if pd.notna(code):
                    print(f"  {code}")
    
    if os.path.exists(matrix_file):
        print(f"\n=== MATRIX FILE ===")
        xl = pd.ExcelFile(matrix_file)
        print(f"Sheets: {xl.sheet_names}")
        
        # Check 7th grade science for the missing standards
        if '7th Grade Science' in xl.sheet_names:
            sci_7th = pd.read_excel(matrix_file, sheet_name='7th Grade Science')
            standards = sci_7th['NGSS (MS)'].dropna().tolist()
            print(f"7th grade science standards: {len(standards)}")
            print(f"Has MS-PS4-3: {'MS-PS4-3' in standards}")
            print(f"Has MS-ESS2-2: {'MS-ESS2-2' in standards}")

if __name__ == '__main__':
    check_files()