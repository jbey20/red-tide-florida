# Google Sheet Header Fix

## Problem
The WordPress sync script is failing with the error:
```
gspread.exceptions.GSpreadException: the header row in the worksheet is not unique
```

This happens when the Google Sheet has duplicate column headers, which typically occurs when:
- New columns are added incorrectly (e.g., "page slug" added as a new row instead of updating "slug")
- Headers are manually edited and duplicates are created
- The sheet structure gets corrupted

## Solution

### Option 1: Automated Fix (Recommended)
If you have the environment variables set up:
```bash
python fix_sheet_headers.py
```

### Option 2: Manual Fix
1. Open your Google Sheet (beach_status worksheet)
2. Select the entire first row (header row)
3. Delete the header row
4. Insert a new row at the top
5. Copy and paste these exact headers into the new row:

```
location_name | location_type | date | current_status | peak_count | avg_count | confidence_score | sample_date | last_updated | region | city | slug | beach_count | city_count | beaches_safe | beaches_caution | beaches_avoid
```

6. Make sure there are NO duplicate column names
7. Ensure the 'slug' column exists (not 'page slug' or similar)
8. Save the sheet

### Option 3: Verify Headers
To check if your headers are correct:
```bash
python verify_sheet_headers.py
```

## Expected Headers
The sheet must have exactly these 17 headers in this exact order:

1. `location_name`
2. `location_type`
3. `date`
4. `current_status`
5. `peak_count`
6. `avg_count`
7. `confidence_score`
8. `sample_date`
9. `last_updated`
10. `region`
11. `city`
12. `slug`
13. `beach_count`
14. `city_count`
15. `beaches_safe`
16. `beaches_caution`
17. `beaches_avoid`

## Important Notes
- The `slug` column should contain values like `beach-name-red-tide`
- Do NOT add `page slug` as a separate column
- Make sure all 17 headers are present and unique
- The order matters - keep them in the exact order shown above

## After Fixing
Once the headers are corrected, your sync script should work again:
```bash
python sync_to_wordpress.py
```

## Prevention
To prevent this issue in the future:
- Don't manually edit the header row in the Google Sheet
- Let the scripts handle column additions automatically
- If you need to add new columns, update the code first, then let it regenerate the headers
