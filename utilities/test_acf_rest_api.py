#!/usr/bin/env python3
"""
Test Script to Check ACF REST API Exposure
Tests which ACF fields are exposed to the WordPress REST API
"""

import requests
import json
import os
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

class ACFRestAPITester:
    def __init__(self):
        # WordPress Configuration
        self.wp_site_url = os.environ['WORDPRESS_SITE_URL'].rstrip('/')
        self.wp_username = os.environ['WORDPRESS_USERNAME']
        self.wp_password = os.environ['WORDPRESS_APP_PASSWORD']
        self.auth = (self.wp_username, self.wp_password)
        
        print(f"🔧 Testing ACF REST API exposure...")
        print(f"   WordPress URL: {self.wp_site_url}")
        print(f"   Username: {self.wp_username}")
    
    def test_acf_field_exposure(self):
        """Test which ACF fields are exposed to the REST API"""
        print("\n🔍 Testing ACF field exposure to REST API...")
        
        # Test different post types
        post_types = ['beach', 'city', 'region']
        
        for post_type in post_types:
            print(f"\n📋 Testing {post_type} post type...")
            
            try:
                # Get a sample post of this type
                url = f"{self.wp_site_url}/wp-json/wp/v2/{post_type}s"
                params = {'per_page': 1}
                
                response = requests.get(url, params=params, auth=self.auth, timeout=10)
                
                if response.status_code == 200:
                    posts = response.json()
                    if posts:
                        post = posts[0]
                        post_id = post['id']
                        
                        print(f"   Found {post_type} post ID: {post_id}")
                        
                        # Get the full post with ACF fields
                        full_url = f"{self.wp_site_url}/wp-json/wp/v2/{post_type}s/{post_id}"
                        full_response = requests.get(full_url, auth=self.auth, timeout=10)
                        
                        if full_response.status_code == 200:
                            full_post = full_response.json()
                            acf_fields = full_post.get('acf', {})
                            
                            print(f"   📊 ACF fields exposed to REST API:")
                            if acf_fields:
                                for key, value in acf_fields.items():
                                    print(f"      - {key}: {value}")
                            else:
                                print(f"      No ACF fields found")
                        else:
                            print(f"   ❌ Failed to get full post: {full_response.status_code}")
                    else:
                        print(f"   No {post_type} posts found")
                else:
                    print(f"   ❌ Failed to get {post_type} posts: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error testing {post_type}: {e}")
    
    def test_acf_field_group_settings(self):
        """Test ACF field group REST API settings"""
        print("\n🔍 Testing ACF field group REST API settings...")
        
        try:
            # Try to get ACF field group information via REST API
            url = f"{self.wp_site_url}/wp-json/acf/v3/field-groups"
            response = requests.get(url, auth=self.auth, timeout=10)
            
            if response.status_code == 200:
                field_groups = response.json()
                print(f"   📊 Found {len(field_groups)} field groups:")
                
                for group in field_groups:
                    group_name = group.get('title', 'Unknown')
                    show_in_rest = group.get('show_in_rest', False)
                    location = group.get('location', [])
                    
                    print(f"      - {group_name}: show_in_rest = {show_in_rest}")
                    
                    # Check location rules
                    for rule_group in location:
                        for rule in rule_group:
                            param = rule.get('param', '')
                            value = rule.get('value', '')
                            if param == 'post_type':
                                print(f"        → Applied to post type: {value}")
            else:
                print(f"   ❌ Failed to get field groups: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error testing field groups: {e}")
    
    def test_direct_acf_update(self):
        """Test direct ACF field update to see if fields are writable"""
        print("\n🔍 Testing direct ACF field update...")
        
        try:
            # Find a city post
            url = f"{self.wp_site_url}/wp-json/wp/v2/cities"
            params = {'per_page': 1}
            
            response = requests.get(url, params=params, auth=self.auth, timeout=10)
            
            if response.status_code == 200:
                posts = response.json()
                if posts:
                    post = posts[0]
                    post_id = post['id']
                    post_title = post['title']['rendered']
                    
                    print(f"   Testing with {post_title} (ID: {post_id})")
                    
                    # Try to update with a simple ACF field
                    update_url = f"{self.wp_site_url}/wp-json/wp/v2/cities/{post_id}"
                    test_data = {
                        'acf': {
                            'current_status': 'safe',
                            'test_field': 'test_value'
                        }
                    }
                    
                    update_response = requests.post(
                        update_url,
                        json=test_data,
                        auth=self.auth,
                        headers={'Content-Type': 'application/json'},
                        timeout=15
                    )
                    
                    print(f"   Update response: {update_response.status_code}")
                    
                    if update_response.status_code in [200, 201]:
                        result = update_response.json()
                        acf_fields = result.get('acf', {})
                        
                        print(f"   📊 ACF fields after update:")
                        for key, value in acf_fields.items():
                            print(f"      - {key}: {value}")
                        
                        # Check if our test field was saved
                        if 'test_field' in acf_fields:
                            print(f"   ✅ Test field was saved successfully")
                        else:
                            print(f"   ❌ Test field was NOT saved")
                    else:
                        print(f"   ❌ Update failed: {update_response.text}")
                else:
                    print(f"   No city posts found")
            else:
                print(f"   ❌ Failed to get city posts: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error testing direct update: {e}")
    
    def run_test(self):
        """Run the complete test"""
        print("🚀 Starting ACF REST API Test")
        print("=" * 50)
        
        # 1. Test ACF field exposure
        self.test_acf_field_exposure()
        
        # 2. Test field group settings
        self.test_acf_field_group_settings()
        
        # 3. Test direct ACF update
        self.test_direct_acf_update()
        
        print(f"\n🏁 Test complete!")

if __name__ == "__main__":
    tester = ACFRestAPITester()
    tester.run_test()
