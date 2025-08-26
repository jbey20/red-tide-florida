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
        
        # Authentication
        self.auth = (self.wp_username, self.wp_password)
        
        # Google Sheets Setup
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
        """Test WordPress API authentication"""
        try:
            test_url = f"{self.wp_site_url}/wp-json/wp/v2/users/me"
            response = requests.get(test_url, auth=self.auth, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ WordPress authenticated as: {user_data.get('name', 'Unknown')}")
            else:
                print(f"❌ WordPress auth failed: {response.status_code} - {response.text}")
                raise Exception("WordPress authentication failed")
                
        except Exception as e:
            print(f"❌ WordPress connection test failed: {e}")
            raise
    
    def load_sheet_data(self):
        """Load processed data from beach_status sheet"""
        try:
            worksheet = self.sheet.worksheet('beach_status')
            records = worksheet.get_all_records()
            
            # Group by location type
            data_by_type = {'beach': [], 'city': [], 'region': []}
            
            for record in records:
                location_type = record.get('location_type', '').lower()
                if location_type in data_by_type:
                    data_by_type[location_type].append(record)
            
            print(f"✅ Loaded from Google Sheets:")
            print(f"   - {len(data_by_type['beach'])} beaches")
            print(f"   - {len(data_by_type['city'])} cities")
            print(f"   - {len(data_by_type['region'])} regions")
            
            return data_by_type
            
        except Exception as e:
            print(f"❌ Failed to load sheet data: {e}")
            raise
    
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
        try:
            search_url = f"{self.wp_site_url}/wp-json/wp/v2/{post_type}"
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
        location_name = data['location_name']
        slug = data['slug']
        
        # Check for existing post
        existing_post = self.find_existing_post(slug, post_type)
        
        if existing_post:
            # Update existing post
            post_id = existing_post['id']
            url = f"{self.wp_site_url}/wp-json/wp/v2/{post_type}/{post_id}"
            method = 'POST'  # WordPress uses POST for updates
            action = "Updating"
        else:
            # Create new post
            url = f"{self.wp_site_url}/wp-json/wp/v2/{post_type}"
            method = 'POST'
            action = "Creating"
        
        print(f"   {action} {post_type}: {location_name}")
        
        # Prepare post data
        post_data = self._prepare_post_data(data, post_type)
        
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
            'region': data.get('region', ''),
            'state': 'FL',
            'featured_location': False
        }
        
        # Add type-specific ACF fields
        if post_type == 'beach':
            # Load additional beach data from locations sheet
            beach_location_data = self._get_beach_location_data(location_name)
            
            acf_data.update({
                'city': data.get('city', ''),
                'coordinates': beach_location_data.get('coordinates', ''),
                'full_address': beach_location_data.get('address', ''),
                'zip_code': beach_location_data.get('zip', ''),
                'peak_count': int(data.get('peak_count', 0)),
                'confidence_score': int(data.get('confidence_score', 0)),
                'sample_date': data.get('sample_date', '')
            })
            
        elif post_type in ['city', 'region']:
            acf_data.update({
                'peak_count': int(data.get('peak_count', 0)),
                'avg_count': int(data.get('avg_count', 0)),
                'confidence_score': int(data.get('confidence_score', 0)),
                'sample_date': data.get('sample_date', ''),
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
        try:
            worksheet = self.sheet.worksheet('locations')
            records = worksheet.get_all_records()
            
            for record in records:
                if record.get('beach', '') == beach_name:
                    return {
                        'coordinates': f"{record.get('lattitude', '')}, {record.get('longitude', '')}".strip(', '),
                        'address': record.get('address', ''),
                        'zip': record.get('zip', '')
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