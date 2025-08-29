# ACF Field Fix - Relationship Fields Issue

## Problem
The WordPress sync script was failing with ACF field validation errors:
```
"acf[child_beaches] must be of post type beach."
```

This error occurs because the `child_beaches` and `child_cities` fields are ACF relationship fields that expect arrays of post IDs, but the script was passing integer counts instead.

## Root Cause
ACF relationship fields require:
- **Expected**: Array of post IDs (e.g., `[123, 456, 789]`)
- **Received**: Integer count (e.g., `5`)

## Solution Implemented

### 1. Relationship Field Detection
The script now properly handles relationship fields by:
- Finding actual post IDs for related beaches/cities
- Using empty arrays when no related posts exist
- Providing configuration to disable relationship fields if needed

### 2. Configuration Options
Added environment variable to control relationship field behavior:
```bash
# Enable relationship fields (default)
export USE_ACF_RELATIONSHIPS=true

# Disable relationship fields (fallback)
export USE_ACF_RELATIONSHIPS=false
```

### 3. Smart Post ID Resolution
The script now:
- Searches for existing posts by slug
- Maps region names to related beach/city posts
- Handles cases where related posts don't exist yet

## Key Changes Made

### In `sync_to_wordpress.py`:

1. **Relationship Field Method**:
   ```python
   def _find_related_post_ids(self, region_name, post_type):
       """Find post IDs for related posts (beaches/cities in a region)"""
       # Searches for existing posts and returns their IDs
   ```

2. **Conditional ACF Field Handling**:
   ```python
   if self.use_relationship_fields:
       # Use actual post IDs for relationship fields
       child_beach_ids = self._find_related_post_ids(region_name, 'beach')
       acf_data.update({'child_beaches': child_beach_ids})
   else:
       # Skip relationship fields, use count fields instead
   ```

3. **Configuration**:
   ```python
   self.use_relationship_fields = os.environ.get('USE_ACF_RELATIONSHIPS', 'true').lower() == 'true'
   ```

## ACF Field Types

### Count Fields (Always Used)
- `beach_count`: Number of beaches in region
- `city_count`: Number of cities in region
- `total_beaches`: Alternative field name
- `total_cities`: Alternative field name

### Relationship Fields (Configurable)
- `child_beaches`: Array of beach post IDs
- `child_cities`: Array of city post IDs

## Testing

### Test ACF Fields
```bash
python test_acf_fields.py
```

This script will:
- Test authentication
- Check existing ACF field configuration
- Validate field types and values
- Test creating posts with ACF fields
- Show detailed error messages for field issues

### Test Different Configurations
```bash
# Test with relationship fields enabled
export USE_ACF_RELATIONSHIPS=true
python sync_to_wordpress.py

# Test with relationship fields disabled
export USE_ACF_RELATIONSHIPS=false
python sync_to_wordpress.py
```

## Troubleshooting

### If Relationship Fields Still Fail

1. **Disable Relationship Fields**:
   ```bash
   export USE_ACF_RELATIONSHIPS=false
   ```

2. **Check ACF Field Configuration**:
   - Verify field names match exactly
   - Ensure relationship fields are configured for correct post types
   - Check field permissions and validation rules

3. **Test Individual Fields**:
   ```bash
   python test_acf_fields.py
   ```

### Common Issues

1. **Field Name Mismatch**: Ensure ACF field names match exactly
2. **Post Type Mismatch**: Relationship fields must target correct post types
3. **Permission Issues**: Check if ACF fields are editable via REST API
4. **Validation Rules**: ACF may have custom validation that's failing

## WordPress ACF Configuration

### Required ACF Fields for Regions
```php
// Count fields (number fields)
beach_count (Number)
city_count (Number)
total_beaches (Number)
total_cities (Number)

// Relationship fields (relationship fields)
child_beaches (Relationship -> Post Type: Beach)
child_cities (Relationship -> Post Type: City)
```

### Field Settings
- **Return Format**: Post ID
- **Allow Null**: Yes (for empty relationships)
- **Minimum/Maximum**: Set as needed
- **Filters**: Configure as needed

## Benefits

1. **Flexible Configuration**: Can enable/disable relationship fields
2. **Better Error Handling**: Clear error messages for field issues
3. **Fallback Options**: Works even if relationship fields fail
4. **Testing Tools**: Easy to test and debug ACF field issues

## Prevention

To prevent future ACF field issues:
1. Test ACF field configuration before running sync
2. Use the test script to validate field types
3. Keep relationship fields optional with fallbacks
4. Monitor ACF field validation errors
5. Document field requirements clearly
