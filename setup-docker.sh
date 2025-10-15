#!/bin/bash

echo "🔧 Docker Setup for ITCurves Widget"
echo "==================================="

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

print_status "Setting up Docker permissions and running ITCurves Widget..."

# Check if user is in docker group
if groups $USER | grep -q docker; then
    print_success "User is already in docker group"
else
    print_warning "User is not in docker group. Adding to docker group..."
    echo "You need to run these commands:"
    echo "  sudo usermod -aG docker \$USER"
    echo "  newgrp docker"
    echo ""
    echo "Then run: docker compose up --build -d"
    exit 1
fi

# Check Docker daemon
if ! docker info &> /dev/null; then
    print_error "Docker daemon is not running or accessible"
    echo "Start Docker with: sudo systemctl start docker"
    exit 1
fi

print_success "Docker is ready!"

# Stop existing services
print_status "Stopping existing services..."
pkill -f "python main.py" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "pnpm dev" 2>/dev/null || true

# Ensure .env file exists
if [ ! -f ".env" ]; then
    print_status "Creating .env file..."
    cp VoiceAgent3/IT_Curves_Bot/.env .env 2>/dev/null || true
    cat ncs_pvt-virtual-agent-frontend-741b6d813bd5/.env.local >> .env 2>/dev/null || true
fi

# Run Docker Compose
print_status "Starting ITCurves Widget with Docker Compose..."
docker compose up --build -d

# Wait and check
sleep 10
print_status "Checking services..."
docker compose ps

echo ""
print_success "🎉 ITCurves Widget is running with Docker!"
echo "📱 Frontend: http://localhost:3000"
echo "🧪 Widget Test: http://localhost:3000/livekit-widget-test"
echo ""
echo "🔧 Management:"
echo "   View logs: docker compose logs -f"
echo "   Stop: docker compose down"
