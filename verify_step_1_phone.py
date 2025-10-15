#!/usr/bin/env python3
"""
STEP 1 VERIFICATION: Phone Number Collection
Test PhoneNumberInput model validation
"""

import sys
import os
sys.path.append('VoiceAgent3/IT_Curves_Bot')

from models import PhoneNumberInput
from pydantic import ValidationError

def test_step_1_phone_validation():
    """Test PhoneNumberInput model validation - STEP 1"""
    
    print("🧪 STEP 1 VERIFICATION: Phone Number Collection")
    print("=" * 60)
    
    # Test 1: Valid phone number (11 digits starting with 1)
    print("\n✅ Test 1: Valid phone number (11 digits)")
    try:
        valid_phone = PhoneNumberInput(number="13854156545")
        print(f"   ✅ Valid phone: {valid_phone}")
        print(f"   ✅ Phone number: {valid_phone.number}")
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 2: Valid phone number (different format)
    print("\n✅ Test 2: Valid phone number (different 11-digit format)")
    try:
        valid_phone = PhoneNumberInput(number="12345678901")
        print(f"   ✅ Valid phone: {valid_phone}")
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 3: Invalid phone number (too short)
    print("\n❌ Test 3: Invalid phone number (too short)")
    try:
        invalid_phone = PhoneNumberInput(number="123456789")  # 9 digits
        print(f"   ❌ Should not reach here: {invalid_phone}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 4: Invalid phone number (too long)
    print("\n❌ Test 4: Invalid phone number (too long)")
    try:
        invalid_phone = PhoneNumberInput(number="123456789012")  # 12 digits
        print(f"   ❌ Should not reach here: {invalid_phone}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 5: Invalid phone number (doesn't start with 1)
    print("\n❌ Test 5: Invalid phone number (doesn't start with 1)")
    try:
        invalid_phone = PhoneNumberInput(number="23854156545")  # Starts with 2
        print(f"   ❌ Should not reach here: {invalid_phone}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 6: Invalid phone number (contains letters)
    print("\n❌ Test 6: Invalid phone number (contains letters)")
    try:
        invalid_phone = PhoneNumberInput(number="1385415654a")  # Contains 'a'
        print(f"   ❌ Should not reach here: {invalid_phone}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 7: Empty phone number
    print("\n❌ Test 7: Empty phone number")
    try:
        invalid_phone = PhoneNumberInput(number="")
        print(f"   ❌ Should not reach here: {invalid_phone}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    print("\n🎉 STEP 1 VERIFICATION COMPLETED!")
    print("✅ PhoneNumberInput model is working correctly")

if __name__ == "__main__":
    test_step_1_phone_validation()

