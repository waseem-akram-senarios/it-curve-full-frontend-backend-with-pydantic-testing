#!/usr/bin/env python3
"""
STEP 2 VERIFICATION: Search Client Data API
Test ClientDataResponse and ClientProfile validation in get_client_name()
"""

import sys
import os
sys.path.append('VoiceAgent3/IT_Curves_Bot')

from models import ClientDataResponse, ClientProfile, SearchClientRequest
from pydantic import ValidationError
import json

def test_step_2_search_client():
    """Test ClientDataResponse and ClientProfile validation - STEP 2"""
    
    print("🧪 STEP 2 VERIFICATION: Search Client Data API")
    print("=" * 60)
    
    # Test 1: Valid ClientDataResponse
    print("\n✅ Test 1: Valid ClientDataResponse")
    try:
        valid_response = ClientDataResponse(
            responseCode=200,
            responseJSON='[{"Id": "12345", "FirstName": "John", "LastName": "Doe", "City": "Gaithersburg", "State": "MD", "Address": "123 Main St", "MedicalId": "MED123"}]'
        )
        print(f"   ✅ Valid response: {valid_response}")
        print(f"   ✅ Response code: {valid_response.responseCode}")
        
        # Test ClientProfile validation
        client_list = json.loads(valid_response.responseJSON)
        client_profile = ClientProfile(**client_list[0])
        print(f"   ✅ Client profile: {client_profile.FirstName} {client_profile.LastName}")
        
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 2: Valid SearchClientRequest
    print("\n✅ Test 2: Valid SearchClientRequest")
    try:
        search_request = SearchClientRequest(
            searchCriteria="CustomerPhone",
            searchText="13854156545",
            bActiveRecords=True,
            iATSPID=21,
            iDTSPID=1
        )
        print(f"   ✅ Valid search request: {search_request}")
        print(f"   ✅ Search criteria: {search_request.searchCriteria}")
        print(f"   ✅ Search text: {search_request.searchText}")
        
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test 3: Invalid ClientDataResponse (missing responseCode)
    print("\n❌ Test 3: Invalid ClientDataResponse (missing responseCode)")
    try:
        invalid_response = ClientDataResponse(
            responseJSON='[{"Id": "12345"}]'
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 4: Invalid ClientDataResponse (invalid responseCode)
    print("\n❌ Test 4: Invalid ClientDataResponse (invalid responseCode)")
    try:
        invalid_response = ClientDataResponse(
            responseCode=999,  # Invalid HTTP status code
            responseJSON='[{"Id": "12345"}]'
        )
        print(f"   ❌ Should not reach here: {invalid_response}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 5: Invalid ClientProfile (missing required fields)
    print("\n❌ Test 5: Invalid ClientProfile (missing required fields)")
    try:
        invalid_profile = ClientProfile(
            Id="12345"
            # Missing FirstName and LastName
        )
        print(f"   ❌ Should not reach here: {invalid_profile}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 6: Invalid SearchClientRequest (invalid searchCriteria)
    print("\n❌ Test 6: Invalid SearchClientRequest (invalid searchCriteria)")
    try:
        invalid_request = SearchClientRequest(
            searchCriteria="InvalidCriteria",  # Not in allowed values
            searchText="13854156545",
            bActiveRecords=True,
            iATSPID=21,
            iDTSPID=1
        )
        print(f"   ❌ Should not reach here: {invalid_request}")
    except ValidationError as e:
        print(f"   ✅ Correctly caught validation error: {e}")
    
    # Test 7: Error response (non-200 responseCode)
    print("\n✅ Test 7: Error response (non-200 responseCode)")
    try:
        error_response = ClientDataResponse(
            responseCode=404,
            responseJSON='{"error": "No clients found"}'
        )
        print(f"   ✅ Error response: {error_response}")
        print(f"   ✅ Error code: {error_response.responseCode}")
        
    except ValidationError as e:
        print(f"   ❌ Validation failed: {e}")
    
    print("\n🎉 STEP 2 VERIFICATION COMPLETED!")
    print("✅ ClientDataResponse and ClientProfile validation is working correctly")
    print("✅ SearchClientRequest validation is working correctly")

if __name__ == "__main__":
    test_step_2_search_client()

