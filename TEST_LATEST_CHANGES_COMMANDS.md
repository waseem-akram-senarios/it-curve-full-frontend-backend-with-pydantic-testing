# 🧪 Commands to Test Latest Changes

## 🚀 START DOCKER COMPOSE

### Quick Start (Foreground - See Logs):
```bash
cd /home/senarios/VoiceAgent8.1
sudo docker compose up
```

### Start in Background (Detached):
```bash
cd /home/senarios/VoiceAgent8.1
sudo docker compose up -d

# Then view logs separately:
sudo docker compose logs -f
```

### View Status:
```bash
sudo docker compose ps
```

---

## 🧪 TEST LATEST CHANGES

### Test 1: "Nearest Coffee Shop" ⭐ CRITICAL TEST

**Scenario**: Test web search for vague locations

```
1. Open browser to http://localhost:3000
2. Start conversation
3. Say: "I want to book a ride"
4. Agent: "Where should I pick you up?"
5. You: "8700 snouffer school road gaithersburg maryland"
6. Agent: "Where are you headed?"
7. You: "nearest coffee shop"  ⭐ THIS IS THE TEST
```

**Expected Results**:
```
✅ Agent should say: "Let me search that for you."
✅ Agent should call search_web function
✅ Agent should find coffee shop locations
✅ Agent should offer options: "I found Coffee Republic at 801 Pleasant Dr, Rockville, MD. Is that correct?"

❌ SHOULD NOT say:
   - "I can't search online"
   - "I need a complete address"
   - "I don't have access to search"
```

### Test 2: Invalid Address Validation

**Test that validation middleware works**:

```
Agent: "Where should I pick you up?"
You: "Main Street"  ⭐ TOO VAGUE

Expected:
✅ Agent should catch error
✅ Should say: "Invalid address format. Please provide a complete address with street name and number"
```

### Test 3: Short Phone Number

**Test phone validation**:

```
Agent: "What's your phone number?"
You: "4567"  ⭐ TOO SHORT

Expected:
✅ Agent should catch error
✅ Should say: "Phone number must be at least 10 digits (you provided 4 digits)"
```

### Test 4: Valid Complete Booking

**Test full booking flow with optimized prompts**:

```
User: "I want to book a ride"
Pickup: "8700 snouffer school road gaithersburg maryland"
Dropoff: "Rockville Metro Station, Rockville, MD"
Time: "now"
Passengers: "1"
Payment: "cash"

Expected:
✅ All data validated automatically
✅ Trip booked successfully
✅ Trip number provided
```

---

## 📊 What Changed vs What to Verify

### What Changed:
1. ✅ Removed validation logic from prompts (~250 lines)
2. ✅ Added validation middleware (pre-validates inputs)
3. ✅ Added response formatter (TTS optimization)
4. ✅ Simplified address validation
5. ✅ Simplified payment flow

### What to Verify:
1. ✅ Agent searches for "nearest coffee shop" instead of rejecting
2. ✅ Agent catches invalid addresses automatically
3. ✅ Agent validates phone numbers
4. ✅ Agent responses are clean (no symbols for TTS)
5. ✅ Booking flow works smoothly

---

## 🔍 VERIFICATION COMMANDS

### Check Containers are Running:
```bash
sudo docker compose ps

# Expected:
# voice-agent-backend    Up    Port 11000
# voice-agent-frontend   Up    Port 3000
```

### Check Backend Logs:
```bash
sudo docker compose logs backend | grep -E "validation|optimized|get_valid_addresses"

# Should see:
# - Validation middleware working
# - Address validation logs
# - No errors
```

### Test Health Endpoint:
```bash
curl http://localhost:11000/health
# Expected: {"status":"ok"}
```

---

## 📝 NOTES

### Docker Compose Services:
- **Backend**: http://localhost:11000
- **Frontend**: http://localhost:3000

### Test URLs:
- Frontend: http://localhost:3000
- Backend Health: http://localhost:11000/health
- Backend Logs: `sudo docker compose logs backend`

### Key Improvements to Test:
1. **Web Search**: "nearest coffee shop" should work
2. **Validation**: Incomplete addresses rejected
3. **Response Quality**: Clean TTS output
4. **Error Handling**: User-friendly messages

---

**Ready to Test**: All changes are in place, just start Docker Compose!

