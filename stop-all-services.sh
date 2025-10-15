#!/bin/bash

# Stop All VoiceAgent Services
# This script stops all running VoiceAgent services

set -e

PROJECT_ROOT="/home/senarios/VoiceAgent5withFeNew"

echo "🛑 Stopping All VoiceAgent Services"
echo "================================="

# Function to stop service by PID file
stop_service_by_pid() {
    local service_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "🛑 Stopping $service_name (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 2
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
            echo "✅ $service_name stopped"
        else
            echo "⚠️  $service_name was not running"
        fi
        rm -f "$pid_file"
    else
        echo "⚠️  No PID file found for $service_name"
    fi
}

# Stop services by PID files
cd "$PROJECT_ROOT"

echo "📡 Stopping NEMT Validation API..."
stop_service_by_pid "NEMT Validation API" "logs/validation_api.pid"

echo "🤖 Stopping Backend LiveKit Agent..."
stop_service_by_pid "Backend LiveKit Agent" "logs/backend_agent.pid"

echo "🌐 Stopping Frontend Next.js..."
stop_service_by_pid "Frontend Next.js" "logs/frontend.pid"

# Kill any remaining processes
echo "🧹 Cleaning up any remaining processes..."
pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
pkill -f "python.*main.py.*start" 2>/dev/null || true
pkill -f "npm.*dev" 2>/dev/null || true
pkill -f "next.*dev" 2>/dev/null || true
pkill -f "node.*next" 2>/dev/null || true

# Wait a moment
sleep 2

# Force kill if any still running
ps aux | grep -E "(uvicorn|python.*main.py|npm.*dev|next.*dev)" | grep -v grep | awk '{print $2}' | xargs -r sudo kill -9 2>/dev/null || true

echo ""
echo "✅ All services stopped successfully!"
echo ""
echo "🔍 Checking for any remaining processes..."
remaining=$(ps aux | grep -E "(uvicorn|python.*main.py|npm.*dev|next.*dev)" | grep -v grep | wc -l)
if [ "$remaining" -eq 0 ]; then
    echo "✅ No remaining processes found"
else
    echo "⚠️  $remaining processes still running:"
    ps aux | grep -E "(uvicorn|python.*main.py|npm.*dev|next.*dev)" | grep -v grep
fi

echo ""
echo "🎯 To start services again, run: ./start-with-two-tier-validation.sh"
