#!/bin/bash

# =============================================================================
# SIMPLE PROJECT STARTUP SCRIPT
# =============================================================================
# Simplified version that focuses on getting the core services running

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 SIMPLE PROJECT STARTUP${NC}"
echo "=========================="

# Project directory
PROJECT_DIR="/home/senarios/VoiceAgent5withFeNew"
AGENT_DIR="$PROJECT_DIR/VoiceAgent3/IT_Curves_Bot"
FRONTEND_DIR="$PROJECT_DIR/ncs_pvt-virtual-agent-frontend-2c4b49def913"

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    echo "🛑 Killing processes on port $port..."
    fuser -k ${port}/tcp 2>/dev/null || true
    sleep 2
}

# Clean up existing processes
echo "🧹 Cleaning up existing processes..."
ports=(8000 3000 11000)
for port in "${ports[@]}"; do
    if check_port $port; then
        kill_port $port
    fi
done

# Kill any remaining processes
pkill -f "python3 main.py" 2>/dev/null || true
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
sleep 3

echo "✅ Cleanup complete"

# Create logs directory
mkdir -p logs

# Start Validation API
echo "🚀 Starting Validation API..."
cd "$PROJECT_DIR"
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level warning > logs/validation_api.log 2>&1 &
VALIDATION_PID=$!

# Wait for Validation API
echo "⏳ Waiting for Validation API..."
for i in {1..10}; do
    if curl -s http://localhost:8000/docs >/dev/null 2>&1; then
        echo "✅ Validation API ready (PID: $VALIDATION_PID)"
        break
    fi
    echo "   Attempt $i/10..."
    sleep 2
done

# Start Voice Agent
echo "🎤 Starting Voice Agent..."
cd "$AGENT_DIR"

# Set environment variables
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

# Load environment variables from .env file
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Start voice agent
nohup python3 main.py dev > ../../logs/voice_agent_simple.log 2>&1 &
AGENT_PID=$!

echo "⏳ Waiting for Voice Agent to initialize..."
sleep 10

# Check if agent is still running
if ps -p $AGENT_PID > /dev/null; then
    echo "✅ Voice Agent started (PID: $AGENT_PID)"
else
    echo "❌ Voice Agent failed to start"
    echo "📝 Check logs/voice_agent_simple.log for details"
fi

# Start Frontend
echo "🌐 Starting Frontend..."
cd "$FRONTEND_DIR"

# Set frontend environment variables
export NEXT_PUBLIC_LIVEKIT_URL="wss://itcurvedev-8eikcg0z.livekit.cloud"

# Clear frontend cache
rm -rf .next

# Start frontend
nohup npm run dev > ../../logs/frontend_simple.log 2>&1 &
FRONTEND_PID=$!

echo "⏳ Waiting for Frontend..."
for i in {1..10}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo "✅ Frontend ready (PID: $FRONTEND_PID)"
        break
    fi
    echo "   Attempt $i/10..."
    sleep 3
done

echo ""
echo -e "${GREEN}🎉 STARTUP COMPLETE!${NC}"
echo "===================="
echo ""
echo "📋 Service URLs:"
echo "  • Validation API: http://localhost:8000/docs"
echo "  • Frontend: http://localhost:3000"
echo ""
echo "📝 Log Files:"
echo "  • Validation API: logs/validation_api.log"
echo "  • Voice Agent: logs/voice_agent_simple.log"
echo "  • Frontend: logs/frontend_simple.log"
echo ""
echo "🛑 To stop all services:"
echo "  pkill -f 'python3 main.py'"
echo "  pkill -f 'uvicorn app.main:app'"
echo "  pkill -f 'npm run dev'"
echo ""
echo -e "${BLUE}🚀 Ready to test!${NC}"


