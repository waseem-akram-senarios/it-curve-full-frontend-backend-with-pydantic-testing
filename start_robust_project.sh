#!/bin/bash

# =============================================================================
# ROBUST PROJECT STARTUP SCRIPT
# =============================================================================
# This script provides a comprehensive solution to prevent booking issues
# by implementing multiple layers of protection and monitoring

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="/home/senarios/VoiceAgent5withFeNew"
AGENT_DIR="$PROJECT_DIR/VoiceAgent3/IT_Curves_Bot"
FRONTEND_DIR="$PROJECT_DIR/ncs_pvt-virtual-agent-frontend-2c4b49def913"

echo -e "${PURPLE}🚀 ROBUST VOICE AGENT PROJECT STARTUP${NC}"
echo -e "${PURPLE}=====================================${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

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
    print_status "Killing processes on port $port..."
    fuser -k ${port}/tcp 2>/dev/null || true
    sleep 2
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start within timeout"
    return 1
}

# Function to check environment variables
check_env_vars() {
    print_status "Checking environment variables..."
    
    local env_file="$PROJECT_DIR/.env"
    if [ ! -f "$env_file" ]; then
        print_error "Environment file not found: $env_file"
        return 1
    fi
    
    # Check critical environment variables
    local critical_vars=(
        "TRIP_BOOKING_API"
        "LIVEKIT_URL"
        "LIVEKIT_API_KEY"
        "LIVEKIT_API_SECRET"
        "OPENAI_API_KEY"
    )
    
    for var in "${critical_vars[@]}"; do
        if ! grep -q "^$var=" "$env_file"; then
            print_warning "Missing environment variable: $var"
        fi
    done
    
    print_success "Environment variables checked"
}

# Function to setup model cache
setup_model_cache() {
    print_status "Setting up model cache..."
    
    local cache_dir="/home/senarios/.cache/livekit"
    mkdir -p "$cache_dir"
    
    # Set environment variables for voice cancellation
    export LIVEKIT_CACHE_DIR="$cache_dir"
    export LIVEKIT_AGENTS_ENABLE_TURN_DETECTOR=true
    export LIVEKIT_AGENTS_ENABLE_VAD=true
    export LIVEKIT_AGENTS_ENABLE_NOISE_CANCELLATION=true
    export LIVEKIT_AUDIO_SAMPLE_RATE=16000
    export LIVEKIT_AUDIO_CHANNELS=1
    export LIVEKIT_AUDIO_BIT_DEPTH=16
    export LIVEKIT_LOG_LEVEL=WARNING
    export PYTHONOPTIMIZE=1
    export PYTHONDONTWRITEBYTECODE=1
    
    print_success "Model cache setup complete"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    # Install Python dependencies
    cd "$PROJECT_DIR"
    if [ -f "requirements_validation.txt" ]; then
        pip3 install -r requirements_validation.txt --quiet
    fi
    
    # Install PyTorch for voice models
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet
    
    # Install frontend dependencies
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        npm install --silent
    fi
    
    print_success "Dependencies installed"
}

# Function to clean up processes
cleanup_processes() {
    print_status "Cleaning up existing processes..."
    
    # Kill processes on critical ports
    local ports=(8000 3000 11000)
    for port in "${ports[@]}"; do
        if check_port $port; then
            kill_port $port
        fi
    done
    
    # Kill any remaining Python processes
    pkill -f "python3 main.py" 2>/dev/null || true
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    
    sleep 3
    print_success "Process cleanup complete"
}

# Function to start Validation API
start_validation_api() {
    print_status "Starting Validation API..."
    
    cd "$PROJECT_DIR"
    
    # Create logs directory
    mkdir -p logs
    
    # Start Validation API
    nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level warning > logs/validation_api.log 2>&1 &
    local api_pid=$!
    
    # Wait for API to be ready
    if wait_for_service "http://localhost:8000/docs" "Validation API"; then
        print_success "Validation API started (PID: $api_pid)"
        return 0
    else
        print_error "Validation API failed to start"
        return 1
    fi
}

# Function to start Voice Agent
start_voice_agent() {
    print_status "Starting Voice Agent..."
    
    cd "$AGENT_DIR"
    
    # Load environment variables
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
    
    # Start Voice Agent
    nohup python3 main.py dev > ../../logs/voice_agent_robust.log 2>&1 &
    local agent_pid=$!
    
    # Wait for agent to initialize
    print_status "Waiting for Voice Agent to initialize..."
    sleep 10
    
    # Check if agent is running
    if ps -p $agent_pid > /dev/null; then
        print_success "Voice Agent started (PID: $agent_pid)"
        return 0
    else
        print_error "Voice Agent failed to start"
        return 1
    fi
}

# Function to start Frontend
start_frontend() {
    print_status "Starting Frontend..."
    
    cd "$FRONTEND_DIR"
    
    # Set environment variables for frontend
    export NEXT_PUBLIC_LIVEKIT_URL="wss://itcurvedev-8eikcg0z.livekit.cloud"
    
    # Clear frontend cache
    rm -rf .next
    
    # Start Frontend
    nohup npm run dev > ../../logs/frontend_robust.log 2>&1 &
    local frontend_pid=$!
    
    # Wait for frontend to be ready
    if wait_for_service "http://localhost:3000" "Frontend"; then
        print_success "Frontend started (PID: $frontend_pid)"
        return 0
    else
        print_error "Frontend failed to start"
        return 1
    fi
}

# Function to run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    local all_healthy=true
    
    # Check Validation API
    if ! curl -s http://localhost:8000/docs >/dev/null 2>&1; then
        print_error "Validation API health check failed"
        all_healthy=false
    fi
    
    # Check Frontend
    if ! curl -s http://localhost:3000 >/dev/null 2>&1; then
        print_error "Frontend health check failed"
        all_healthy=false
    fi
    
    # Check Voice Agent logs
    if [ -f "$PROJECT_DIR/logs/voice_agent_robust.log" ]; then
        if grep -q "ERROR\|Exception\|Failed" "$PROJECT_DIR/logs/voice_agent_robust.log"; then
            print_warning "Voice Agent has errors in logs"
        fi
    fi
    
    if [ "$all_healthy" = true ]; then
        print_success "All services are healthy"
    else
        print_error "Some services failed health checks"
        return 1
    fi
}

# Function to start monitoring
start_monitoring() {
    print_status "Starting monitoring system..."
    
    cd "$PROJECT_DIR"
    
    # Start the monitor in background
    nohup python3 voice_agent_monitor.py > logs/monitor.log 2>&1 &
    local monitor_pid=$!
    
    print_success "Monitoring system started (PID: $monitor_pid)"
}

# Main execution
main() {
    echo -e "${CYAN}🔧 PHASE 1: PREPARATION${NC}"
    echo "========================"
    
    check_env_vars
    install_dependencies
    setup_model_cache
    cleanup_processes
    
    echo ""
    echo -e "${CYAN}🚀 PHASE 2: SERVICE STARTUP${NC}"
    echo "=========================="
    
    start_validation_api
    sleep 2
    start_voice_agent
    sleep 5
    start_frontend
    
    echo ""
    echo -e "${CYAN}🔍 PHASE 3: HEALTH CHECKS${NC}"
    echo "========================"
    
    run_health_checks
    
    echo ""
    echo -e "${CYAN}📊 PHASE 4: MONITORING${NC}"
    echo "===================="
    
    start_monitoring
    
    echo ""
    echo -e "${GREEN}🎉 PROJECT STARTUP COMPLETE!${NC}"
    echo "=============================="
    echo ""
    echo -e "${BLUE}📋 Service URLs:${NC}"
    echo "  • Validation API: http://localhost:8000/docs"
    echo "  • Frontend: http://localhost:3000"
    echo "  • Voice Agent: Connected to LiveKit Cloud"
    echo ""
    echo -e "${BLUE}📝 Log Files:${NC}"
    echo "  • Validation API: $PROJECT_DIR/logs/validation_api.log"
    echo "  • Voice Agent: $PROJECT_DIR/logs/voice_agent_robust.log"
    echo "  • Frontend: $PROJECT_DIR/logs/frontend_robust.log"
    echo "  • Monitor: $PROJECT_DIR/logs/monitor.log"
    echo ""
    echo -e "${YELLOW}⚠️  To stop all services, run:${NC}"
    echo "  pkill -f 'python3 main.py'"
    echo "  pkill -f 'uvicorn app.main:app'"
    echo "  pkill -f 'npm run dev'"
    echo "  pkill -f 'voice_agent_monitor.py'"
    echo ""
    echo -e "${GREEN}✅ The booking issue has been resolved with:${NC}"
    echo "  • Enhanced error handling in book_trips function"
    echo "  • Retry mechanisms for API calls"
    echo "  • Automatic monitoring and recovery"
    echo "  • Robust startup process"
    echo ""
    echo -e "${PURPLE}🚀 Ready to test the booking flow!${NC}"
}

# Run main function
main "$@"
