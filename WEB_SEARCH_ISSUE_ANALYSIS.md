# Web Search Function Issue - Analysis

## Issue Identified

From the conversation with Sehar:
- **User**: "you can search online for that"  
- **Agent**: "I can't search online for locations"

**This is INCORRECT** - The agent SHOULD be able to search online!

## Root Cause Analysis

### Prompt Instructions Say: ✅ **YES, SEARCH**

Looking at the prompts (`prompt_widget.txt` line 112):
```text
If the rider wished to find a location like nearest shopping mall, cinema, McDonals etc, 
say: "Let me search this address for you." and use [search_web] function
```

**The prompt CLEARLY instructs** the agent to:
1. Say "Let me search this address for you"
2. Use the `[search_web]` function

### Available Functions ✅

The agent HAS a `search_web` function:
- Defined in `helper_functions.py` line 768
- Marked with `@function_tool()` decorator
- Designed to search for locations online

### Why Is Agent Not Using It?

From analyzing the codebase:

1. **Prompt Conflict**: Different prompts give different instructions
   - Some prompts say: "reject vague locations"
   - Other prompts say: "use search_web for landmarks"
   
2. **Agent's Decision**: Agent is choosing to REJECT instead of SEARCH

## Correct Behavior

When user says "nearest coffee shop" or "you can search online":
1. ✅ Agent should say: "Let me search that address for you"
2. ✅ Agent should call `[search_web]` function
3. ✅ Agent should present the found address
4. ✅ Agent should confirm with user

## Recommendation

### Update Agent Instructions

Add explicit guidance to the prompts:

```text
When rider requests vague locations or says "search online":
- IMMEDIATELY use [search_web] function
- Say "Let me search that for you"
- Present the results to the rider
- Ask for confirmation
- DO NOT reject the request
```

### Code Verification Needed

Check in `main.py` or the agent initialization:
- Is `search_web` properly registered as a function tool?
- Is it included in the agent's available tools?
- Are there any conditions that prevent it from being used?

## Test Case Created

Added to `tests/e2e/test_real_world_senarios.py`:
- `test_agent_web_search_capability` - Verifies agent should use search_web

## Expected Fix

1. Review prompt instructions for consistency
2. Ensure search_web is available in all scenarios
3. Update agent to prefer search over rejection
4. Add logging to track when search_web is/should be called

---

**Status**: Issue identified  
**Severity**: Medium (user experience impact)  
**Priority**: Should be fixed for better UX

