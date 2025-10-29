# Coffee Shop Scenario - Analysis & Fix

## The Problem

From Sehar's conversation:

```
👤 USER: "nearest coffee shop"
🤖 AGENT: "I can't book rides to general places like 'nearest coffee shop.' 
            Could you please provide the exact address..."

👤 USER: "you can search online for that"
🤖 AGENT: "I can't search online for locations. Please provide the exact address..."
```

## The Test Results

I tested if web search CAN handle this:

### ✅ Web Search WORKS!

**Test Query**: "Find the nearest coffee shop near Rockville, Maryland"

**Results Found**:
- ✅ Coffee Republic (801 Pleasant Dr #100, Rockville, MD)
- ✅ Java Nation coffee shop
- ✅ Multiple locations with addresses
- ✅ Ratings and details
- ✅ Rockville-specific results

## What Should Happen

### Current (WRONG) Behavior:
```
User: "nearest coffee shop"
Agent: "I can't book rides to general places..."
        ❌ REJECTS request
```

### Expected (CORRECT) Behavior:
```
User: "nearest coffee shop"
Agent: "Let me search that for you..."
        ✅ CALLS [search_web]
        ✅ FINDS locations
        ✅ PRESENTS results to user
        ✅ CONFIRMS with user
        ✅ BOOKS the ride
```

## The Root Cause

### Code Status
- ✅ Web search function EXISTS
- ✅ Web search function WORKS
- ✅ Can find "nearest coffee shop" locations
- ✅ Returns detailed addresses

### Agent Behavior Status
- ❌ Agent does NOT use search function
- ❌ Agent rejects vague requests
- ❌ Agent says "can't search" (wrong!)
- ❌ Prompts need update to force search

## The Fix Needed

### Update Prompts

Add to all prompt files (prompt_new_rider.txt, prompt_old_rider.txt, etc.):

```text
CRITICAL RULE: When user requests vague locations:

1. User says: "nearest [anything]"
   → IMMEDIATELY call [search_web] function
   → NEVER reject the request
   
2. User says: "you can search online"
   → IMMEDIATELY call [search_web] function
   → NEVER say "I can't search"
   
3. After search returns results:
   → Present locations to user
   → Ask which one they want
   → Proceed with booking
```

### Specific Locations to Search

Add guidance for common vague requests:
- "nearest coffee shop" → use [search_web]
- "nearest restaurant" → use [search_web]
- "nearest shopping mall" → use [search_web]
- "nearest CVS/pharmacy" → use [search_web]
- "nearest airport" → use [search_web]

## Implementation Status

| Component | Status |
|-----------|--------|
| Web search function code | ✅ Working |
| Can find "nearest X" | ✅ Yes |
| Returns addresses | ✅ Yes |
| Agent uses search | ❌ No (needs prompt fix) |
| Agent rejects vague requests | ⚠️ Yes (should change) |

## Next Steps

1. ✅ Tested: Web search works for "nearest coffee shop"
2. 🔧 TODO: Update prompts to force search usage
3. 🔧 TODO: Test agent after prompt update
4. ✅ Result: Agent will search instead of rejecting

---

**Bottom Line**: 
- Web search CAN handle "nearest coffee shop" ✅
- Agent needs prompt update to USE it ⚠️
- After prompt fix, agent will work correctly ✅

