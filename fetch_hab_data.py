#!/usr/bin/env python3
"""
HAB Data Fetcher - Simplified Version
Fetches data from FWC HAB API, processes it, and updates Google Sheets
"""

import requests
import json
import os
import re
import time
from datetime import datetime, timedelta
import pytz
import gspread
from google.oauth2.service_account import Credentials

class HABDataFetcher:
    def __init__(self):
        # API Configuration
        self.fwc_api_url = "https://atoll.floridamarine.org/arcgis/rest/services/FWC_GIS/OpenData_HAB/MapServer/9/query"
        
        # Google Sheets Setup
        self._init_google_sheets()
        
        # Load configuration from sheets
        self.locations_data = self._load_locations()
        self.sample_mapping = self._load_sample_mapping()
        
        print(f"Initialized with {len(self.locations_data)} locations and {len(self.sample_mapping)} sample mappings")
    
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
    
    def _load_locations(self):
        """Load beach locations from locations sheet"""
        try:
            worksheet = self.sheet.worksheet('locations')
            records = worksheet.get_all_records()
            print(f"Loaded {len(records)} location records from Google Sheets")
            return {record['beach']: record for record in records}
        except Exception as e:
            print(f"Error loading locations: {e}")
            return {}
    
    def _load_sample_mapping(self):
        """Load HAB sample site mappings from sample_mapping sheet"""
        try:
            worksheet = self.sheet.worksheet('sample_mapping')
            records = worksheet.get_all_records()
            
            # Group by beach name
            mapping = {}
            for record in records:
                beach_name = record['beach']
                if beach_name not in mapping:
                    mapping[beach_name] = []
                mapping[beach_name].append(record)
            
            print(f"Loaded sample mappings for {len(mapping)} beaches")
            return mapping
        except Exception as e:
            print(f"Error loading sample mapping: {e}")
            return {}
    
    def fetch_fwc_data(self):
        """Fetch latest HAB data from Florida FWC API"""
        print("Fetching data from FWC HAB API...")
        
        params = {
            'where': '1=1',
            'outFields': '*',
            'outSR': '4326',
            'f': 'json',
            'orderByFields': 'SAMPLE_DATE DESC',
            'resultRecordCount': 1000  # Get more recent records
        }
        
        try:
            response = requests.get(self.fwc_api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            print(f"✅ Fetched {len(features)} HAB samples from FWC API")
            return data
            
        except Exception as e:
            print(f"❌ Failed to fetch FWC data: {e}")
            raise
    
    def parse_abundance_to_status(self, abundance_text):
        """Convert FWC abundance categories to status and cell count"""
        if not abundance_text:
            return 0, 'no_data'
        
        abundance_lower = abundance_text.lower()
        
        # Extract numbers from text
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
    
    def calculate_beach_status(self, beach_name, fwc_data):
        """Calculate beach status from HAB sampling sites"""
        sampling_sites = self.sample_mapping.get(beach_name, [])
        
        if not sampling_sites:
            return {
                'location_name': beach_name,
                'location_type': 'beach',
                'current_status': 'no_data',
                'peak_count': 0,
                'confidence_score': 0,
                'sample_date': '',
                'region': self.locations_data.get(beach_name, {}).get('region', ''),
                'city': self.locations_data.get(beach_name, {}).get('city', ''),
                'slug': self._generate_slug(beach_name)
            }
        
        site_results = []
        weighted_scores = []
        latest_sample_date = None
        
        # Process each sampling site
        for site in sampling_sites:
            hab_id = site['HAB_id']
            distance = float(site.get('sample_distance', 99))
            
            # Find matching FWC data
            site_data = self._find_hab_data_by_id(fwc_data, hab_id, site['sample_location'])
            
            if site_data:
                cell_count, status = self.parse_abundance_to_status(site_data['abundance'])
                sample_date = datetime.fromtimestamp(site_data['sample_date'] / 1000)
                
                # Update latest sample date
                if not latest_sample_date or sample_date > latest_sample_date:
                    latest_sample_date = sample_date
                
                # Distance weighting
                if distance <= 1.0:
                    weight = 1.0
                elif distance <= 3.0:
                    weight = 0.7
                elif distance <= 10.0:
                    weight = 0.4
                else:
                    weight = 0.2
                
                # Age weighting (reduce weight for old samples)
                age_days = (datetime.now() - sample_date).days
                age_weight = max(0.1, 1 - (age_days / 7.0)) if age_days > 7 else 1.0
                
                final_weight = weight * age_weight
                status_score = {'safe': 0, 'caution': 1, 'avoid': 2, 'no_data': 0}.get(status, 0)
                weighted_scores.append(status_score * final_weight)
                
                site_results.append({
                    'cell_count': cell_count,
                    'status': status,
                    'weight': final_weight,
                    'sample_date': sample_date
                })
        
        # Calculate overall status
        if not weighted_scores:
            overall_status = 'no_data'
            confidence = 0
            peak_count = 0
        else:
            avg_weighted_score = sum(weighted_scores) / len(weighted_scores)
            
            if avg_weighted_score >= 1.5:
                overall_status = 'avoid'
            elif avg_weighted_score >= 0.5:
                overall_status = 'caution'
            else:
                overall_status = 'safe'
            
            confidence = min(100, int(sum([s['weight'] for s in site_results]) * 40 + len(site_results) * 15))
            peak_count = max([s['cell_count'] for s in site_results]) if site_results else 0
        
        return {
            'location_name': beach_name,
            'location_type': 'beach',
            'current_status': overall_status,
            'peak_count': peak_count,
            'confidence_score': confidence,
            'sample_date': latest_sample_date.strftime('%Y-%m-%d') if latest_sample_date else '',
            'region': self.locations_data.get(beach_name, {}).get('region', ''),
            'city': self.locations_data.get(beach_name, {}).get('city', ''),
            'slug': self._generate_slug(beach_name)
        }
    
    def _find_hab_data_by_id(self, fwc_data, hab_id, sample_location):
        """Find FWC data by HAB ID or location matching"""
        # Try exact HAB ID match first
        for feature in fwc_data['features']:
            attrs = feature['attributes']
            if attrs.get('HAB_ID') == hab_id:
                return {
                    'abundance': attrs.get('Abundance', 'No Data'),
                    'sample_date': attrs.get('SAMPLE_DATE'),
                    'location': attrs.get('LOCATION')
                }
        
        # Fallback: match by location name
        sample_location_lower = sample_location.lower()
        best_match = None
        best_score = 0
        
        for feature in fwc_data['features']:
            attrs = feature['attributes']
            location = attrs.get('LOCATION', '').lower()
            
            if sample_location_lower in location or location in sample_location_lower:
                sample_date = datetime.fromtimestamp(attrs['SAMPLE_DATE'] / 1000)
                age_days = (datetime.now() - sample_date).days
                score = max(0, 10 - age_days)  # Prefer recent samples
                
                if score > best_score:
                    best_score = score
                    best_match = attrs
        
        if best_match:
            return {
                'abundance': best_match.get('Abundance', 'No Data'),
                'sample_date': best_match.get('SAMPLE_DATE'),
                'location': best_match.get('LOCATION')
            }
        
        return None
    
    def aggregate_city_data(self, beach_results):
        """Calculate city-level aggregations from beach data"""
        city_data = {}
        
        for beach in beach_results:
            city_name = beach['city']
            if not city_name:
                continue
                
            if city_name not in city_data:
                city_data[city_name] = {
                    'location_name': city_name,
                    'location_type': 'city',
                    'beaches': [],
                    'region': beach['region'],
                    'slug': self._generate_slug(city_name)
                }
            
            city_data[city_name]['beaches'].append(beach)
        
        # Calculate aggregates for each city
        city_results = []
        for city_name, data in city_data.items():
            beaches = data['beaches']
            
            # Status counts
            safe_count = len([b for b in beaches if b['current_status'] == 'safe'])
            caution_count = len([b for b in beaches if b['current_status'] == 'caution'])
            avoid_count = len([b for b in beaches if b['current_status'] == 'avoid'])
            
            # Determine city status (worst among beaches)
            if avoid_count > 0:
                city_status = 'avoid'
            elif caution_count > 0:
                city_status = 'caution'
            elif safe_count > 0:
                city_status = 'safe'
            else:
                city_status = 'no_data'
            
            # Numeric aggregates
            peak_counts = [b['peak_count'] for b in beaches if b['peak_count'] > 0]
            confidences = [b['confidence_score'] for b in beaches if b['confidence_score'] > 0]
            
            city_results.append({
                'location_name': city_name,
                'location_type': 'city',
                'current_status': city_status,
                'peak_count': max(peak_counts) if peak_counts else 0,
                'avg_count': int(sum(peak_counts) / len(peak_counts)) if peak_counts else 0,
                'confidence_score': int(sum(confidences) / len(confidences)) if confidences else 0,
                'sample_date': max([b['sample_date'] for b in beaches if b['sample_date']]) if any(b['sample_date'] for b in beaches) else '',
                'beach_count': len(beaches),
                'beaches_safe': safe_count,
                'beaches_caution': caution_count,
                'beaches_avoid': avoid_count,
                'region': data['region'],
                'slug': data['slug']
            })
        
        return city_results
    
    def aggregate_region_data(self, beach_results, city_results):
        """Calculate region-level aggregations"""
        region_data = {}
        
        # Group beaches by region
        for beach in beach_results:
            region_name = beach['region']
            if not region_name:
                continue
                
            if region_name not in region_data:
                region_data[region_name] = {
                    'beaches': [],
                    'cities': set()
                }
            
            region_data[region_name]['beaches'].append(beach)
            if beach['city']:
                region_data[region_name]['cities'].add(beach['city'])
        
        # Calculate aggregates for each region
        region_results = []
        for region_name, data in region_data.items():
            beaches = data['beaches']
            cities = list(data['cities'])
            
            # Status counts
            safe_count = len([b for b in beaches if b['current_status'] == 'safe'])
            caution_count = len([b for b in beaches if b['current_status'] == 'caution'])
            avoid_count = len([b for b in beaches if b['current_status'] == 'avoid'])
            
            # Determine region status (worst among beaches)
            if avoid_count > 0:
                region_status = 'avoid'
            elif caution_count > 0:
                region_status = 'caution'
            elif safe_count > 0:
                region_status = 'safe'
            else:
                region_status = 'no_data'
            
            # Numeric aggregates
            peak_counts = [b['peak_count'] for b in beaches if b['peak_count'] > 0]
            confidences = [b['confidence_score'] for b in beaches if b['confidence_score'] > 0]
            
            region_results.append({
                'location_name': region_name,
                'location_type': 'region',
                'current_status': region_status,
                'peak_count': max(peak_counts) if peak_counts else 0,
                'avg_count': int(sum(peak_counts) / len(peak_counts)) if peak_counts else 0,
                'confidence_score': int(sum(confidences) / len(confidences)) if confidences else 0,
                'sample_date': max([b['sample_date'] for b in beaches if b['sample_date']]) if any(b['sample_date'] for b in beaches) else '',
                'beach_count': len(beaches),
                'city_count': len(cities),
                'beaches_safe': safe_count,
                'beaches_caution': caution_count,
                'beaches_avoid': avoid_count,
                'slug': self._generate_slug(region_name)
            })
        
        return region_results
    
    def _generate_slug(self, name):
        """Generate URL-friendly slug"""
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')
    
    def update_google_sheets(self, all_results):
        """Update beach_status sheet with all processed data"""
        try:
            worksheet = self.sheet.worksheet('beach_status')
            
            # Clear and add headers
            worksheet.clear()
            headers = [
                'location_name', 'location_type', 'date', 'current_status',
                'peak_count', 'confidence_score', 'sample_date', 'last_updated',
                'region', 'city', 'slug'
            ]
            worksheet.append_row(headers)
            time.sleep(1)
            
            # Add all results
            today = datetime.now().strftime('%Y-%m-%d')
            timestamp = datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S')
            
            for result in all_results:
                row = [
                    result['location_name'],
                    result['location_type'],
                    today,
                    result['current_status'],
                    result.get('peak_count', 0),
                    result.get('confidence_score', 0),
                    result.get('sample_date', ''),
                    timestamp,
                    result.get('region', ''),
                    result.get('city', ''),
                    result['slug']
                ]
                worksheet.append_row(row)
                time.sleep(1.5)  # Rate limiting
            
            print(f"✅ Updated Google Sheets with {len(all_results)} records")
            
        except Exception as e:
            print(f"❌ Failed to update Google Sheets: {e}")
            raise
    
    def run(self):
        """Main execution function"""
        print("🌊 Starting HAB Data Processing...")
        
        try:
            # 1. Fetch FWC data
            fwc_data = self.fetch_fwc_data()
            
            # 2. Process beaches
            print(f"\n📍 Processing {len(self.sample_mapping)} beaches...")
            beach_results = []
            for beach_name in self.sample_mapping.keys():
                result = self.calculate_beach_status(beach_name, fwc_data)
                beach_results.append(result)
                print(f"  {beach_name}: {result['current_status']} ({result['peak_count']} cells/L)")
            
            # 3. Aggregate cities
            print(f"\n🏙️ Aggregating city data...")
            city_results = self.aggregate_city_data(beach_results)
            for city in city_results:
                print(f"  {city['location_name']}: {city['current_status']} ({city['beach_count']} beaches)")
            
            # 4. Aggregate regions
            print(f"\n🌍 Aggregating region data...")
            region_results = self.aggregate_region_data(beach_results, city_results)
            for region in region_results:
                print(f"  {region['location_name']}: {region['current_status']} ({region['beach_count']} beaches, {region['city_count']} cities)")
            
            # 5. Update Google Sheets
            all_results = beach_results + city_results + region_results
            self.update_google_sheets(all_results)
            
            print(f"\n✅ Processing complete! Updated {len(all_results)} records.")
            print(f"   - {len(beach_results)} beaches")
            print(f"   - {len(city_results)} cities") 
            print(f"   - {len(region_results)} regions")
            
        except Exception as e:
            print(f"\n❌ Processing failed: {e}")
            raise

if __name__ == "__main__":
    # Check for required environment variables
    required_vars = ['GOOGLE_SERVICE_ACCOUNT', 'GOOGLE_SHEET_ID']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)
    
    # Run the fetcher
    fetcher = HABDataFetcher()
    fetcher.run()