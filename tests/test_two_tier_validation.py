"""
Tests for Two-Tier Validation Implementation

This module tests the two-tier validation approach:
- Tier 1: Format validation in models.py (LLM interface)
- Tier 2: Business logic validation in NEMT schema
"""

import pytest
import sys
import os
from pydantic import ValidationError

# Add the backend path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../VoiceAgent3/IT_Curves_Bot'))

from models import MainTripPayload, ReturnTripPayload
from models_validators import (
    validate_name, validate_phone_number, validate_zip_code_format,
    validate_state_code, validate_datetime_string, validate_latitude,
    validate_longitude, validate_id_field, validate_count_field
)


class TestTier1Validation:
    """Test Tier 1 format validation in models.py"""
    
    def test_valid_main_trip_payload(self):
        """Test that valid data passes Tier 1 validation"""
        valid_data = {
            "pickup_street_address": "123 Main St",
            "dropoff_street_address": "456 Oak Ave", 
            "pickup_city": "Baltimore",
            "dropoff_city": "Annapolis",
            "pickup_state": "MD",
            "dropoff_state": "MD",
            "extra_details": "",
            "client_id": "123",
            "funding_source_id": "456",
            "rider_name": "John Doe",
            "payment_type_id": "789",
            "copay_funding_source_id": "-1",
            "copay_payment_type_id": "-1",
            "booking_time": "2024-01-15 14:30",
            "pickup_lat": "39.2904",
            "pickup_lng": "-76.6122",
            "dropoff_lat": "38.9784",
            "dropoff_lng": "-76.4922",
            "rider_id": "101",
            "number_of_wheel_chairs": "0",
            "number_of_passengers": "1",
            "is_schedule": "1",
            "pickup_city_zip_code": "21201",
            "dropoff_city_zip_code": "21401",
            "rider_home_address": "789 Pine St",
            "rider_home_city": "Baltimore",
            "rider_home_state": "MD",
            "home_phone": "+13015551234",
            "office_phone": "",
            "total_passengers": 1,
            "total_wheelchairs": 0,
            "is_will_call": False,
            "will_call_day": "",
            "pickup_remarks": "",
            "pickup_phone_number": "",
            "dropoff_remarks": "",
            "dropoff_phone_number": ""
        }
        
        # Should not raise ValidationError
        payload = MainTripPayload(**valid_data)
        assert payload.rider_name == "John Doe"
        assert payload.pickup_state == "MD"
        assert payload.home_phone == "+13015551234"
    
    def test_invalid_name_format(self):
        """Test that invalid name format fails Tier 1 validation"""
        invalid_data = {
            "pickup_street_address": "123 Main St",
            "dropoff_street_address": "456 Oak Ave",
            "pickup_city": "Baltimore", 
            "dropoff_city": "Annapolis",
            "pickup_state": "MD",
            "dropoff_state": "MD",
            "extra_details": "",
            "client_id": "123",
            "funding_source_id": "456",
            "rider_name": "John123",  # Invalid: contains numbers
            "payment_type_id": "789",
            "copay_funding_source_id": "-1",
            "copay_payment_type_id": "-1",
            "booking_time": "2024-01-15 14:30",
            "pickup_lat": "39.2904",
            "pickup_lng": "-76.6122",
            "dropoff_lat": "38.9784",
            "dropoff_lng": "-76.4922",
            "rider_id": "101",
            "number_of_wheel_chairs": "0",
            "number_of_passengers": "1",
            "is_schedule": "1",
            "pickup_city_zip_code": "21201",
            "dropoff_city_zip_code": "21401",
            "rider_home_address": "789 Pine St",
            "rider_home_city": "Baltimore",
            "rider_home_state": "MD",
            "home_phone": "+13015551234",
            "office_phone": "",
            "total_passengers": 1,
            "total_wheelchairs": 0,
            "is_will_call": False,
            "will_call_day": "",
            "pickup_remarks": "",
            "pickup_phone_number": "",
            "dropoff_remarks": "",
            "dropoff_phone_number": ""
        }
        
        with pytest.raises(ValidationError) as exc_info:
            MainTripPayload(**invalid_data)
        
        # Check that the error message mentions name validation
        error_messages = str(exc_info.value)
        assert "Name can only contain letters" in error_messages or "rider_name" in error_messages
    
    def test_invalid_phone_format(self):
        """Test that invalid phone format fails Tier 1 validation"""
        invalid_data = {
            "pickup_street_address": "123 Main St",
            "dropoff_street_address": "456 Oak Ave",
            "pickup_city": "Baltimore",
            "dropoff_city": "Annapolis", 
            "pickup_state": "MD",
            "dropoff_state": "MD",
            "extra_details": "",
            "client_id": "123",
            "funding_source_id": "456",
            "rider_name": "John Doe",
            "payment_type_id": "789",
            "copay_funding_source_id": "-1",
            "copay_payment_type_id": "-1",
            "booking_time": "2024-01-15 14:30",
            "pickup_lat": "39.2904",
            "pickup_lng": "-76.6122",
            "dropoff_lat": "38.9784",
            "dropoff_lng": "-76.4922",
            "rider_id": "101",
            "number_of_wheel_chairs": "0",
            "number_of_passengers": "1",
            "is_schedule": "1",
            "pickup_city_zip_code": "21201",
            "dropoff_city_zip_code": "21401",
            "rider_home_address": "789 Pine St",
            "rider_home_city": "Baltimore",
            "rider_home_state": "MD",
            "home_phone": "301-555-1234",  # Invalid: not E.164 format
            "office_phone": "",
            "total_passengers": 1,
            "total_wheelchairs": 0,
            "is_will_call": False,
            "will_call_day": "",
            "pickup_remarks": "",
            "pickup_phone_number": "",
            "dropoff_remarks": "",
            "dropoff_phone_number": ""
        }
        
        with pytest.raises(ValidationError) as exc_info:
            MainTripPayload(**invalid_data)
        
        error_messages = str(exc_info.value)
        assert "E.164" in error_messages or "home_phone" in error_messages
    
    def test_invalid_state_code(self):
        """Test that invalid state code fails Tier 1 validation"""
        invalid_data = {
            "pickup_street_address": "123 Main St",
            "dropoff_street_address": "456 Oak Ave",
            "pickup_city": "Baltimore",
            "dropoff_city": "Annapolis",
            "pickup_state": "XX",  # Invalid: not a valid US state
            "dropoff_state": "MD",
            "extra_details": "",
            "client_id": "123",
            "funding_source_id": "456",
            "rider_name": "John Doe",
            "payment_type_id": "789",
            "copay_funding_source_id": "-1",
            "copay_payment_type_id": "-1",
            "booking_time": "2024-01-15 14:30",
            "pickup_lat": "39.2904",
            "pickup_lng": "-76.6122",
            "dropoff_lat": "38.9784",
            "dropoff_lng": "-76.4922",
            "rider_id": "101",
            "number_of_wheel_chairs": "0",
            "number_of_passengers": "1",
            "is_schedule": "1",
            "pickup_city_zip_code": "21201",
            "dropoff_city_zip_code": "21401",
            "rider_home_address": "789 Pine St",
            "rider_home_city": "Baltimore",
            "rider_home_state": "MD",
            "home_phone": "+13015551234",
            "office_phone": "",
            "total_passengers": 1,
            "total_wheelchairs": 0,
            "is_will_call": False,
            "will_call_day": "",
            "pickup_remarks": "",
            "pickup_phone_number": "",
            "dropoff_remarks": "",
            "dropoff_phone_number": ""
        }
        
        with pytest.raises(ValidationError) as exc_info:
            MainTripPayload(**invalid_data)
        
        error_messages = str(exc_info.value)
        assert "Invalid state code" in error_messages or "pickup_state" in error_messages
    
    def test_invalid_zip_code(self):
        """Test that invalid ZIP code fails Tier 1 validation"""
        invalid_data = {
            "pickup_street_address": "123 Main St",
            "dropoff_street_address": "456 Oak Ave",
            "pickup_city": "Baltimore",
            "dropoff_city": "Annapolis",
            "pickup_state": "MD",
            "dropoff_state": "MD",
            "extra_details": "",
            "client_id": "123",
            "funding_source_id": "456",
            "rider_name": "John Doe",
            "payment_type_id": "789",
            "copay_funding_source_id": "-1",
            "copay_payment_type_id": "-1",
            "booking_time": "2024-01-15 14:30",
            "pickup_lat": "39.2904",
            "pickup_lng": "-76.6122",
            "dropoff_lat": "38.9784",
            "dropoff_lng": "-76.4922",
            "rider_id": "101",
            "number_of_wheel_chairs": "0",
            "number_of_passengers": "1",
            "is_schedule": "1",
            "pickup_city_zip_code": "12345-67890",  # Invalid: too long
            "dropoff_city_zip_code": "21401",
            "rider_home_address": "789 Pine St",
            "rider_home_city": "Baltimore",
            "rider_home_state": "MD",
            "home_phone": "+13015551234",
            "office_phone": "",
            "total_passengers": 1,
            "total_wheelchairs": 0,
            "is_will_call": False,
            "will_call_day": "",
            "pickup_remarks": "",
            "pickup_phone_number": "",
            "dropoff_remarks": "",
            "dropoff_phone_number": ""
        }
        
        with pytest.raises(ValidationError) as exc_info:
            MainTripPayload(**invalid_data)
        
        error_messages = str(exc_info.value)
        assert "ZIP" in error_messages or "pickup_city_zip_code" in error_messages
    
    def test_return_trip_payload_validation(self):
        """Test ReturnTripPayload with invalid phone number"""
        invalid_data = {
            "pickup_street_address": "123 Main St",
            "dropoff_street_address": "456 Oak Ave",
            "pickup_city": "Baltimore",
            "dropoff_city": "Annapolis",
            "pickup_state": "MD",
            "dropoff_state": "MD",
            "extra_details": "",
            "phone_number": "301-555-1234",  # Invalid: not E.164 format
            "client_id": "123",
            "funding_source_id": "456",
            "rider_name": "Jane Doe",
            "payment_type_id": "789",
            "copay_funding_source_id": "-1",
            "copay_payment_type_id": "-1",
            "booking_time": "2024-01-15 14:30",
            "pickup_lat": "39.2904",
            "pickup_lng": "-76.6122",
            "dropoff_lat": "38.9784",
            "dropoff_lng": "-76.4922",
            "rider_id": "101",
            "number_of_wheel_chairs": "0",
            "number_of_passengers": "1",
            "family_id": "0",
            "is_schedule": "1",
            "pickup_city_zip_code": "21201",
            "dropoff_city_zip_code": "21401",
            "rider_home_address": "789 Pine St",
            "rider_home_city": "Baltimore",
            "rider_home_state": "MD",
            "home_phone": "+13015551234",
            "office_phone": "",
            "total_passengers": 1,
            "total_wheelchairs": 0,
            "is_will_call": False,
            "will_call_day": "",
            "pickup_remarks": "",
            "pickup_phone_number": "",
            "dropoff_remarks": "",
            "dropoff_phone_number": ""
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ReturnTripPayload(**invalid_data)
        
        error_messages = str(exc_info.value)
        assert "E.164" in error_messages or "phone_number" in error_messages


class TestValidationUtilities:
    """Test individual validation utility functions"""
    
    def test_validate_name(self):
        """Test name validation utility"""
        # Valid names
        assert validate_name("John Doe") == "John Doe"
        assert validate_name("Mary Jane Smith") == "Mary Jane Smith"
        assert validate_name("O'Connor") == "O'Connor"
        assert validate_name("Dr. Smith") == "Dr. Smith"
        
        # Invalid names
        with pytest.raises(ValueError):
            validate_name("John123")
        
        with pytest.raises(ValueError):
            validate_name("")
        
        with pytest.raises(ValueError):
            validate_name("A")  # Too short
    
    def test_validate_phone_number(self):
        """Test phone validation utility"""
        # Valid phones
        assert validate_phone_number("+13015551234") == "+13015551234"
        assert validate_phone_number("+44123456789") == "+44123456789"
        
        # Invalid phones
        with pytest.raises(ValueError):
            validate_phone_number("301-555-1234")
        
        with pytest.raises(ValueError):
            validate_phone_number("")
        
        with pytest.raises(ValueError):
            validate_phone_number("123")
    
    def test_validate_state_code(self):
        """Test state code validation utility"""
        # Valid states
        assert validate_state_code("MD") == "MD"
        assert validate_state_code("ca") == "CA"  # Should convert to uppercase
        assert validate_state_code("NY") == "NY"
        
        # Invalid states
        with pytest.raises(ValueError):
            validate_state_code("XX")
        
        with pytest.raises(ValueError):
            validate_state_code("")
    
    def test_validate_zip_code_format(self):
        """Test ZIP code validation utility"""
        # Valid ZIP codes
        assert validate_zip_code_format("12345") == "12345"
        assert validate_zip_code_format("12345-6789") == "12345-6789"
        
        # Invalid ZIP codes
        with pytest.raises(ValueError):
            validate_zip_code_format("1234")
        
        with pytest.raises(ValueError):
            validate_zip_code_format("12345-67890")
        
        with pytest.raises(ValueError):
            validate_zip_code_format("")
    
    def test_validate_coordinates(self):
        """Test coordinate validation utility"""
        # Valid coordinates
        assert validate_latitude("39.2904") == "39.2904"
        assert validate_longitude("-76.6122") == "-76.6122"
        assert validate_latitude("0") == "0"
        assert validate_longitude("0") == "0"
        
        # Invalid coordinates
        with pytest.raises(ValueError):
            validate_latitude("91")  # Too high
        
        with pytest.raises(ValueError):
            validate_latitude("-91")  # Too low
        
        with pytest.raises(ValueError):
            validate_longitude("181")  # Too high
        
        with pytest.raises(ValueError):
            validate_longitude("-181")  # Too low
    
    def test_validate_id_field(self):
        """Test ID field validation utility"""
        # Valid IDs
        assert validate_id_field("123") == "123"
        assert validate_id_field("-1") == "-1"
        assert validate_id_field("0") == "0"
        
        # Invalid IDs
        with pytest.raises(ValueError):
            validate_id_field("abc")
        
        with pytest.raises(ValueError):
            validate_id_field("")


class TestTwoTierIntegration:
    """Test integration between Tier 1 and Tier 2 validation"""
    
    def test_tier1_passes_tier2_fails(self):
        """Test scenario where Tier 1 passes but Tier 2 fails"""
        # This would require the NEMT schema validation
        # For now, we'll test that Tier 1 validation works correctly
        valid_format_data = {
            "pickup_street_address": "123 Main St",
            "dropoff_street_address": "456 Oak Ave",
            "pickup_city": "Baltimore",
            "dropoff_city": "Annapolis",
            "pickup_state": "MD",
            "dropoff_state": "MD",
            "extra_details": "",
            "client_id": "123",
            "funding_source_id": "456",
            "rider_name": "John Doe",
            "payment_type_id": "789",
            "copay_funding_source_id": "-1",
            "copay_payment_type_id": "-1",
            "booking_time": "2024-01-15 14:30",
            "pickup_lat": "39.2904",
            "pickup_lng": "-76.6122",
            "dropoff_lat": "38.9784",
            "dropoff_lng": "-76.4922",
            "rider_id": "101",
            "number_of_wheel_chairs": "0",
            "number_of_passengers": "1",
            "is_schedule": "1",
            "pickup_city_zip_code": "21201",
            "dropoff_city_zip_code": "21401",
            "rider_home_address": "789 Pine St",
            "rider_home_city": "Baltimore",
            "rider_home_state": "MD",
            "home_phone": "+13015551234",
            "office_phone": "",
            "total_passengers": 1,
            "total_wheelchairs": 0,
            "is_will_call": False,
            "will_call_day": "",
            "pickup_remarks": "",
            "pickup_phone_number": "",
            "dropoff_remarks": "",
            "dropoff_phone_number": ""
        }
        
        # Tier 1 should pass
        payload = MainTripPayload(**valid_format_data)
        assert payload.rider_name == "John Doe"
        
        # Tier 2 validation would happen in helper_functions.py
        # and could fail for business logic reasons (e.g., insurance validation)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

