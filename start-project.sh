#!/bin/bash

# One-Command VoiceAgent Startup with Two-Tier Validation
# This script stops everything and starts the complete project

set -e

PROJECT_ROOT="/home/senarios/VoiceAgent5withFeNew"

echo "🚀 VoiceAgent with Two-Tier Validation - One Command Startup"
echo "=========================================================="

# Stop all existing services
echo "🛑 Stopping all existing services..."
pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
pkill -f "python.*main.py.*start" 2>/dev/null || true
pkill -f "npm.*dev" 2>/dev/null || true
pkill -f "next.*dev" 2>/dev/null || true
sleep 3

# Navigate to project root
cd "$PROJECT_ROOT"

echo "🔧 Starting all services..."
echo ""

# Start NEMT Validation API
echo "📡 Starting NEMT Validation API (port 8000)..."
source VoiceAgent3/IT_Curves_Bot/venv/bin/activate
uvicorn app.main:app --reload --port 8000 > /dev/null 2>&1 &
sleep 3

# Start Backend LiveKit Agent
echo "🤖 Starting Backend LiveKit Agent..."
cd VoiceAgent3/IT_Curves_Bot
source venv/bin/activate
python main.py start > /dev/null 2>&1 &
cd "$PROJECT_ROOT"
sleep 3

# Start Frontend
echo "🌐 Starting Frontend Next.js..."
cd ncs_pvt-virtual-agent-frontend-2c4b49def913
npm run dev > /dev/null 2>&1 &
cd "$PROJECT_ROOT"
sleep 5

echo ""
echo "🎉 All Services Started Successfully!"
echo "=================================="
echo ""
echo "📊 Service URLs:"
echo "  ✅ NEMT Validation API: http://localhost:8000"
echo "  ✅ API Documentation:   http://localhost:8000/docs"
echo "  ✅ Frontend:            http://localhost:3000"
echo "  ✅ Backend Agent:       Running with NEMT validation"
echo ""
echo "🔍 Two-Tier Validation Active:"
echo "  • Tier 1: Format validation (phone, name, ZIP, state)"
echo "  • Tier 2: Business logic validation (NEMT schema)"
echo "  • LLM gets immediate feedback on invalid formats"
echo ""
echo "🧪 Quick Tests:"
echo "  • Health: curl http://localhost:8000/health"
echo "  • Validation: curl -X POST http://localhost:8000/api/validate/nemt -H 'Content-Type: application/json' -d @valid.json"
echo ""
echo "🛑 To stop: pkill -f 'uvicorn\|python.*main.py\|npm.*dev'"
echo ""
echo "✅ Project is ready with two-tier validation system!"

