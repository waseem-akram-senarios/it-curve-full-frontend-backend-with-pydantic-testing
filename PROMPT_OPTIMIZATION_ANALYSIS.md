# Prompt Optimization Analysis - Reducing Redundancy

## Current Situation Analysis

### What Prompts Are Handling (Should NOT be):
1. **Time format conversion** (24h → 12h) - Can be done by code
2. **Symbol restrictions** (*, #, -) - Can be handled by Pydantic/formatter
3. **Abbreviation expansion** (Ave → avenue, MD → Maryland) - Can be done by formatter
4. **Address format validation** - Should be handled by Pydantic models
5. **Phone number format validation** - Should be handled by Pydantic models
6. **Symbol guidelines** (no quotes, emojis) - Can be enforced in response formatter
7. **Time presentation rules** (include minutes) - Can be done by formatter

### What Pydantic Is Already Handling:
1. ✅ **Phone number validation** - `PhoneNumberModel` validates format
2. ✅ **Address validation** - `AddressModel` validates structure
3. ✅ **Coordinate validation** - `CoordinateModel` validates lat/lng ranges
4. ✅ **Type validation** - All models enforce correct types
5. ✅ **Length constraints** - Fields have min/max lengths
6. ✅ **Required fields** - Pydantic enforces required fields

### What Prompts Should Focus On:
1. **Conversation flow** - When to ask for what information
2. **User interaction** - How to ask questions
3. **Function calling logic** - When to call which function
4. **Error handling** - How to handle user responses
5. **Confirmations** - When and how to confirm
6. **Return trip logic** - When to ask
7. **Closing conversation** - Flow for ending calls

## Redundancies Identified

### 1. Time Format Guidelines (4+ locations in prompts)
**Current** (Duplicated in 6 prompt files):
```text
# Time Format Guidelines:
   - Always communicate times to riders using 12-hour format with am/pm indicators
   - Convert any 24-hour format times in your system to 12-hour format before responding
```

**Better**: Create a utility function `format_time_for_tts(time_str)` that handles this.
- Prompts: Focus on WHEN to present time, not HOW to format it

### 2. Symbol Guidelines (Duplicated across all prompts)
**Current**:
```text
# Symbol Guidelines:
    Do not add '"' (single or double quotations mark)
    Do not add emoji's in your response.
    MUST NOT USE ASTERISK (*) IN YOUR RESPONSE.
    MUST NOT USE DASH (-) IN YOUR RESPONSE.
    MUST NOT USE HASH (#) IN YOUR RESPONSE.
```

**Better**: Create a response sanitizer function that removes these symbols.
- Prompts: Just say "Keep responses clean for TTS"
- Code: Enforces it automatically

### 3. Pronunciation Guidelines (Duplicated everywhere)
**Current**:
```text
# Pronunciation Guidelines:
    Example: Instead of "Ave" (which TTS might read as "ave"), Present as "avenue"
    Example: Instead of "MD" (which TTS might read as "md"), Present as "Maryland"
```

**Better**: Create an abbreviation formatter dictionary.
- Prompts: Remove these examples
- Code: Automatically expands abbreviations

### 4. Address Collection Steps (Verification already in Pydantic)
**Current** (Long prompts):
```text
1. Ask: "Where are you headed?"
2. Confirm by repeating: "I got [address]. Is that correct?"
3. Call [get_valid_addresses] to validate
4. Check if 'isWithinServiceArea' is True
...
```

**Better**: Let Pydantic validate the address structure.
- Prompts: Focus on "Ask for address → Confirm → Call validation function"
- Pydantic: Handles structure validation automatically

## Optimization Plan

### Phase 1: Create Utility Functions (Code)
Create these utilities in `side_functions.py` or new `response_formatters.py`:

1. **Time Formatter**:
```python
def format_time_for_tts(time_str: str, include_minutes: bool = True) -> str:
    """Convert 24h to 12h format for TTS"""
    # Implementation
```

2. **Abbreviation Expander**:
```python
ABBREVIATIONS = {
    'Ave': 'Avenue',
    'Rd': 'Road', 
    'MD': 'Maryland',
    'ME': 'Maryland',  # Common typo
    ...
}

def expand_abbreviations(text: str) -> str:
    """Expand abbreviations for TTS"""
    for abbrev, full in ABBREVIATIONS.items():
        text = text.replace(abbrev, full)
    return text
```

3. **Response Sanitizer**:
```python
def sanitize_for_tts(response: str) -> str:
    """Remove symbols that TTS can't pronounce"""
    response = response.replace('*', '')
    response = response.replace('#', '')
    response = response.replace('"', '')
    response = response.replace("'", '')
    # Remove emojis
    return response
```

4. **Address Format Validator**:
```python
# Already have AddressModel in models.py
# Just use it to validate before sending to agent
```

### Phase 2: Update Prompts (Remove Redundancy)

**Before** (Long):
```text
# Time Format Guidelines:
   - Always communicate times to riders using 12-hour format with am/pm indicators
   - Convert any 24-hour format times in your system to 12-hour format before responding
   - Examples:
      Present "4:00" as "4:00 pm" (not 16:00)
      Present "14:00:00" as "2:00 pm"
      Present "09:30" as "9:30 am" (not 9:30)
   - Include minutes when available (e.g., "3:15 pm" rather than just "3 pm")
```

**After** (Short):
```text
# Time Format
- Always present times in 12-hour format with am/pm
- Time formatting is handled automatically by the system
```

### Phase 3: Leverage Pydantic Models

**Before** (Prompts handling validation):
```text
- If no valid address found, call [handle_invalid_address]
- check if 'isWithinServiceArea' for closest matching address is True
- If there is more than 80% match...
```

**After** (Let Pydantic validate first):
```python
# In helper_functions.py before calling agent:
try:
    validated_address = AddressModel(**address_data)
except ValidationError:
    # Handle invalid address
    return "Invalid address format"
```

## Recommendations

### 1. Create Response Formatter Module
**File**: `IT_Curves_Bot/response_formatters.py`

```python
"""Format agent responses for TTS"""

ABBREVIATIONS = {
    'Ave': 'Avenue',
    'Rd': 'Road',
    'MD': 'Maryland',
    'ME': 'Maryland',
    'St': 'Street',
    # Add more as needed
}

def sanitize_response(response: str) -> str:
    """Remove symbols that break TTS"""
    response = response.replace('*', '')
    response = response.replace('#', '')
    response = response.replace('-', ' ')  # Replace dash with space
    response = response.replace('"', '')
    response = response.replace("'", '')
    return response

def expand_abbreviations(text: str) -> str:
    """Expand abbreviations for better TTS"""
    for abbrev, full in ABBREVIATIONS.items():
        text = text.replace(abbrev, full)
    return text

def format_time_12h(time_str: str) -> str:
    """Convert time to 12-hour format for TTS"""
    # Implementation
    pass

def prepare_for_tts(response: str) -> str:
    """Complete formatting pipeline for TTS"""
    response = sanitize_response(response)
    response = expand_abbreviations(response)
    return response
```

### 2. Simplify Prompt Files

**Remove from prompts**:
- ❌ Time format conversion examples
- ❌ Symbol restriction lists
- ❌ Pronunciation examples
- ❌ Detailed formatting instructions

**Keep in prompts**:
- ✅ Conversation flow logic
- ✅ Function calling requirements
- ✅ Confirmation requirements
- ✅ Error handling procedures
- ✅ Return trip logic

### 3. Add Formatting to Helper Functions

Wrap agent responses before sending to TTS:
```python
# In main.py or helper_functions.py
def format_agent_response(response: str) -> str:
    from response_formatters import prepare_for_tts
    return prepare_for_tts(response)
```

## Expected Benefits

### Reduced Prompt Size
- **Before**: ~400 lines per prompt
- **After**: ~300 lines per prompt
- **Savings**: ~25% reduction

### Better Maintainability
- Formatting rules in ONE place (code)
- Easier to update formatting
- No need to update 6+ prompt files

### Clearer Separation
- **Prompts**: Handle conversation logic
- **Code**: Handle data validation & formatting

## Implementation Priority

### High Priority (Implement Now):
1. Create `response_formatters.py`
2. Add `sanitize_response()` function
3. Add `expand_abbreviations()` function
4. Update all prompts to remove formatting guidelines

### Medium Priority:
1. Add `format_time_12h()` function
2. Integrate with TTS output
3. Add Pydantic validation before function calls

### Low Priority:
1. Add more abbreviation expansions
2. Create formatter config file
3. Add unit tests for formatters

---

**Result**: Cleaner prompts focused on conversation flow, better maintainability, code handles formatting automatically!

