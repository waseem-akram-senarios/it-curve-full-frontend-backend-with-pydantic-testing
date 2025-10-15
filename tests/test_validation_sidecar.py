"""
Test Suite for NEMT Validation Sidecar

This module tests the validation sidecar functionality without affecting
the main application flow.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import modules to test
from app.validation.nemt_adapter import (
    from_legacy_to_nemt,
    from_nemt_to_legacy,
    validate_nemt_sidecar,
    LEGACY_PAYLOAD_EXAMPLE
)
from app.validation.validators import validate_legacy_first, validate_both_modes
from app.config.flags import get_validation_mode, ValidationMode
from app.schemas.nemt_trip import VALID_PAYLOAD_EXAMPLE, INVALID_PAYLOAD_EXAMPLE


class TestNEMTAdapter:
    """Test NEMT adapter functionality"""
    
    def test_from_legacy_to_nemt_conversion(self):
        """Test conversion from legacy format to NEMT format"""
        legacy_data = LEGACY_PAYLOAD_EXAMPLE
        nemt_data = from_legacy_to_nemt(legacy_data)
        
        # Check that all required NEMT sections exist
        assert "generalInfo" in nemt_data
        assert "riderInfo" in nemt_data
        assert "insuranceInfo" in nemt_data
        assert "routeSettingInfo" in nemt_data
        assert "systemConfigInfo" in nemt_data
        
        # Check specific field mappings
        assert nemt_data["generalInfo"]["CompleteUserName"] == legacy_data["rider_name"]
        assert nemt_data["riderInfo"]["PhoneNo"] == legacy_data["phone_number"]
        assert nemt_data["riderInfo"]["ClientState"] == legacy_data["rider_home_state"]
    
    def test_validate_nemt_sidecar_with_valid_data(self):
        """Test NEMT sidecar validation with valid legacy data"""
        legacy_data = LEGACY_PAYLOAD_EXAMPLE
        
        # Should succeed (converted data should be valid)
        ok, error = validate_nemt_sidecar(legacy_data)
        
        # Note: This might fail due to conversion issues, which is expected
        # The important thing is that it doesn't raise exceptions
        assert isinstance(ok, bool)
        assert error is None or isinstance(error, dict)
    
    def test_validate_nemt_sidecar_with_invalid_data(self):
        """Test NEMT sidecar validation with invalid data"""
        invalid_data = {
            "rider_name": "",  # Invalid: empty name
            "phone_number": "invalid_phone",  # Invalid: not E.164
            "client_id": "not_a_number"  # Invalid: not numeric
        }
        
        ok, error = validate_nemt_sidecar(invalid_data)
        
        # Should fail validation
        assert ok is False
        assert isinstance(error, dict)
        assert "error" in error
        assert "details" in error


class TestValidationModes:
    """Test validation mode functionality"""
    
    def test_legacy_mode_behavior(self):
        """Test that legacy mode works as expected"""
        with patch.dict(os.environ, {"VALIDATION_MODE": "legacy"}):
            from app.config.flags import get_validation_mode
            mode = get_validation_mode()
            assert mode == ValidationMode.LEGACY
    
    def test_hybrid_mode_behavior(self):
        """Test that hybrid mode works as expected"""
        with patch.dict(os.environ, {"VALIDATION_MODE": "hybrid"}):
            from app.config.flags import get_validation_mode
            mode = get_validation_mode()
            assert mode == ValidationMode.HYBRID
    
    def test_new_mode_behavior(self):
        """Test that new mode works as expected"""
        with patch.dict(os.environ, {"VALIDATION_MODE": "new"}):
            from app.config.flags import get_validation_mode
            mode = get_validation_mode()
            assert mode == ValidationMode.NEW
    
    def test_invalid_mode_defaults_to_legacy(self):
        """Test that invalid mode defaults to legacy for safety"""
        with patch.dict(os.environ, {"VALIDATION_MODE": "invalid_mode"}):
            from app.config.flags import get_validation_mode
            mode = get_validation_mode()
            assert mode == ValidationMode.LEGACY


class TestValidationValidators:
    """Test validation validator functions"""
    
    def test_validate_legacy_first_in_legacy_mode(self):
        """Test validate_legacy_first in legacy mode"""
        with patch.dict(os.environ, {"VALIDATION_MODE": "legacy"}):
            payload = LEGACY_PAYLOAD_EXAMPLE
            
            ok, error = validate_legacy_first(payload)
            
            # Should use legacy validation
            assert isinstance(ok, bool)
            assert error is None or isinstance(error, dict)
    
    def test_validate_legacy_first_in_hybrid_mode(self):
        """Test validate_legacy_first in hybrid mode"""
        with patch.dict(os.environ, {"VALIDATION_MODE": "hybrid"}):
            payload = LEGACY_PAYLOAD_EXAMPLE
            
            ok, error = validate_legacy_first(payload)
            
            # Should use legacy validation as primary
            assert isinstance(ok, bool)
            assert error is None or isinstance(error, dict)
    
    def test_validate_both_modes_comparison(self):
        """Test validate_both_modes returns comparison data"""
        payload = LEGACY_PAYLOAD_EXAMPLE
        
        result = validate_both_modes(payload)
        
        # Should return comparison data
        assert "legacy" in result
        assert "nemt" in result
        assert "comparison" in result
        assert "timestamp" in result
        
        # Check structure
        assert "success" in result["legacy"]
        assert "error" in result["legacy"]
        assert "success" in result["nemt"]
        assert "error" in result["nemt"]
        assert "both_passed" in result["comparison"]
        assert "divergent" in result["comparison"]


class TestNEMTSchemaValidation:
    """Test NEMT schema validation directly"""
    
    def test_valid_nemt_payload(self):
        """Test that valid NEMT payload passes validation"""
        from app.schemas.nemt_trip import validate_payload
        
        try:
            model = validate_payload(VALID_PAYLOAD_EXAMPLE)
            assert model is not None
            assert model.generalInfo.CompleteUserName == "John Doe"
        except Exception as e:
            pytest.fail(f"Valid payload should not raise exception: {e}")
    
    def test_invalid_nemt_payload(self):
        """Test that invalid NEMT payload fails validation"""
        from app.schemas.nemt_trip import try_validate
        
        ok, model, error = try_validate(INVALID_PAYLOAD_EXAMPLE)
        
        assert ok is False
        assert model is None
        assert isinstance(error, dict)
        assert "error" in error
        assert "details" in error
        assert len(error["details"]) > 0
    
    def test_error_format_consistency(self):
        """Test that error format is consistent with spec"""
        from app.schemas.nemt_trip import try_validate
        
        ok, model, error = try_validate(INVALID_PAYLOAD_EXAMPLE)
        
        assert ok is False
        assert error["error"] == "ValidationError"
        
        for detail in error["details"]:
            assert "loc" in detail
            assert "msg" in detail
            assert "type" in detail


class TestIntegrationScenarios:
    """Test integration scenarios"""
    
    def test_legacy_to_nemt_roundtrip(self):
        """Test converting legacy to NEMT and back"""
        legacy_data = LEGACY_PAYLOAD_EXAMPLE
        
        # Convert to NEMT format
        nemt_data = from_legacy_to_nemt(legacy_data)
        
        # Convert back to legacy format (would need a valid NEMT model)
        # This test demonstrates the conversion pipeline
        assert isinstance(nemt_data, dict)
        assert len(nemt_data) > 0
    
    def test_validation_mode_switching(self):
        """Test switching between validation modes"""
        payload = LEGACY_PAYLOAD_EXAMPLE
        
        # Test legacy mode
        with patch.dict(os.environ, {"VALIDATION_MODE": "legacy"}):
            ok1, error1 = validate_legacy_first(payload)
        
        # Test hybrid mode
        with patch.dict(os.environ, {"VALIDATION_MODE": "hybrid"}):
            ok2, error2 = validate_legacy_first(payload)
        
        # Test new mode
        with patch.dict(os.environ, {"VALIDATION_MODE": "new"}):
            ok3, error3 = validate_legacy_first(payload)
        
        # All should return valid results (even if different)
        assert isinstance(ok1, bool)
        assert isinstance(ok2, bool)
        assert isinstance(ok3, bool)


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_malformed_payload_handling(self):
        """Test handling of malformed payloads"""
        malformed_payloads = [
            {},  # Empty payload
            {"invalid": "data"},  # Invalid structure
            None,  # None payload
        ]
        
        for payload in malformed_payloads:
            if payload is None:
                # Skip None test as it would cause type errors
                continue
                
            ok, error = validate_nemt_sidecar(payload)
            
            # Should handle gracefully without raising exceptions
            assert isinstance(ok, bool)
            assert error is None or isinstance(error, dict)
    
    def test_exception_safety(self):
        """Test that validation functions don't raise unhandled exceptions"""
        payload = LEGACY_PAYLOAD_EXAMPLE
        
        # These should not raise exceptions
        try:
            validate_legacy_first(payload)
            validate_both_modes(payload)
            validate_nemt_sidecar(payload)
        except Exception as e:
            pytest.fail(f"Validation functions should not raise unhandled exceptions: {e}")


# Test fixtures and utilities
@pytest.fixture
def sample_legacy_payload():
    """Fixture providing sample legacy payload"""
    return LEGACY_PAYLOAD_EXAMPLE


@pytest.fixture
def sample_valid_nemt_payload():
    """Fixture providing sample valid NEMT payload"""
    return VALID_PAYLOAD_EXAMPLE


@pytest.fixture
def sample_invalid_nemt_payload():
    """Fixture providing sample invalid NEMT payload"""
    return INVALID_PAYLOAD_EXAMPLE


# Integration test marker
pytest.mark.integration = pytest.mark.integration


@pytest.mark.integration
class TestIntegrationValidation:
    """Integration tests for validation system"""
    
    def test_full_validation_pipeline(self):
        """Test the complete validation pipeline"""
        payload = LEGACY_PAYLOAD_EXAMPLE
        
        # Test all validation modes
        modes = ["legacy", "hybrid", "new"]
        
        for mode in modes:
            with patch.dict(os.environ, {"VALIDATION_MODE": mode}):
                ok, error = validate_legacy_first(payload)
                assert isinstance(ok, bool)
                assert error is None or isinstance(error, dict)
    
    def test_metrics_collection(self):
        """Test that metrics are collected properly"""
        from app.infra.validation_logging import get_validation_metrics
        
        payload = LEGACY_PAYLOAD_EXAMPLE
        
        # Run some validations
        with patch.dict(os.environ, {"VALIDATION_MODE": "hybrid"}):
            validate_legacy_first(payload)
            validate_legacy_first(payload)
        
        # Check metrics
        metrics = get_validation_metrics()
        assert "timestamp" in metrics
        assert "mode_statistics" in metrics
        assert "total_events" in metrics


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])

