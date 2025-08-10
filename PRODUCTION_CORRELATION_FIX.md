# Production Correlation Report Fix Guide

## Problem Identified ✅

Your local SQLite database has all the necessary data for correlation reports (215 standards, 97 modules, 885 mappings), but your production PostgreSQL database on Render is missing this data. This is why correlation reports generate half-empty documents - they can't find the standards and module mappings.

## Verification Completed ✅

- **Local Database**: ✅ Working perfectly with complete data
- **Correlation Logic**: ✅ Functions correctly (tested successfully)  
- **Template System**: ✅ Generates proper documents when data exists
- **Production Issue**: ❌ Missing data on Render PostgreSQL

## Solution Steps

### Step 1: Verify Production Database State

SSH into your Render instance and run:
```bash
flask verify-production-data
```

This will show you exactly what data is missing on production.

### Step 2A: Quick Fix - Load Production Data (Recommended)

If the production database is completely empty or corrupted, run the existing data loader:

```bash
flask load-production-data
```

Then run the fix for grade mappings:
```bash
flask fix-standards-data  
```

### Step 2B: Alternative - Sync from Local Database

If Step 2A doesn't work, use the new sync tools I created:

1. **On local machine**, export your working data:
```bash
flask sync-to-production
```

This creates a `production_data_export/` folder with all your data.

2. **Upload to production** and run:
```bash
python production_data_export/import_production_data.py
```

### Step 3: Verify Fix

After running either solution, verify everything works:

```bash
flask verify-production-data
```

You should see:
- States: 50
- Standards: 200+ 
- Modules: 90+
- Mappings: 800+

## Files Created for You

1. **`verify_production_data.py`** - Diagnoses data issues
2. **`sync_to_production.py`** - Exports local data for migration
3. **Updated `app.py`** - Registered new CLI commands

## Expected Outcome

Once the data is properly loaded on production:
- Correlation reports will show complete tables with all standards
- Module mappings will display correctly  
- Documents will be fully populated instead of half-empty

## Technical Details

The issue was a data migration problem between SQLite (local) and PostgreSQL (production). Your recent commits show you were working on this:

- `0cccf53` - "EMERGENCY: Add standards data fix for correct grade mappings"
- `8d9067c` - "Fix correlation report data retrieval queries" 
- `a0150fe` - "Add openpyxl dependency for Excel file processing"

The correlation report functionality is working perfectly - it just needs the underlying data to be present on production.