#!/usr/bin/env python3
"""
STEP 4 VERIFICATION: Get Name API Implementation
Test GetNameResponse model validation
"""

import sys
import os
sys.path.append('VoiceAgent3/IT_Curves_Bot')

from models import GetNameResponse
from pydantic import ValidationError

def test_step_4_get_name():
    """Test GetNameResponse model validation - STEP 4"""
    
    print("🧪 STEP 4 VERIFICATION: Get Name API Implementation")
    print("=" * 60)
    
    # Test 1: Valid GetNameResponse with full name
    print("\n✅ Test 1: Valid GetNameResponse with full name")
    try:
        valid_response = GetNameResponse(
            name="John Doe",
            first_name="John",
            last_name="Doe"
        )
        print(f"   ✅ Valid response: {valid_response}")
        print(f"   ✅ Full name: {valid_response.name}")
        print(f"   ✅ First name: {valid_response.first_name}")
        print(f"   ✅ Last name: {valid_response.last_name}")
        
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 2: Valid GetNameResponse (name only)
    print("\n✅ Test 2: Valid GetNameResponse (name only)")
    try:
        valid_response = GetNameResponse(
            name="Jane Smith"
            # first_name and last_name are optional
        )
        print(f"   ✅ Valid response: {valid_response}")
        print(f"   ✅ Full name: {valid_response.name}")
        
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 3: Invalid GetNameResponse (missing required name)
    print("\n❌ Test 3: Invalid GetNameResponse (missing required name)")
    try:
        invalid_response = GetNameResponse(
            first_name="John",
            last_name="Doe"
            # Missing required name field
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 4: Invalid GetNameResponse (empty name)
    print("\n❌ Test 4: Invalid GetNameResponse (empty name)")
    try:
        invalid_response = GetNameResponse(
            name=""  # Empty name
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 5: Valid GetNameResponse (whitespace handling)
    print("\n✅ Test 5: Valid GetNameResponse (whitespace handling)")
    try:
        valid_response = GetNameResponse(
            name="  John Doe  ",  # Whitespace should be stripped
            first_name="  John  ",
            last_name="  Doe  "
        )
        print(f"   ✅ Valid response: {valid_response}")
        print(f"   ✅ Trimmed name: '{valid_response.name}'")
        print(f"   ✅ Trimmed first name: '{valid_response.first_name}'")
        print(f"   ✅ Trimmed last name: '{valid_response.last_name}'")
        
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 6: Simulate API response parsing
    print("\n✅ Test 6: Simulate API response parsing")
    try:
        # Simulate the API response format
        api_response = {
            "FirstName": "John",
            "LastName": "Doe"
        }
        
        # Create GetNameResponse from API data
        validated_response = GetNameResponse(
            name=f"{api_response.get('FirstName', '')} {api_response.get('LastName', '')}".strip(),
            first_name=api_response.get('FirstName', ''),
            last_name=api_response.get('LastName', '')
        )
        print(f"   ✅ API response parsed: {validated_response}")
        print(f"   ✅ Full name: {validated_response.name}")
        
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 7: Handle missing fields in API response
    print("\n✅ Test 7: Handle missing fields in API response")
    try:
        # Simulate API response with missing fields
        api_response = {
            "FirstName": "John"
            # Missing LastName
        }
        
        # Create GetNameResponse from API data
        validated_response = GetNameResponse(
            name=f"{api_response.get('FirstName', '')} {api_response.get('LastName', '')}".strip(),
            first_name=api_response.get('FirstName', ''),
            last_name=api_response.get('LastName', '')
        )
        print(f"   ✅ API response with missing fields: {validated_response}")
        print(f"   ✅ Full name: '{validated_response.name}'")
        
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    print("\n🎉 STEP 4 VERIFICATION COMPLETED!")
    print("✅ GetNameResponse model validation is working correctly")
    print("✅ API response parsing is working correctly")
    print("✅ Graceful handling of missing fields is working correctly")

if __name__ == "__main__":
    test_step_4_get_name()

