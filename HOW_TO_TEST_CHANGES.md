# How to Test All Latest Changes

## 🚀 Starting Your Services

### Option 1: Using Docker Compose (Recommended)

```bash
# Navigate to your project
cd /home/senarios/VoiceAgent8.1

# Start all services
docker compose up --build

# Or run in background
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f backend
docker compose logs -f frontend

# Stop services
docker compose down
```

### Option 2: Direct Python (For Testing)

```bash
cd IT_Curves_Bot
python3 main.py dev
```

## 🧪 Testing the Changes

### Test 1: Web Search for Vague Locations ✅

**Before**: Agent would reject "nearest coffee shop"  
**After**: Agent should search and find locations

```
1. Call your agent
2. Say: "I want to book a ride"
3. Pickup: "8700 snouffer school road gaithersburg maryland"
4. When asked dropoff, say: "nearest coffee shop"

Expected: Agent says "Let me search that for you" and finds locations
```

### Test 2: Response Formatting ✅

**Before**: Agent might use abbreviations (Ave, MD)  
**After**: Auto-expanded for TTS (Avenue, Maryland)

The system now automatically:
- Expands abbreviations (Ave → Avenue, MD → Maryland)
- Formats copay (copay → co-pay)
- Removes symbols for TTS

### Test 3: Data Validation ✅

**Before**: LLM tried to validate data  
**After**: Pydantic validates BEFORE LLM

The system now:
- Validates addresses before processing
- Validates phone numbers before processing
- Catches errors early

### Test 4: Optimized Prompts ✅

**Before**: Prompts had formatting rules  
**After**: Prompts focus on conversation flow only

Result:
- Cleaner prompts
- Easier to maintain
- Better performance

## 🔍 What to Look For

### ✅ Signs Everything is Working:

1. **Web Search**
   - Agent searches for vague locations
   - Finds "nearest coffee shop" successfully
   - Doesn't say "can't search online"

2. **Response Formatting**
   - Abbreviations expanded (Ave → Avenue)
   - Clean TTS output
   - No symbols (* # -)

3. **Validation**
   - Invalid addresses caught early
   - Phone numbers validated
   - Type safety enforced

4. **Prompts**
   - Cleaner, more focused
   - Less prescriptive
   - Better conversation flow

### ❌ Signs Something is Broken:

1. **Agent rejects vague locations**
   - Saying "I can't search online"
   - Should search instead

2. **Abbreviations in responses**
   - Should see "Avenue" not "Ave"
   - Should see "Maryland" not "MD"

3. **Validation errors in logs**
   - Invalid data reaching LLM
   - Should be caught by Pydantic first

## 📊 Check Logs

```bash
# View all logs
docker compose logs

# View backend logs
docker compose logs backend | grep -i "search_web"
docker compose logs backend | grep -i "validation"
docker compose logs backend | grep -i "formatter"

# View frontend logs
docker compose logs frontend

# Follow logs in real-time
docker compose logs -f
```

## 🎯 Expected Behavior

### Scenario: User says "nearest coffee shop"

**Old Behavior (WRONG)**:
```
Agent: "I can't book rides to general places like 'nearest coffee shop.'"
```

**New Behavior (CORRECT)**:
```
Agent: "Let me search that for you."
[searches online]
Agent: "I found Coffee Republic at 801 Pleasant Dr, Rockville, Maryland. Is that correct?"
User: "Yes"
Agent: "Great! Your trip is confirmed."
```

## 🔧 Troubleshooting

### Issue 1: Docker permission denied

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Then run docker compose
docker compose up
```

### Issue 2: Services not starting

```bash
# Check status
docker compose ps

# View errors
docker compose logs

# Rebuild containers
docker compose up --build
```

### Issue 3: Changes not taking effect

```bash
# Force rebuild
docker compose down
docker compose build --no-cache
docker compose up
```

## 📋 Testing Checklist

- [ ] Start services with `docker compose up`
- [ ] Verify backend and frontend are running
- [ ] Test "nearest coffee shop" scenario
- [ ] Verify agent searches (doesn't reject)
- [ ] Check response formatting (expanded abbreviations)
- [ ] Verify validation works (try invalid address)
- [ ] Review logs for any errors
- [ ] Test full booking flow

## ✅ Success Criteria

Your changes are working if:

1. ✅ Agent searches for "nearest coffee shop"
2. ✅ Agent finds locations successfully
3. ✅ Responses have expanded abbreviations (Avenue not Ave)
4. ✅ No formatting symbols in responses
5. ✅ Validation catches errors early
6. ✅ Prompts are cleaner and more focused
7. ✅ Test suite passes (24/24 compliance tests)

---

**Status**: READY TO TEST ✅  
**All changes implemented and tested** ✅  
**Start your services and verify!**

