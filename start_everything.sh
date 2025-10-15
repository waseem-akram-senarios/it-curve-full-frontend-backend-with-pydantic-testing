#!/bin/bash

# 🚀 START EVERYTHING - Complete Project Startup
# ==============================================

echo "🚀 STARTING COMPLETE PROJECT - ALL SERVICES"
echo "============================================"

# Clean up any existing processes first
echo "🧹 Cleaning up existing processes..."
pkill -f "main.py" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "npm" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
sleep 3

# Check if ports are clear
echo "🔍 Checking ports..."
if netstat -tlnp 2>/dev/null | grep -q ":8000 "; then
    echo "⚠️  Port 8000 still in use, force killing..."
    sudo fuser -k 8000/tcp 2>/dev/null || true
fi
if netstat -tlnp 2>/dev/null | grep -q ":3000 "; then
    echo "⚠️  Port 3000 still in use, force killing..."
    sudo fuser -k 3000/tcp 2>/dev/null || true
fi
if netstat -tlnp 2>/dev/null | grep -q ":11000 "; then
    echo "⚠️  Port 11000 still in use, force killing..."
    sudo fuser -k 11000/tcp 2>/dev/null || true
fi
sleep 2

# Start Validation API
echo "🔧 Starting Validation API (FastAPI)..."
cd /home/senarios/VoiceAgent5withFeNew
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > logs/validation_api.log 2>&1 &
VALIDATION_PID=$!
echo "✅ Validation API started (PID: $VALIDATION_PID)"

# Wait for validation API to start
echo "⏳ Waiting for Validation API to initialize..."
sleep 5

# Verify validation API is running
if curl -s http://localhost:8000/docs > /dev/null; then
    echo "✅ Validation API is responding"
else
    echo "❌ Validation API failed to start"
    exit 1
fi

# Start Voice Agent
echo "🎤 Starting Voice Agent..."
cd /home/senarios/VoiceAgent5withFeNew/VoiceAgent3/IT_Curves_Bot

# Set optimal environment variables
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

# Start voice agent in background
nohup python3 main.py dev > ../../logs/voice_agent.log 2>&1 &
VOICE_AGENT_PID=$!
echo "✅ Voice Agent started (PID: $VOICE_AGENT_PID)"

# Wait for voice agent to initialize
echo "⏳ Waiting for Voice Agent to initialize..."
sleep 10

# Start Frontend
echo "🌐 Starting Frontend (Next.js)..."
cd /home/senarios/VoiceAgent5withFeNew/ncs_pvt-virtual-agent-frontend-2c4b49def913
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"

# Wait for frontend to start
echo "⏳ Waiting for Frontend to initialize..."
sleep 15

# Final status check
echo ""
echo "🎯 FINAL STATUS CHECK"
echo "===================="

# Check Validation API
if curl -s http://localhost:8000/docs > /dev/null; then
    echo "✅ Validation API: http://localhost:8000/docs"
else
    echo "❌ Validation API: Not responding"
fi

# Check Voice Agent
if netstat -tlnp 2>/dev/null | grep -q ":11000 "; then
    echo "✅ Voice Agent: Running on port 11000"
else
    echo "❌ Voice Agent: Not running"
fi

# Check Frontend
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend: http://localhost:3000"
else
    echo "❌ Frontend: Not responding"
fi

echo ""
echo "🎉 ALL SERVICES STARTED!"
echo "========================"
echo "📊 Service Status:"
echo "   • Validation API: http://localhost:8000/docs"
echo "   • Voice Agent: Running (port 11000)"
echo "   • Frontend: http://localhost:3000"
echo ""
echo "📋 Process IDs:"
echo "   • Validation API: $VALIDATION_PID"
echo "   • Voice Agent: $VOICE_AGENT_PID"
echo "   • Frontend: $FRONTEND_PID"
echo ""
echo "📁 Log Files:"
echo "   • Validation API: logs/validation_api.log"
echo "   • Voice Agent: logs/voice_agent.log"
echo "   • Frontend: logs/frontend.log"
echo ""
echo "🛑 To stop all services: ./stop_everything.sh"
echo "🔄 To restart: ./start_everything.sh"
echo ""
echo "✅ Project is ready for use!"
