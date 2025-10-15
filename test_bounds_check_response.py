#!/usr/bin/env python3
"""
Test script for BoundsCheckResponse Pydantic model
"""

import sys
import os
sys.path.append('VoiceAgent3/IT_Curves_Bot')

from models import BoundsCheckResponse
from pydantic import ValidationError

def test_bounds_check_response():
    """Test BoundsCheckResponse model validation"""
    
    print("🧪 Testing BoundsCheckResponse Model")
    print("=" * 50)
    
    # Test 1: Valid bounds check response (in bounds)
    print("\n✅ Test 1: Valid bounds check response (in bounds)")
    try:
        valid_response = BoundsCheckResponse(
            in_bounds=True,
            message="Location is within service area",
            affiliate_data={"x1": "39.0", "y1": "-77.0", "x2": "40.0", "y2": "-76.0"}
        )
        print(f"   ✅ Valid response: {valid_response}")
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 2: Valid bounds check response (out of bounds)
    print("\n✅ Test 2: Valid bounds check response (out of bounds)")
    try:
        valid_response = BoundsCheckResponse(
            in_bounds=False,
            message="Location is outside service area"
        )
        print(f"   ✅ Valid response: {valid_response}")
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 3: Minimal valid response
    print("\n✅ Test 3: Minimal valid response")
    try:
        minimal_response = BoundsCheckResponse(
            in_bounds=True
        )
        print(f"   ✅ Minimal response: {minimal_response}")
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 4: Invalid response (missing required field)
    print("\n❌ Test 4: Invalid response (missing in_bounds)")
    try:
        invalid_response = BoundsCheckResponse(
            message="This should fail"
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 5: Invalid response (wrong type for in_bounds)
    print("\n❌ Test 5: Invalid response (wrong type for in_bounds)")
    try:
        invalid_response = BoundsCheckResponse(
            in_bounds="true"  # Should be bool, not string
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    print("\n🎉 BoundsCheckResponse tests completed!")

if __name__ == "__main__":
    test_bounds_check_response()

