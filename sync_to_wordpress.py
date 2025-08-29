#!/usr/bin/env python3
"""
WordPress Sync Script - Simplified Version
Reads data from Google Sheets and creates/updates WordPress posts via REST API
"""

import requests
import json
import os
import time
import re
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
        test_limit_str = os.environ.get('TEST_LIMIT', '2')
        self.test_limit = int(test_limit_str) if test_limit_str and test_limit_str.strip() else 2
        self.wordpress_test_only = os.environ.get('WORDPRESS_TEST_ONLY', 'false').lower() == 'true'
        
        # Rate limiting and caching
        self.sheet_cache = {}
        self.last_api_call = 0
        # Adjust rate limiting based on environment (more conservative for production)
        rate_limit_str = os.environ.get('API_RATE_LIMIT_SECONDS', '1.1')
        self.min_call_interval = float(rate_limit_str)
        print(f"⏱️  API rate limiting: {self.min_call_interval}s between calls")
        
        # ACF configuration
        self.use_relationship_fields = os.environ.get('USE_ACF_RELATIONSHIPS', 'true').lower() == 'true'
        print(f"🔗 ACF relationship fields: {'enabled' if self.use_relationship_fields else 'disabled'}")
        
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
        
        # Preload all sheet data to minimize API calls
        if not self.wordpress_test_only:
            self._preload_sheet_data()
        
        print("✅ WordPress syncer initialized successfully")
    
    def _rate_limit(self):
        """Ensure minimum time between API calls"""
        current_time = time.time()
        time_since_last = current_time - self.last_api_call
        if time_since_last < self.min_call_interval:
            sleep_time = self.min_call_interval - time_since_last
            time.sleep(sleep_time)
        self.last_api_call = time.time()
    
    def _get_cached_sheet_data(self, worksheet_name):
        """Get sheet data with caching to reduce API calls"""
        if worksheet_name in self.sheet_cache:
            return self.sheet_cache[worksheet_name]
        
        self._rate_limit()
        try:
            worksheet = self.sheet.worksheet(worksheet_name)
            records = worksheet.get_all_records()
            self.sheet_cache[worksheet_name] = records
            return records
        except Exception as e:
            if "429" in str(e) or "quota exceeded" in str(e).lower():
                print(f"⚠️  Rate limit hit while loading {worksheet_name}. Waiting 60 seconds...")
                time.sleep(60)
                # Retry once after waiting
                self._rate_limit()
                worksheet = self.sheet.worksheet(worksheet_name)
                records = worksheet.get_all_records()
                self.sheet_cache[worksheet_name] = records
                return records
            else:
                raise
    
    def clear_cache(self):
        """Clear the sheet cache to force fresh data"""
        self.sheet_cache.clear()
        print("🗑️  Sheet cache cleared")
    
    def _find_related_post_ids(self, region_name, post_type):
        """Find post IDs for related posts (beaches/cities in a region)"""
        try:
            # Get the beach_status data to find related posts
            beach_status_records = self._get_cached_sheet_data('beach_status')
            
            related_ids = []
            for record in beach_status_records:
                record_region = record.get('region', '')
                record_type = record.get('location_type', '').lower()
                
                # Match region and post type
                if record_region == region_name and record_type == post_type:
                    # Try to find the WordPress post ID for this location
                    location_name = record.get('location_name', '')
                    if location_name:
                        # Search for existing post
                        search_slug = f"{location_name.lower().replace(' ', '-')}-red-tide"
                        existing_post = self.find_existing_post(search_slug, post_type)
                        if existing_post:
                            related_ids.append(existing_post['id'])
            
            return related_ids
            
        except Exception as e:
            print(f"   Warning: Could not find related post IDs for {region_name}: {e}")
            return []
    
    def _preload_sheet_data(self):
        """Preload all required sheet data to minimize API calls during processing"""
        print("📥 Preloading Google Sheets data...")
        try:
            # Load all required worksheets
            required_sheets = ['beach_status', 'locations', 'sample_mapping']
            for sheet_name in required_sheets:
                print(f"   Loading {sheet_name}...")
                self._get_cached_sheet_data(sheet_name)
            print("✅ All sheet data preloaded successfully")
        except Exception as e:
            print(f"⚠️  Warning: Could not preload all sheet data: {e}")
            print("   Will load data as needed during processing")
    
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
            records = self._get_cached_sheet_data('beach_status')
            
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
            
            # Debug: Show sample region data
            if data_by_type['region']:
                sample_region = data_by_type['region'][0]
                print(f"   📊 Sample region data for {sample_region.get('location_name', 'Unknown')}:")
                print(f"      - beach_count: {sample_region.get('beach_count', 'N/A')}")
                print(f"      - city_count: {sample_region.get('city_count', 'N/A')}")
                print(f"      - beaches_safe: {sample_region.get('beaches_safe', 'N/A')}")
                print(f"      - beaches_caution: {sample_region.get('beaches_caution', 'N/A')}")
                print(f"      - beaches_avoid: {sample_region.get('beaches_avoid', 'N/A')}")
            
            return data_by_type
            
        except Exception as e:
            error_msg = str(e)
            if "header row in the worksheet is not unique" in error_msg:
                print(f"❌ Failed to load sheet data: {e}")
                print("\n🔧 HEADER ISSUE DETECTED!")
                print("   Your Google Sheet has duplicate column headers.")
                print("   This usually happens when new columns are added incorrectly.")
                print("\n📋 REQUIRED HEADERS (in exact order):")
                required_headers = [
                    'location_name', 'location_type', 'date', 'current_status',
                    'peak_count', 'avg_count', 'confidence_score', 'sample_date', 'last_updated',
                    'region', 'city', 'slug', 'beach_count', 'city_count', 
                    'beaches_safe', 'beaches_caution', 'beaches_avoid'
                ]
                for i, header in enumerate(required_headers, 1):
                    print(f"   {i:2d}. {header}")
                print("\n🔧 MANUAL FIX:")
                print("   1. Open your Google Sheet (beach_status worksheet)")
                print("   2. Delete the current header row")
                print("   3. Add a new header row with the exact headers above")
                print("   4. Ensure NO duplicate column names exist")
                print("   5. Make sure 'slug' column exists (not 'page slug')")
                print("\n💡 Or run: python fix_sheet_headers.py for automated fix")
            else:
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
                    'slug': 'test-beach-one-red-tide'
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
                    'slug': 'test-beach-two-red-tide'
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
                    'slug': 'test-city-red-tide'
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
                    'slug': 'test-region-red-tide'
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
        # Rate limit WordPress API calls
        self._rate_limit()
        
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
        # Rate limit WordPress API calls too
        self._rate_limit()
        
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
        
        # Ensure slug format is consistent
        if not slug.endswith('-red-tide'):
            slug = f"{slug}-red-tide"
        
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
            'location_name': location_name,
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
            
            # Get HAB sampling sites for this beach
            beach_sampling_sites = self._get_beach_sampling_sites(location_name)
            
            # Get parent city and region post IDs
            parent_city_id = self._find_parent_post_id(data.get('city', ''), 'city')
            parent_region_id = self._find_parent_post_id(data.get('region', ''), 'region')
            
            acf_data.update({
                'city': data.get('city', '') or None,
                'coordinates': beach_location_data.get('coordinates', '') or None,
                'full_address': beach_location_data.get('address', '') or None,
                'zip_code': beach_location_data.get('zip', '') or None,
                'peak_count': int(data.get('peak_count', 0)),
                'confidence_score': int(data.get('confidence_score', 0)),
                'sample_date': data.get('sample_date', '') or None,
                'parent_city_post': parent_city_id,
                'parent_region_post': parent_region_id,
                'sampling_sites': beach_sampling_sites,
                'beach_description': self._generate_beach_description(location_name, data),
                'nearby_beaches': self._get_nearby_beaches(location_name, data.get('region', '')),
                'nearby_regions': self._get_nearby_regions(data.get('region', ''))
            })
            
        elif post_type == 'city':
            # Get HAB sampling sites for this city
            hab_sites = self._get_city_hab_sampling_sites(location_name)
            
            # Get parent region post ID
            parent_region_id = self._find_parent_post_id(data.get('region', ''), 'region')
            
            # Get child beach post IDs
            child_beach_ids = self._find_child_post_ids(location_name, 'beach')
            
            acf_data.update({
                'peak_count': int(data.get('peak_count', 0)),
                'avg_count': int(data.get('avg_count', 0)),
                'confidence_score': int(data.get('confidence_score', 0)),
                'sample_date': data.get('sample_date', '') or None,
                'beach_count': int(data.get('beach_count', 0)),
                'beaches_safe': int(data.get('beaches_safe', 0)),
                'beaches_caution': int(data.get('beaches_caution', 0)),
                'beaches_avoid': int(data.get('beaches_avoid', 0)),
                'child_beaches': child_beach_ids,
                'parent_region': parent_region_id,
                'peak_cell_count': int(data.get('peak_count', 0)),
                'average_cell_count': int(data.get('avg_count', 0)),
                'average_confidence': int(data.get('confidence_score', 0)),
                'latest_sample_data': data.get('sample_date', '') or None,
                'total_beaches': int(data.get('beach_count', 0)),
                'city_description': self._generate_city_description(location_name, data),
                'nearby_cities': self._get_nearby_cities(location_name, data.get('region', '')),
                'nearby_beaches': self._get_nearby_beaches_for_city(location_name, data.get('region', ''))
            })
            
        elif post_type == 'region':
            # Get child post IDs
            child_beach_ids = self._find_child_post_ids(location_name, 'beach')
            child_city_ids = self._find_child_post_ids(location_name, 'city')
            
            acf_data.update({
                'peak_count': int(data.get('peak_count', 0)),
                'avg_count': int(data.get('avg_count', 0)),
                'confidence_score': int(data.get('confidence_score', 0)),
                'sample_date': data.get('sample_date', '') or None,
                'beach_count': int(data.get('beach_count', 0)),
                'beaches_safe': int(data.get('beaches_safe', 0)),
                'beaches_caution': int(data.get('beaches_caution', 0)),
                'beaches_avoid': int(data.get('beaches_avoid', 0)),
                'city_count': int(data.get('city_count', 0)),
                'total_beaches': int(data.get('beach_count', 0)),
                'total_cities': int(data.get('city_count', 0)),
                'child_beaches': child_beach_ids,
                'child_cities': child_city_ids,
                'region_description': self._generate_region_description(location_name, data),
                'nearby_regions': self._get_nearby_regions(location_name)
            })
            
            # Debug: Print region ACF data
            print(f"   🔍 Region ACF data for {location_name}:")
            print(f"      - beach_count: {acf_data.get('beach_count', 'N/A')}")
            print(f"      - city_count: {acf_data.get('city_count', 'N/A')}")
            print(f"      - beaches_safe: {acf_data.get('beaches_safe', 'N/A')}")
            print(f"      - beaches_caution: {acf_data.get('beaches_caution', 'N/A')}")
            print(f"      - beaches_avoid: {acf_data.get('beaches_avoid', 'N/A')}")
            print(f"      - child_beaches (IDs): {child_beach_ids}")
            print(f"      - child_cities (IDs): {child_city_ids}")
        
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
            records = self._get_cached_sheet_data('locations')
            
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
    
    def _get_city_hab_sampling_sites(self, city_name):
        """Get HAB sampling sites for a city from the sample_mapping sheet"""
        if self.wordpress_test_only:
            # Return mock HAB sampling sites for testing
            return [
                {
                    'hab_id': 'TEST_HAB_001',
                    'sample_location': f'Test Location 1 in {city_name}',
                    'distance_miles': '0.5',
                    'cell_count': '2500',
                    'sample_date': '2025-01-15'
                },
                {
                    'hab_id': 'TEST_HAB_002', 
                    'sample_location': f'Test Location 2 in {city_name}',
                    'distance_miles': '1.2',
                    'cell_count': '15000',
                    'sample_date': '2025-01-14'
                }
            ]
            
        try:
            # Get cached data from both sheets
            locations_records = self._get_cached_sheet_data('locations')
            sample_records = self._get_cached_sheet_data('sample_mapping')
            
            # Create a mapping of beach names to cities
            beach_to_city = {}
            for location_record in locations_records:
                beach_name = location_record.get('beach', '')
                beach_city = location_record.get('city', '')
                if beach_name and beach_city:
                    beach_to_city[beach_name] = beach_city
            
            hab_sites = []
            for record in sample_records:
                beach_name = record.get('beach', '')
                
                # Check if this beach belongs to the target city
                if beach_name in beach_to_city and beach_to_city[beach_name] == city_name:
                    hab_sites.append({
                        'hab_id': record.get('HAB_id', ''),
                        'sample_location': record.get('sample_location', ''),
                        'distance_miles': str(record.get('sample_distance', 0)),
                        'cell_count': str(record.get('cell_count', 0)),
                        'sample_date': record.get('sample_date', '')
                    })
            
            return hab_sites
            
        except Exception as e:
            print(f"   Warning: Could not load HAB sampling sites for {city_name}: {e}")
            return []
    
    def _get_beach_sampling_sites(self, beach_name):
        """Get HAB sampling sites for a specific beach"""
        if self.wordpress_test_only:
            # Return mock sampling sites for testing
            return [
                {
                    'hab_id': f'TEST_HAB_{beach_name.upper().replace(" ", "_")}_001',
                    'sample_location': f'{beach_name} - Main Beach',
                    'distance_miles': '0.1',
                    'current_concentration': '2500',
                    'sample_date': '2025-01-15'
                }
            ]
            
        try:
            sample_records = self._get_cached_sheet_data('sample_mapping')
            
            sampling_sites = []
            for record in sample_records:
                if record.get('beach', '') == beach_name:
                    sampling_sites.append({
                        'hab_id': record.get('HAB_id', ''),
                        'sample_location': record.get('sample_location', ''),
                        'distance_miles': str(record.get('sample_distance', 0)),
                        'current_concentration': str(record.get('cell_count', 0)),
                        'sample_date': record.get('sample_date', '')
                    })
            
            return sampling_sites
            
        except Exception as e:
            print(f"   Warning: Could not load sampling sites for {beach_name}: {e}")
            return []
    
    def _find_parent_post_id(self, parent_name, post_type):
        """Find post ID for parent city or region"""
        if not parent_name:
            return None
            
        try:
            # Search for existing post by name
            search_slug = f"{parent_name.lower().replace(' ', '-')}-red-tide"
            existing_post = self.find_existing_post(search_slug, post_type)
            return existing_post['id'] if existing_post else None
        except Exception as e:
            print(f"   Warning: Could not find parent {post_type} ID for {parent_name}: {e}")
            return None
    
    def _find_child_post_ids(self, parent_name, child_type):
        """Find post IDs for child beaches or cities in a parent region/city"""
        try:
            # Get the beach_status data to find related posts
            beach_status_records = self._get_cached_sheet_data('beach_status')
            
            child_ids = []
            for record in beach_status_records:
                record_parent = record.get('region' if child_type == 'beach' else 'city', '')
                record_type = record.get('location_type', '').lower()
                
                # Match parent and child type
                if record_parent == parent_name and record_type == child_type:
                    # Try to find the WordPress post ID for this location
                    location_name = record.get('location_name', '')
                    if location_name:
                        # Search for existing post
                        search_slug = f"{location_name.lower().replace(' ', '-')}-red-tide"
                        existing_post = self.find_existing_post(search_slug, child_type)
                        if existing_post:
                            child_ids.append(existing_post['id'])
            
            return child_ids
            
        except Exception as e:
            print(f"   Warning: Could not find child {child_type} IDs for {parent_name}: {e}")
            return []
    
    def _generate_beach_description(self, beach_name, data):
        """Generate a description for a beach"""
        status = data.get('current_status', 'no_data')
        peak_count = data.get('peak_count', 0)
        city = data.get('city', '')
        
        if status == 'safe':
            return f"{beach_name} in {city}, Florida currently has safe red tide conditions with low cell counts ({peak_count} cells/L). The beach is open for swimming and recreation."
        elif status == 'caution':
            return f"{beach_name} in {city}, Florida is experiencing moderate red tide conditions ({peak_count} cells/L). Visitors should exercise caution and check for any posted advisories."
        elif status == 'avoid':
            return f"{beach_name} in {city}, Florida has high red tide levels ({peak_count} cells/L). Swimming and water activities are not recommended at this time."
        else:
            return f"{beach_name} in {city}, Florida. Current red tide monitoring data is being collected to assess conditions."
    
    def _generate_city_description(self, city_name, data):
        """Generate a description for a city"""
        status = data.get('current_status', 'no_data')
        beach_count = data.get('beach_count', 0)
        region = data.get('region', '')
        
        if status == 'safe':
            return f"{city_name} in {region}, Florida has {beach_count} monitored beaches, all currently showing safe red tide conditions. The area is open for beach activities."
        elif status == 'caution':
            return f"{city_name} in {region}, Florida has {beach_count} monitored beaches with some showing moderate red tide conditions. Check individual beach status before visiting."
        elif status == 'avoid':
            return f"{city_name} in {region}, Florida has {beach_count} monitored beaches with high red tide levels. Beach activities are not recommended at this time."
        else:
            return f"{city_name} in {region}, Florida has {beach_count} monitored beaches. Current red tide monitoring data is being collected."
    
    def _generate_region_description(self, region_name, data):
        """Generate a description for a region"""
        status = data.get('current_status', 'no_data')
        beach_count = data.get('beach_count', 0)
        city_count = data.get('city_count', 0)
        
        if status == 'safe':
            return f"{region_name} region in Florida encompasses {city_count} cities and {beach_count} monitored beaches, all currently showing safe red tide conditions."
        elif status == 'caution':
            return f"{region_name} region in Florida encompasses {city_count} cities and {beach_count} monitored beaches with some areas showing moderate red tide conditions."
        elif status == 'avoid':
            return f"{region_name} region in Florida encompasses {city_count} cities and {beach_count} monitored beaches with high red tide levels affecting multiple areas."
        else:
            return f"{region_name} region in Florida encompasses {city_count} cities and {beach_count} monitored beaches. Comprehensive red tide monitoring is ongoing."
    
    def _get_nearby_beaches(self, beach_name, region_name):
        """Get nearby beaches for a specific beach"""
        if self.wordpress_test_only:
            return [
                {
                    'beach': None,  # Will be populated with post object ID
                    'distance': 2.5,
                    'current_status': 'safe',
                    'status_color': '#28a745',
                    'description': 'Nearby beach with safe conditions'
                }
            ]
            
        try:
            beach_status_records = self._get_cached_sheet_data('beach_status')
            
            nearby_beaches = []
            for record in beach_status_records:
                record_name = record.get('location_name', '')
                record_type = record.get('location_type', '').lower()
                record_region = record.get('region', '')
                
                # Find other beaches in the same region
                if (record_type == 'beach' and 
                    record_name != beach_name and 
                    record_region == region_name):
                    
                    # Try to find the WordPress post ID
                    search_slug = f"{record_name.lower().replace(' ', '-')}-red-tide"
                    existing_post = self.find_existing_post(search_slug, 'beach')
                    
                    nearby_beaches.append({
                        'beach': existing_post['id'] if existing_post else None,
                        'distance': 2.5,  # Mock distance
                        'current_status': record.get('current_status', 'no_data'),
                        'status_color': self.get_status_color(record.get('current_status', 'no_data')),
                        'description': f"{record_name} - {record.get('current_status', 'no_data')} conditions"
                    })
                    
                    # Limit to 5 nearby beaches
                    if len(nearby_beaches) >= 5:
                        break
            
            return nearby_beaches
            
        except Exception as e:
            print(f"   Warning: Could not get nearby beaches for {beach_name}: {e}")
            return []
    
    def _get_nearby_beaches_for_city(self, city_name, region_name):
        """Get nearby beaches for a city (different from beach nearby beaches)"""
        if self.wordpress_test_only:
            return [
                {
                    'beach': None,
                    'distance': 1.5,
                    'current_status': 'safe',
                    'status_color': '#28a745',
                    'description': 'Popular beach in the area'
                }
            ]
            
        try:
            beach_status_records = self._get_cached_sheet_data('beach_status')
            
            nearby_beaches = []
            for record in beach_status_records:
                record_name = record.get('location_name', '')
                record_type = record.get('location_type', '').lower()
                record_city = record.get('city', '')
                
                # Find beaches in the same city
                if (record_type == 'beach' and 
                    record_city == city_name):
                    
                    # Try to find the WordPress post ID
                    search_slug = f"{record_name.lower().replace(' ', '-')}-red-tide"
                    existing_post = self.find_existing_post(search_slug, 'beach')
                    
                    nearby_beaches.append({
                        'beach': existing_post['id'] if existing_post else None,
                        'distance': 1.5,  # Mock distance
                        'current_status': record.get('current_status', 'no_data'),
                        'status_color': self.get_status_color(record.get('current_status', 'no_data')),
                        'description': f"{record_name} - {record.get('current_status', 'no_data')} conditions"
                    })
                    
                    # Limit to 8 nearby beaches
                    if len(nearby_beaches) >= 8:
                        break
            
            return nearby_beaches
            
        except Exception as e:
            print(f"   Warning: Could not get nearby beaches for city {city_name}: {e}")
            return []
    
    def _get_nearby_cities(self, city_name, region_name):
        """Get nearby cities for a specific city"""
        if self.wordpress_test_only:
            return [
                {
                    'city': None,
                    'distance': 15.0,
                    'current_status': 'caution',
                    'status_color': '#ffc107',
                    'description': 'Nearby city with moderate conditions'
                }
            ]
            
        try:
            beach_status_records = self._get_cached_sheet_data('beach_status')
            
            # Get unique cities in the same region
            cities_in_region = set()
            for record in beach_status_records:
                record_city = record.get('city', '')
                record_region = record.get('region', '')
                record_type = record.get('location_type', '').lower()
                
                if record_type == 'city' and record_region == region_name and record_city != city_name:
                    cities_in_region.add(record_city)
            
            nearby_cities = []
            for city in list(cities_in_region)[:5]:  # Limit to 5 nearby cities
                # Try to find the WordPress post ID
                search_slug = f"{city.lower().replace(' ', '-')}-red-tide"
                existing_post = self.find_existing_post(search_slug, 'city')
                
                # Get city status from records
                city_status = 'no_data'
                for record in beach_status_records:
                    if (record.get('location_name', '') == city and 
                        record.get('location_type', '').lower() == 'city'):
                        city_status = record.get('current_status', 'no_data')
                        break
                
                nearby_cities.append({
                    'city': existing_post['id'] if existing_post else None,
                    'distance': 15.0,  # Mock distance
                    'current_status': city_status,
                    'status_color': self.get_status_color(city_status),
                    'description': f"{city} - {city_status} conditions"
                })
            
            return nearby_cities
            
        except Exception as e:
            print(f"   Warning: Could not get nearby cities for {city_name}: {e}")
            return []
    
    def _get_nearby_regions(self, region_name):
        """Get nearby regions for a specific region"""
        if self.wordpress_test_only:
            return [
                {
                    'region': None,
                    'distance': 50.0,
                    'current_status': 'safe',
                    'status_color': '#28a745',
                    'description': 'Adjacent region with safe conditions'
                }
            ]
            
        try:
            beach_status_records = self._get_cached_sheet_data('beach_status')
            
            # Get unique regions
            all_regions = set()
            for record in beach_status_records:
                record_region = record.get('region', '')
                if record_region and record_region != region_name:
                    all_regions.add(record_region)
            
            nearby_regions = []
            for region in list(all_regions)[:3]:  # Limit to 3 nearby regions
                # Try to find the WordPress post ID
                search_slug = f"{region.lower().replace(' ', '-')}-red-tide"
                existing_post = self.find_existing_post(search_slug, 'region')
                
                # Get region status from records
                region_status = 'no_data'
                for record in beach_status_records:
                    if (record.get('location_name', '') == region and 
                        record.get('location_type', '').lower() == 'region'):
                        region_status = record.get('current_status', 'no_data')
                        break
                
                nearby_regions.append({
                    'region': existing_post['id'] if existing_post else None,
                    'distance': 50.0,  # Mock distance
                    'current_status': region_status,
                    'status_color': self.get_status_color(region_status),
                    'description': f"{region} - {region_status} conditions"
                })
            
            return nearby_regions
            
        except Exception as e:
            print(f"   Warning: Could not get nearby regions for {region_name}: {e}")
            return []
    
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
    
    def _generate_slug(self, name):
        """Generate URL-friendly slug in format: <location-name>-red-tide"""
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        return f"{slug}-red-tide"

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