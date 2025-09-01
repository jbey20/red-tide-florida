#!/usr/bin/env python3
"""
Test Script for Sarasota City ACF Fields
Tests writing and reading ACF field data for Sarasota city post
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

class SarasotaCityTester:
    def __init__(self):
        # WordPress Configuration
        self.wp_site_url = os.environ['WORDPRESS_SITE_URL'].rstrip('/')
        self.wp_username = os.environ['WORDPRESS_USERNAME']
        self.wp_password = os.environ['WORDPRESS_APP_PASSWORD']
        self.auth = (self.wp_username, self.wp_password)
        
        print(f"🔧 Testing Sarasota city ACF fields...")
        print(f"   WordPress URL: {self.wp_site_url}")
        print(f"   Username: {self.wp_username}")
    
    def find_sarasota_city_post(self):
        """Find the Sarasota city post"""
        print("\n🔍 Searching for Sarasota city post...")
        
        try:
            search_url = f"{self.wp_site_url}/wp-json/wp/v2/cities"
            params = {'slug': 'sarasota-red-tide'}
            
            response = requests.get(search_url, params=params, auth=self.auth, timeout=10)
            
            if response.status_code == 200:
                posts = response.json()
                if posts:
                    post = posts[0]
                    print(f"✅ Found Sarasota city post: ID {post['id']}")
                    return post
                else:
                    print("❌ Sarasota city post not found")
                    return None
            else:
                print(f"❌ Search failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error searching for Sarasota post: {e}")
            return None
    
    def read_current_acf_fields(self, post_id):
        """Read current ACF field values for the post"""
        print(f"\n📖 Reading current ACF fields for post ID {post_id}...")
        
        try:
            # Get the post with ACF fields
            url = f"{self.wp_site_url}/wp-json/wp/v2/cities/{post_id}"
            params = {'_fields': 'id,title,acf'}
            
            response = requests.get(url, params=params, auth=self.auth, timeout=10)
            
            if response.status_code == 200:
                post_data = response.json()
                acf_fields = post_data.get('acf', {})
                
                print("📊 Current ACF field values:")
                print(f"   - peak_cell_count: {acf_fields.get('peak_cell_count', 'NOT SET')}")
                print(f"   - average_cell_count: {acf_fields.get('average_cell_count', 'NOT SET')}")
                print(f"   - average_confidence: {acf_fields.get('average_confidence', 'NOT SET')}")
                print(f"   - latest_sample_data: {acf_fields.get('latest_sample_data', 'NOT SET')}")
                print(f"   - total_beaches: {acf_fields.get('total_beaches', 'NOT SET')}")
                print(f"   - beaches_safe: {acf_fields.get('beaches_safe', 'NOT SET')}")
                print(f"   - beaches_caution: {acf_fields.get('beaches_caution', 'NOT SET')}")
                print(f"   - beaches_avoid: {acf_fields.get('beaches_avoid', 'NOT SET')}")
                print(f"   - child_beaches: {acf_fields.get('child_beaches', 'NOT SET')}")
                print(f"   - parent_region: {acf_fields.get('parent_region', 'NOT SET')}")
                
                return acf_fields
            else:
                print(f"❌ Failed to read post: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error reading ACF fields: {e}")
            return None
    
    def update_sarasota_acf_fields(self, post_id):
        """Update Sarasota city post with test ACF field data"""
        print(f"\n✏️  Updating Sarasota city post ID {post_id} with test ACF data...")
        
        # Test ACF data for Sarasota
        test_acf_data = {
            'current_status': 'caution',  # Required field
            'status_color': '#ffc107',    # Required field
            'last_updated': datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S'),
            'url_slug': 'sarasota-red-tide',
            'region': 'Southwest Florida',
            'state': 'FL',
            'featured_location': False,
            'location_name': 'Sarasota',
            'peak_cell_count': 15000,
            'average_cell_count': 8750,
            'average_confidence': 85,
            'latest_sample_data': '2025-01-15',
            'total_beaches': 3,
            'beaches_safe': 1,
            'beaches_caution': 2,
            'beaches_avoid': 0,
            'child_beaches': [212, 213, 214],  # Mock beach post IDs
            'parent_region': 317,  # Mock region post ID
            'city_description': 'Sarasota, Florida has 3 monitored beaches with mixed red tide conditions. Check individual beach status before visiting.',
            'nearby_cities': [],
            'nearby_beaches': []
        }
        
        print("📝 Test ACF data to be written:")
        for key, value in test_acf_data.items():
            print(f"   - {key}: {value}")
        
        try:
            url = f"{self.wp_site_url}/wp-json/wp/v2/cities/{post_id}"
            
            # Prepare the update payload
            update_payload = {
                'acf': test_acf_data
            }
            
            print(f"\n📤 Sending update request to: {url}")
            print(f"📦 Payload: {json.dumps(update_payload, indent=2)}")
            
            response = requests.post(
                url,
                json=update_payload,
                auth=self.auth,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            print(f"\n📥 Response Status: {response.status_code}")
            print(f"📥 Response Headers: {dict(response.headers)}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                print(f"✅ Update successful!")
                print(f"📊 Response data: {json.dumps(result, indent=2)}")
                
                # Check if ACF fields are in the response
                if 'acf' in result:
                    print(f"✅ ACF fields found in response!")
                    acf_response = result['acf']
                    print(f"📊 ACF fields in response:")
                    for key, value in acf_response.items():
                        print(f"   - {key}: {value}")
                else:
                    print(f"⚠️  No ACF fields found in response")
                
                return True
            else:
                print(f"❌ Update failed: {response.status_code}")
                print(f"❌ Error response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating post: {e}")
            return False
    
    def test_acf_field_names(self, post_id):
        """Test if ACF field names are correct by trying different variations"""
        print(f"\n🧪 Testing ACF field name variations for post ID {post_id}...")
        
        # Test different field name variations
        field_variations = [
            {
                'name': 'Standard ACF names',
                'fields': {
                    'current_status': 'caution',
                    'status_color': '#ffc107',
                    'location_name': 'Sarasota',
                    'peak_cell_count': 10000,
                    'average_cell_count': 5000,
                    'average_confidence': 75
                }
            },
            {
                'name': 'Alternative field names',
                'fields': {
                    'current_status': 'caution',
                    'status_color': '#ffc107',
                    'location_name': 'Sarasota',
                    'peak_count': 10000,
                    'avg_count': 5000,
                    'confidence_score': 75
                }
            },
            {
                'name': 'Mixed field names',
                'fields': {
                    'current_status': 'caution',
                    'status_color': '#ffc107',
                    'location_name': 'Sarasota',
                    'peak_cell_count': 10000,
                    'avg_count': 5000,
                    'confidence_score': 75
                }
            }
        ]
        
        for variation in field_variations:
            print(f"\n🧪 Testing: {variation['name']}")
            print(f"📝 Fields: {variation['fields']}")
            
            try:
                url = f"{self.wp_site_url}/wp-json/wp/v2/cities/{post_id}"
                update_payload = {'acf': variation['fields']}
                
                response = requests.post(
                    url,
                    json=update_payload,
                    auth=self.auth,
                    headers={'Content-Type': 'application/json'},
                    timeout=15
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    print(f"✅ {variation['name']} - Update successful")
                    
                    if 'acf' in result:
                        acf_response = result['acf']
                        print(f"📊 ACF fields returned:")
                        for key, value in acf_response.items():
                            print(f"   - {key}: {value}")
                    else:
                        print(f"⚠️  No ACF fields in response")
                else:
                    print(f"❌ {variation['name']} - Update failed: {response.status_code}")
                    print(f"   Error: {response.text}")
                    
            except Exception as e:
                print(f"❌ {variation['name']} - Error: {e}")
            
            time.sleep(2)  # Rate limiting
    
    def run_test(self):
        """Run the complete test"""
        print("🚀 Starting Sarasota City ACF Field Test")
        print("=" * 50)
        
        # 1. Find Sarasota city post
        sarasota_post = self.find_sarasota_city_post()
        if not sarasota_post:
            print("❌ Cannot continue without finding Sarasota post")
            return
        
        post_id = sarasota_post['id']
        
        # 2. Read current ACF fields
        current_acf = self.read_current_acf_fields(post_id)
        
        # 3. Update with test data
        update_success = self.update_sarasota_acf_fields(post_id)
        
        if update_success:
            # 4. Read ACF fields again to verify
            print(f"\n🔍 Verifying update...")
            time.sleep(2)  # Wait for update to process
            updated_acf = self.read_current_acf_fields(post_id)
            
            # 5. Compare before and after
            if current_acf and updated_acf:
                print(f"\n📊 Comparison:")
                fields_to_check = [
                    'peak_cell_count', 'average_cell_count', 'average_confidence',
                    'latest_sample_data', 'total_beaches', 'beaches_safe',
                    'beaches_caution', 'beaches_avoid'
                ]
                
                for field in fields_to_check:
                    before = current_acf.get(field, 'NOT SET')
                    after = updated_acf.get(field, 'NOT SET')
                    status = "✅ CHANGED" if before != after else "❌ NO CHANGE"
                    print(f"   {field}: {before} → {after} {status}")
        
        # 6. Test field name variations
        self.test_acf_field_names(post_id)
        
        print(f"\n🏁 Test complete!")

if __name__ == "__main__":
    tester = SarasotaCityTester()
    tester.run_test()
