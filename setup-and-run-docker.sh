#!/bin/bash

echo "🐳 ITCurves Widget - Docker Setup and Run Script"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please don't run this script as root. Run as your regular user."
    exit 1
fi

print_status "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_success "Docker is installed"

# Check Docker daemon status
print_status "Checking Docker daemon status..."
if ! docker info &> /dev/null; then
    print_warning "Docker daemon is not accessible. Attempting to fix permissions..."
    
    # Add user to docker group
    print_status "Adding user '$USER' to docker group..."
    sudo usermod -aG docker $USER
    
    # Start Docker service
    print_status "Starting Docker service..."
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # Apply group changes
    print_status "Applying group changes..."
    newgrp docker
    
    # Test Docker access
    if docker info &> /dev/null; then
        print_success "Docker permissions fixed!"
    else
        print_error "Failed to fix Docker permissions. You may need to logout and login again."
        print_warning "Alternatively, you can run the services manually without Docker."
        exit 1
    fi
else
    print_success "Docker daemon is accessible"
fi

# Stop any existing services
print_status "Stopping any existing services..."
pkill -f "python main.py" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "pnpm dev" 2>/dev/null || true
lsof -ti:3000,3001,11000 | xargs kill -9 2>/dev/null || true

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating it from existing configuration..."
    cp VoiceAgent3/IT_Curves_Bot/.env .env
    cat ncs_pvt-virtual-agent-frontend-741b6d813bd5/.env.local >> .env
fi

print_success "Environment file ready"

# Build and start services with Docker Compose
print_status "Building and starting services with Docker Compose..."

# Try docker compose first (newer version)
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    print_status "Using 'docker compose' (newer version)..."
    if docker compose up --build -d; then
        print_success "Services started successfully with Docker Compose!"
    else
        print_error "Failed to start services with 'docker compose'"
        exit 1
    fi
# Fallback to docker-compose (older version)
elif command -v docker-compose &> /dev/null; then
    print_status "Using 'docker-compose' (older version)..."
    if docker-compose up --build -d; then
        print_success "Services started successfully with Docker Compose!"
    else
        print_error "Failed to start services with 'docker-compose'"
        exit 1
    fi
else
    print_error "Neither 'docker compose' nor 'docker-compose' is available"
    exit 1
fi

# Wait for services to start
print_status "Waiting for services to start..."
sleep 10

# Check service status
print_status "Checking service status..."
if docker compose ps &> /dev/null; then
    docker compose ps
elif docker-compose ps &> /dev/null; then
    docker-compose ps
fi

# Test services
print_status "Testing services..."

# Test frontend
if curl -s http://localhost:3000 | grep -q "ITCurves"; then
    print_success "Frontend is running on http://localhost:3000"
else
    print_warning "Frontend may not be ready yet. Check http://localhost:3000"
fi

# Test API
if curl -s "http://localhost:3000/api/token?roomName=test" | grep -q "accessToken"; then
    print_success "API is working correctly"
else
    print_warning "API may not be ready yet"
fi

# Check backend logs
print_status "Backend logs (last 10 lines):"
if docker compose logs --tail=10 backend 2>/dev/null || docker-compose logs --tail=10 backend 2>/dev/null; then
    echo ""
fi

print_success "🐳 ITCurves Widget is now running with Docker!"
echo ""
echo "📋 Access URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Widget Test: http://localhost:3000/livekit-widget-test"
echo ""
echo "🔧 Management Commands:"
echo "   View logs: docker compose logs -f"
echo "   Stop services: docker compose down"
echo "   Restart: docker compose restart"
echo ""
echo "✅ Setup complete!"
