# ACF Field Update Summary

## Overview
Updated the `sync_to_wordpress.py` script to populate all the new ACF fields defined in the ACF Export JSON file. The script now supports comprehensive relationship fields, repeater fields, and additional data fields for beaches, cities, and regions.

## New ACF Fields Added

### Beach Post Type Fields

#### Core Fields (Already Supported)
- `location_name` - Beach name
- `current_status` - Red tide status (safe/caution/avoid/no_data)
- `status_color` - Color code for status
- `last_updated` - Timestamp of last update
- `url_slug` - SEO-friendly URL slug
- `region` - Geographic region
- `state` - State (FL)
- `featured_location` - Featured status flag

#### New Fields Added
- `city` - City where beach is located
- `coordinates` - Latitude, longitude coordinates
- `full_address` - Complete street address
- `zip_code` - ZIP code
- `peak_count` - Highest cell count from sampling
- `confidence_score` - Data confidence percentage
- `sample_date` - Date of most recent sample
- `parent_city_post` - Relationship to parent city post
- `parent_region_post` - Relationship to parent region post
- `sampling_sites` - Repeater field with HAB sampling site data
- `beach_description` - Auto-generated description
- `nearby_beaches` - Repeater field with nearby beach relationships
- `nearby_regions` - Repeater field with nearby region relationships

### City Post Type Fields

#### Core Fields (Already Supported)
- All core fields listed above

#### New Fields Added
- `peak_count` - Highest cell count across city beaches
- `avg_count` - Average cell count across city beaches
- `confidence_score` - Average confidence score
- `sample_date` - Latest sample date
- `beach_count` - Number of beaches in city
- `beaches_safe` - Count of safe beaches
- `beaches_caution` - Count of caution beaches
- `beaches_avoid` - Count of avoid beaches
- `child_beaches` - Relationship to child beach posts
- `parent_region` - Relationship to parent region post
- `peak_cell_count` - Alternative field name for peak count
- `average_cell_count` - Alternative field name for average count
- `average_confidence` - Alternative field name for confidence
- `latest_sample_data` - Alternative field name for sample date
- `total_beaches` - Alternative field name for beach count
- `city_description` - Auto-generated description
- `nearby_cities` - Repeater field with nearby city relationships
- `nearby_beaches` - Repeater field with nearby beach relationships

### Region Post Type Fields

#### Core Fields (Already Supported)
- All core fields listed above

#### New Fields Added
- `peak_count` - Highest cell count across region
- `avg_count` - Average cell count across region
- `confidence_score` - Average confidence score
- `sample_date` - Latest sample date
- `beach_count` - Number of beaches in region
- `beaches_safe` - Count of safe beaches
- `beaches_caution` - Count of caution beaches
- `beaches_avoid` - Count of avoid beaches
- `city_count` - Number of cities in region
- `total_beaches` - Alternative field name for beach count
- `total_cities` - Alternative field name for city count
- `child_beaches` - Relationship to child beach posts
- `child_cities` - Relationship to child city posts
- `region_description` - Auto-generated description
- `nearby_regions` - Repeater field with nearby region relationships

## New Helper Methods Added

### Relationship Methods
- `_find_parent_post_id()` - Find post ID for parent city/region
- `_find_child_post_ids()` - Find post IDs for child beaches/cities

### Data Generation Methods
- `_generate_beach_description()` - Generate beach descriptions
- `_generate_city_description()` - Generate city descriptions
- `_generate_region_description()` - Generate region descriptions

### Sampling Site Methods
- `_get_beach_sampling_sites()` - Get HAB sampling sites for a beach
- `_get_city_hab_sampling_sites()` - Get HAB sampling sites for a city (existing, enhanced)

### Nearby Location Methods
- `_get_nearby_beaches()` - Get nearby beaches for a beach
- `_get_nearby_beaches_for_city()` - Get nearby beaches for a city
- `_get_nearby_cities()` - Get nearby cities for a city
- `_get_nearby_regions()` - Get nearby regions for a region

## Repeater Field Structure

### Sampling Sites Repeater
```json
{
  "hab_id": "HABW250819-050",
  "sample_location": "Siesta Beach",
  "distance_miles": "0.5",
  "current_concentration": "2500",
  "sample_date": "2025-01-15"
}
```

### Nearby Beaches/Cities/Regions Repeater
```json
{
  "beach": 123,  // Post object ID
  "distance": 2.5,
  "current_status": "safe",
  "status_color": "#28a745",
  "description": "Nearby beach with safe conditions"
}
```

## Key Features

### 1. Relationship Management
- Automatically finds and links parent/child posts
- Uses post IDs for WordPress relationships
- Handles bidirectional relationships where configured

### 2. Auto-Generated Content
- Creates contextual descriptions based on status and data
- Generates appropriate meta descriptions for SEO
- Provides fallback content when data is missing

### 3. Comprehensive Data Mapping
- Maps all Google Sheets data to appropriate ACF fields
- Handles both numeric and text field types
- Provides alternative field names for compatibility

### 4. Error Handling
- Graceful handling of missing relationships
- Fallback to mock data in test mode
- Comprehensive logging for debugging

### 5. Performance Optimization
- Caches sheet data to minimize API calls
- Rate limiting for WordPress API calls
- Efficient data processing and mapping

## Testing Support

The script includes comprehensive test mode support:
- Mock data generation for all new fields
- Test mode limits for controlled testing
- WordPress-only testing mode
- Detailed logging and debugging output

## Usage

The updated script maintains backward compatibility while adding all new ACF field support. No changes to existing workflows are required.

### Environment Variables
All existing environment variables continue to work:
- `TEST_MODE` - Enable test mode
- `TEST_LIMIT` - Limit number of posts in test mode
- `WORDPRESS_TEST_ONLY` - Test WordPress only
- `USE_ACF_RELATIONSHIPS` - Enable/disable relationship fields

### Execution
```bash
python sync_to_wordpress.py
```

## Migration Notes

1. **Existing Posts**: Existing posts will be updated with new fields on next sync
2. **Relationship Fields**: May take multiple sync cycles to establish all relationships
3. **Performance**: Initial sync may be slower due to relationship lookups
4. **Data Quality**: Ensure Google Sheets data is complete for best results

## Future Enhancements

1. **Distance Calculations**: Implement real distance calculations for nearby locations
2. **Image Support**: Add support for featured images and galleries
3. **Advanced Filtering**: Add filtering options for relationship fields
4. **Bulk Operations**: Optimize for large-scale data processing
5. **Webhook Integration**: Add webhook support for real-time updates
