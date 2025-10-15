"""
Integration Tests for LLM Function Tools with Two-Tier Validation

This module tests the integration between LLM function tools and the two-tier validation system.
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock

# Add the backend path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../VoiceAgent3/IT_Curves_Bot'))

from models import MainTripPayload, ReturnTripPayload
from helper_functions import Assistant


class TestLLMIntegration:
    """Test LLM function tool integration with two-tier validation"""
    
    @pytest.fixture
    def mock_assistant(self):
        """Create a mock assistant instance"""
        assistant = Assistant()
        assistant.client_id = "123"
        return assistant
    
    @pytest.mark.asyncio
    async def test_collect_main_trip_payload_valid_data(self, mock_assistant):
        """Test collect_main_trip_payload with valid data"""
        valid_payload = MainTripPayload(
            pickup_street_address="123 Main St",
            dropoff_street_address="456 Oak Ave",
            pickup_city="Baltimore",
            dropoff_city="Annapolis",
            pickup_state="MD",
            dropoff_state="MD",
            extra_details="",
            client_id="123",
            funding_source_id="456",
            rider_name="John Doe",
            payment_type_id="789",
            copay_funding_source_id="-1",
            copay_payment_type_id="-1",
            booking_time="2024-01-15 14:30",
            pickup_lat="39.2904",
            pickup_lng="-76.6122",
            dropoff_lat="38.9784",
            dropoff_lng="-76.4922",
            rider_id="101",
            number_of_wheel_chairs="0",
            number_of_passengers="1",
            is_schedule="1",
            pickup_city_zip_code="21201",
            dropoff_city_zip_code="21401",
            rider_home_address="789 Pine St",
            rider_home_city="Baltimore",
            rider_home_state="MD",
            home_phone="+13015551234",
            office_phone="",
            total_passengers=1,
            total_wheelchairs=0,
            is_will_call=False,
            will_call_day="",
            pickup_remarks="",
            pickup_phone_number="",
            dropoff_remarks="",
            dropoff_phone_number=""
        )
        
        # Mock the NEMT validation to return success
        with pytest.MonkeyPatch().context() as m:
            m.setattr("helper_functions.try_validate", lambda x: (True, Mock(), None))
            
            result = await mock_assistant.collect_main_trip_payload(valid_payload)
            
            # Should not contain validation error messages
            assert "Format validation failed" not in result
            assert "Business validation failed" not in result
            assert "Validation failed" not in result
    
    @pytest.mark.asyncio
    async def test_collect_main_trip_payload_invalid_format(self, mock_assistant):
        """Test collect_main_trip_payload with invalid format data"""
        # This should fail at Tier 1 (Pydantic model validation)
        with pytest.raises(Exception):  # ValidationError from Pydantic
            invalid_payload = MainTripPayload(
                pickup_street_address="123 Main St",
                dropoff_street_address="456 Oak Ave",
                pickup_city="Baltimore",
                dropoff_city="Annapolis",
                pickup_state="MD",
                dropoff_state="MD",
                extra_details="",
                client_id="123",
                funding_source_id="456",
                rider_name="John123",  # Invalid: contains numbers
                payment_type_id="789",
                copay_funding_source_id="-1",
                copay_payment_type_id="-1",
                booking_time="2024-01-15 14:30",
                pickup_lat="39.2904",
                pickup_lng="-76.6122",
                dropoff_lat="38.9784",
                dropoff_lng="-76.4922",
                rider_id="101",
                number_of_wheel_chairs="0",
                number_of_passengers="1",
                is_schedule="1",
                pickup_city_zip_code="21201",
                dropoff_city_zip_code="21401",
                rider_home_address="789 Pine St",
                rider_home_city="Baltimore",
                rider_home_state="MD",
                home_phone="301-555-1234",  # Invalid: not E.164
                office_phone="",
                total_passengers=1,
                total_wheelchairs=0,
                is_will_call=False,
                will_call_day="",
                pickup_remarks="",
                pickup_phone_number="",
                dropoff_remarks="",
                dropoff_phone_number=""
            )
    
    @pytest.mark.asyncio
    async def test_collect_main_trip_payload_tier2_failure(self, mock_assistant):
        """Test collect_main_trip_payload where Tier 2 validation fails"""
        valid_format_payload = MainTripPayload(
            pickup_street_address="123 Main St",
            dropoff_street_address="456 Oak Ave",
            pickup_city="Baltimore",
            dropoff_city="Annapolis",
            pickup_state="MD",
            dropoff_state="MD",
            extra_details="",
            client_id="123",
            funding_source_id="456",
            rider_name="John Doe",
            payment_type_id="789",
            copay_funding_source_id="-1",
            copay_payment_type_id="-1",
            booking_time="2024-01-15 14:30",
            pickup_lat="39.2904",
            pickup_lng="-76.6122",
            dropoff_lat="38.9784",
            dropoff_lng="-76.4922",
            rider_id="101",
            number_of_wheel_chairs="0",
            number_of_passengers="1",
            is_schedule="1",
            pickup_city_zip_code="21201",
            dropoff_city_zip_code="21401",
            rider_home_address="789 Pine St",
            rider_home_city="Baltimore",
            rider_home_state="MD",
            home_phone="+13015551234",
            office_phone="",
            total_passengers=1,
            total_wheelchairs=0,
            is_will_call=False,
            will_call_day="",
            pickup_remarks="",
            pickup_phone_number="",
            dropoff_remarks="",
            dropoff_phone_number=""
        )
        
        # Mock NEMT validation to return failure
        mock_error_details = {
            "details": [
                {"msg": "Insurance authorization required", "loc": ["insuranceInfo", "AuthID"]},
                {"msg": "Invalid service code", "loc": ["insuranceInfo", "ServiceCodeID"]}
            ]
        }
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr("helper_functions.try_validate", lambda x: (False, None, mock_error_details))
            
            result = await mock_assistant.collect_main_trip_payload(valid_format_payload)
            
            # Should contain business validation error
            assert "Business validation failed" in result
            assert "Insurance authorization required" in result
            assert "Invalid service code" in result
    
    @pytest.mark.asyncio
    async def test_collect_return_trip_payload_valid_data(self, mock_assistant):
        """Test collect_return_trip_payload with valid data"""
        valid_payload = ReturnTripPayload(
            pickup_street_address="456 Oak Ave",
            dropoff_street_address="123 Main St",
            pickup_city="Annapolis",
            dropoff_city="Baltimore",
            pickup_state="MD",
            dropoff_state="MD",
            extra_details="",
            phone_number="+13015551234",
            client_id="123",
            funding_source_id="456",
            rider_name="John Doe",
            payment_type_id="789",
            copay_funding_source_id="-1",
            copay_payment_type_id="-1",
            booking_time="2024-01-15 16:30",
            pickup_lat="38.9784",
            pickup_lng="-76.4922",
            dropoff_lat="39.2904",
            dropoff_lng="-76.6122",
            rider_id="101",
            number_of_wheel_chairs="0",
            number_of_passengers="1",
            family_id="0",
            is_schedule="1",
            pickup_city_zip_code="21401",
            dropoff_city_zip_code="21201",
            rider_home_address="789 Pine St",
            rider_home_city="Baltimore",
            rider_home_state="MD",
            home_phone="+13015551234",
            office_phone="",
            total_passengers=1,
            total_wheelchairs=0,
            is_will_call=False,
            will_call_day="",
            pickup_remarks="",
            pickup_phone_number="",
            dropoff_remarks="",
            dropoff_phone_number=""
        )
        
        # Mock the NEMT validation to return success
        with pytest.MonkeyPatch().context() as m:
            m.setattr("helper_functions.try_validate", lambda x: (True, Mock(), None))
            
            result = await mock_assistant.collect_return_trip_payload(valid_payload)
            
            # Should not contain validation error messages
            assert "Format validation failed" not in result
            assert "Business validation failed" not in result
            assert "Validation failed" not in result
    
    def test_model_field_requirements(self):
        """Test that models have proper field requirements and descriptions"""
        # Test MainTripPayload field requirements
        main_fields = MainTripPayload.model_fields
        
        # Check that required fields are properly defined
        assert "rider_name" in main_fields
        assert "pickup_street_address" in main_fields
        assert "dropoff_street_address" in main_fields
        assert "home_phone" in main_fields
        
        # Check that descriptions are present
        assert main_fields["rider_name"].description is not None
        assert main_fields["pickup_street_address"].description is not None
        
        # Test ReturnTripPayload field requirements
        return_fields = ReturnTripPayload.model_fields
        
        assert "rider_name" in return_fields
        assert "phone_number" in return_fields
        assert "pickup_street_address" in return_fields
        
        assert return_fields["rider_name"].description is not None
        assert return_fields["phone_number"].description is not None
    
    def test_model_config(self):
        """Test that models have proper configuration"""
        # Test MainTripPayload config
        assert MainTripPayload.model_config.get("extra") == "forbid"
        assert MainTripPayload.model_config.get("str_strip_whitespace") is True
        assert MainTripPayload.model_config.get("validate_assignment") is True
        
        # Test ReturnTripPayload config
        assert ReturnTripPayload.model_config.get("extra") == "forbid"
        assert ReturnTripPayload.model_config.get("str_strip_whitespace") is True
        assert ReturnTripPayload.model_config.get("validate_assignment") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

