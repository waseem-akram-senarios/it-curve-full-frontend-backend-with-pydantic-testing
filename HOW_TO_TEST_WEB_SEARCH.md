# How to Test Web Search Feature - Complete Guide

## ✅ What Was Fixed

- **Prompts Updated**: All 3 prompt files now force web search for vague location requests
- **Web Search Code**: Working and tested successfully
- **Tests**: 24/24 compliance tests passing

## 🚀 How to Start Your Agent

### Option 1: Using Docker Compose

```bash
# Navigate to your project
cd /home/senarios/VoiceAgent8.1

# Start the services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Option 2: Direct Python (for testing)

```bash
cd IT_Curves_Bot
python3 main.py dev
```

## 🧪 Testing the Web Search Feature

### Test Scenario 1: "Nearest Coffee Shop"

**Step-by-Step**:
1. Call the agent
2. **Greeting**: Wait for agent to finish greeting
3. **Say**: "I want to book a ride"
4. **Pickup Location**: "8700 snouffer school road gaithersburg maryland"
5. **When asked for dropoff, say**: "nearest coffee shop"

**✅ Expected Behavior** (After the fix):
```
👤 You: "nearest coffee shop"
🤖 Agent: "Let me search that for you."
         *[search_web function called]*
🤖 Agent: "I found Coffee Republic at 801 Pleasant Dr, Rockville, MD. 
           Is that the location you want?"
```

**❌ OLD Behavior** (Before fix - should NOT happen):
```
👤 You: "nearest coffee shop"
🤖 Agent: "I can't book rides to general places..."
         ❌ WRONG
```

### Test Scenario 2: "You Can Search Online"

**Step-by-Step**:
1. Call the agent
2. Say: "I want to book a ride"
3. Pickup: "8700 snouffer school road gaithersburg maryland"
4. Dropoff: "nearest restaurant"
5. Agent says can't find it
6. **You say**: "you can search online for that"

**✅ Expected Behavior**:
```
👤 You: "you can search online for that"
🤖 Agent: "Let me search that for you."
         *[search_web function called]*
🤖 Agent: *presents found restaurants*
```

**❌ OLD Behavior** (should NOT happen):
```
🤖 Agent: "I can't search online for locations"
         ❌ WRONG
```

### Test Scenario 3: Direct Web Search

**Step-by-Step**:
1. Call the agent
2. Say: "I want to book a ride"
3. Pickup: "8700 snouffer school road gaithersburg maryland"
4. Dropoff: "find me a Starbucks near me"

**✅ Expected**:
- Agent searches online
- Finds Starbucks locations
- Presents options to you
- Books the ride

## 🔍 How to Verify It's Working

### Signs Web Search is Working:

1. **Agent Says**: "Let me search that for you"
2. **Agent Doesn't Say**: "I can't search online" or "can't book rides to general places"
3. **Agent Presents**: Multiple location options with addresses
4. **Agent Asks**: "Which one do you prefer?" or "Is this the correct location?"

### Check Logs:

```bash
# Check backend logs
docker compose logs backend | grep search_web

# Or if running Python directly
# Look for logs showing:
# "Called search_web function"
# "Web search successful"
```

### What to Look For in Logs:

```
✅ Good: "Called search_web function"
✅ Good: "Web search payload: Find nearest coffee shop..."
✅ Good: "Found locations: Coffee Republic, Java Nation..."
❌ Bad: "I can't search online" (shouldn't happen)
❌ Bad: "I can't book rides to general places" (shouldn't happen)
```

## 📋 Test Checklist

Use this checklist to verify the fix:

- [ ] Agent doesn't reject "nearest coffee shop"
- [ ] Agent says "Let me search that for you"
- [ ] Agent calls search_web function (check logs)
- [ ] Agent returns location results
- [ ] Agent presents options to choose from
- [ ] Agent confirms selection with user
- [ ] Booking continues successfully
- [ ] Ride is booked with correct location

## 🐛 Troubleshooting

### If Agent Still Rejects:

1. **Check if prompts were updated**:
```bash
grep -n "NEVER reject vague" IT_Curves_Bot/prompts/prompt_new_rider.txt
```
Should show lines 33-37

2. **Restart the agent** (docker compose down && docker compose up -d)

3. **Check which prompt is being used**:
```bash
grep "instructions=" main.py
```

### If Search Doesn't Work:

1. **Check OpenAI API key** in `.env` file
2. **Check logs** for search errors
3. **Verify search_web function** exists in helper_functions.py

## 📊 Summary

**What You Fixed**:
- ✅ Prompts updated to force web search
- ✅ "NEVER reject vague location requests" added
- ✅ Code working (tested successfully)

**How to Test**:
1. Start agent
2. Say "nearest coffee shop" when asked for destination
3. Agent should search and find locations
4. Agent should present options and book ride

**Expected Result**:
- ✅ Agent searches instead of rejecting
- ✅ Finds locations (Coffee Republic, etc.)
- ✅ Books ride successfully

---

**Status**: Ready to Test ✅
**The agent will now search for "nearest coffee shop"!**

