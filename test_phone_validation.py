#!/usr/bin/env python3
"""
Test script to verify phone number validation works correctly
"""

import sys
import os
sys.path.append('/home/senarios/VoiceAgent5withFeNew/VoiceAgent3/IT_Curves_Bot')

from models import PhoneNumberInput, MainTripPayload
from pydantic import ValidationError

def test_phone_validation():
    """Test phone number validation"""
    print("🧪 Testing Phone Number Validation")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        ("9876543210", "Valid 10-digit number"),
        ("987-654-3210", "Valid formatted number"),
        ("(987) 654-3210", "Valid with parentheses and spaces"),
        ("987654321", "Invalid 9-digit number"),
        ("98765432101", "Invalid 11-digit number"),
        ("abc1234567", "Invalid with letters"),
        ("", "Empty string"),
    ]
    
    for phone_input, description in test_cases:
        print(f"\n📱 Testing: {phone_input} ({description})")
        try:
            phone_validation = PhoneNumberInput(number=phone_input)
            print(f"✅ SUCCESS: {phone_validation.number}")
        except ValidationError as e:
            print(f"❌ FAILED: {e}")
        except Exception as e:
            print(f"💥 ERROR: {e}")

def test_main_trip_payload():
    """Test MainTripPayload with phone number"""
    print("\n🧪 Testing MainTripPayload with Phone Number")
    print("=" * 50)
    
    try:
        payload = MainTripPayload(
            pickup_street_address="123 Main St",
            dropoff_street_address="456 Oak Ave",
            pickup_city="Gaithersburg",
            dropoff_city="Rockville",
            pickup_state="MD",
            dropoff_state="MD",
            extra_details="",
            phone_number="9876543210",  # This should be formatted to 987-654-3210
            client_id="-1",
            funding_source_id="1",
            rider_name="Test User",
            payment_type_id="1",
            copay_funding_source_id="1",
            copay_payment_type_id="1",
            booking_time="2025-10-15 19:00",
            pickup_lat="39.1683",
            pickup_lng="-77.1652",
            dropoff_lat="39.2854",
            dropoff_lng="-77.2081",
            rider_id="-1",
            number_of_wheel_chairs="0",
            number_of_passengers="1",
            is_schedule="0",
            pickup_city_zip_code="20878",
            dropoff_city_zip_code="20850",
            rider_home_address="",
            rider_home_city="",
            rider_home_state="",
            home_phone="",
            office_phone="",
            total_passengers=1,
            total_wheelchairs=0,
            is_will_call=True,
            will_call_day="2025-10-15",
            pickup_remarks="",
            pickup_phone_number="",
            dropoff_remarks="",
            dropoff_phone_number=""
        )
        print(f"✅ MainTripPayload created successfully")
        print(f"📱 Phone number: {payload.phone_number}")
        
        # Test phone validation
        phone_validation = PhoneNumberInput(number=payload.phone_number)
        print(f"✅ Phone validation passed: {phone_validation.number}")
        
    except ValidationError as e:
        print(f"❌ MainTripPayload validation failed: {e}")
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    test_phone_validation()
    test_main_trip_payload()
    print("\n🎉 Phone number validation testing complete!")
