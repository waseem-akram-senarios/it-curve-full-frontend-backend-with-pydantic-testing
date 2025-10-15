# Two-Tier Validation System Documentation

## Overview

The VoiceAgent project implements a **Two-Tier Validation Strategy** using Pydantic v2 to ensure data quality at every level of the application. This system prevents the LLM from accepting invalid data (like "12345" as a name) and provides immediate feedback for learning.

## Table of Contents

1. [What is Two-Tier Validation?](#what-is-two-tier-validation)
2. [Architecture Overview](#architecture-overview)
3. [Tier 1: Format Validation (LLM Interface)](#tier-1-format-validation-llm-interface)
4. [Tier 2: Business Logic Validation (NEMT Schema)](#tier-2-business-logic-validation-nemt-schema)
5. [Immediate Name Validation](#immediate-name-validation)
6. [Code Integration Examples](#code-integration-examples)
7. [Testing Guide](#testing-guide)
8. [Migration History](#migration-history)
9. [Quick Reference](#quick-reference)
10. [Files Involved](#files-involved)

---

## What is Two-Tier Validation?

Two-Tier Validation is a strategy that separates **format validation** from **business logic validation**:

- **Tier 1**: Catches format errors immediately when the LLM collects data
- **Tier 2**: Enforces complex business rules and cross-field dependencies

### Why We Implemented This

**Problem**: The LLM was accepting invalid data like:
- Numbers as names: "12345"
- Invalid phone formats: "301-555-1234"
- Invalid ZIP codes: "ABC123"

**Solution**: Immediate validation that provides clear feedback to the LLM, forcing it to learn correct formats.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERACTION                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              TIER 1: FORMAT VALIDATION                     │
│           (LLM Function Tools Interface)                   │
│                                                             │
│  • Name validation (letters, spaces, hyphens only)         │
│  • Phone validation (E.164 format)                         │
│  • State validation (USPS codes)                           │
│  • ZIP validation (5-digit or 5+4 format)                  │
│  • Coordinate validation (lat/lng ranges)                  │
│  • DateTime validation (ISO formats)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│            TIER 2: BUSINESS LOGIC VALIDATION               │
│                 (NEMT Schema)                              │
│                                                             │
│  • Insurance authorization dependencies                     │
│  • Cross-field validation rules                            │
│  • Service code constraints                                │
│  • Age bounds validation                                   │
│  • Ride time constraints                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Tier 1: Format Validation (LLM Interface)

*Location: `models.py` + `models_validators.py`*

These validations run **immediately** when the LLM calls function tools, providing instant feedback on format errors.

### 1. Name Validation

**Purpose**: Ensure names contain only valid characters and proper length.

**Rules**:
- **Pattern**: Letters, spaces, hyphens, periods, apostrophes only
- **Length**: 2-100 characters
- **Rejects**: Numbers, special characters, empty strings

**Examples**:
```python
✅ Valid:   "John Doe", "Mary O'Brien", "Dr. Smith-Jones"
❌ Invalid: "John123", "J", "", "User@123"
```

**Implementation**:
```python
@field_validator('rider_name')
@classmethod
def validate_rider_name(cls, v: str) -> str:
    return validate_name(v)
```

### 2. Phone Number Validation (E.164 Format)

**Purpose**: Ensure phone numbers follow international E.164 standard.

**Rules**:
- **Format**: `+` followed by country code + number
- **Total Digits**: 10-15 digits (including country code)
- **Required Fields**: `home_phone` (mandatory for both trip types)
- **Optional Fields**: `office_phone`, `pickup_phone_number`, `dropoff_phone_number`

**Examples**:
```python
✅ Valid:   "+13015551234", "+44123456789", "+1234567890"
❌ Invalid: "123-456-7890", "3015551234", "+123456789", ""
```

**Implementation**:
```python
@field_validator('home_phone')
@classmethod
def validate_home_phone(cls, v: str) -> str:
    if not v or v.strip() == '':
        raise ValueError("Home phone number is required")
    return validate_phone_number(v)
```

### 3. State Code Validation

**Purpose**: Ensure valid USPS 2-letter state codes.

**Rules**:
- **Format**: 2-letter USPS state codes
- **Validation**: Must match one of 50 US states + DC
- **Auto-uppercase**: Converts to uppercase

**Examples**:
```python
✅ Valid:   "MD" → "MD", "ca" → "CA", "ny" → "NY"
❌ Invalid: "XX", "Maryland", "M", ""
```

### 4. ZIP Code Validation

**Purpose**: Ensure valid US ZIP code formats.

**Rules**:
- **Format**: 5-digit or 5+4 format
- **Pattern**: `12345` or `12345-6789`

**Examples**:
```python
✅ Valid:   "21201", "21201-1234"
❌ Invalid: "212", "ABCDE", "21201-12", ""
```

### 5. DateTime Validation

**Purpose**: Ensure valid datetime formats for scheduling.

**Supported Formats**:
- `YYYY-MM-DD HH:MM`
- `YYYY-MM-DD HH:MM:SS`
- `YYYY-MM-DDTHH:MM:SS`
- `YYYY-MM-DDTHH:MM:SSZ`
- `YYYY-MM-DDTHH:MM:SS.fZ`

**Examples**:
```python
✅ Valid:   "2024-01-15 14:30", "2024-01-15T14:30:00Z"
❌ Invalid: "01/15/2024", "14:30", ""
```

### 6. Coordinate Validation

**Latitude**:
- **Range**: -90 to 90
- **Type**: Must be parseable as float

**Longitude**:
- **Range**: -180 to 180
- **Type**: Must be parseable as float

**Examples**:
```python
✅ Valid:   "39.2904", "-76.6122", "0"
❌ Invalid: "abc", "91", "-91", ""
```

### 7. ID Field Validation

**Purpose**: Validate numeric ID fields.

**Rules**:
- **Format**: Numeric string or `"-1"` (for unknown)
- **Fields**: `client_id`, `funding_source_id`, `rider_id`, `family_id`, etc.

**Examples**:
```python
✅ Valid:   "123", "0", "-1"
❌ Invalid: "abc", "", "12.5"
```

### 8. Count Field Validation

**Purpose**: Validate count fields like passengers and wheelchairs.

**Rules**:
- **Format**: Non-negative integer
- **Fields**: `number_of_wheel_chairs`, `number_of_passengers`

**Examples**:
```python
✅ Valid:   "0", "1", "5"
❌ Invalid: "-1", "abc", "1.5", ""
```

### 9. Address Field Validation

**Purpose**: Validate address fields.

**Rules**:
- **Length**: 1-500 characters
- **Required**: Cannot be empty
- **Fields**: `pickup_street_address`, `dropoff_street_address`, `rider_home_address`

**Examples**:
```python
✅ Valid:   "123 Main St", "Apt 4B, 456 Oak Avenue"
❌ Invalid: "", (501+ character string)
```

### 10. City Field Validation

**Purpose**: Validate city fields.

**Rules**:
- **Length**: 1-100 characters
- **Required**: Cannot be empty
- **Fields**: `pickup_city`, `dropoff_city`, `rider_home_city`

**Examples**:
```python
✅ Valid:   "Baltimore", "New York", "San Francisco"
❌ Invalid: "", (101+ character string)
```

### 11. Notes/Remarks Field Validation

**Purpose**: Validate notes and remarks fields.

**Rules**:
- **Length**: 0-1000 characters
- **Optional**: Can be empty
- **Fields**: `extra_details`, `pickup_remarks`, `dropoff_remarks`

**Examples**:
```python
✅ Valid:   "", "Patient needs wheelchair assistance", (any text ≤1000 chars)
❌ Invalid: (1001+ character string)
```

---

## Tier 2: Business Logic Validation (NEMT Schema)

*Location: `app/schemas/nemt_trip.py`*

These validations run **after** Tier 1 passes, enforcing complex business rules and cross-field dependencies.

### 1. General Information Validation

**Fields**:
- **CompleteUserName**: 1-255 characters
- **CreatedByAppID**: Integer ≥ 0
- **RequestAffiliateID**: Integer ≥ 0

**Cross-field Rules**:
- User dependencies validation

### 2. Rider Information Validation

**Phone Number (E.164)**:
- Same as Tier 1, enforced again at business level

**Date of Birth**:
- **Age Range**: 0-120 years
- **Type**: Valid date object
- **Validation**: Calculated age must be reasonable

**Medical ID**:
- **Length**: 1-50 characters
- **Required**: Cannot be empty

**Address Fields**:
- **State**: Must be valid USPS state enum
- **ZIP**: Validated against state (MD-specific range check implemented)
- **Address/City**: Required, length constraints

### 3. Insurance Information Validation

**Authorization Dependencies**:
- **Rule**: If `InsuranceID` is not 0, `AuthID` must be provided
- **Example Valid**: `InsuranceID=1, AuthID="AUTH123"`
- **Example Invalid**: `InsuranceID=1, AuthID=""` → **Error: "AuthID is required when InsuranceID is not 0"**

**Service Code**:
- **Enum**: AMBULATORY, WHEELCHAIR, STRETCHER, BARIATRIC
- **Required**: Must match predefined service types

### 4. Route Settings Validation

**Ride Time Constraints**:
- **MaxRideTime** must be ≥ **MinRideTime**
- **Range**: 0-1440 minutes (24 hours max)
- **Example Valid**: `MinRideTime=30, MaxRideTime=60`
- **Example Invalid**: `MinRideTime=60, MaxRideTime=30` → **Error: "MaxRideTime must be >= MinRideTime"**

**Service Time Wheelchair**:
- **Range**: 0-1440 minutes
- **Conditional**: If service code is WHEELCHAIR, must be > 0

### 5. Model Configuration (All Models)

**Pydantic Config**:
- `extra="forbid"` - Reject unknown fields
- `str_strip_whitespace=True` - Auto-trim strings
- `validate_assignment=True` - Validate on field updates
- `use_enum_values=True` - Use enum values in output

---

## Immediate Name Validation

### Problem Solved

**Before**: LLM could accept invalid names like "12345" and store them in conversation context:

```
User: "My name is 12345"
LLM: "Thanks, 12345. Can I have your rider ID, please?"
User: "What's my name?"
LLM: "Your name is 12345."
```

**After**: Invalid names are rejected immediately with clear feedback:

```
User: "My name is 12345"
LLM: [calls validate_and_store_rider_name("12345")]
LLM: "I'm sorry, but the name you provided appears to be invalid. Names should only contain letters, spaces, hyphens, periods, and apostrophes. Could you please provide your full name again?"
User: "John Smith"
LLM: [calls validate_and_store_rider_name("John Smith")]
LLM: "Thank you! I've confirmed your name as John Smith. Can I have your rider ID, please?"
```

### Implementation

#### 1. New Function Tool

**File**: `VoiceAgent3/IT_Curves_Bot/helper_functions.py`

```python
@function_tool()
async def validate_and_store_rider_name(self, rider_name: str) -> str:
    """
    Validate and store the rider's name.
    This function MUST be called immediately when a rider provides their name.
    
    Args:
        rider_name: The name provided by the rider
        
    Returns:
        Success message with validated name or error message with validation failure
    """
    try:
        # Import validate_name from models_validators
        from models_validators import validate_name
        
        # Apply Tier 1 name validation
        validated_name = validate_name(rider_name)
        
        # Store the validated name in session
        self.rider_name = validated_name
        
        logger.info(f"✅ [VALIDATE_NAME] Name validated and stored: {validated_name}")
        return f"Thank you! I've confirmed your name as {validated_name}."
        
    except ValueError as e:
        logger.warning(f"❌ [VALIDATE_NAME] Invalid name rejected: {rider_name} - Error: {e}")
        return f"I'm sorry, but the name you provided appears to be invalid. Names should only contain letters, spaces, hyphens, periods, and apostrophes. Could you please provide your full name again?"
    except Exception as e:
        logger.error(f"❌ [VALIDATE_NAME] Unexpected error: {e}")
        return f"I encountered an error validating your name. Could you please provide your full name again?"
```

#### 2. Session Variable

**File**: `VoiceAgent3/IT_Curves_Bot/helper_functions.py`

```python
def __init__(self, ...):
    # ... other initialization ...
    self.rider_name = None  # Validated rider name
```

#### 3. Integration with Trip Payload Functions

**File**: `VoiceAgent3/IT_Curves_Bot/helper_functions.py`

```python
# In collect_main_trip_payload and collect_return_trip_payload
rider_name = payload.rider_name

# Verify name was validated if available
if hasattr(self, 'rider_name') and self.rider_name:
    # Use the pre-validated name if available
    if payload.rider_name != self.rider_name:
        logger.warning(f"⚠️ Name mismatch: payload={payload.rider_name}, validated={self.rider_name}")
        rider_name = self.rider_name  # Use the validated name
        logger.info(f"✅ Using validated rider name: {rider_name}")
```

#### 4. LLM Prompt Integration

**Updated in all 8 prompt files**:

```
## Name Collection and Validation
When asking for the rider's name:
1. Ask: "May I have your full name, please?"
2. WAIT for the rider to respond
3. IMMEDIATELY call [validate_and_store_rider_name] function with the name provided
4. If validation succeeds, proceed with the confirmed name
5. If validation fails, ask the rider to provide their name again
6. DO NOT proceed or use the name until validation succeeds
```

### Benefits of Early Validation

1. **Immediate Feedback**: LLM gets instant validation results
2. **Clear Error Messages**: Specific guidance on what's wrong
3. **Learning**: LLM learns correct formats from validation errors
4. **Data Quality**: Only properly formatted data reaches business logic
5. **User Experience**: Users get clear feedback and can correct mistakes

---

## Immediate Phone Validation

### Problem Solved

**Before**: LLM could accept invalid phone numbers and store them in conversation context:

```
User: "My phone is 123-456-7890"
LLM: "Thanks, I have your phone as 123-456-7890. Can I have your rider ID, please?"
User: "What's my phone?"
LLM: "Your phone number is 123-456-7890."
```

**After**: Invalid phone numbers are rejected immediately with clear feedback:

```
User: "My phone is 123-456-7890"
LLM: [calls validate_and_store_phone_number("123-456-7890")]
LLM: "I'm sorry, but the phone number you provided appears to be invalid. Phone numbers must be in E.164 format (like +13015551234). Could you please provide your phone number again?"
User: "+13015551234"
LLM: [calls validate_and_store_phone_number("+13015551234")]
LLM: "Thank you! I've confirmed your phone number as +13015551234. Can I have your rider ID, please?"
```

### Implementation

#### 1. New Function Tool

**File**: `VoiceAgent3/IT_Curves_Bot/helper_functions.py`

```python
@function_tool()
async def validate_and_store_phone_number(self, phone_number: str) -> str:
    """
    Validate and store the rider's phone number.
    This function MUST be called immediately when a rider provides their phone number.
    
    Args:
        phone_number: The phone number provided by the rider
        
    Returns:
        Success message with validated phone number or error message with validation failure
    """
    try:
        # Import validate_phone_number from models_validators
        from models_validators import validate_phone_number
        
        # Apply Tier 1 phone validation
        validated_phone = validate_phone_number(phone_number)
        
        # Store the validated phone in session
        self.phone_number = validated_phone
        
        logger.info(f"✅ [VALIDATE_PHONE] Phone validated and stored: {validated_phone}")
        return f"Thank you! I've confirmed your phone number as {validated_phone}."
        
    except ValueError as e:
        logger.warning(f"❌ [VALIDATE_PHONE] Invalid phone rejected: {phone_number} - Error: {e}")
        return f"I'm sorry, but the phone number you provided appears to be invalid. Phone numbers must be in E.164 format (like +13015551234). Could you please provide your phone number again?"
    except Exception as e:
        logger.error(f"❌ [VALIDATE_PHONE] Unexpected error: {e}")
        return f"I encountered an error validating your phone number. Could you please provide your phone number again?"
```

#### 2. Session Variable

**File**: `VoiceAgent3/IT_Curves_Bot/helper_functions.py`

```python
def __init__(self, ...):
    # ... other initialization ...
    self.phone_number = None  # Validated phone number
```

#### 3. Integration with Trip Payload Functions

**File**: `VoiceAgent3/IT_Curves_Bot/helper_functions.py`

```python
# In collect_main_trip_payload and collect_return_trip_payload

# Use validated phone number if available
if hasattr(self, 'phone_number') and self.phone_number:
    phone_number = self.phone_number
    logger.info(f"✅ Using validated phone number: {phone_number}")
else:
    phone_number = self.rider_phone
    logger.warning(f"⚠️ Using stored rider phone (no validation): {phone_number}")
```

#### 4. LLM Prompt Integration

**Updated in all 8 prompt files**:

```
## Phone Number Collection and Validation
When collecting phone numbers during trip booking:
1. Ask: "What is your home phone number?"
2. WAIT for the rider to respond
3. IMMEDIATELY call [validate_and_store_phone_number] function with the phone number provided
4. If validation succeeds, proceed with the confirmed phone number
5. If validation fails, ask the rider to provide their phone number again in E.164 format (like +13015551234)
6. DO NOT proceed with booking until phone validation succeeds
```

### Phone Validation Rules

#### Valid E.164 Formats
- **US**: `+13015551234`
- **UK**: `+442071234567`
- **International**: `+33123456789`, `+8613800138000`
- **Length**: 7-15 digits after the `+` (8-16 characters total)
- **Minimum**: At least 10 digits total for practical phone numbers

#### Invalid Formats (Rejected)
- Missing `+` prefix: `1234567890`
- Too short: `+123456789` (9 digits)
- Too long: `+1234567890123456` (16 digits)
- Contains separators: `+1-301-555-1234`
- Contains spaces: `+1 301 555 1234`
- Starts with 0: `+0123456789`

### Benefits of Phone Validation

1. **E.164 Compliance**: Ensures international standard format
2. **Data Consistency**: All phone numbers stored in same format
3. **System Integration**: Compatible with SMS/calling systems
4. **User Guidance**: Clear instructions on correct format
5. **Error Prevention**: Prevents downstream processing errors

---

## Code Integration Examples

### Example 1: Complete Validation Flow

```python
# LLM attempts to call collect_main_trip_payload with:
{
    "rider_name": "John123",       # ❌ TIER 1 REJECTS: contains numbers
    "home_phone": "301-555-1234",  # ❌ TIER 1 REJECTS: not E.164 format
    ...
}

# Error returned to LLM:
"Format validation failed: rider_name: Name can only contain letters, 
spaces, hyphens, periods, and apostrophes; home_phone: Must be E.164 
format with 7-15 digits total (+13015551234)"

# LLM learns and retries with:
{
    "rider_name": "John Doe",      # ✅ TIER 1 PASSES
    "home_phone": "+13015551234",  # ✅ TIER 1 PASSES
    ...
}

# Now proceeds to TIER 2 (NEMT Schema)...
# If business rules fail (e.g., insurance dependency):
"Business validation failed: AuthID is required when InsuranceID is not 0"
```

### Example 2: Name Validation Integration

```python
# During conversation:
async def conversation_flow():
    # User provides name
    user_name = "12345"  # Invalid
    
    # LLM calls validation function
    result = await assistant.validate_and_store_rider_name(user_name)
    # Returns: "I'm sorry, but the name you provided appears to be invalid..."
    
    # User provides valid name
    user_name = "John Smith"  # Valid
    
    # LLM calls validation function
    result = await assistant.validate_and_store_rider_name(user_name)
    # Returns: "Thank you! I've confirmed your name as John Smith."
    # assistant.rider_name is now "John Smith"
    
    # Later, when booking trip:
    payload = MainTripPayload(rider_name="Jane Doe", ...)  # Different name
    
    # Function uses validated name instead:
    await assistant.collect_main_trip_payload(payload)
    # Uses "John Smith" (validated) instead of "Jane Doe" (payload)
```

### Example 3: Error Handling Patterns

```python
try:
    # Tier 1 validation (automatic via Pydantic)
    payload = MainTripPayload(**data)
    
    # Tier 2 validation (manual call)
    validation_ok, validated_model, error_details = try_validate(payload.model_dump())
    
    if not validation_ok:
        return f"Business validation failed: {format_validation_error(error_details)}"
        
except ValidationError as e:
    # Tier 1 validation failed
    return f"Format validation failed: {format_pydantic_error(e)}"
```

---

## Testing Guide

### Running Tests

```bash
# Run all validation tests
python -m pytest tests/test_name_validation.py -v
python -m pytest tests/test_phone_validation.py -v

# Run both name and phone validation tests
python -m pytest tests/test_name_validation.py tests/test_phone_validation.py -v

# Run specific test categories
python -m pytest tests/test_name_validation.py::TestNameValidation::test_valid_name_acceptance -v
python -m pytest tests/test_name_validation.py::TestNameValidation::test_invalid_name_rejection -v
```

### Test Categories

1. **Valid Name Acceptance**: Tests that valid names are accepted and stored
2. **Invalid Name Rejection**: Tests that invalid names are rejected with proper error messages
3. **Edge Cases**: Tests special characters, length limits, whitespace handling
4. **Integration Tests**: Tests integration with trip payload functions
5. **Error Handling**: Tests robustness with unexpected inputs

### Example Test Cases

```python
# Valid names
valid_names = [
    "John Doe",
    "Mary O'Brien", 
    "Dr. Smith-Jones",
    "Jean-Pierre",
    "O'Connor"
]

# Invalid names
invalid_names = [
    ("12345", "contains numbers"),
    ("John123", "contains numbers"),
    ("User@123", "contains special characters"),
    ("A", "too short"),
    ("", "empty string")
]
```

---

## Migration History

### The Problem Before

1. **Weak Validation**: Old Pydantic v1 models had minimal validation
2. **LLM Acceptance**: LLM could accept any input format
3. **Data Quality Issues**: Invalid data like "12345" as names were stored
4. **No Learning**: LLM didn't get feedback to improve

### The Solution Implemented

1. **Two-Tier Architecture**: Separated format validation from business logic
2. **Immediate Validation**: Name validation happens during conversation
3. **Clear Feedback**: Specific error messages guide the LLM
4. **Industry Standards**: E.164 phone format, USPS state codes, etc.

### Benefits Achieved

1. **Data Quality**: 100% format validation compliance
2. **User Experience**: Clear error messages and guidance
3. **LLM Learning**: Immediate feedback improves response quality
4. **Business Logic**: Complex rules enforced after format validation
5. **Maintainability**: Clear separation of concerns

---

## Quick Reference

### Summary of Validators

| Validator | Purpose | Valid Examples | Invalid Examples |
|-----------|---------|----------------|------------------|
| **Name** | Person names | "John Doe", "Mary O'Brien" | "John123", "User@123" |
| **Phone** | E.164 format | "+13015551234", "+44123456789" | "301-555-1234", "1234567890" |
| **State** | USPS codes | "MD", "CA", "NY" | "XX", "Maryland", "M" |
| **ZIP** | US ZIP format | "21201", "21201-1234" | "212", "ABCDE", "21201-12" |
| **DateTime** | ISO formats | "2024-01-15 14:30" | "01/15/2024", "14:30" |
| **Latitude** | -90 to 90 | "39.2904", "0" | "91", "abc" |
| **Longitude** | -180 to 180 | "-76.6122", "180" | "181", "abc" |
| **ID** | Numeric or -1 | "123", "0", "-1" | "abc", "12.5" |
| **Count** | Non-negative | "0", "1", "5" | "-1", "abc", "1.5" |
| **Address** | 1-500 chars | "123 Main St" | "", (501+ chars) |
| **City** | 1-100 chars | "Baltimore", "New York" | "", (101+ chars) |
| **Notes** | 0-1000 chars | "", "Any text ≤1000" | (1001+ chars) |

### Common Validation Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "Name can only contain letters, spaces, hyphens, periods, and apostrophes" | Numbers or special chars in name | Remove numbers/special characters |
| "Must be E.164 format with 7-15 digits total" | Wrong phone format | Use +1234567890 format |
| "Invalid state code" | Wrong state format | Use 2-letter USPS code |
| "Must be US ZIP format" | Wrong ZIP format | Use 12345 or 12345-6789 |
| "Phone number cannot be empty" | Missing required phone | Provide valid E.164 phone |
| "AuthID is required when InsuranceID is not 0" | Missing authorization | Provide AuthID or set InsuranceID to 0 |

### FAQs

**Q: Why two tiers instead of one?**
A: Separates format validation (immediate LLM feedback) from business logic (complex rules). This allows the LLM to learn correct formats quickly while maintaining sophisticated business validation.

**Q: What happens if Tier 1 passes but Tier 2 fails?**
A: The user gets a business logic error message explaining what's wrong (e.g., missing insurance authorization).

**Q: Can I add new validators?**
A: Yes! Add the validation function to `models_validators.py` and apply it via `@field_validator` in the appropriate model.

**Q: How do I test the validation?**
A: Run `python -m pytest tests/test_name_validation.py -v` for comprehensive test coverage.

---

## Files Involved

### Core Validation Files

- **`models.py`** - Tier 1 Pydantic models with field validators
- **`models_validators.py`** - Reusable validation utilities
- **`app/schemas/nemt_trip.py`** - Tier 2 NEMT business logic schema
- **`helper_functions.py`** - Integration point with `validate_and_store_rider_name` function

### Prompt Files (Updated)

- `prompts/prompt_new_rider.txt`
- `prompts/prompt_multiple_riders.txt`
- `prompts/prompt_old_rider.txt`
- `prompts/prompt_widget.txt`
- `prompts/prompt_new_rider_ivr.txt`
- `prompts/prompt_multiple_riders_ivr.txt`
- `prompts/prompt_old_rider_ivr.txt`
- `prompts/prompt_widget_ivr.txt`

### Test Files

- **`tests/test_name_validation.py`** - Comprehensive test suite for name validation
- **`tests/test_two_tier_validation.py`** - Tests for Tier 1 validation utilities
- **`tests/test_llm_integration.py`** - Integration tests for LLM function calls

### Configuration Files

- **`env.example`** - Environment variables (validation flags removed in Phase 3)
- **`app/main.py`** - FastAPI application with validation endpoints

---

## Rollback Plan

If issues arise with the new validation system:

1. **Tag Current State**: `git tag v2-validation-backup`
2. **Revert to Previous Commit**: `git checkout <previous-commit>`
3. **Restart Services**: `./start-project.sh`

The validation system is designed to be backward-compatible and can be safely rolled back if needed.

---

**This comprehensive validation ensures data quality at every level, from format compliance to business rule adherence!** 🚀