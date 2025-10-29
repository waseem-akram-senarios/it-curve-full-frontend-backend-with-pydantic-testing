# 🐳 How to Restart Docker Compose with Latest Changes

## 📋 Files Modified in This Session

### Prompts (8 files):
1. `IT_Curves_Bot/prompts/prompt_new_rider.txt` - Optimized (~46 lines removed)
2. `IT_Curves_Bot/prompts/prompt_old_rider.txt` - Optimized (~45 lines removed)
3. `IT_Curves_Bot/prompts/prompt_multiple_riders.txt` - Optimized (~42 lines removed)
4. `IT_Curves_Bot/prompts/prompt_widget.txt` - Optimized (~47 lines removed)
5. `IT_Curves_Bot/prompts/prompt_new_rider_ivr.txt` - Optimized
6. `IT_Curves_Bot/prompts/prompt_old_rider_ivr.txt` - Optimized
7. `IT_Curves_Bot/prompts/prompt_multiple_riders_ivr.txt` - Optimized
8. `IT_Curves_Bot/prompts/prompt_widget_ivr.txt` - Optimized

### Code (2 files):
1. `IT_Curves_Bot/helper_functions.py` - Enhanced with validation middleware
2. `IT_Curves_Bot/validation_middleware.py` - Created (new file)
3. `IT_Curves_Bot/response_formatters.py` - Created (new file, already existed)

### Test Framework (12+ files):
- Complete test directory structure created
- Fixtures, unit tests, E2E tests created

---

## 🚀 RESTART COMMANDS

Run these commands in your terminal:

```bash
cd /home/senarios/VoiceAgent8.1

# 1. Stop and remove containers
sudo docker compose down --volumes --remove-orphans

# 2. Rebuild images with latest changes
sudo docker compose build --no-cache

# 3. Start services
sudo docker compose up -d

# 4. Check status
sudo docker compose ps

# 5. View logs
sudo docker compose logs -f
```

---

## ✅ What Will Be Updated

### Backend Container Will Rebuild:
- ✅ Latest optimized prompts (8 files)
- ✅ Validation middleware integration
- ✅ Response formatter integration
- ✅ Enhanced helper_functions.py
- ✅ All latest code changes

### Frontend Container Will Rebuild:
- ✅ Latest frontend code (if any changes)

---

## 🎯 Expected Results

After restarting, you should see:
1. ✅ Both containers running
2. ✅ Backend on port 11000
3. ✅ Frontend on port 3000
4. ✅ Latest optimized prompts active
5. ✅ Validation middleware working
6. ✅ Response formatter active

---

## 🧪 Testing Your Changes

### Test "Nearest Coffee Shop" Scenario:
1. Open browser to `http://localhost:3000`
2. Start a conversation
3. Say: "I want to book a ride"
4. Pickup: "8700 snouffer school road gaithersburg maryland"
5. Dropoff: "nearest coffee shop"
6. **Expected**: Agent should search and find coffee shops
7. **Should NOT**: Say "I can't search online" or reject

---

## 📊 Verification

### After Restart, Verify:
```bash
# Check container logs for any errors
sudo docker compose logs backend | tail -50
sudo docker compose logs frontend | tail -50

# Check if containers are healthy
sudo docker compose ps

# Test the API
curl http://localhost:11000/health
```

---

## 🐛 Troubleshooting

### If containers fail to start:
```bash
# Check logs
sudo docker compose logs

# Check Docker daemon
sudo systemctl status docker

# Rebuild from scratch
sudo docker compose down --volumes
sudo docker compose build --no-cache
sudo docker compose up -d
```

---

**Status**: Ready for restart  
**Changes**: All 8 prompts optimized + validation + formatters  
**Next**: Run the sudo commands to restart

