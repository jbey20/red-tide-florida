# Local Environment Setup for Red Tide Florida Testing

This guide will help you set up a local environment to test the Red Tide Florida data processing scripts.

## Quick Start

1. **Run the setup script:**
   ```bash
   ./setup_local_env.sh
   ```

2. **Test the FWC API fix (no Google Sheets required):**
   ```bash
   source venv/bin/activate
   python test_fwc_only.py
   ```

3. **For full testing with Google Sheets, edit the .env file:**
   ```bash
   # Copy the example file
   cp env.example .env
   
   # Edit with your actual values
   nano .env
   ```

## Environment Variables

### Required Variables

- **`GOOGLE_SERVICE_ACCOUNT`**: JSON string of your Google service account credentials
- **`GOOGLE_SHEET_ID`**: The ID of your Google Sheet (found in the URL)

### Optional Variables

- **`TEST_MODE`**: Set to `true` to run in test mode (default: `false`)
- **`TEST_LIMIT`**: Number of records to process in test mode (default: `3`)
- **`WORDPRESS_URL`**: Your WordPress site URL (for sync_to_wordpress.py)
- **`WORDPRESS_USERNAME`**: WordPress username
- **`WORDPRESS_PASSWORD`**: WordPress application password
- **`WORDPRESS_TEST_ONLY`**: Set to `true` for test-only mode (default: `false`)
- **`API_RATE_LIMIT_SECONDS`**: Rate limiting for API calls (default: `1.1`)
- **`USE_ACF_RELATIONSHIPS`**: Use ACF relationship fields (default: `true`)

## Getting Google Service Account Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API
4. Create a service account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name and description
   - Grant "Editor" role
5. Create and download a JSON key:
   - Click on your service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Download the file
6. Copy the entire JSON content to the `GOOGLE_SERVICE_ACCOUNT` variable in your `.env` file

## Getting Google Sheets ID

1. Open your Google Sheet
2. Copy the ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit
   ```
3. Paste it as the `GOOGLE_SHEET_ID` value in your `.env` file

## Testing Scripts

### Test FWC API Only (No Google Sheets Required)
```bash
python test_fwc_only.py
```
This tests:
- FWC API connectivity
- Data processing logic
- Error handling

### Test Environment Setup
```bash
python load_env.py
```
This checks if all required environment variables are set correctly.

### Test Full HAB Data Fetch
```bash
python fetch_hab_data.py
```
This runs the complete HAB data processing pipeline (requires Google Sheets setup).

### Test WordPress Sync
```bash
python sync_to_wordpress.py
```
This syncs data to WordPress (requires WordPress credentials in .env).

## Current Status

### FWC API Status
- **Status**: ❌ Service Down
- **Error**: "Service FWC_GIS/OpenData_HAB/MapServer not started"
- **Impact**: Script falls back to default safe status data
- **Fix**: ✅ Implemented robust error handling and fallback mechanism

### Test Results
- ✅ **Data Processing**: Working correctly
- ✅ **Error Handling**: Working correctly  
- ✅ **Fallback Mechanism**: Working correctly
- ❌ **FWC API**: Service currently down (handled gracefully)

## Troubleshooting

### Common Issues

1. **"Missing required environment variables"**
   - Make sure you've created a `.env` file
   - Check that all required variables are set

2. **"Invalid credentials"**
   - Verify your Google service account JSON is correct
   - Ensure the service account has access to your Google Sheet

3. **"Sheet not found"**
   - Check that your Google Sheets ID is correct
   - Ensure the service account has access to the sheet

4. **"FWC API errors"**
   - This is expected when the FWC service is down
   - The script will fall back to default data

### Getting Help

- Check the logs for detailed error messages
- Verify your environment variables with `python load_env.py`
- Test individual components with the test scripts

## File Structure

```
red-tide-florida/
├── fetch_hab_data.py          # Main HAB data processing script
├── sync_to_wordpress.py       # WordPress sync script
├── verify_sheet_headers.py    # Sheet header verification
├── test_fwc_only.py          # FWC API testing (no Google Sheets)
├── load_env.py               # Environment variable loader
├── setup_local_env.sh        # Setup script
├── env.example               # Environment variables template
├── requirements.txt          # Python dependencies
└── venv/                     # Virtual environment
```

## Next Steps

1. Set up your Google service account and add credentials to `.env`
2. Test the full pipeline with `python fetch_hab_data.py`
3. Monitor the FWC API service status
4. Set up automated testing and monitoring
