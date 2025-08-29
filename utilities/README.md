# Utilities Folder

This folder contains helper scripts, test files, and documentation that support the main Red Tide Florida data processing workflow.

## Test Scripts

### `test_fwc_fallback.py`
Tests the FWC API fallback behavior when the API is unavailable. Verifies that the main script fails gracefully with appropriate error messages.

**Usage:**
```bash
python utilities/test_fwc_fallback.py
```

### `test_fwc_only.py`
Tests FWC API functionality without requiring Google Sheets integration. Useful for debugging API connectivity and data processing logic.

**Usage:**
```bash
python utilities/test_fwc_only.py
```

## Utility Scripts

### `load_env.py`
Loads environment variables from a `.env` file and validates that required variables are set. Useful for local development and testing.

**Usage:**
```bash
python utilities/load_env.py
```

### `verify_sheet_headers.py`
Verifies that Google Sheet headers match the expected format for the sync script to work properly.

**Usage:**
```bash
python utilities/verify_sheet_headers.py
```

## Configuration Files

### `ACF_fields.txt`
Contains the ACF (Advanced Custom Fields) field definitions for WordPress integration.

### `ACF Export Aug 29 2025.json`
Exported ACF field configuration from WordPress for reference and backup.

## Documentation

### `ACF_FIELD_FIX.md`
Documentation about fixes applied to ACF field handling in the WordPress sync process.

### `ACF_FIELD_UPDATE_SUMMARY.md`
Summary of updates made to ACF field processing and relationship handling.

### `FWC_API_FIX_SUMMARY.md`
Documentation about fixes applied to the FWC API integration and error handling.

### `RATE_LIMITING_FIX.md`
Documentation about rate limiting improvements for API calls.

### `HEADER_FIX_README.md`
Documentation about Google Sheet header fixes and validation.

## Running Tests

To run all tests in the utilities folder:

```bash
# Test FWC API functionality
python utilities/test_fwc_only.py

# Test FWC fallback behavior
python utilities/test_fwc_fallback.py

# Verify environment setup
python utilities/load_env.py

# Verify sheet headers
python utilities/verify_sheet_headers.py
```

## Notes

- All test scripts can be run independently
- The utilities folder is not part of the main processing workflow
- Configuration files are kept here for reference and backup purposes
- Documentation files provide context for fixes and improvements made to the system
