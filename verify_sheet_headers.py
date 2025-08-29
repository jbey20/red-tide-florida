#!/usr/bin/env python3
"""
Verify Google Sheet Headers
Quick check to see if the beach_status sheet headers are correct
"""

import os
import json
import gspread
from google.oauth2.service_account import Credentials

def verify_headers():
    """Verify the beach_status sheet headers"""
    
    # Check if we have the required environment variables
    if not os.environ.get('GOOGLE_SERVICE_ACCOUNT') or not os.environ.get('GOOGLE_SHEET_ID'):
        print("⚠️  Environment variables not available.")
        print("   Set GOOGLE_SERVICE_ACCOUNT and GOOGLE_SHEET_ID to verify headers.")
        return
    
    # Initialize Google Sheets
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
    
    try:
        creds_dict = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT'])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        sheets_client = gspread.authorize(creds)
        sheet = sheets_client.open_by_key(os.environ['GOOGLE_SHEET_ID'])
        
        print("🔍 Verifying Google Sheet headers...")
        
        worksheet = sheet.worksheet('beach_status')
        
        # Get headers
        all_values = worksheet.get_all_values()
        if not all_values:
            print("❌ Sheet is empty")
            return
        
        headers = all_values[0]
        print(f"📊 Found {len(headers)} columns")
        print(f"📋 Current headers: {headers}")
        
        # Check for duplicates
        seen_headers = set()
        duplicate_headers = []
        for i, header in enumerate(headers):
            if header in seen_headers:
                duplicate_headers.append((i, header))
            else:
                seen_headers.add(header)
        
        if duplicate_headers:
            print(f"❌ Found duplicate headers: {duplicate_headers}")
        else:
            print("✅ No duplicate headers found")
        
        # Define expected headers
        expected_headers = [
            'location_name', 'location_type', 'date', 'current_status',
            'peak_count', 'avg_count', 'confidence_score', 'sample_date', 'last_updated',
            'region', 'city', 'slug', 'beach_count', 'city_count', 
            'beaches_safe', 'beaches_caution', 'beaches_avoid'
        ]
        
        print(f"\n🎯 Expected headers ({len(expected_headers)} columns):")
        for i, header in enumerate(expected_headers, 1):
            print(f"   {i:2d}. {header}")
        
        # Check if headers match
        if headers == expected_headers:
            print("\n✅ Headers are correct!")
            print("   Your sync script should work properly.")
        else:
            print("\n❌ Headers don't match expected format")
            print("   Run: python fix_sheet_headers.py to fix this")
            
            # Show differences
            if len(headers) != len(expected_headers):
                print(f"   - Expected {len(expected_headers)} columns, found {len(headers)}")
            
            # Check for missing headers
            missing = set(expected_headers) - set(headers)
            if missing:
                print(f"   - Missing headers: {list(missing)}")
            
            # Check for extra headers
            extra = set(headers) - set(expected_headers)
            if extra:
                print(f"   - Extra headers: {list(extra)}")
        
        # Test if get_all_records works
        try:
            records = worksheet.get_all_records()
            print(f"\n✅ Successfully loaded {len(records)} records")
        except Exception as e:
            print(f"\n❌ Cannot load records: {e}")
            
    except Exception as e:
        print(f"❌ Error verifying headers: {e}")

if __name__ == "__main__":
    verify_headers()
