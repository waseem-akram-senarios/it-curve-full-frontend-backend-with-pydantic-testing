# 🚀 Build Latest Images & Start Docker Compose

## 📋 COMPLETE COMMAND SEQUENCE

Copy and paste these commands one by one:

```bash
# Navigate to project directory
cd /home/senarios/VoiceAgent8.1

# Stop any running containers
sudo docker compose down --volumes --remove-orphans

# Build fresh images with latest changes (NO CACHE)
sudo docker compose build --no-cache

# Start services in detached mode
sudo docker compose up -d

# Check status
sudo docker compose ps

# View logs
sudo docker compose logs -f
```

---

## ⚡ ONE-LINER (All in one)

```bash
cd /home/senarios/VoiceAgent8.1 && sudo docker compose down --volumes --remove-orphans && sudo docker compose build --no-cache && sudo docker compose up -d && sudo docker compose ps
```

---

## 📊 STEP-BY-STEP BREAKDOWN

### Step 1: Stop Existing Containers
```bash
sudo docker compose down --volumes --remove-orphans
```
**What this does**: Stops and removes all containers and volumes

### Step 2: Build Fresh Images
```bash
sudo docker compose build --no-cache
```
**What this does**: Rebuilds backend and frontend with latest changes
- Backend: Latest prompts + validation middleware + response formatter
- Frontend: Latest frontend code

### Step 3: Start Services
```bash
sudo docker compose up -d
```
**What this does**: Starts services in background (detached mode)

### Step 4: Check Status
```bash
sudo docker compose ps
```
**Expected output**:
```
NAME                     STATUS          PORTS
voice-agent-backend      Up 30 seconds   0.0.0.0:11000->11000/tcp
voice-agent-frontend     Up 30 seconds   0.0.0.0:3000->3000/tcp
```

---

## 🔍 VERIFY IT'S WORKING

### Check Logs:
```bash
# Backend logs
sudo docker compose logs backend | tail -50

# Frontend logs  
sudo docker compose logs frontend | tail -50

# All logs together
sudo docker compose logs -f
```

### Check Health:
```bash
curl http://localhost:11000/health
```

### Access Services:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:11000

---

## 🧪 TEST YOUR LATEST CHANGES

After starting, test:

### 1. "Nearest Coffee Shop" Test
Open http://localhost:3000 and try:
- "I want to book a ride"
- Pickup: "8700 snouffer school road gaithersburg maryland"
- Dropoff: "nearest coffee shop"
- **Expected**: Agent searches and finds coffee shops ✅

### 2. Address Validation Test
Try incomplete address:
- "Main Street"
- **Expected**: Validation error, asks for complete address ✅

### 3. Booking Flow Test
Complete booking with valid data
- **Expected**: Trip booked successfully ✅

---

## 🎯 WHAT'S IN LATEST BUILD

### Backend Container Includes:
✅ All 8 optimized prompts  
✅ Validation middleware  
✅ Response formatters  
✅ Enhanced helper_functions.py  
✅ All latest code changes  

### Frontend Container Includes:
✅ Latest frontend code  
✅ Environment variables  
✅ API connections  

---

**Ready to Build**: Run the commands above!

