# Quick Testing Instructions

## 🚀 Starting Your Agent

Choose one method:

### Method 1: Docker Compose (Recommended)

```bash
cd /home/senarios/VoiceAgent8.1
docker compose up
```

### Method 2: Direct Python

```bash
cd IT_Curves_Bot
python3 main.py dev
```

## 🧪 Test the Fix

### Simple Test Conversation:

```
👤 You: "Hello"
🤖 Agent: "Hello! My name is Alina..."

👤 You: "I want to book a ride"
🤖 Agent: "Where should I pick you up?"

👤 You: "8700 snouffer school road gaithersburg maryland"
🤖 Agent: "Where are you headed?"

👤 You: "nearest coffee shop"  ⬅️ TEST THIS

✅ EXPECTED: Agent says "Let me search that for you"
✅ EXPECTED: Agent presents location options
✅ EXPECTED: Booking continues successfully

❌ OLD BEHAVIOR: Agent rejects "I can't book rides to general places"
```

## 🎯 What Was Fixed

1. **Prompts Updated**: 3 files (prompt_new_rider.txt, prompt_old_rider.txt, prompt_widget.txt)
2. **Added Instructions**: "NEVER reject vague location requests"
3. **Forces Web Search**: Agent must use [search_web] function

## ✅ Verification

If working correctly, you should see:
- Agent says "Let me search that for you"
- Agent finds locations (Coffee Republic, etc.)
- Agent asks which location you want
- Ride books successfully

If NOT working, you'll see:
- Agent says "I can't book rides to general places"
- Agent says "I can't search online"
- Agent rejects the request

---

**Ready**: Start your agent and test with "nearest coffee shop"!

