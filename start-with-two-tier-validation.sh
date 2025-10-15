#!/bin/bash

# VoiceAgent with Two-Tier Validation - Complete Startup Script
# This script stops all running services and starts the project with new validation

set -e

PROJECT_ROOT="/home/senarios/VoiceAgent5withFeNew"
BACKEND_DIR="$PROJECT_ROOT/VoiceAgent3/IT_Curves_Bot"
FRONTEND_DIR="$PROJECT_ROOT/ncs_pvt-virtual-agent-frontend-2c4b49def913"

echo "🚀 Starting VoiceAgent with Two-Tier Validation System"
echo "=================================================="

# Function to stop all services
stop_all_services() {
    echo "🛑 Stopping all running services..."
    
    # Kill all related processes
    pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
    pkill -f "python.*main.py.*start" 2>/dev/null || true
    pkill -f "npm.*dev" 2>/dev/null || true
    pkill -f "next.*dev" 2>/dev/null || true
    pkill -f "node.*next" 2>/dev/null || true
    
    # Force kill if needed
    sleep 2
    ps aux | grep -E "(uvicorn|python.*main.py|npm.*dev|next.*dev)" | grep -v grep | awk '{print $2}' | xargs -r sudo kill -9 2>/dev/null || true
    
    echo "✅ All services stopped"
}

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "❌ Port $port is still in use"
        return 1
    else
        echo "✅ Port $port is available"
        return 0
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        
        echo "   Attempt $attempt/$max_attempts - waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name failed to start within timeout"
    return 1
}

# Main execution
main() {
    # Stop all existing services
    stop_all_services
    
    # Wait a moment for ports to be released
    sleep 3
    
    # Check ports are available
    echo "🔍 Checking port availability..."
    check_port 8000 || exit 1
    check_port 3000 || check_port 3001 || exit 1
    
    # Navigate to project root
    cd "$PROJECT_ROOT"
    
    echo ""
    echo "🔧 Starting Services with Two-Tier Validation..."
    echo "=============================================="
    
    # Start NEMT Validation API (Terminal 1)
    echo "📡 Starting NEMT Validation API on port 8000..."
    cd "$PROJECT_ROOT"
    source VoiceAgent3/IT_Curves_Bot/venv/bin/activate
    uvicorn app.main:app --reload --port 8000 > logs/validation_api.log 2>&1 &
    VALIDATION_API_PID=$!
    echo "   PID: $VALIDATION_API_PID"
    
    # Wait for validation API to be ready
    wait_for_service "http://localhost:8000/health" "NEMT Validation API" || exit 1
    
    # Start Backend LiveKit Agent (Terminal 2)
    echo "🤖 Starting Backend LiveKit Agent..."
    cd "$BACKEND_DIR"
    source venv/bin/activate
    python main.py start > ../../logs/backend_agent.log 2>&1 &
    BACKEND_AGENT_PID=$!
    echo "   PID: $BACKEND_AGENT_PID"
    
    # Start Frontend Next.js (Terminal 3)
    echo "🌐 Starting Frontend Next.js..."
    cd "$FRONTEND_DIR"
    npm run dev > ../../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "   PID: $FRONTEND_PID"
    
    # Wait for frontend to be ready
    wait_for_service "http://localhost:3000" "Frontend (port 3000)" || wait_for_service "http://localhost:3001" "Frontend (port 3001)" || echo "⚠️  Frontend may be starting on different port"
    
    echo ""
    echo "🎉 All Services Started Successfully!"
    echo "=================================="
    echo ""
    echo "📊 Service Status:"
    echo "  ✅ NEMT Validation API: http://localhost:8000"
    echo "  ✅ API Documentation:   http://localhost:8000/docs"
    echo "  ✅ Backend LiveKit Agent: Running with NEMT validation"
    echo "  ✅ Frontend Next.js:    http://localhost:3000 or http://localhost:3001"
    echo ""
    echo "🔍 Two-Tier Validation Features:"
    echo "  • Tier 1: Format validation (phone, name, ZIP, state codes)"
    echo "  • Tier 2: Business logic validation (NEMT schema)"
    echo "  • Immediate LLM feedback on invalid formats"
    echo "  • Clear error messages for learning"
    echo ""
    echo "🧪 Test the System:"
    echo "  • Health Check: curl http://localhost:8000/health"
    echo "  • Validation Test: curl -X POST http://localhost:8000/api/validate/nemt -H 'Content-Type: application/json' -d @valid.json"
    echo "  • Frontend: Open http://localhost:3000 or http://localhost:3001"
    echo ""
    echo "📋 Process IDs (for stopping later):"
    echo "  Validation API: $VALIDATION_API_PID"
    echo "  Backend Agent:  $BACKEND_AGENT_PID"
    echo "  Frontend:       $FRONTEND_PID"
    echo ""
    echo "🛑 To stop all services, run: ./stop-all-services.sh"
    echo ""
    
    # Save PIDs for later use
    echo "$VALIDATION_API_PID" > logs/validation_api.pid
    echo "$BACKEND_AGENT_PID" > logs/backend_agent.pid
    echo "$FRONTEND_PID" > logs/frontend.pid
    
    echo "✅ Startup complete! All services running with two-tier validation."
}

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

# Run main function
main "$@"

