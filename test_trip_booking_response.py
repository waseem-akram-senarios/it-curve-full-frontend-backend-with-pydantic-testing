#!/usr/bin/env python3
"""
Test script for TripBookingResponse Pydantic model - CRITICAL API
"""

import sys
import os
sys.path.append('VoiceAgent3/IT_Curves_Bot')

from models import TripBookingResponse
from pydantic import ValidationError

def test_trip_booking_response():
    """Test TripBookingResponse model validation - THE MOST CRITICAL API"""
    
    print("🧪 Testing TripBookingResponse Model - CRITICAL BOOKING API")
    print("=" * 60)
    
    # Test 1: Valid successful booking response
    print("\n✅ Test 1: Valid successful booking response")
    try:
        success_response = TripBookingResponse(
            responseCode=200,
            iRefID="TRIP123456",
            responseMessage="Trip booked successfully",
            returnLegsList="TRIP123457",
            estimatedDistance=5.2,
            estimatedTime=15,
            estimatedCost=12.50
        )
        print(f"   ✅ Success response: {success_response}")
        print(f"   ✅ Trip ID: {success_response.iRefID}")
        print(f"   ✅ Estimated cost: ${success_response.estimatedCost}")
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 2: Valid error response
    print("\n✅ Test 2: Valid error response")
    try:
        error_response = TripBookingResponse(
            responseCode=400,
            responseMessage="Invalid pickup address"
        )
        print(f"   ✅ Error response: {error_response}")
        print(f"   ✅ Error code: {error_response.responseCode}")
        print(f"   ✅ Error message: {error_response.responseMessage}")
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 3: Minimal valid response
    print("\n✅ Test 3: Minimal valid response")
    try:
        minimal_response = TripBookingResponse(
            responseCode=200
        )
        print(f"   ✅ Minimal response: {minimal_response}")
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 4: Invalid response code (out of range)
    print("\n❌ Test 4: Invalid response code (out of range)")
    try:
        invalid_response = TripBookingResponse(
            responseCode=999,  # Invalid HTTP status code
            iRefID="TRIP123456"
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 5: Invalid response code (too low)
    print("\n❌ Test 5: Invalid response code (too low)")
    try:
        invalid_response = TripBookingResponse(
            responseCode=50,  # Too low
            iRefID="TRIP123456"
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 6: Invalid estimated cost (negative)
    print("\n❌ Test 6: Invalid estimated cost (negative)")
    try:
        invalid_response = TripBookingResponse(
            responseCode=200,
            iRefID="TRIP123456",
            estimatedCost=-5.0  # Negative cost
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 7: Invalid estimated time (negative)
    print("\n❌ Test 7: Invalid estimated time (negative)")
    try:
        invalid_response = TripBookingResponse(
            responseCode=200,
            iRefID="TRIP123456",
            estimatedTime=-10  # Negative time
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 8: Invalid estimated distance (negative)
    print("\n❌ Test 8: Invalid estimated distance (negative)")
    try:
        invalid_response = TripBookingResponse(
            responseCode=200,
            iRefID="TRIP123456",
            estimatedDistance=-2.5  # Negative distance
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 9: Missing required responseCode
    print("\n❌ Test 9: Missing required responseCode")
    try:
        invalid_response = TripBookingResponse(
            iRefID="TRIP123456"
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    print("\n🎉 TripBookingResponse tests completed!")
    print("⭐ This is the MOST CRITICAL API - booking validation is essential!")

if __name__ == "__main__":
    test_trip_booking_response()

