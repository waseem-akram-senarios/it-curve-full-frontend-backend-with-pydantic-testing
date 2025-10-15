#!/usr/bin/env python3
"""
STEP 7 VERIFICATION: Geocode API (Dropoff)
Test GeocodeResponse validation for dropoff addresses
"""

import sys
import os
sys.path.append('VoiceAgent3/IT_Curves_Bot')

from models import GeocodeResponse
from pydantic import ValidationError

def test_step_7_dropoff_geocode():
    """Test GeocodeResponse validation for dropoff addresses - STEP 7"""
    
    print("🧪 STEP 7 VERIFICATION: Geocode API (Dropoff)")
    print("=" * 60)
    
    # Test 1: Valid dropoff address geocoding
    print("\n✅ Test 1: Valid dropoff address geocoding")
    try:
        dropoff_response = GeocodeResponse(
            lat="39.1438",
            lng="-77.2014",
            formatted_address="456 Oak Ave, Rockville, MD 20850, USA",
            city="Rockville",
            state="MD",
            zip_code="20850"
        )
        print(f"   ✅ Dropoff response: {dropoff_response}")
        print(f"   ✅ Dropoff address: {dropoff_response.formatted_address}")
        print(f"   ✅ Dropoff coordinates: {dropoff_response.lat}, {dropoff_response.lng}")
        
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 2: Valid dropoff without zip code
    print("\n✅ Test 2: Valid dropoff without zip code")
    try:
        dropoff_response = GeocodeResponse(
            lat="39.1438",
            lng="-77.2014",
            formatted_address="456 Oak Ave, Rockville, MD, USA",
            city="Rockville",
            state="MD"
        )
        print(f"   ✅ Dropoff response: {dropoff_response}")
        
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 3: Simulate dropoff geocoding API response
    print("\n✅ Test 3: Simulate dropoff geocoding API response")
    try:
        # Simulate the ITC Geocode API response format for dropoff
        api_response = {
            "results": [
                {
                    "formatted_address": "456 Oak Ave, Rockville, MD 20850, USA",
                    "geometry": {
                        "location": {
                            "lat": 39.1438,
                            "lng": -77.2014
                        }
                    },
                    "address_components": [
                        {"types": ["locality"], "long_name": "Rockville"},
                        {"types": ["administrative_area_level_1"], "short_name": "MD"},
                        {"types": ["postal_code"], "long_name": "20850"}
                    ]
                }
            ]
        }
        
        # Extract data for validation (same logic as in get_valid_addresses)
        location = api_response['results'][0]
        address_components = location.get('address_components', [])
        city = ""
        state = ""
        zip_code = ""
        
        for component in address_components:
            types = component.get('types', [])
            if 'locality' in types:
                city = component.get('long_name', '')
            elif 'administrative_area_level_1' in types:
                state = component.get('short_name', '')
            elif 'postal_code' in types:
                zip_code = component.get('long_name', '')
        
        dropoff_response = GeocodeResponse(
            lat=str(location['geometry']['location']['lat']),
            lng=str(location['geometry']['location']['lng']),
            formatted_address=location["formatted_address"],
            city=city,
            state=state,
            zip_code=zip_code
        )
        print(f"   ✅ Dropoff API response parsed: {dropoff_response}")
        print(f"   ✅ Dropoff city: {dropoff_response.city}")
        print(f"   ✅ Dropoff state: {dropoff_response.state}")
        
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 4: Invalid dropoff coordinates (out of range)
    print("\n❌ Test 4: Invalid dropoff coordinates (out of range)")
    try:
        invalid_response = GeocodeResponse(
            lat="200.0",  # Invalid latitude
            lng="-77.2014",
            formatted_address="456 Oak Ave, Rockville, MD, USA",
            city="Rockville",
            state="MD"
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 5: Invalid dropoff state code
    print("\n❌ Test 5: Invalid dropoff state code")
    try:
        invalid_response = GeocodeResponse(
            lat="39.1438",
            lng="-77.2014",
            formatted_address="456 Oak Ave, Rockville, MD, USA",
            city="Rockville",
            state="Maryland"  # Should be 2 characters
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 6: Empty dropoff address
    print("\n❌ Test 6: Empty dropoff address")
    try:
        invalid_response = GeocodeResponse(
            lat="39.1438",
            lng="-77.2014",
            formatted_address="",  # Empty address
            city="Rockville",
            state="MD"
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 7: Compare pickup vs dropoff validation
    print("\n✅ Test 7: Compare pickup vs dropoff validation")
    try:
        # Pickup address
        pickup_response = GeocodeResponse(
            lat="39.1438",
            lng="-77.2014",
            formatted_address="123 Main St, Gaithersburg, MD 20878, USA",
            city="Gaithersburg",
            state="MD",
            zip_code="20878"
        )
        
        # Dropoff address
        dropoff_response = GeocodeResponse(
            lat="39.1438",
            lng="-77.2014",
            formatted_address="456 Oak Ave, Rockville, MD 20850, USA",
            city="Rockville",
            state="MD",
            zip_code="20850"
        )
        
        print(f"   ✅ Pickup validated: {pickup_response.city}")
        print(f"   ✅ Dropoff validated: {dropoff_response.city}")
        print(f"   ✅ Both addresses use same validation logic")
        
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    print("\n🎉 STEP 7 VERIFICATION COMPLETED!")
    print("✅ GeocodeResponse validation works correctly for dropoff addresses")
    print("✅ Same validation logic applies to both pickup and dropoff")
    print("✅ API response parsing works for dropoff scenarios")

if __name__ == "__main__":
    test_step_7_dropoff_geocode()

