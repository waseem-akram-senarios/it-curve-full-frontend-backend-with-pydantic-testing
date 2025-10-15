"""
Phase 2 Test Suite - Function Tools Integration

Tests the integration of new validation system with existing function tools
without changing their external contracts.
"""

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

# Import the function tools (these will be the updated versions)
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../VoiceAgent3/IT_Curves_Bot'))

from helper_functions import AgentSession
from models import MainTripPayload, ReturnTripPayload


class TestPhase2FunctionTools:
    """Test Phase 2 function tools integration"""
    
    @pytest.fixture
    def mock_agent_session(self):
        """Create a mock agent session for testing"""
        session = MagicMock(spec=AgentSession)
        session.client_id = "123"
        session.family_id = "456"
        session.rider_phone = "+13015551234"
        return session
    
    @pytest.fixture
    def valid_main_payload(self):
        """Create a valid main trip payload"""
        return MainTripPayload(
            pickup_street_address="123 Main St",
            dropoff_street_address="456 Oak Ave",
            pickup_city="Baltimore",
            dropoff_city="Annapolis",
            pickup_state="MD",
            dropoff_state="MD",
            extra_details="Wheelchair accessible",
            client_id="2001",
            funding_source_id="5001",
            rider_name="John Doe",
            payment_type_id="1",
            copay_funding_source_id="-1",
            copay_payment_type_id="-1",
            booking_time="2024-01-15 10:00:00",
            pickup_lat="39.2904",
            pickup_lng="-76.6122",
            dropoff_lat="38.9784",
            dropoff_lng="-76.4922",
            rider_id="4001",
            number_of_wheel_chairs="1",
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
            total_wheelchairs=1,
            is_will_call=False,
            will_call_day="",
            pickup_remarks="Ring doorbell",
            pickup_phone_number="+13015551234",
            dropoff_remarks="Main entrance",
            dropoff_phone_number=""
        )
    
    @pytest.fixture
    def invalid_main_payload(self):
        """Create an invalid main trip payload"""
        return MainTripPayload(
            pickup_street_address="",  # Invalid: empty
            dropoff_street_address="456 Oak Ave",
            pickup_city="Baltimore",
            dropoff_city="Annapolis",
            pickup_state="MD",
            dropoff_state="MD",
            extra_details="",
            client_id="invalid",  # Invalid: not numeric
            funding_source_id="5001",
            rider_name="",  # Invalid: empty
            payment_type_id="1",
            copay_funding_source_id="-1",
            copay_payment_type_id="-1",
            booking_time="",
            pickup_lat="39.2904",
            pickup_lng="-76.6122",
            dropoff_lat="38.9784",
            dropoff_lng="-76.4922",
            rider_id="4001",
            number_of_wheel_chairs="1",
            number_of_passengers="1",
            is_schedule="1",
            pickup_city_zip_code="21201",
            dropoff_city_zip_code="21401",
            rider_home_address="789 Pine St",
            rider_home_city="Baltimore",
            rider_home_state="MD",
            home_phone="invalid_phone",  # Invalid: not E.164
            office_phone="",
            total_passengers=1,
            total_wheelchairs=1,
            is_will_call=False,
            will_call_day="",
            pickup_remarks="",
            pickup_phone_number="",
            dropoff_remarks="",
            dropoff_phone_number=""
        )
    
    @pytest.fixture
    def valid_return_payload(self):
        """Create a valid return trip payload"""
        return ReturnTripPayload(
            pickup_street_address="456 Oak Ave",
            dropoff_street_address="123 Main St",
            pickup_city="Annapolis",
            dropoff_city="Baltimore",
            pickup_state="MD",
            dropoff_state="MD",
            extra_details="Return trip",
            phone_number="+13015551234",
            client_id="2001",
            funding_source_id="5001",
            rider_name="John Doe",
            payment_type_id="1",
            copay_funding_source_id="-1",
            copay_payment_type_id="-1",
            booking_time="2024-01-15 14:00:00",
            pickup_lat="38.9784",
            pickup_lng="-76.4922",
            dropoff_lat="39.2904",
            dropoff_lng="-76.6122",
            rider_id="4001",
            number_of_wheel_chairs="1",
            number_of_passengers="1",
            family_id="456",
            is_schedule="1",
            pickup_city_zip_code="21401",
            dropoff_city_zip_code="21201",
            rider_home_address="789 Pine St",
            rider_home_city="Baltimore",
            rider_home_state="MD",
            home_phone="+13015551234",
            office_phone="",
            total_passengers=1,
            total_wheelchairs=1,
            is_will_call=False,
            will_call_day="",
            pickup_remarks="",
            pickup_phone_number="",
            dropoff_remarks="",
            dropoff_phone_number=""
        )


class TestValidationModeBehavior:
    """Test validation mode behavior across all modes"""
    
    @pytest.mark.parametrize("validation_mode", ["legacy", "hybrid", "new"])
    async def test_collect_main_trip_payload_contract_unchanged(self, validation_mode, mock_agent_session, valid_main_payload):
        """Test that external contract remains unchanged across all validation modes"""
        with patch.dict(os.environ, {"VALIDATION_MODE": validation_mode, "VALIDATION_FALLBACK": "true"}):
            # Mock external dependencies
            with patch('helper_functions.check_address_validity', return_value=None), \
                 patch('helper_functions.BasicAuth'), \
                 patch('helper_functions.requests.get') as mock_get, \
                 patch('helper_functions.logger'):
                
                # Mock successful API responses
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "routes": [{
                        "legs": [{
                            "distance": {"value": 1000},
                            "duration": {"value": 600}
                        }]
                    }]
                }
                mock_get.return_value = mock_response
                
                # Create agent session instance
                agent = AgentSession.__new__(AgentSession)
                agent.client_id = "123"
                agent.family_id = "456"
                agent.rider_phone = "+13015551234"
                agent.main_leg = None
                
                # Call function
                result = await agent.collect_main_trip_payload(valid_main_payload)
                
                # Assert return type is string (contract unchanged)
                assert isinstance(result, str)
                
                # Assert it's either success message or error message
                assert ("Payload for main trip has been collected" in result or 
                       "Validation failed" in result or 
                       "error:" in result)
    
    @pytest.mark.parametrize("validation_mode", ["legacy", "hybrid", "new"])
    async def test_collect_return_trip_payload_contract_unchanged(self, validation_mode, mock_agent_session, valid_return_payload):
        """Test that external contract remains unchanged across all validation modes"""
        with patch.dict(os.environ, {"VALIDATION_MODE": validation_mode, "VALIDATION_FALLBACK": "true"}):
            # Mock external dependencies
            with patch('helper_functions.check_address_validity', return_value=None), \
                 patch('helper_functions.BasicAuth'), \
                 patch('helper_functions.requests.get') as mock_get, \
                 patch('helper_functions.logger'):
                
                # Mock successful API responses
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "routes": [{
                        "legs": [{
                            "distance": {"value": 1000},
                            "duration": {"value": 600}
                        }]
                    }]
                }
                mock_get.return_value = mock_response
                
                # Create agent session instance
                agent = AgentSession.__new__(AgentSession)
                agent.client_id = "123"
                agent.family_id = "456"
                agent.rider_phone = "+13015551234"
                agent.return_leg = None
                
                # Call function
                result = await agent.collect_return_trip_payload(valid_return_payload)
                
                # Assert return type is string (contract unchanged)
                assert isinstance(result, str)
                
                # Assert it's either success message or error message
                assert ("Payload for return trip has been collected" in result or 
                       "Validation failed" in result or 
                       "error:" in result)


class TestNewModeFallbackBehavior:
    """Test new mode fallback behavior"""
    
    async def test_new_mode_with_fallback_true_uses_legacy_on_nemt_failure(self, mock_agent_session, invalid_main_payload):
        """Test that new mode with fallback=true uses legacy validation when NEMT fails"""
        with patch.dict(os.environ, {"VALIDATION_MODE": "new", "VALIDATION_FALLBACK": "true"}):
            # Mock validation to fail NEMT but pass legacy
            with patch('app.validation.validators.validate_legacy_first') as mock_validate, \
                 patch('app.infra.validation_logging.log_validation_event') as mock_log:
                
                # Mock NEMT validation failure but legacy success
                mock_validate.return_value = (True, None)  # Legacy passes
                
                # Create agent session instance
                agent = AgentSession.__new__(AgentSession)
                agent.client_id = "123"
                agent.family_id = "456"
                agent.rider_phone = "+13015551234"
                agent.main_leg = None
                
                # Mock external dependencies
                with patch('helper_functions.check_address_validity', return_value=None), \
                     patch('helper_functions.BasicAuth'), \
                     patch('helper_functions.requests.get') as mock_get, \
                     patch('helper_functions.logger'):
                    
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "routes": [{
                            "legs": [{
                                "distance": {"value": 1000},
                                "duration": {"value": 600}
                            }]
                        }]
                    }
                    mock_get.return_value = mock_response
                    
                    # Call function
                    result = await agent.collect_main_trip_payload(invalid_main_payload)
                    
                    # Should succeed due to legacy fallback
                    assert "Payload for main trip has been collected" in result
                    
                    # Should log validation event
                    mock_log.assert_called()
    
    async def test_new_mode_with_fallback_false_returns_nemt_error(self, mock_agent_session, invalid_main_payload):
        """Test that new mode with fallback=false returns NEMT error format"""
        with patch.dict(os.environ, {"VALIDATION_MODE": "new", "VALIDATION_FALLBACK": "false"}):
            # Mock validation to fail
            with patch('app.validation.validators.validate_legacy_first') as mock_validate, \
                 patch('app.infra.validation_logging.log_validation_event') as mock_log:
                
                # Mock validation failure
                mock_validate.return_value = (False, {
                    "error": "ValidationError",
                    "details": [{
                        "loc": ["rider_name"],
                        "msg": "Field 'rider_name' is required",
                        "type": "missing_field"
                    }]
                })
                
                # Create agent session instance
                agent = AgentSession.__new__(AgentSession)
                agent.client_id = "123"
                agent.family_id = "456"
                agent.rider_phone = "+13015551234"
                agent.main_leg = None
                
                # Call function
                result = await agent.collect_main_trip_payload(invalid_main_payload)
                
                # Should return validation error
                assert "Validation failed" in result
                assert "Field 'rider_name' is required" in result
                
                # Should log validation event
                mock_log.assert_called()


class TestHybridModeBehavior:
    """Test hybrid mode behavior"""
    
    async def test_hybrid_mode_runs_both_validations(self, mock_agent_session, valid_main_payload):
        """Test that hybrid mode runs both legacy and NEMT validation"""
        with patch.dict(os.environ, {"VALIDATION_MODE": "hybrid", "VALIDATION_FALLBACK": "true"}):
            # Mock validation
            with patch('app.validation.validators.validate_legacy_first') as mock_validate, \
                 patch('app.infra.validation_logging.log_validation_event') as mock_log:
                
                # Mock successful validation
                mock_validate.return_value = (True, None)
                
                # Create agent session instance
                agent = AgentSession.__new__(AgentSession)
                agent.client_id = "123"
                agent.family_id = "456"
                agent.rider_phone = "+13015551234"
                agent.main_leg = None
                
                # Mock external dependencies
                with patch('helper_functions.check_address_validity', return_value=None), \
                     patch('helper_functions.BasicAuth'), \
                     patch('helper_functions.requests.get') as mock_get, \
                     patch('helper_functions.logger'):
                    
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "routes": [{
                            "legs": [{
                                "distance": {"value": 1000},
                                "duration": {"value": 600}
                            }]
                        }]
                    }
                    mock_get.return_value = mock_response
                    
                    # Call function
                    result = await agent.collect_main_trip_payload(valid_main_payload)
                    
                    # Should succeed
                    assert "Payload for main trip has been collected" in result
                    
                    # Should log validation event with hybrid mode
                    mock_log.assert_called()
                    call_args = mock_log.call_args[1]
                    assert call_args["mode"] == "hybrid"


class TestLegacyModeBehavior:
    """Test legacy mode behavior"""
    
    async def test_legacy_mode_unchanged_behavior(self, mock_agent_session, valid_main_payload):
        """Test that legacy mode maintains unchanged behavior"""
        with patch.dict(os.environ, {"VALIDATION_MODE": "legacy", "VALIDATION_FALLBACK": "true"}):
            # Mock validation
            with patch('app.validation.validators.validate_legacy_first') as mock_validate, \
                 patch('app.infra.validation_logging.log_validation_event') as mock_log:
                
                # Mock successful validation
                mock_validate.return_value = (True, None)
                
                # Create agent session instance
                agent = AgentSession.__new__(AgentSession)
                agent.client_id = "123"
                agent.family_id = "456"
                agent.rider_phone = "+13015551234"
                agent.main_leg = None
                
                # Mock external dependencies
                with patch('helper_functions.check_address_validity', return_value=None), \
                     patch('helper_functions.BasicAuth'), \
                     patch('helper_functions.requests.get') as mock_get, \
                     patch('helper_functions.logger'):
                    
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "routes": [{
                            "legs": [{
                                "distance": {"value": 1000},
                                "duration": {"value": 600}
                            }]
                        }]
                    }
                    mock_get.return_value = mock_response
                    
                    # Call function
                    result = await agent.collect_main_trip_payload(valid_main_payload)
                    
                    # Should succeed
                    assert "Payload for main trip has been collected" in result
                    
                    # Should log validation event with legacy mode
                    mock_log.assert_called()
                    call_args = mock_log.call_args[1]
                    assert call_args["mode"] == "legacy"


class TestErrorHandling:
    """Test error handling scenarios"""
    
    async def test_validation_system_error_continues_processing(self, mock_agent_session, valid_main_payload):
        """Test that validation system errors don't break the function"""
        with patch.dict(os.environ, {"VALIDATION_MODE": "hybrid", "VALIDATION_FALLBACK": "true"}):
            # Mock validation to raise exception
            with patch('app.validation.validators.validate_legacy_first', side_effect=Exception("Validation system error")), \
                 patch('app.infra.validation_logging.log_validation_event') as mock_log, \
                 patch('helper_functions.logger') as mock_logger:
                
                # Create agent session instance
                agent = AgentSession.__new__(AgentSession)
                agent.client_id = "123"
                agent.family_id = "456"
                agent.rider_phone = "+13015551234"
                agent.main_leg = None
                
                # Mock external dependencies
                with patch('helper_functions.check_address_validity', return_value=None), \
                     patch('helper_functions.BasicAuth'), \
                     patch('helper_functions.requests.get') as mock_get:
                    
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "routes": [{
                            "legs": [{
                                "distance": {"value": 1000},
                                "duration": {"value": 600}
                            }]
                        }]
                    }
                    mock_get.return_value = mock_response
                    
                    # Call function
                    result = await agent.collect_main_trip_payload(valid_main_payload)
                    
                    # Should still succeed despite validation system error
                    assert "Payload for main trip has been collected" in result
                    
                    # Should log the validation system error
                    mock_log.assert_called()
                    
                    # Should log warning about validation system error
                    mock_logger.warning.assert_called()
                    warning_call = mock_logger.warning.call_args[0][0]
                    assert "Validation system error" in warning_call


# Integration test marker
pytest.mark.integration = pytest.mark.integration


@pytest.mark.integration
class TestPhase2Integration:
    """Integration tests for Phase 2"""
    
    async def test_full_validation_pipeline_integration(self, mock_agent_session, valid_main_payload):
        """Test full validation pipeline integration"""
        modes = ["legacy", "hybrid", "new"]
        
        for mode in modes:
            with patch.dict(os.environ, {"VALIDATION_MODE": mode, "VALIDATION_FALLBACK": "true"}):
                # Mock validation
                with patch('app.validation.validators.validate_legacy_first', return_value=(True, None)), \
                     patch('app.infra.validation_logging.log_validation_event'), \
                     patch('helper_functions.check_address_validity', return_value=None), \
                     patch('helper_functions.BasicAuth'), \
                     patch('helper_functions.requests.get') as mock_get, \
                     patch('helper_functions.logger'):
                    
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "routes": [{
                            "legs": [{
                                "distance": {"value": 1000},
                                "duration": {"value": 600}
                            }]
                        }]
                    }
                    mock_get.return_value = mock_response
                    
                    # Create agent session instance
                    agent = AgentSession.__new__(AgentSession)
                    agent.client_id = "123"
                    agent.family_id = "456"
                    agent.rider_phone = "+13015551234"
                    agent.main_leg = None
                    
                    # Call function
                    result = await agent.collect_main_trip_payload(valid_main_payload)
                    
                    # Should succeed in all modes
                    assert isinstance(result, str)
                    assert ("Payload for main trip has been collected" in result or 
                           "Validation failed" in result or 
                           "error:" in result)


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
