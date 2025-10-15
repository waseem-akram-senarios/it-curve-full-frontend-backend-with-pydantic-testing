#!/bin/bash

# LiveKit Voice Agent Startup Script with Model Cache
# This script fixes voice cancellation and latency issues

echo "🚀 Starting LiveKit Voice Agent with Model Cache"
echo "================================================"

# Set model cache directory
export LIVEKIT_CACHE_DIR=/home/senarios/.cache/livekit

# Additional LiveKit optimizations
export LIVEKIT_AGENTS_ENABLE_TURN_DETECTOR=true
export LIVEKIT_AGENTS_ENABLE_VAD=true

echo "✅ Environment variables set:"
echo "   LIVEKIT_CACHE_DIR: $LIVEKIT_CACHE_DIR"
echo "   LIVEKIT_AGENTS_ENABLE_TURN_DETECTOR: $LIVEKIT_AGENTS_ENABLE_TURN_DETECTOR"
echo "   LIVEKIT_AGENTS_ENABLE_VAD: $LIVEKIT_AGENTS_ENABLE_VAD"

# Navigate to agent directory
cd VoiceAgent3/IT_Curves_Bot

echo ""
echo "🔊 Starting voice agent..."
echo "💡 Models will be downloaded automatically on first use"
echo "💡 This will fix voice cancellation and latency issues"
echo ""

# Run the agent
python3 main.py

echo ""
echo "🛑 Agent stopped"
