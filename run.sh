#!/bin/bash

echo "🚀 ITCurves Widget - One Command Setup"
echo "======================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Function to start services manually
start_manual_services() {
    print_status "Starting backend service..."
    cd VoiceAgent3/IT_Curves_Bot
    source venv/bin/activate
    python main.py start &
    BACKEND_PID=$!
    cd ../..
    
    print_status "Starting frontend service..."
    cd ncs_pvt-virtual-agent-frontend-2c4b49def913
    pnpm dev &
    FRONTEND_PID=$!
    cd ..
    
    # Wait for services to start
    sleep 15
    
    # Check if services are running
    if ps -p $BACKEND_PID > /dev/null && ps -p $FRONTEND_PID > /dev/null; then
        print_success "🎉 ITCurves Widget is running!"
        echo "📱 Frontend: http://localhost:3000 (or 3001 if 3000 is busy)"
        echo "🧪 Widget Test: http://localhost:3000/livekit-widget-test"
        echo ""
        echo "🔧 To stop services: pkill -f 'python main.py' && pkill -f 'pnpm dev'"
    else
        print_error "Failed to start services"
    fi
}

# Stop any existing services
print_status "Stopping existing services..."
pkill -f "python main.py" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "pnpm dev" 2>/dev/null || true
lsof -ti:3000,3001,11000 | xargs kill -9 2>/dev/null || true

# Check if Docker is accessible
if docker info &> /dev/null; then
    print_success "Docker is accessible"
    
    # Ensure .env file exists
    if [ ! -f ".env" ]; then
        print_status "Creating .env file..."
        cp VoiceAgent3/IT_Curves_Bot/.env .env 2>/dev/null || true
        cat ncs_pvt-virtual-agent-frontend-741b6d813bd5/.env.local >> .env 2>/dev/null || true
    fi
    
    # Try Docker Compose
    print_status "Starting services with Docker Compose..."
    if docker compose up --build -d; then
        print_success "Services started with Docker Compose!"
        
        # Wait and check
        sleep 10
        print_status "Checking services..."
        docker compose ps
        
        echo ""
        print_success "🎉 ITCurves Widget is running!"
        echo "📱 Frontend: http://localhost:3000"
        echo "🧪 Widget Test: http://localhost:3000/livekit-widget-test"
        echo ""
        echo "🔧 Commands:"
        echo "   View logs: docker compose logs -f"
        echo "   Stop: docker compose down"
        
    else
        print_warning "Docker Compose failed, starting manually..."
        start_manual_services
    fi
else
    print_warning "Docker not accessible, starting services manually..."
    start_manual_services
fi