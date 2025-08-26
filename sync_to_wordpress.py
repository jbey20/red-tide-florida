#!/usr/bin/env python3
"""
WordPress Sync Script - Simplified Version
Reads data from Google Sheets and creates/updates WordPress posts via REST API
"""

import requests
import json
import os
import time
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

class WordPressSyncer:
    def __init__(self):
        # WordPress Configuration
        self.wp_site_url = os.environ['WORDPRESS_SITE_URL'].rstrip('/')
        self.wp_username = os.environ['WORDPRESS_USERNAME']
        self.wp_password = os.environ['WORDPRESS_APP_PASSWORD']
        
        # Test mode configuration
        self.test_mode = os.environ.get('TEST_MODE', 'false').lower() == 'true'
        self.test_limit = int(os.environ.get('TEST_LIMIT', '2'))
        self.wordpress_test_only = os.environ.get('WORDPRESS_TEST_ONLY', 'false').lower() == 'true'
        
        if self.test_mode:
            print(f"🧪 Running in TEST MODE (limited to {self.test_limit} posts per type)")
        
        if self.wordpress_test_only:
            print(f"🔧 Running WordPress-only test (using mock data)")
        
        # Authentication
        self.auth = (self.wp_username, self.wp_password)
        
        # Google Sheets Setup (skip if WordPress-only test)
        if not self.wordpress_test_only:
            self._init_google_sheets()
        
        # Test WordPress connection
        self._test_wordpress_auth()
        
        print("✅ WordPress syncer initialized successfully")
    
    def _init_google_sheets(self):
        """Initialize Google Sheets client"""
        try:
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            
            creds_dict = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT'])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            self.sheets_client = gspread.authorize(creds)
            self.sheet = self.sheets_client.open_by_key(os.environ['GOOGLE_SHEET_ID'])
            print("✅ Google Sheets connected successfully")
        except Exception as e:
            print(f"❌ Google Sheets connection failed: {e}")
            raise
    
    def _test_wordpress_auth(self):
        """Test WordPress API authentication and check available endpoints"""
        try:
            # Test basic auth
            test_url = f"{self.wp_site_url}/wp-json/wp/v2/users/me"
            response = requests.get(test_url, auth=self.auth, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ WordPress authenticated as: {user_data.get('name', 'Unknown')}")
            else:
                print(f"❌ WordPress auth failed: {response.status_code} - {response.text}")
                raise Exception("WordPress authentication failed")
            
            # Test REST API endpoints for our post types
            print("\n🔍 Checking REST API endpoints...")
            endpoints_to_test = ['beaches', 'cities', 'regions']
            
            for endpoint in endpoints_to_test:
                test_endpoint_url = f"{self.wp_site_url}/wp-json/wp/v2/{endpoint}"
                endpoint_response = requests.get(test_endpoint_url, auth=self.auth, timeout=10)
                
                if endpoint_response.status_code == 200:
                    print(f"   ✅ /{endpoint} endpoint available")
                elif endpoint_response.status_code == 404:
                    print(f"   ❌ /{endpoint} endpoint not found (404)")
                else:
                    print(f"   ⚠️  /{endpoint} endpoint returned {endpoint_response.status_code}")
            
            # List all available post types
            print("\n📋 Available post types in REST API:")
            try:
                types_url = f"{self.wp_site_url}/wp-json/wp/v2/types"
                types_response = requests.get(types_url, auth=self.auth, timeout=10)
                if types_response.status_code == 200:
                    types_data = types_response.json()
                    for type_key, type_info in types_data.items():
                        rest_base = type_info.get('rest_base', 'N/A')
                        print(f"   - {type_key}: /wp-json/wp/v2/{rest_base}")
                else:
                    print("   Could not fetch post types list")
            except Exception as e:
                print(f"   Error fetching post types: {e}")
                
        except Exception as e:
            print(f"❌ WordPress connection test failed: {e}")
            raise
    
    def load_sheet_data(self):
        """Load most recent processed data from beach_status sheet or generate mock data"""
        if self.wordpress_test_only:
            return self._generate_mock_data()
            
        try:
            worksheet = self.sheet.worksheet('beach_status')
            records = worksheet.get_all_records()
            
            # Group by location name and type, keeping only the most recent record for each
            data_by_type = {'beach': [], 'city': [], 'region': []}
            latest_records = {}  # Key: (location_name, location_type), Value: record
            
            for record in records:
                location_name = record.get('location_name', '')
                location_type = record.get('location_type', '').lower()
                last_updated = record.get('last_updated', '')
                
                if location_type in data_by_type and location_name:
                    key = (location_name, location_type)
                    
                    # Keep the most recent record for each location
                    if key not in latest_records or last_updated > latest_records[key].get('last_updated', ''):
                        latest_records[key] = record
            
            # Convert back to lists organized by type
            for (location_name, location_type), record in latest_records.items():
                data_by_type[location_type].append(record)
            
            # Apply test mode limits
            if self.test_mode:
                for location_type in data_by_type:
                    data_by_type[location_type] = data_by_type[location_type][:self.test_limit]
                    print(f"🧪 Test mode: Limited {location_type} to {len(data_by_type[location_type])} records")
            
            print(f"✅ Loaded most recent data from Google Sheets:")
            print(f"   - {len(data_by_type['beach'])} beaches")
            print(f"   - {len(data_by_type['city'])} cities")
            print(f"   - {len(data_by_type['region'])} regions")
            
            return data_by_type
            
        except Exception as e:
            print(f"❌ Failed to load sheet data: {e}")
            raise
    
    def _generate_mock_data(self):
        """Generate mock data for WordPress-only testing"""
        print("🔧 Generating mock data for WordPress testing...")
        
        mock_data = {
            'beach': [
                {
                    'location_name': 'Test Beach One',
                    'location_type': 'beach',
                    'current_status': 'safe',
                    'peak_count': 2500,
                    'confidence_score': 85,
                    'sample_date': '2025-01-15',
                    'region': 'Test Region',
                    'city': 'Test City',
                    'slug': 'test-beach-one'
                },
                {
                    'location_name': 'Test Beach Two',
                    'location_type': 'beach',
                    'current_status': 'caution',
                    'peak_count': 15000,
                    'confidence_score': 78,
                    'sample_date': '2025-01-14',
                    'region': 'Test Region',
                    'city': 'Test City',
                    'slug': 'test-beach-two'
                }
            ],
            'city': [
                {
                    'location_name': 'Test City',
                    'location_type': 'city',
                    'current_status': 'caution',
                    'peak_count': 15000,
                    'avg_count': 8750,
                    'confidence_score': 82,
                    'sample_date': '2025-01-15',
                    'beach_count': 2,
                    'beaches_safe': 1,
                    'beaches_caution': 1,
                    'beaches_avoid': 0,
                    'region': 'Test Region',
                    'slug': 'test-city'
                }
            ],
            'region': [
                {
                    'location_name': 'Test Region',
                    'location_type': 'region',
                    'current_status': 'caution',
                    'peak_count': 15000,
                    'avg_count': 8750,
                    'confidence_score': 82,
                    'sample_date': '2025-01-15',
                    'beach_count': 2,
                    'city_count': 1,
                    'beaches_safe': 1,
                    'beaches_caution': 1,
                    'beaches_avoid': 0,
                    'slug': 'test-region'
                }
            ]
        }
        
        # Apply test mode limits to mock data too
        if self.test_mode:
            for location_type in mock_data:
                mock_data[location_type] = mock_data[location_type][:self.test_limit]
        
        print(f"🔧 Generated mock data:")
        print(f"   - {len(mock_data['beach'])} test beaches")
        print(f"   - {len(mock_data['city'])} test cities")  
        print(f"   - {len(mock_data['region'])} test regions")
        
        return mock_data
    
    def get_status_color(self, status):
        """Get color code for status"""
        colors = {
            'safe': '#28a745',
            'caution': '#ffc107',
            'avoid': '#dc3545',
            'no_data': '#6c757d'
        }
        return colors.get(status, '#6c757d')
    
    def find_existing_post(self, slug, post_type):
        """Find existing WordPress post by slug"""
        # Map post types to REST endpoints
        rest_endpoints = {
            'beach': 'beaches',
            'city': 'cities', 
            'region': 'regions'
        }
        
        rest_base = rest_endpoints.get(post_type, post_type)
        
        try:
            search_url = f"{self.wp_site_url}/wp-json/wp/v2/{rest_base}"
            params = {'slug': slug}
            
            response = requests.get(search_url, params=params, auth=self.auth, timeout=10)
            
            if response.status_code == 200:
                posts = response.json()
                return posts[0] if posts else None
            else:
                print(f"   Warning: Search failed for {slug}: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"   Warning: Could not search for existing post {slug}: {e}")
            return None
    
    def create_or_update_post(self, data, post_type):
        """Create or update a WordPress post"""
        # Map post types to REST endpoints
        rest_endpoints = {
            'beach': 'beaches',
            'city': 'cities',
            'region': 'regions'
        }
        
        rest_base = rest_endpoints.get(post_type, post_type)
        location_name = data['location_name']
        slug = data['slug']
        
        # In test mode, add prefix to avoid conflicts
        if self.test_mode or self.wordpress_test_only:
            slug = f"test-{slug}"
            print(f"   🧪 Test mode: Using slug '{slug}' to avoid conflicts")
        
        # Check for existing post
        existing_post = self.find_existing_post(slug, post_type)
        
        if existing_post:
            # Update existing post
            post_id = existing_post['id']
            url = f"{self.wp_site_url}/wp-json/wp/v2/{rest_base}/{post_id}"
            method = 'POST'  # WordPress uses POST for updates
            action = "Updating"
        else:
            # Create new post
            url = f"{self.wp_site_url}/wp-json/wp/v2/{rest_base}"
            method = 'POST'
            action = "Creating"
        
        print(f"   {action} {post_type}: {location_name} (endpoint: {rest_base})")
        
        # Prepare post data (update slug in data for title generation)
        data_copy = data.copy()
        data_copy['slug'] = slug
        post_data = self._prepare_post_data(data_copy, post_type)
        
        try:
            response = requests.request(
                method, url,
                json=post_data,
                auth=self.auth,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                print(f"   ✅ Success: {location_name} (ID: {result['id']})")
                return result['id']
            else:
                print(f"   ❌ Failed: {location_name} - {response.status_code}")
                print(f"      Error: {response.text[:200]}")
                print(f"      URL attempted: {url}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error creating/updating {location_name}: {e}")
            return None
    
    def _prepare_post_data(self, data, post_type):
        """Prepare WordPress post data with ACF fields"""
        location_name = data['location_name']
        current_status = data['current_status']
        
        # Generate title and meta description
        if post_type == 'beach':
            title = f"{location_name} Red Tide Status - Current Conditions & Updates"
            meta_desc = f"Current red tide conditions at {location_name}. Real-time HAB monitoring data, safety information, and beach status updates."
        elif post_type == 'city':
            title = f"{location_name} Red Tide Status - All Beaches Current Conditions"
            meta_desc = f"Red tide conditions for all beaches in {location_name}, FL. Current status, safety advisories, and detailed monitoring data."
        else:  # region
            title = f"{location_name} Red Tide Status - Regional Overview & Beach Conditions"
            meta_desc = f"Comprehensive red tide monitoring for {location_name}. Track conditions across all beaches and cities in the region."
        
        # Core ACF fields (all post types)
        acf_data = {
            'current_status': current_status,
            'status_color': self.get_status_color(current_status),
            'last_updated': datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S'),
            'url_slug': data['slug'],
            'region': data.get('region', '') or None,
            'state': 'FL',
            'featured_location': False
        }
        
        # Add type-specific ACF fields
        if post_type == 'beach':
            # Load additional beach data from locations sheet
            beach_location_data = self._get_beach_location_data(location_name)
            
            acf_data.update({
                'city': data.get('city', '') or None,
                'coordinates': beach_location_data.get('coordinates', '') or None,
                'full_address': beach_location_data.get('address', '') or None,
                'zip_code': beach_location_data.get('zip', '') or None,
                'peak_count': int(data.get('peak_count', 0)),
                'confidence_score': int(data.get('confidence_score', 0)),
                'sample_date': data.get('sample_date', '') or None
            })
            
        elif post_type in ['city', 'region']:
            acf_data.update({
                'peak_count': int(data.get('peak_count', 0)),
                'avg_count': int(data.get('avg_count', 0)),
                'confidence_score': int(data.get('confidence_score', 0)),
                'sample_date': data.get('sample_date', '') or None,
                'beach_count': int(data.get('beach_count', 0)),
                'beaches_safe': int(data.get('beaches_safe', 0)),
                'beaches_caution': int(data.get('beaches_caution', 0)),
                'beaches_avoid': int(data.get('beaches_avoid', 0))
            })
            
            if post_type == 'region':
                acf_data['city_count'] = int(data.get('city_count', 0))
        
        # WordPress post payload
        post_payload = {
            'title': title,
            'slug': data['slug'],
            'status': 'publish',
            'acf': acf_data,
            'meta': {
                '_yoast_wpseo_metadesc': meta_desc
            }
        }
        
        return post_payload
    
    def _get_beach_location_data(self, beach_name):
        """Get additional beach data from locations sheet"""
        if self.wordpress_test_only:
            # Return mock location data for testing
            return {
                'coordinates': '27.265862, -82.552521',
                'address': '123 Test Beach Road, Test City, FL 12345',
                'zip': '12345'
            }
            
        try:
            worksheet = self.sheet.worksheet('locations')
            records = worksheet.get_all_records()
            
            for record in records:
                if record.get('beach', '') == beach_name:
                    return {
                        'coordinates': f"{record.get('lattitude', '')}, {record.get('longitude', '')}".strip(', ') or None,
                        'address': record.get('address', '') or None,
                        'zip': str(record.get('zip', '')) if record.get('zip') else None
                    }
            
            return {}
            
        except Exception as e:
            print(f"   Warning: Could not load location data for {beach_name}: {e}")
            return {}
    
    def sync_post_type(self, data_list, post_type):
        """Sync all posts of a specific type"""
        if not data_list:
            print(f"📝 No {post_type} data to sync")
            return []
        
        print(f"\n📝 Syncing {len(data_list)} {post_type} posts...")
        
        created_ids = []
        success_count = 0
        
        for data in data_list:
            post_id = self.create_or_update_post(data, post_type)
            if post_id:
                created_ids.append(post_id)
                success_count += 1
            
            # Rate limiting
            time.sleep(2)
        
        print(f"   ✅ {success_count}/{len(data_list)} {post_type} posts synced successfully")
        return created_ids
    
    def run(self):
        """Main execution function"""
        print("🔄 Starting WordPress sync...")
        
        try:
            # 1. Load data from Google Sheets
            sheet_data = self.load_sheet_data()
            
            # 2. Sync in hierarchical order (beaches → cities → regions)
            all_created_ids = []
            
            # Sync beaches first
            beach_ids = self.sync_post_type(sheet_data['beach'], 'beach')
            all_created_ids.extend(beach_ids)
            
            # Sync cities
            city_ids = self.sync_post_type(sheet_data['city'], 'city')
            all_created_ids.extend(city_ids)
            
            # Sync regions
            region_ids = self.sync_post_type(sheet_data['region'], 'region')
            all_created_ids.extend(region_ids)
            
            # 3. Summary
            total_beaches = len(sheet_data['beach'])
            total_cities = len(sheet_data['city'])
            total_regions = len(sheet_data['region'])
            total_synced = len(all_created_ids)
            total_attempted = total_beaches + total_cities + total_regions
            
            print(f"\n✅ WordPress sync complete!")
            print(f"   📊 Summary:")
            print(f"   - {len(beach_ids)}/{total_beaches} beaches synced")
            print(f"   - {len(city_ids)}/{total_cities} cities synced")
            print(f"   - {len(region_ids)}/{total_regions} regions synced")
            print(f"   - {total_synced}/{total_attempted} total posts synced")
            
            if total_synced < total_attempted:
                print(f"   ⚠️  {total_attempted - total_synced} posts failed to sync")
            
        except Exception as e:
            print(f"\n❌ WordPress sync failed: {e}")
            raise

if __name__ == "__main__":
    # Check for required environment variables
    required_vars = [
        'WORDPRESS_SITE_URL',
        'WORDPRESS_USERNAME', 
        'WORDPRESS_APP_PASSWORD',
        'GOOGLE_SERVICE_ACCOUNT',
        'GOOGLE_SHEET_ID'
    ]
    
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)
    
    # Run the syncer
    syncer = WordPressSyncer()
    syncer.run()