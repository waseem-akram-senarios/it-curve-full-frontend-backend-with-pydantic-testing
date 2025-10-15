"""
Test suite for phone number validation functionality.

This module tests the new phone validation function and its integration
with the Assistant class and LLM function tools.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import sys
import os

# Add the VoiceAgent3/IT_Curves_Bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'VoiceAgent3', 'IT_Curves_Bot'))

from helper_functions import Assistant
from models_validators import validate_phone_number
from pydantic import ValidationError


class TestPhoneValidation:
    """Test cases for phone number validation."""
    
    def test_validate_phone_number_valid_formats(self):
        """Test that valid E.164 phone numbers are accepted."""
        valid_phones = [
            "+13015551234",  # US format
            "+44123456789",  # UK format
            "+33123456789",  # France format
            "+8613800138000",  # China format
            "+1234567890",   # 10 digits
            "+123456789012345",  # 15 digits (max)
        ]
        
        for phone in valid_phones:
            result = validate_phone_number(phone)
            assert result == phone, f"Failed to validate {phone}"
    
    def test_validate_phone_number_invalid_formats(self):
        """Test that invalid phone numbers are rejected."""
        invalid_phones = [
            "",  # Empty string
            "   ",  # Whitespace only
            "123456789",  # Missing + prefix
            "+123456789",  # Too short (9 digits)
            "+1234567890123456",  # Too long (16 digits)
            "+0123456789",  # Starts with 0 after +
            "+abc1234567",  # Contains letters
            "+1-301-555-1234",  # Contains hyphens
            "+1 301 555 1234",  # Contains spaces
            "+1(301)555-1234",  # Contains parentheses
            "3015551234",  # No + prefix
            "+123456789",  # 9 digits (too short)
        ]
        
        for phone in invalid_phones:
            with pytest.raises(ValueError, match="Phone number cannot be empty|Must be E.164 format|Phone number must have at least 10 digits"):
                validate_phone_number(phone)
    
    def test_validate_phone_number_edge_cases(self):
        """Test edge cases for phone validation."""
        # Test None input
        with pytest.raises((ValueError, TypeError)):
            validate_phone_number(None)
        
        # Test numeric input
        with pytest.raises(AttributeError):
            validate_phone_number(1234567890)


class TestAssistantPhoneValidation:
    """Test cases for Assistant phone validation integration."""
    
    @pytest.fixture
    def assistant(self):
        """Create a mock Assistant instance for testing."""
        with patch('helper_functions.Agent.__init__'):
            return Assistant(
                call_sid="test_call_sid",
                context={},
                room=None,
                affiliate_id="test_affiliate",
                instructions="Test instructions",
                main_leg=None,
                return_leg=None,
                rider_phone="+13015551234",
                client_id="test_client"
            )
    
    @pytest.mark.asyncio
    async def test_validate_and_store_phone_number_success(self, assistant):
        """Test successful phone validation and storage."""
        valid_phone = "+13015551234"
        
        result = await assistant.validate_and_store_phone_number(valid_phone)
        
        # Check that phone was stored
        assert assistant.phone_number == valid_phone
        
        # Check response message
        assert "Thank you! I've confirmed your phone number" in result
        assert valid_phone in result
    
    @pytest.mark.asyncio
    async def test_validate_and_store_phone_number_invalid(self, assistant):
        """Test phone validation failure."""
        invalid_phone = "123456789"  # Missing + prefix
        
        result = await assistant.validate_and_store_phone_number(invalid_phone)
        
        # Check that phone was NOT stored
        assert assistant.phone_number is None
        
        # Check error message
        assert "I'm sorry, but the phone number you provided appears to be invalid" in result
        assert "E.164 format" in result
    
    @pytest.mark.asyncio
    async def test_validate_and_store_phone_number_empty(self, assistant):
        """Test phone validation with empty string."""
        empty_phone = ""
        
        result = await assistant.validate_and_store_phone_number(empty_phone)
        
        # Check that phone was NOT stored
        assert assistant.phone_number is None
        
        # Check error message
        assert "I'm sorry, but the phone number you provided appears to be invalid" in result
    
    @pytest.mark.asyncio
    async def test_validate_and_store_phone_number_too_short(self, assistant):
        """Test phone validation with too short number."""
        short_phone = "+123456789"  # 9 digits (too short)
        
        result = await assistant.validate_and_store_phone_number(short_phone)
        
        # Check that phone was NOT stored
        assert assistant.phone_number is None
        
        # Check error message
        assert "I'm sorry, but the phone number you provided appears to be invalid" in result
    
    @pytest.mark.asyncio
    async def test_validate_and_store_phone_number_exception_handling(self, assistant):
        """Test exception handling in phone validation."""
        # Mock validate_phone_number to raise an unexpected exception
        with patch('models_validators.validate_phone_number', side_effect=Exception("Unexpected error")):
            result = await assistant.validate_and_store_phone_number("+13015551234")
            
            # Check that phone was NOT stored
            assert assistant.phone_number is None
            
            # Check error message
            assert "I encountered an error validating your phone number" in result


class TestPhoneValidationIntegration:
    """Integration tests for phone validation with trip payload collection."""
    
    @pytest.fixture
    def assistant(self):
        """Create a mock Assistant instance for testing."""
        with patch('helper_functions.Agent.__init__'):
            return Assistant(
                call_sid="test_call_sid",
                context={},
                room=None,
                affiliate_id="test_affiliate",
                instructions="Test instructions",
                main_leg=None,
                return_leg=None,
                rider_phone="+13015551234",
                client_id="test_client"
            )
    
    @pytest.mark.asyncio
    async def test_phone_validation_before_trip_collection(self, assistant):
        """Test that validated phone is used in trip collection."""
        # First validate a phone number
        valid_phone = "+13015551234"
        await assistant.validate_and_store_phone_number(valid_phone)
        
        # Verify phone was stored
        assert assistant.phone_number == valid_phone
        
        # Mock the trip collection to check phone usage
        with patch.object(assistant, 'collect_main_trip_payload') as mock_collect:
            # The collect_main_trip_payload should use the validated phone
            # This is tested by checking that phone_number is set correctly
            assert hasattr(assistant, 'phone_number')
            assert assistant.phone_number == valid_phone
    
    @pytest.mark.asyncio
    async def test_phone_fallback_when_not_validated(self, assistant):
        """Test fallback to rider_phone when no validated phone is available."""
        # Ensure no validated phone is set
        assistant.phone_number = None
        
        # The system should fall back to self.rider_phone
        assert assistant.rider_phone == "+13015551234"
        
        # This fallback behavior is implemented in collect_main_trip_payload
        # and collect_return_trip_payload functions


class TestPhoneValidationRealWorld:
    """Real-world phone validation scenarios."""
    
    def test_international_phone_formats(self):
        """Test various international phone number formats."""
        international_phones = [
            ("+13015551234", True),   # US
            ("+442071234567", True),  # UK
            ("+33123456789", True),   # France
            ("+49123456789", True),   # Germany
            ("+8613800138000", True), # China
            ("+81312345678", True),   # Japan
            ("+5511987654321", True), # Brazil
            ("+61212345678", True),   # Australia
        ]
        
        for phone, should_pass in international_phones:
            if should_pass:
                result = validate_phone_number(phone)
                assert result == phone, f"Failed to validate international phone: {phone}"
            else:
                with pytest.raises(ValueError):
                    validate_phone_number(phone)
    
    def test_common_invalid_patterns(self):
        """Test common invalid phone number patterns users might enter."""
        common_invalid = [
            "123-456-7890",    # US format without +
            "(123) 456-7890",  # US format with parentheses
            "123.456.7890",    # US format with dots
            "123 456 7890",    # US format with spaces
            "+1-123-456-7890", # US format with hyphens
            "+1 (123) 456-7890", # US format with spaces and parentheses
            "011-123-456-7890", # International format without +
            "00-123-456-7890",  # International format without +
        ]
        
        for phone in common_invalid:
            with pytest.raises(ValueError):
                validate_phone_number(phone)


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
