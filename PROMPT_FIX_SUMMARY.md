# Prompt Fix Summary - Web Search Now Enforced

## What I Fixed

Updated all 3 main prompt files to force the agent to use web search for vague location requests.

### Files Updated:
1. ✅ `prompt_new_rider.txt` (lines 33-37)
2. ✅ `prompt_old_rider.txt` (lines 61-65)
3. ✅ `prompt_widget.txt` (lines 112-116)

### Changes Made:

**Added CRITICAL instruction** to all prompts:

```text
CRITICAL: If the rider mentions vague locations like "nearest coffee shop", "nearest restaurant", 
"nearest anything", "you can search online", "find me a coffee shop", etc:

- IMMEDIATELY say: "Let me search that for you."
- IMMEDIATELY call [search_web] function
- NEVER reject vague location requests
- ALWAYS attempt to search first
```

## Expected New Behavior

### Before (Wrong):
```
👤 User: "nearest coffee shop"
🤖 Agent: "I can't book rides to general places..."
         ❌ REJECTS request
```

### After (Correct):
```
👤 User: "nearest coffee shop"  
🤖 Agent: "Let me search that for you."
         ✅ CALLS [search_web]
         ✅ FINDS: Coffee Republic, Java Nation, etc.
         ✅ SAYS: "I found Coffee Republic at 801 Pleasant Dr, Rockville, MD. Is that correct?"
         ✅ USER: "Yes"
         ✅ CONTINUES booking
```

## How to Test

1. Start the agent with updated prompts
2. Say: "I want to book a ride"
3. Provide pickup: "8700 snouffer school road gaithersburg maryland"
4. When asked for dropoff, say: "nearest coffee shop"
5. **Expected**: Agent should say "Let me search that for you" and call [search_web]
6. **Expected**: Agent presents search results
7. **Expected**: Agent asks which location you want
8. **Expected**: Booking continues successfully

## Next Steps

The prompts are now updated with strong instructions to use web search.

**To test it:**
1. Restart your agent with the updated prompts
2. Have a conversation with the "nearest coffee shop" scenario
3. Verify agent uses [search_web] function
4. Verify agent presents results
5. Verify booking completes successfully

---

**Status**: Prompts updated ✅  
**Ready**: To test with real agent ✅

