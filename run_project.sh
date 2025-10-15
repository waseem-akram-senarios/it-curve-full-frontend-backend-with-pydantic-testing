#!/bin/bash

# 🚀 RUN PROJECT - Simple Startup Script
# ======================================

echo "🚀 STARTING VOICE AGENT PROJECT"
echo "================================"

# Kill any existing processes
echo "🧹 Cleaning up..."
pkill -f "python3 main.py" 2>/dev/null
pkill -f "uvicorn.*8000" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
pkill -f "next-server" 2>/dev/null
fuser -k 11000/tcp 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 3000/tcp 2>/dev/null || true
sleep 3

# Start Validation API
echo "🔧 Starting Validation API..."
cd /home/senarios/VoiceAgent5withFeNew
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level warning &
sleep 3

# Start Voice Agent
echo "🎤 Starting Voice Agent..."
cd /home/senarios/VoiceAgent5withFeNew/VoiceAgent3/IT_Curves_Bot

# Load environment variables
export $(grep -v '^#' ../../.env | xargs)

# Set optimizations
export LIVEKIT_CACHE_DIR=/home/senarios/.cache/livekit
export LIVEKIT_AGENTS_ENABLE_TURN_DETECTOR=true
export LIVEKIT_AGENTS_ENABLE_VAD=true
export LIVEKIT_AGENTS_ENABLE_NOISE_CANCELLATION=true
export LIVEKIT_AUDIO_SAMPLE_RATE=16000
export LIVEKIT_AUDIO_CHANNELS=1
export LIVEKIT_AUDIO_BIT_DEPTH=16
export LIVEKIT_LOG_LEVEL=WARNING
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1

python3 main.py start &
sleep 5

# Start Frontend with correct LiveKit URL
echo "🌐 Starting Frontend..."
cd /home/senarios/VoiceAgent5withFeNew/ncs_pvt-virtual-agent-frontend-2c4b49def913
NEXT_PUBLIC_LIVEKIT_URL=ws://localhost:11000 npm run dev &
sleep 10

echo ""
echo "🎉 PROJECT IS RUNNING!"
echo "======================"
echo "✅ Validation API: http://localhost:8000/docs"
echo "✅ Voice Agent: Running on port 11000"
echo "✅ Frontend: http://localhost:3001 (or 3000)"
echo ""
echo "🎯 Ready to use!"
echo ""
echo "Press Ctrl+C to stop all services"

# Keep script running
trap 'echo ""; echo "🛑 Stopping services..."; pkill -f "python3 main.py"; pkill -f "uvicorn"; pkill -f "npm run dev"; echo "✅ All services stopped"; exit 0' INT

while true; do
    sleep 10
done
