#!/usr/bin/env python3
"""
Simple script to inspect Excel files and understand their structure
"""

import pandas as pd
import os

def inspect_standards():
    """Inspect the standards Excel file"""
    standards_path = 'data/standards/CC and NGSS Standards.xlsx'
    
    if not os.path.exists(standards_path):
        print(f"⚠️  Standards file not found: {standards_path}")
        return
    
    print(f"📋 Inspecting: {standards_path}")
    print("=" * 50)
    
    try:
        excel_file = pd.ExcelFile(standards_path)
        print(f"📄 Available sheets: {excel_file.sheet_names}")
        print()
        
        for sheet_name in excel_file.sheet_names:
            print(f"🔍 Sheet: '{sheet_name}'")
            df = pd.read_excel(standards_path, sheet_name=sheet_name)
            print(f"   📊 Dimensions: {df.shape[0]} rows × {df.shape[1]} columns")
            print(f"   📝 Columns: {list(df.columns)}")
            print(f"   🔢 First few rows:")
            print(df.head(3).to_string())
            print()
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")

def inspect_modules():
    """Inspect the modules Excel file"""
    modules_path = 'data/modules/Modules and Standards Matrix.xlsx'
    
    if not os.path.exists(modules_path):
        print(f"⚠️  Modules file not found: {modules_path}")
        return
    
    print(f"📋 Inspecting: {modules_path}")
    print("=" * 50)
    
    try:
        excel_file = pd.ExcelFile(modules_path)
        print(f"📄 Available sheets: {excel_file.sheet_names}")
        print()
        
        for sheet_name in excel_file.sheet_names:
            print(f"🔍 Sheet: '{sheet_name}'")
            df = pd.read_excel(modules_path, sheet_name=sheet_name)
            print(f"   📊 Dimensions: {df.shape[0]} rows × {df.shape[1]} columns")
            print(f"   📝 Columns: {list(df.columns)}")
            print(f"   🔢 First few rows:")
            print(df.head(3).to_string())
            print()
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")

if __name__ == '__main__':
    print("🔍 Excel File Inspector")
    print("=" * 30)
    print()
    
    inspect_standards()
    print("\n" + "="*70 + "\n")
    inspect_modules()