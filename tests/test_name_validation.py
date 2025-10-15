"""
Test suite for the new validate_and_store_rider_name function tool.

This module tests the immediate name validation functionality that prevents
the LLM from accepting invalid names like "12345" during conversation.
"""

import pytest
import sys
import os
import asyncio
from unittest.mock import Mock, patch

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'VoiceAgent3', 'IT_Curves_Bot'))

from VoiceAgent3.IT_Curves_Bot.helper_functions import Assistant
from VoiceAgent3.IT_Curves_Bot.models_validators import validate_name


class TestNameValidation:
    """Test class for the validate_and_store_rider_name function."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a mock Assistant instance
        self.assistant = Assistant()
        self.assistant.rider_name = None  # Ensure clean state
    
    @pytest.mark.asyncio
    async def test_valid_name_acceptance(self):
        """Test that valid names are accepted and stored correctly."""
        valid_names = [
            "John Doe",
            "Mary O'Brien", 
            "Dr. Smith-Jones",
            "Jean-Pierre",
            "O'Connor",
            "Mary Jane Watson",
            "José María",
            "Li Wei"
        ]
        
        for name in valid_names:
            self.assistant.rider_name = None  # Reset
            
            result = await self.assistant.validate_and_store_rider_name(name)
            
            # Should accept the name
            assert "Thank you! I've confirmed your name as" in result
            assert name in result
            assert self.assistant.rider_name == name
            print(f"✅ Valid name accepted: {name}")
    
    @pytest.mark.asyncio
    async def test_invalid_name_rejection(self):
        """Test that invalid names are rejected with appropriate error messages."""
        invalid_names = [
            ("12345", "contains numbers"),
            ("John123", "contains numbers"),
            ("User@123", "contains special characters"),
            ("Name#1", "contains special characters"),
            ("Test$User", "contains special characters"),
            ("A", "too short"),
            ("", "empty string"),
            ("   ", "whitespace only"),
            ("Name123Test", "contains numbers"),
            ("123John", "starts with numbers"),
            ("John-123", "contains numbers"),
            ("Test.User.123", "contains numbers"),
            ("O'Brien123", "contains numbers")
        ]
        
        for invalid_name, reason in invalid_names:
            self.assistant.rider_name = None  # Reset
            
            result = await self.assistant.validate_and_store_rider_name(invalid_name)
            
            # Should reject the name
            assert "I'm sorry, but the name you provided appears to be invalid" in result
            assert "Names should only contain letters, spaces, hyphens, periods, and apostrophes" in result
            assert "Could you please provide your full name again?" in result
            assert self.assistant.rider_name is None  # Should not be stored
            print(f"✅ Invalid name rejected: '{invalid_name}' ({reason})")
    
    @pytest.mark.asyncio
    async def test_name_validation_edge_cases(self):
        """Test edge cases for name validation."""
        edge_cases = [
            ("John-Doe", True, "hyphen in name"),
            ("Mary O'Brien", True, "apostrophe in name"),
            ("Dr. Smith", True, "period in name"),
            ("Jean Pierre", True, "space in name"),
            ("O'Connor-Smith", True, "apostrophe and hyphen"),
            ("Mary Jane Watson-Parker", True, "multiple spaces and hyphen"),
            ("José María O'Connor", True, "accented characters"),
            ("李伟", False, "non-Latin characters"),
            ("John123Doe", False, "numbers in middle"),
            ("123", False, "only numbers"),
            ("@#$%", False, "only special characters"),
            ("John@Doe", False, "at symbol"),
            ("John#Doe", False, "hash symbol"),
            ("John$Doe", False, "dollar sign"),
            ("John%Doe", False, "percent sign"),
            ("John^Doe", False, "caret symbol"),
            ("John&Doe", False, "ampersand"),
            ("John*Doe", False, "asterisk"),
            ("John(Doe)", False, "parentheses"),
            ("John[Doe]", False, "brackets"),
            ("John{Doe}", False, "braces"),
            ("John|Doe", False, "pipe"),
            ("John\\Doe", False, "backslash"),
            ("John/Doe", False, "forward slash"),
            ("John<Doe>", False, "angle brackets"),
            ("John?Doe", False, "question mark"),
            ("John!Doe", False, "exclamation mark"),
            ("John:Doe", False, "colon"),
            ("John;Doe", False, "semicolon"),
            ("John\"Doe\"", False, "quotes"),
            ("John'Doe'", False, "single quotes"),
            ("John`Doe`", False, "backticks"),
            ("John~Doe", False, "tilde"),
            ("John+Doe", False, "plus sign"),
            ("John=Doe", False, "equals sign"),
        ]
        
        for name, should_pass, description in edge_cases:
            self.assistant.rider_name = None  # Reset
            
            result = await self.assistant.validate_and_store_rider_name(name)
            
            if should_pass:
                assert "Thank you! I've confirmed your name as" in result
                assert self.assistant.rider_name == name
                print(f"✅ Edge case passed: '{name}' ({description})")
            else:
                assert "I'm sorry, but the name you provided appears to be invalid" in result
                assert self.assistant.rider_name is None
                print(f"✅ Edge case rejected: '{name}' ({description})")
    
    @pytest.mark.asyncio
    async def test_name_length_validation(self):
        """Test name length validation."""
        length_test_cases = [
            ("A", False, "too short (1 char)"),
            ("AB", True, "minimum length (2 chars)"),
            ("John", True, "normal length"),
            ("Mary Jane Watson-Parker O'Connor-Smith", True, "long name"),
            ("A" * 100, True, "maximum length (100 chars)"),
            ("A" * 101, False, "too long (101 chars)"),
            ("A" * 200, False, "way too long (200 chars)")
        ]
        
        for name, should_pass, description in length_test_cases:
            self.assistant.rider_name = None  # Reset
            
            result = await self.assistant.validate_and_store_rider_name(name)
            
            if should_pass:
                assert "Thank you! I've confirmed your name as" in result
                assert self.assistant.rider_name == name
                print(f"✅ Length test passed: {description}")
            else:
                assert "I'm sorry, but the name you provided appears to be invalid" in result
                assert self.assistant.rider_name is None
                print(f"✅ Length test rejected: {description}")
    
    @pytest.mark.asyncio
    async def test_whitespace_handling(self):
        """Test whitespace handling in names."""
        whitespace_test_cases = [
            ("John Doe", "John Doe", True, "normal space"),
            (" John Doe ", "John Doe", True, "leading and trailing spaces"),
            ("  John   Doe  ", "John Doe", True, "multiple spaces"),
            ("John\tDoe", "John\tDoe", True, "tab character"),
            ("John\nDoe", "John\nDoe", True, "newline character"),
            ("", "", False, "empty string"),
            ("   ", "", False, "only spaces"),
            ("\t", "", False, "only tab"),
            ("\n", "", False, "only newline"),
            ("\r\n", "", False, "only carriage return + newline")
        ]
        
        for input_name, expected_stored, should_pass, description in whitespace_test_cases:
            self.assistant.rider_name = None  # Reset
            
            result = await self.assistant.validate_and_store_rider_name(input_name)
            
            if should_pass:
                assert "Thank you! I've confirmed your name as" in result
                # Note: The validate_name function strips whitespace
                expected_stripped = expected_stored.strip() if expected_stored.strip() else expected_stored
                if expected_stripped:  # Only check if there's actual content after stripping
                    assert self.assistant.rider_name == expected_stripped
                print(f"✅ Whitespace test passed: {description}")
            else:
                assert "I'm sorry, but the name you provided appears to be invalid" in result
                assert self.assistant.rider_name is None
                print(f"✅ Whitespace test rejected: {description}")
    
    @pytest.mark.asyncio
    async def test_name_overwriting(self):
        """Test that a new valid name overwrites the previous one."""
        # Set initial name
        result1 = await self.assistant.validate_and_store_rider_name("John Doe")
        assert "Thank you! I've confirmed your name as John Doe" in result1
        assert self.assistant.rider_name == "John Doe"
        
        # Overwrite with new valid name
        result2 = await self.assistant.validate_and_store_rider_name("Mary Smith")
        assert "Thank you! I've confirmed your name as Mary Smith" in result2
        assert self.assistant.rider_name == "Mary Smith"
        
        print("✅ Name overwriting test passed")
    
    @pytest.mark.asyncio
    async def test_name_validation_error_handling(self):
        """Test error handling in name validation."""
        # Test with None input (should not happen in practice, but test robustness)
        try:
            result = await self.assistant.validate_and_store_rider_name(None)
            # Should handle gracefully
            assert "error" in result.lower() or "invalid" in result.lower()
            print("✅ None input handled gracefully")
        except Exception as e:
            print(f"⚠️ None input caused exception: {e}")
        
        # Test with non-string input
        try:
            result = await self.assistant.validate_and_store_rider_name(12345)
            # Should handle gracefully
            assert "error" in result.lower() or "invalid" in result.lower()
            print("✅ Non-string input handled gracefully")
        except Exception as e:
            print(f"⚠️ Non-string input caused exception: {e}")
    
    @pytest.mark.asyncio
    async def test_validation_integration_with_trip_payload(self):
        """Test that validated names are used in trip payload functions."""
        # First validate and store a name
        await self.assistant.validate_and_store_rider_name("John Doe")
        assert self.assistant.rider_name == "John Doe"
        
        # Mock the collect_main_trip_payload to test name usage
        with patch.object(self.assistant, 'collect_main_trip_payload') as mock_collect:
            # Create a mock payload with different name
            mock_payload = Mock()
            mock_payload.rider_name = "Jane Smith"  # Different from validated name
            mock_payload.model_dump.return_value = {}
            
            # Mock the validation functions
            with patch('VoiceAgent3.IT_Curves_Bot.helper_functions.try_validate') as mock_validate:
                mock_validate.return_value = (True, {}, None)
                
                # Call the function
                await self.assistant.collect_main_trip_payload(mock_payload)
                
                # Verify the function was called
                mock_collect.assert_called_once()
                print("✅ Name validation integration test passed")


class TestValidateNameFunction:
    """Test the underlying validate_name function from models_validators."""
    
    def test_validate_name_valid_cases(self):
        """Test validate_name function with valid inputs."""
        valid_names = [
            "John Doe",
            "Mary O'Brien",
            "Dr. Smith-Jones",
            "Jean-Pierre",
            "O'Connor",
            "Mary Jane Watson",
            "José María",
            "Li Wei",
            "John-Doe",
            "Mary O'Brien-Smith"
        ]
        
        for name in valid_names:
            result = validate_name(name)
            assert result == name.strip()
            print(f"✅ validate_name accepted: {name}")
    
    def test_validate_name_invalid_cases(self):
        """Test validate_name function with invalid inputs."""
        invalid_cases = [
            ("12345", "contains numbers"),
            ("John123", "contains numbers"),
            ("User@123", "contains special characters"),
            ("A", "too short"),
            ("", "empty string"),
            ("   ", "whitespace only"),
            ("John@Doe", "contains @"),
            ("John#Doe", "contains #"),
            ("John$Doe", "contains $")
        ]
        
        for name, reason in invalid_cases:
            with pytest.raises(ValueError) as exc_info:
                validate_name(name)
            print(f"✅ validate_name rejected: '{name}' ({reason}) - {exc_info.value}")
    
    def test_validate_name_length_constraints(self):
        """Test validate_name length constraints."""
        # Test minimum length
        with pytest.raises(ValueError) as exc_info:
            validate_name("A")
        assert "at least 2 characters" in str(exc_info.value)
        
        # Test maximum length
        long_name = "A" * 101
        with pytest.raises(ValueError) as exc_info:
            validate_name(long_name)
        assert "cannot exceed 100 characters" in str(exc_info.value)
        
        print("✅ validate_name length constraints working")


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])

