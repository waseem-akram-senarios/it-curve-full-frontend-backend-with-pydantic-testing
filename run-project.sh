#!/bin/bash

# VoiceAgent5withFeNew - One Command Runner
# This script provides multiple ways to run the project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to show help
show_help() {
    echo "VoiceAgent5withFeNew - Project Runner"
    echo "====================================="
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  docker          Run with Docker Compose (recommended)"
    echo "  docker-dev      Run with Docker Compose in development mode"
    echo "  native          Run services natively without Docker"
    echo "  stop            Stop all running services"
    echo "  status          Check status of services"
    echo "  logs            Show logs from running services"
    echo "  clean           Stop and clean up all containers/images"
    echo "  fix-docker      Fix Docker permissions"
    echo "  help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 docker       # Start with Docker (production mode)"
    echo "  $0 native       # Start without Docker (development)"
    echo "  $0 stop         # Stop all services"
    echo ""
}

# Function to fix Docker permissions
fix_docker_permissions() {
    print_status "Attempting to fix Docker permissions..."
    
    # Check if user is in docker group
    if groups $USER | grep -q docker; then
        print_success "User is already in docker group"
    else
        print_warning "Adding user to docker group..."
        echo "You may need to enter your password:"
        sudo usermod -aG docker $USER
        print_warning "Please logout and login again, or run: newgrp docker"
    fi
    
    # Start Docker service
    print_status "Starting Docker service..."
    sudo systemctl start docker
    sudo systemctl enable docker
    
    print_success "Docker permissions fixed! Please logout and login again."
}

# Function to run with Docker
run_docker() {
    print_status "Starting services with Docker Compose..."
    
    # Check if .env exists
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from template..."
        cp env.example .env
        print_warning "Please edit .env file with your actual API keys"
        return 1
    fi
    
    # Check Docker access
    if ! docker info >/dev/null 2>&1; then
        print_error "Cannot access Docker. Try running: $0 fix-docker"
        return 1
    fi
    
    # Stop any existing services
    docker compose down 2>/dev/null || true
    
    # Build and start
    print_status "Building and starting services..."
    docker compose up --build -d
    
    # Wait for services
    print_status "Waiting for services to start..."
    sleep 15
    
    # Check status
    docker compose ps
    
    print_success "Services started with Docker!"
    show_urls
}

# Function to run in development mode with Docker
run_docker_dev() {
    print_status "Starting services with Docker Compose (Development Mode)..."
    
    # Check if .env exists
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from template..."
        cp env.example .env
        print_warning "Please edit .env file with your actual API keys"
        return 1
    fi
    
    # Check Docker access
    if ! docker info >/dev/null 2>&1; then
        print_error "Cannot access Docker. Try running: $0 fix-docker"
        return 1
    fi
    
    # Stop any existing services
    docker compose -f docker-compose.dev.yml down 2>/dev/null || true
    
    # Build and start
    print_status "Building and starting services in development mode..."
    docker compose -f docker-compose.dev.yml up --build -d
    
    # Wait for services
    print_status "Waiting for services to start..."
    sleep 15
    
    # Check status
    docker compose -f docker-compose.dev.yml ps
    
    print_success "Services started with Docker (Development Mode)!"
    show_urls
}

# Function to run natively without Docker
run_native() {
    print_status "Starting services natively (without Docker)..."
    
    # Check if .env exists
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from template..."
        cp env.example .env
        print_warning "Please edit .env file with your actual API keys"
        return 1
    fi
    
    # Stop any existing services
    pkill -f "python main.py" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    
    # Start backend
    print_status "Starting backend service..."
    cd VoiceAgent3/IT_Curves_Bot
    cp ../../.env .env
    source venv/bin/activate
    python main.py start &
    BACKEND_PID=$!
    cd ../..
    
    # Wait a moment for backend to start
    sleep 5
    
    # Start frontend
    print_status "Starting frontend service..."
    cd ncs_pvt-virtual-agent-frontend-2c4b49def913
    cp ../.env .env.local
    rm -rf .next
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    
    # Wait for services to start
    print_status "Waiting for services to start..."
    sleep 10
    
    # Check if services are running
    if ps -p $BACKEND_PID > /dev/null && ps -p $FRONTEND_PID > /dev/null; then
        print_success "Services started natively!"
        show_urls
        echo ""
        print_status "Process IDs:"
        echo "  Backend PID: $BACKEND_PID"
        echo "  Frontend PID: $FRONTEND_PID"
        echo ""
        print_status "To stop services: $0 stop"
    else
        print_error "Failed to start services"
        return 1
    fi
}

# Function to stop services
stop_services() {
    print_status "Stopping all services..."
    
    # Stop Docker services
    docker compose down 2>/dev/null || true
    docker compose -f docker-compose.dev.yml down 2>/dev/null || true
    
    # Stop native services
    pkill -f "python main.py" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    
    # Kill any processes on ports 3000 and 11000
    lsof -ti:3000,3001,11000 | xargs kill -9 2>/dev/null || true
    
    print_success "All services stopped"
}

# Function to check status
check_status() {
    print_status "Checking service status..."
    
    # Check Docker services
    if docker info >/dev/null 2>&1; then
        echo "Docker Services:"
        docker compose ps 2>/dev/null || echo "  No Docker services running"
        echo ""
    fi
    
    # Check native services
    echo "Native Services:"
    if pgrep -f "python main.py" > /dev/null; then
        echo "  Backend (Python): Running (PID: $(pgrep -f 'python main.py'))"
    else
        echo "  Backend (Python): Not running"
    fi
    
    if pgrep -f "next dev" > /dev/null; then
        echo "  Frontend (Next.js): Running (PID: $(pgrep -f 'next dev'))"
    else
        echo "  Frontend (Next.js): Not running"
    fi
    
    # Check ports
    echo ""
    echo "Port Status:"
    if netstat -tlnp 2>/dev/null | grep -q ":3000"; then
        echo "  Port 3000: In use"
    else
        echo "  Port 3000: Available"
    fi
    
    if netstat -tlnp 2>/dev/null | grep -q ":11000"; then
        echo "  Port 11000: In use"
    else
        echo "  Port 11000: Available"
    fi
}

# Function to show logs
show_logs() {
    print_status "Showing service logs..."
    
    # Try Docker logs first
    if docker info >/dev/null 2>&1; then
        if docker compose ps | grep -q "Up"; then
            echo "Docker Service Logs:"
            docker compose logs --tail=20
            return
        fi
    fi
    
    # Show native service info
    echo "Native Service Information:"
    echo "Backend logs: tail -f VoiceAgent3/IT_Curves_Bot/logs/ivr-bot.log"
    echo "Frontend logs: Check the terminal where 'npm run dev' is running"
    
    # Check if services are running
    if pgrep -f "python main.py" > /dev/null; then
        echo "Backend is running"
    fi
    if pgrep -f "next dev" > /dev/null; then
        echo "Frontend is running"
    fi
}

# Function to clean up
clean_up() {
    print_status "Cleaning up Docker resources..."
    
    stop_services
    
    # Remove containers and images
    docker compose down --rmi all --volumes --remove-orphans 2>/dev/null || true
    docker compose -f docker-compose.dev.yml down --rmi all --volumes --remove-orphans 2>/dev/null || true
    
    # Clean up Docker system
    docker system prune -f 2>/dev/null || true
    
    print_success "Cleanup completed"
}

# Function to show URLs
show_urls() {
    echo ""
    print_success "🎉 VoiceAgent Project is Running!"
    echo ""
    echo "📱 Access URLs:"
    echo "   Frontend: http://localhost:3000"
    echo "   Widget Test: http://localhost:3000/livekit-widget-test"
    echo "   Chat Embed: http://localhost:3000/chat-embed-demo"
    echo "   Backend API: http://localhost:11000"
    echo ""
    echo "🔧 Management Commands:"
    echo "   Check status: $0 status"
    echo "   View logs: $0 logs"
    echo "   Stop services: $0 stop"
    echo ""
}

# Main script logic
case "${1:-help}" in
    "docker")
        run_docker
        ;;
    "docker-dev")
        run_docker_dev
        ;;
    "native")
        run_native
        ;;
    "stop")
        stop_services
        ;;
    "status")
        check_status
        ;;
    "logs")
        show_logs
        ;;
    "clean")
        clean_up
        ;;
    "fix-docker")
        fix_docker_permissions
        ;;
    "help"|*)
        show_help
        ;;
esac

