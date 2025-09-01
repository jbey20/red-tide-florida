#!/usr/bin/env python3
"""
Focused Test Script for City Sync
Tests city sync with updated child beach finding logic
"""

import requests
import json
import os
import time
from datetime import datetime
import pytz
from pathlib import Path

# Load environment variables
def load_env_file(env_file_path='.env'):
    """Load environment variables from .env file"""
    env_path = Path(env_file_path)
    
    if env_path.exists():
        print(f"📁 Loading environment variables from {env_path}")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    os.environ[key] = value
        print("✅ Environment variables loaded")

# Load environment variables
load_env_file()

class FocusedCityTester:
    def __init__(self):
        # WordPress Configuration
        self.wp_site_url = os.environ['WORDPRESS_SITE_URL'].rstrip('/')
        self.wp_username = os.environ['WORDPRESS_USERNAME']
        self.wp_password = os.environ['WORDPRESS_APP_PASSWORD']
        self.auth = (self.wp_username, self.wp_password)
        
        print(f"🔧 Testing focused city sync...")
        print(f"   WordPress URL: {self.wp_site_url}")
        print(f"   Username: {self.wp_username}")
    
    def test_single_city_sync(self, city_name):
        """Test syncing a single city to see the child beach finding logic"""
        print(f"\n🔍 Testing city sync for: {city_name}")
        
        try:
            # Find the city post
            search_url = f"{self.wp_site_url}/wp-json/wp/v2/cities"
            params = {'slug': f'{city_name.lower().replace(" ", "-")}-red-tide'}
            
            response = requests.get(search_url, params=params, auth=self.auth, timeout=10)
            
            if response.status_code == 200:
                posts = response.json()
                if posts:
                    post = posts[0]
                    post_id = post['id']
                    print(f"✅ Found {city_name} city post: ID {post_id}")
                    
                    # Test the child beach finding logic
                    self.test_child_beach_finding(city_name)
                    
                else:
                    print(f"❌ {city_name} city post not found")
            else:
                print(f"❌ Search failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error testing {city_name}: {e}")
    
    def test_child_beach_finding(self, city_name):
        """Test the child beach finding logic"""
        print(f"\n🔍 Testing child beach finding for {city_name}...")
        
        # Mock the data structure that would come from Google Sheets
        mock_city_data = {
            'location_name': city_name,
            'current_status': 'safe',
            'peak_count': 500,
            'avg_count': 500,
            'confidence_score': 85,
            'sample_date': '2025-01-15',
            'beach_count': 2,
            'beaches_safe': 2,
            'beaches_caution': 0,
            'beaches_avoid': 0,
            'region': 'Southwest Florida'
        }
        
        # Simulate the child beach finding logic
        print(f"   📊 Mock city data:")
        for key, value in mock_city_data.items():
            print(f"      - {key}: {value}")
        
        # Try to find child beaches
        child_beach_ids = self.find_child_beach_ids(city_name)
        
        print(f"   📊 Child beach IDs found: {child_beach_ids}")
        
        if child_beach_ids:
            print(f"   ✅ Successfully found {len(child_beach_ids)} child beaches")
        else:
            print(f"   ⚠️  No child beaches found - this will cause validation errors")
    
    def find_child_beach_ids(self, city_name):
        """Find child beach post IDs for a city (simplified version)"""
        try:
            # This would normally come from Google Sheets data
            # For testing, let's try to find beaches that belong to this city
            
            # Search for beaches with this city name
            search_url = f"{self.wp_site_url}/wp-json/wp/v2/beaches"
            params = {'per_page': 50}  # Get more beaches to search through
            
            response = requests.get(search_url, params=params, auth=self.auth, timeout=10)
            
            if response.status_code == 200:
                beaches = response.json()
                child_ids = []
                
                print(f"      🔍 Searching through {len(beaches)} beaches for city '{city_name}'...")
                
                for beach in beaches:
                    beach_title = beach.get('title', {}).get('rendered', '')
                    beach_slug = beach.get('slug', '')
                    
                    # Check if this beach belongs to the city
                    # This is a simplified check - in reality we'd use ACF field data
                    if city_name.lower() in beach_title.lower() or city_name.lower() in beach_slug.lower():
                        child_ids.append(beach['id'])
                        print(f"         ✅ Found beach: {beach_title} (ID: {beach['id']})")
                
                return child_ids
            else:
                print(f"      ❌ Failed to get beaches: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"      ❌ Error finding child beaches: {e}")
            return []
    
    def run_test(self):
        """Run the focused test"""
        print("🚀 Starting Focused City Sync Test")
        print("=" * 50)
        
        # Test with a few specific cities
        test_cities = ['Sarasota', 'Anna Maria', 'Clearwater']
        
        for city in test_cities:
            self.test_single_city_sync(city)
            time.sleep(1)  # Rate limiting
        
        print(f"\n🏁 Test complete!")

if __name__ == "__main__":
    tester = FocusedCityTester()
    tester.run_test()
