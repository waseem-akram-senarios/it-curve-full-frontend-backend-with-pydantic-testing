#!/usr/bin/env python3
"""
Test script for RiderVerificationResponse Pydantic model
"""

import sys
import os
sys.path.append('VoiceAgent3/IT_Curves_Bot')

from models import RiderVerificationResponse
from pydantic import ValidationError

def test_rider_verification_response():
    """Test RiderVerificationResponse model validation"""
    
    print("🧪 Testing RiderVerificationResponse Model")
    print("=" * 50)
    
    # Test 1: Valid response
    print("\n✅ Test 1: Valid verification response")
    try:
        valid_response = RiderVerificationResponse(
            VerificationSuccess=True,
            message="Rider verified successfully",
            rider_id="12345"
        )
        print(f"   ✅ Valid response: {valid_response}")
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 2: Minimal valid response
    print("\n✅ Test 2: Minimal valid response")
    try:
        minimal_response = RiderVerificationResponse(
            VerificationSuccess=False
        )
        print(f"   ✅ Minimal response: {minimal_response}")
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 3: Invalid response (missing required field)
    print("\n❌ Test 3: Invalid response (missing VerificationSuccess)")
    try:
        invalid_response = RiderVerificationResponse(
            message="This should fail"
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 4: Invalid response (wrong type)
    print("\n❌ Test 4: Invalid response (wrong type for VerificationSuccess)")
    try:
        invalid_response = RiderVerificationResponse(
            VerificationSuccess="invalid"  # Should be bool, not string
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    print("\n🎉 RiderVerificationResponse tests completed!")

if __name__ == "__main__":
    test_rider_verification_response()
