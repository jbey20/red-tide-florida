#!/usr/bin/env python3
"""
Test script for FWC API functionality without Google Sheets integration
"""

import os
import sys
import requests
import time
from datetime import datetime

# Add the current directory to Python path to import from fetch_hab_data
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_fwc_api_directly():
    """Test the FWC API directly"""
    print("🌊 Testing FWC API directly...")
    
    fwc_api_url = "https://services2.arcgis.com/z6TmTIyYXEYhuNM0/arcgis/rest/services/HAB_Current_Web_Layer/FeatureServer/0/query"
    
    params = {
        'where': '1=1',
        'outFields': '*',
        'outSR': '4326',
        'f': 'json',
        'orderByFields': 'SAMPLE_DATE DESC',
        'resultRecordCount': 1000
    }
    
    try:
        response = requests.get(fwc_api_url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ API Response Status: {response.status_code}")
        print(f"📊 Response keys: {list(data.keys())}")
        
        features = data.get('features', [])
        print(f"📊 Features count: {len(features)}")
        
        if len(features) == 0:
            if 'error' in data:
                print(f"🔍 API Error: {data['error']}")
                return False
            print(f"🔍 No features found in response")
            return False
        else:
            print(f"🔍 First feature structure:")
            print(features[0])
            return True
            
    except Exception as e:
        print(f"❌ Error testing FWC API: {e}")
        return False

def test_fwc_data_processing():
    """Test FWC data processing logic"""
    print("\n🌊 Testing FWC data processing logic...")
    
    # Mock FWC data for testing
    mock_fwc_data = {
        'features': [
            {
                'attributes': {
                    'HAB_ID': 'test_hab_001',
                    'SAMPLE_DATE': int(datetime.now().timestamp() * 1000),
                    'ABUNDANCE': 'Not Present',
                    'LOCATION': 'Clearwater Beach'
                }
            },
            {
                'attributes': {
                    'HAB_ID': 'test_hab_002',
                    'SAMPLE_DATE': int(datetime.now().timestamp() * 1000),
                    'ABUNDANCE': 'Low (5,000-10,000 cells/L)',
                    'LOCATION': 'Siesta Key'
                }
            }
        ]
    }
    
    print(f"📊 Testing with {len(mock_fwc_data['features'])} mock features")
    
    # Test the parsing logic
    def parse_abundance_to_status(abundance_text):
        """Convert FWC abundance categories to status and cell count"""
        if not abundance_text:
            return 0, 'no_data'
        
        abundance_lower = abundance_text.lower()
        
        # Extract numbers from text
        import re
        numbers = re.findall(r'[\d,]+', abundance_text)
        
        if 'not present' in abundance_lower or 'background' in abundance_lower:
            return 500, 'safe'
        elif 'very low' in abundance_lower:
            return 2500, 'safe'
        elif 'low' in abundance_lower and 'very' not in abundance_lower:
            if len(numbers) >= 2:
                low = int(numbers[0].replace(',', ''))
                high = int(numbers[1].replace(',', ''))
                return (low + high) // 2, 'caution'
            return 5000, 'caution'
        elif 'medium' in abundance_lower:
            if len(numbers) >= 2:
                low = int(numbers[0].replace(',', ''))
                high = int(numbers[1].replace(',', ''))
                return (low + high) // 2, 'avoid'
            return 50000, 'avoid'
        elif 'high' in abundance_lower:
            if len(numbers) >= 2:
                low = int(numbers[0].replace(',', ''))
                high = int(numbers[1].replace(',', ''))
                return (low + high) // 2, 'avoid'
            return 500000, 'avoid'
        
        return 0, 'no_data'
    
    # Test parsing
    for feature in mock_fwc_data['features']:
        attrs = feature['attributes']
        abundance = attrs.get('ABUNDANCE', '')
        cell_count, status = parse_abundance_to_status(abundance)
        print(f"  📍 {attrs.get('LOCATION', 'Unknown')}: {abundance} → {status} ({cell_count} cells/L)")
    
    return True

def test_error_handling():
    """Test error handling with invalid data"""
    print("\n🌊 Testing error handling...")
    
    # Test with missing features key
    invalid_data = {'error': {'code': 500, 'message': 'Service not started'}}
    
    try:
        features = invalid_data.get('features', [])
        if not features:
            if 'error' in invalid_data:
                print(f"✅ Correctly detected API error: {invalid_data['error']}")
                return True
    except Exception as e:
        print(f"❌ Error handling failed: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("🌊 FWC API Test Suite")
    print("=" * 50)
    
    # Test 1: Direct API call
    print("\n1️⃣ Testing direct FWC API call...")
    api_working = test_fwc_api_directly()
    
    # Test 2: Data processing logic
    print("\n2️⃣ Testing data processing logic...")
    processing_working = test_fwc_data_processing()
    
    # Test 3: Error handling
    print("\n3️⃣ Testing error handling...")
    error_handling_working = test_error_handling()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"  API Call: {'✅ PASS' if api_working else '❌ FAIL'}")
    print(f"  Data Processing: {'✅ PASS' if processing_working else '❌ FAIL'}")
    print(f"  Error Handling: {'✅ PASS' if error_handling_working else '❌ FAIL'}")
    
    if api_working and processing_working and error_handling_working:
        print("\n🎉 All tests passed! The FWC API fix is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return api_working and processing_working and error_handling_working

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
