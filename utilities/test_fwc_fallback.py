#!/usr/bin/env python3
"""
Test script to verify the new FWC fallback behavior
"""

import os
import sys
import requests
from unittest.mock import patch, MagicMock

# Add the current directory to Python path to import from fetch_hab_data
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_fwc_failure_behavior():
    """Test that the script fails gracefully when FWC data is unavailable"""
    print("🧪 Testing FWC failure behavior...")
    
    # Mock environment variables
    os.environ['GOOGLE_SERVICE_ACCOUNT'] = '{"test": "data"}'
    os.environ['GOOGLE_SHEET_ID'] = 'test_sheet_id'
    os.environ['TEST_MODE'] = 'true'
    os.environ['TEST_LIMIT'] = '1'
    
    # Import the HABDataFetcher class
    from fetch_hab_data import HABDataFetcher
    
    # Mock the Google Sheets connection to avoid actual API calls
    with patch('gspread.authorize') as mock_authorize, \
         patch('google.oauth2.service_account.Credentials.from_service_account_info') as mock_creds:
        
        mock_client = MagicMock()
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        
        # Mock the worksheet data
        mock_worksheet.get_all_records.return_value = [
            {'beach': 'Test Beach', 'region': 'Test Region', 'city': 'Test City'},
            {'HAB_id': 'TEST_001', 'beach': 'Test Beach', 'sample_location': 'Test Location', 'sample_distance': 1.0, 'cell_count': 500}
        ]
        mock_sheet.worksheet.return_value = mock_sheet
        mock_client.open_by_key.return_value = mock_sheet
        mock_authorize.return_value = mock_client
        mock_creds.return_value = MagicMock()
        
        # Create the fetcher instance
        fetcher = HABDataFetcher()
        
        # Mock the FWC API to simulate failure
        with patch('requests.get') as mock_get:
            # Simulate a network error
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            # Test that the run method raises an exception
            try:
                fetcher.run()
                print("❌ FAIL: Script should have failed but didn't")
                return False
            except Exception as e:
                if "FWC HAB data unavailable" in str(e):
                    print("✅ PASS: Script correctly failed with FWC data unavailable error")
                    return True
                else:
                    print(f"❌ FAIL: Unexpected error: {e}")
                    return False

def test_fwc_success_behavior():
    """Test that the script works when FWC data is available"""
    print("🧪 Testing FWC success behavior...")
    
    # Mock environment variables
    os.environ['GOOGLE_SERVICE_ACCOUNT'] = '{"test": "data"}'
    os.environ['GOOGLE_SHEET_ID'] = 'test_sheet_id'
    os.environ['TEST_MODE'] = 'true'
    os.environ['TEST_LIMIT'] = '1'
    
    # Import the HABDataFetcher class
    from fetch_hab_data import HABDataFetcher
    
    # Mock the Google Sheets connection
    with patch('gspread.authorize') as mock_authorize, \
         patch('google.oauth2.service_account.Credentials.from_service_account_info') as mock_creds:
        
        mock_client = MagicMock()
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        
        # Mock the worksheet data
        mock_worksheet.get_all_records.return_value = [
            {'beach': 'Test Beach', 'region': 'Test Region', 'city': 'Test City'},
            {'HAB_id': 'TEST_001', 'beach': 'Test Beach', 'sample_location': 'Test Location', 'sample_distance': 1.0, 'cell_count': 500}
        ]
        mock_sheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_sheet
        mock_authorize.return_value = mock_client
        mock_creds.return_value = MagicMock()
        
        # Create the fetcher instance
        fetcher = HABDataFetcher()
        
        # Mock the FWC API to simulate success
        with patch('requests.get') as mock_get:
            # Simulate successful API response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                'features': [
                    {
                        'attributes': {
                            'HAB_ID': 'TEST_001',
                            'SAMPLE_DATE': 1640995200000,  # Mock timestamp
                            'Abundance': 'Not Present',
                            'LOCATION': 'Test Location'
                        }
                    }
                ]
            }
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Mock the Google Sheets update to avoid actual writes
            with patch.object(fetcher, 'update_google_sheets') as mock_update:
                mock_update.return_value = None
                
                # Test that the run method completes successfully
                try:
                    fetcher.run()
                    print("✅ PASS: Script completed successfully with FWC data")
                    return True
                except Exception as e:
                    print(f"❌ FAIL: Script failed unexpectedly: {e}")
                    return False

def main():
    """Main test function"""
    print("🧪 FWC Fallback Behavior Test Suite")
    print("=" * 50)
    
    # Test 1: FWC failure behavior
    print("\n1️⃣ Testing FWC failure behavior...")
    failure_test_passed = test_fwc_failure_behavior()
    
    # Test 2: FWC success behavior
    print("\n2️⃣ Testing FWC success behavior...")
    success_test_passed = test_fwc_success_behavior()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"  FWC Failure Behavior: {'✅ PASS' if failure_test_passed else '❌ FAIL'}")
    print(f"  FWC Success Behavior: {'✅ PASS' if success_test_passed else '❌ FAIL'}")
    
    if failure_test_passed and success_test_passed:
        print("\n🎉 All tests passed! The new FWC fallback behavior is working correctly.")
        print("   - Script fails gracefully when FWC data is unavailable")
        print("   - Script continues normally when FWC data is available")
        print("   - No fallback to cached/default data")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return failure_test_passed and success_test_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
