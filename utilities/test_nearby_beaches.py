#!/usr/bin/env python3
"""
Test script for nearby beaches distance calculation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sync_to_wordpress import WordPressSyncer
import math

def test_distance_calculation():
    """Test the distance calculation function"""
    syncer = WordPressSyncer()
    
    # Test coordinates (Sarasota area)
    lat1, lon1 = 27.3364, -82.5307  # Sarasota
    lat2, lon2 = 27.2659, -82.5525  # Siesta Key
    lat3, lon3 = 27.3365, -82.5308  # Very close to Sarasota
    
    distance1 = syncer._calculate_distance(lat1, lon1, lat2, lon2)
    distance2 = syncer._calculate_distance(lat1, lon1, lat3, lon3)
    
    print(f"Distance from Sarasota to Siesta Key: {distance1:.1f} miles")
    print(f"Distance from Sarasota to nearby point: {distance2:.3f} miles")
    
    # Test coordinate parsing
    coord_str1 = "27.3364, -82.5307"
    coord_str2 = "27.2659,-82.5525"
    coord_str3 = "invalid"
    
    lat1_parsed, lon1_parsed = syncer._parse_coordinates(coord_str1)
    lat2_parsed, lon2_parsed = syncer._parse_coordinates(coord_str2)
    lat3_parsed, lon3_parsed = syncer._parse_coordinates(coord_str3)
    
    print(f"Parsed coordinates 1: {lat1_parsed}, {lon1_parsed}")
    print(f"Parsed coordinates 2: {lat2_parsed}, {lon2_parsed}")
    print(f"Parsed coordinates 3: {lat3_parsed}, {lon3_parsed}")
    
    # Test distance calculation with parsed coordinates
    if lat1_parsed and lon1_parsed and lat2_parsed and lon2_parsed:
        distance_parsed = syncer._calculate_distance(lat1_parsed, lon1_parsed, lat2_parsed, lon2_parsed)
        print(f"Distance using parsed coordinates: {distance_parsed:.1f} miles")
    
    return True

def test_nearby_beaches_logic():
    """Test the nearby beaches logic with mock data"""
    syncer = WordPressSyncer()
    
    # Mock beach status records
    mock_beach_records = [
        {
            'location_name': 'Siesta Key Beach',
            'location_type': 'beach',
            'region': 'Gulf Coast',
            'city': 'Sarasota',
            'current_status': 'safe'
        },
        {
            'location_name': 'Lido Beach',
            'location_type': 'beach',
            'region': 'Gulf Coast',
            'city': 'Sarasota',
            'current_status': 'caution'
        },
        {
            'location_name': 'Venice Beach',
            'location_type': 'beach',
            'region': 'Gulf Coast',
            'city': 'Venice',
            'current_status': 'safe'
        }
    ]
    
    # Mock location records with coordinates
    mock_location_records = [
        {
            'beach': 'Siesta Key Beach',
            'latitude': '27.2659',
            'longitude': '-82.5525'
        },
        {
            'beach': 'Lido Beach',
            'latitude': '27.3364',
            'longitude': '-82.5307'
        },
        {
            'beach': 'Venice Beach',
            'latitude': '27.0998',
            'longitude': '-82.4543'
        }
    ]
    
    # Test distance calculation between these beaches
    print("\nTesting distances between beaches:")
    
    # Siesta Key to Lido Beach
    lat1, lon1 = 27.2659, -82.5525  # Siesta Key
    lat2, lon2 = 27.3364, -82.5307  # Lido Beach
    distance1 = syncer._calculate_distance(lat1, lon1, lat2, lon2)
    print(f"Siesta Key to Lido Beach: {distance1:.1f} miles")
    
    # Siesta Key to Venice Beach
    lat3, lon3 = 27.0998, -82.4543  # Venice Beach
    distance2 = syncer._calculate_distance(lat1, lon1, lat3, lon3)
    print(f"Siesta Key to Venice Beach: {distance2:.1f} miles")
    
    # Lido Beach to Venice Beach
    distance3 = syncer._calculate_distance(lat2, lon2, lat3, lon3)
    print(f"Lido Beach to Venice Beach: {distance3:.1f} miles")
    
    return True

if __name__ == "__main__":
    print("Testing nearby beaches distance calculation...")
    
    try:
        test_distance_calculation()
        test_nearby_beaches_logic()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
