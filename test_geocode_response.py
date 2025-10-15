#!/usr/bin/env python3
"""
Test script for GeocodeResponse Pydantic model
"""

import sys
import os
sys.path.append('VoiceAgent3/IT_Curves_Bot')

from models import GeocodeResponse
from pydantic import ValidationError

def test_geocode_response():
    """Test GeocodeResponse model validation"""
    
    print("🧪 Testing GeocodeResponse Model")
    print("=" * 50)
    
    # Test 1: Valid geocode response
    print("\n✅ Test 1: Valid geocode response")
    try:
        valid_response = GeocodeResponse(
            lat="39.1438",
            lng="-77.2014",
            formatted_address="123 Main St, Gaithersburg, MD 20878, USA",
            city="Gaithersburg",
            state="MD",
            zip_code="20878"
        )
        print(f"   ✅ Valid response: {valid_response}")
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 2: Valid response without zip code
    print("\n✅ Test 2: Valid response without zip code")
    try:
        valid_response = GeocodeResponse(
            lat="39.1438",
            lng="-77.2014",
            formatted_address="123 Main St, Gaithersburg, MD, USA",
            city="Gaithersburg",
            state="MD"
        )
        print(f"   ✅ Valid response: {valid_response}")
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 3: Invalid latitude (out of range)
    print("\n❌ Test 3: Invalid latitude (out of range)")
    try:
        invalid_response = GeocodeResponse(
            lat="200.0",  # Invalid latitude
            lng="-77.2014",
            formatted_address="123 Main St, Gaithersburg, MD, USA",
            city="Gaithersburg",
            state="MD"
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 4: Invalid latitude format
    print("\n❌ Test 4: Invalid latitude format")
    try:
        invalid_response = GeocodeResponse(
            lat="invalid",  # Invalid format
            lng="-77.2014",
            formatted_address="123 Main St, Gaithersburg, MD, USA",
            city="Gaithersburg",
            state="MD"
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 5: Invalid state code (too long)
    print("\n❌ Test 5: Invalid state code (too long)")
    try:
        invalid_response = GeocodeResponse(
            lat="39.1438",
            lng="-77.2014",
            formatted_address="123 Main St, Gaithersburg, MD, USA",
            city="Gaithersburg",
            state="Maryland"  # Should be 2 characters
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 6: Empty formatted address
    print("\n❌ Test 6: Empty formatted address")
    try:
        invalid_response = GeocodeResponse(
            lat="39.1438",
            lng="-77.2014",
            formatted_address="",  # Empty address
            city="Gaithersburg",
            state="MD"
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    print("\n🎉 GeocodeResponse tests completed!")

if __name__ == "__main__":
    test_geocode_response()

