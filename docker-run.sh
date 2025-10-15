#!/bin/bash

echo "🐳 ITCurves Widget - Docker Compose One Command"
echo "=============================================="

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

# Stop any existing services
print_status "Stopping existing services..."
pkill -f "python main.py" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "pnpm dev" 2>/dev/null || true
lsof -ti:3000,3001,11000 | xargs kill -9 2>/dev/null || true

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_status "Creating .env file..."
    cp VoiceAgent3/IT_Curves_Bot/.env .env 2>/dev/null || true
    cat ncs_pvt-virtual-agent-frontend-741b6d813bd5/.env.local >> .env 2>/dev/null || true
fi

# Check Docker permissions
print_status "Checking Docker permissions..."
if docker info &> /dev/null; then
    print_success "Docker is accessible"
    
    # Run Docker Compose
    print_status "Starting services with Docker Compose..."
    docker compose up --build -d
    
    # Wait for services to start
    sleep 15
    
    # Check status
    print_status "Checking service status..."
    docker compose ps
    
    # Test services
    print_status "Testing services..."
    if curl -s http://localhost:3000 | grep -q "ITCurves"; then
        print_success "Frontend is running!"
    else
        print_warning "Frontend may still be starting..."
    fi
    
    echo ""
    print_success "🎉 ITCurves Widget is running with Docker Compose!"
    echo "📱 Frontend: http://localhost:3000"
    echo "🧪 Widget Test: http://localhost:3000/livekit-widget-test"
    echo ""
    echo "🔧 Docker Commands:"
    echo "   View logs: docker compose logs -f"
    echo "   Stop: docker compose down"
    echo "   Restart: docker compose restart"
    
else
    print_error "Docker is not accessible. You need to fix permissions first."
    echo ""
    echo "Run these commands to fix Docker permissions:"
    echo "  sudo usermod -aG docker \$USER"
    echo "  sudo systemctl start docker"
    echo "  newgrp docker"
    echo ""
    echo "Then run this script again: ./docker-run.sh"
fi
