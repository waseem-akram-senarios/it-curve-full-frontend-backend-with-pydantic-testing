# Prompt vs Pydantic: Clear Division of Responsibilities

## 🎯 Goal: Reduce Redundancy and Clarify Responsibilities

### Current Problem
- Prompts handling data formatting (should be code)
- Prompts handling validation (should be Pydantic)
- Pydantic models exist but not fully utilized
- Duplicate instructions across 6+ prompt files

## 📊 Clear Division of Work

### PROMPTS Should Handle:
1. **Conversation Flow**
   - When to ask for information
   - What question to ask next
   - How to respond to user inputs

2. **Function Calling Logic**
   - When to call `[get_valid_addresses]`
   - When to call `[book_trips]`
   - When to ask for return trip

3. **Confirmation Requirements**
   - Must confirm pickup before proceeding
   - Must confirm dropoff before proceeding
   - Must confirm payment method

4. **Error Handling**
   - What to say when address invalid
   - What to say when payment fails
   - How to guide user to correct input

5. **Closing Conversation**
   - Must ask "Is there anything else?"
   - When to use `[Close_Call]`

### PYDANTIC Should Handle:
1. **Data Validation**
   - Phone number format
   - Address structure
   - Coordinate ranges (-90 to 90 for lat)
   - Date/time formats
   - Required fields

2. **Type Safety**
   - Ensures data types are correct
   - Converts strings to numbers
   - Validates enums

3. **Default Values**
   - Sets sensible defaults
   - Makes optional fields optional

### CODE (Helper Functions) Should Handle:
1. **Formatting for TTS**
   - Remove symbols (*, #, -)
   - Expand abbreviations (Ave → Avenue)
   - Format times (24h → 12h)
   - Remove emojis and quotes

2. **Business Logic**
   - Address verification API calls
   - Payment processing
   - Trip booking

3. **Data Transformation**
   - Normalize phone numbers
   - Parse addresses
   - Calculate distances

## 🔄 Current Redundancies

### Redundancy 1: Time Formatting
**Location**: In 6+ prompt files (lines 332-353)

**What Prompts Say**:
```text
- Always use 12-hour format with am/pm
- Convert 24h to 12h
- Include minutes
- Examples: "4:00" as "4:00 pm"
```

**What Should Happen**:
- ✅ PROMPT: "Present time clearly to user"
- ✅ CODE: Function `format_time_12h()` handles conversion
- ❌ REMOVE: All examples and conversion logic from prompts

### Redundancy 2: Symbol Restrictions
**Location**: In 6+ prompt files (lines 350-367)

**What Prompts Say**:
```text
MUST NOT USE ASTERISK (*)
MUST NOT USE DASH (-)
MUST NOT USE HASH (#)
Do not add quotation marks
Do not add emojis
```

**What Should Happen**:
- ✅ PROMPT: "Keep responses clean for voice output"
- ✅ CODE: Function `sanitize_response()` removes symbols
- ❌ REMOVE: Detailed symbol lists from prompts

### Redundancy 3: Abbreviation Expansion
**Location**: In 6+ prompt files (lines 341-344)

**What Prompts Say**:
```text
Instead of "Ave" present as "avenue"
Instead of "MD" present as "Maryland"
Example: 'Rd' means Road
```

**What Should Happen**:
- ✅ PROMPT: "Use clear language for voice"
- ✅ CODE: Dictionary lookup replaces abbreviations
- ❌ REMOVE: All examples from prompts

### Redundancy 4: Address Validation Steps
**Location**: In all booking prompts

**What Prompts Say**:
```text
1. Check if address has street
2. Check if address is valid
3. Check match percentage > 80%
4. Check if within service area
```

**What Should Happen**:
- ✅ PROMPT: "Collect address and verify it"
- ✅ PYDANTIC: `AddressModel` validates structure
- ✅ CODE: Validation function checks service area
- ❌ REMOVE: Detailed validation steps from prompts

## ✅ Optimization Plan

### Step 1: Create Response Formatter (Code)
```python
# File: response_formatters.py

def format_for_tts(text: str) -> str:
    """Complete formatting for text-to-speech"""
    # Remove symbols
    text = re.sub(r'[*#"]', '', text)
    
    # Expand abbreviations
    text = expand_abbreviations(text)
    
    # Format time
    text = format_times_in_text(text)
    
    return text
```

### Step 2: Use Pydantic Validation (Before Agent Calls)
```python
# In helper_functions.py

async def process_pickup_address(address: str):
    # Validate with Pydantic
    try:
        validated = AddressModel.parse_raw(address)
    except ValidationError:
        return "Invalid address format"
    
    # Then call agent
    # Agent doesn't need to validate structure
```

### Step 3: Simplify Prompts

**Before** (100+ lines of formatting rules):
```text
# Time Format Guidelines:
   - Always communicate times to riders using 12-hour format
   - Convert any 24-hour format times to 12-hour format
   [examples...]

# Pronunciation Guidelines:
  - When presenting abbreviations, use complete word
    Example: Instead of "Ave"...
    [more examples...]

# Symbol Guidelines:
    MUST NOT USE ASTERISK (*)
    MUST NOT USE DASH (-)
    [more rules...]
```

**After** (10 lines):
```text
# Output Guidelines
- Responses are automatically formatted for clear voice delivery
- System handles time formatting, symbol removal, and abbreviation expansion
- Focus on clear communication and accurate information
```

## 📋 Implementation Checklist

### Phase 1: Create Utilities
- [ ] Create `response_formatters.py`
- [ ] Add `sanitize_response()` function
- [ ] Add `expand_abbreviations()` function  
- [ ] Add `format_time_12h()` function
- [ ] Add `format_for_tts()` main function

### Phase 2: Update Code
- [ ] Integrate formatter in `main.py` or agent output
- [ ] Use Pydantic models for validation before agent calls
- [ ] Add automatic formatting to all agent responses

### Phase 3: Update Prompts
- [ ] Remove time format guidelines from all prompts
- [ ] Remove symbol guidelines from all prompts
- [ ] Remove pronunciation guidelines from all prompts
- [ ] Add short note about automatic formatting
- [ ] Keep conversation flow logic

### Phase 4: Test
- [ ] Test formatting functions work correctly
- [ ] Test prompts still guide agent properly
- [ ] Test agent responses are properly formatted
- [ ] Verify Pydantic validation catches errors

## 🎯 Expected Results

### Prompt File Size
- **Before**: ~420 lines
- **After**: ~320 lines
- **Reduction**: ~25%

### Maintainability
- **Before**: Update 6 files for formatting changes
- **After**: Update 1 code file for formatting changes

### Clarity
- **Before**: Mixing conversation logic with formatting rules
- **After**: Clear separation - prompts = logic, code = formatting

### Validation
- **Before**: LLM tries to validate data
- **After**: Pydantic validates, LLM focuses on conversation

---

**Status**: Ready to implement optimization!

