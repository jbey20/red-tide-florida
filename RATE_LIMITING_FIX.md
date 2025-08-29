# Google Sheets API Rate Limiting Fix

## Problem
The WordPress sync script was failing with rate limiting errors:
```
Quota exceeded for quota metric 'Read requests' and limit 'Read requests per minute per user' of service 'sheets.googleapis.com'
```

This happened because the script was making too many API calls to Google Sheets without proper rate limiting.

## Solution Implemented

### 1. Rate Limiting
- Added minimum 1.1 seconds between all API calls
- Configurable via `API_RATE_LIMIT_SECONDS` environment variable
- Applied to both Google Sheets and WordPress API calls

### 2. Caching System
- Implemented sheet data caching to reduce API calls
- Data is loaded once and reused throughout the process
- Cache can be cleared if fresh data is needed

### 3. Preloading
- All required sheet data is preloaded at startup
- Reduces API calls during processing
- Better error handling for rate limit issues

### 4. Retry Logic
- Automatic retry with 60-second wait when rate limits are hit
- Graceful handling of quota exceeded errors

## Key Changes Made

### In `sync_to_wordpress.py`:

1. **Rate Limiting Method**:
   ```python
   def _rate_limit(self):
       """Ensure minimum time between API calls"""
       current_time = time.time()
       time_since_last = current_time - self.last_api_call
       if time_since_last < self.min_call_interval:
           sleep_time = self.min_call_interval - time_since_last
           time.sleep(sleep_time)
       self.last_api_call = time.time()
   ```

2. **Cached Data Loading**:
   ```python
   def _get_cached_sheet_data(self, worksheet_name):
       """Get sheet data with caching to reduce API calls"""
       if worksheet_name in self.sheet_cache:
           return self.sheet_cache[worksheet_name]
       
       self._rate_limit()
       # ... load data with retry logic
   ```

3. **Preloading at Startup**:
   ```python
   def _preload_sheet_data(self):
       """Preload all required sheet data to minimize API calls"""
       required_sheets = ['beach_status', 'locations', 'sample_mapping']
       for sheet_name in required_sheets:
           self._get_cached_sheet_data(sheet_name)
   ```

## Configuration

### Environment Variables
- `API_RATE_LIMIT_SECONDS`: Time between API calls (default: 1.1)
- Can be increased for more conservative rate limiting

### Example Configuration
```bash
# More conservative rate limiting for production
export API_RATE_LIMIT_SECONDS=2.0

# Standard rate limiting for development
export API_RATE_LIMIT_SECONDS=1.1
```

## Testing

### Test Rate Limiting
```bash
python test_rate_limiting.py
```

### Verify Headers
```bash
python verify_sheet_headers.py
```

## Benefits

1. **Prevents Rate Limiting**: No more quota exceeded errors
2. **Faster Processing**: Caching reduces redundant API calls
3. **Better Reliability**: Retry logic handles temporary issues
4. **Configurable**: Adjust rate limiting based on environment needs

## Monitoring

The script now provides better feedback:
- Shows rate limiting configuration on startup
- Displays preloading progress
- Warns when rate limits are hit
- Shows retry attempts

## Prevention

To prevent future rate limiting issues:
1. Always use the cached data loading methods
2. Preload data at startup when possible
3. Add rate limiting to new API calls
4. Monitor API usage in Google Cloud Console
5. Consider increasing quotas if needed for high-volume usage
