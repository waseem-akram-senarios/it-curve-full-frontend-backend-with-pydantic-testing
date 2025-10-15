#!/bin/bash

# VoiceAgent5withFeNew - Docker Runner with sudo
# This script runs the project with Docker using sudo when needed

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
    echo "VoiceAgent5withFeNew - Docker Runner"
    echo "===================================="
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  start           Start with Docker Compose"
    echo "  stop            Stop Docker services"
    echo "  restart         Restart Docker services"
    echo "  status          Check Docker service status"
    echo "  logs            Show Docker service logs"
    echo "  clean           Stop and clean up all containers/images"
    echo "  help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start        # Start with Docker Compose"
    echo "  $0 stop         # Stop Docker services"
    echo ""
}

# Function to check if Docker is accessible
check_docker() {
    if sudo docker info >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to run with Docker Compose using sudo
run_docker() {
    print_status "Starting services with Docker Compose (using sudo)..."
    
    # Check if .env exists
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from template..."
        cp env.example .env
        print_warning "Please edit .env file with your actual API keys"
        return 1
    fi
    
    # Check Docker access
    if ! check_docker; then
        print_error "Cannot access Docker even with sudo. Please check Docker installation."
        return 1
    fi
    
    # Stop any existing services
    print_status "Stopping any existing Docker services..."
    sudo docker compose down 2>/dev/null || true
    
    # Build and start
    print_status "Building and starting services..."
    sudo docker compose up --build -d
    
    # Wait for services
    print_status "Waiting for services to start..."
    sleep 20
    
    # Check status
    print_status "Checking service status..."
    sudo docker compose ps
    
    print_success "Services started with Docker!"
    show_urls
}

# Function to stop Docker services
stop_docker() {
    print_status "Stopping Docker services..."
    
    if check_docker; then
        sudo docker compose down 2>/dev/null || true
        print_success "Docker services stopped"
    else
        print_warning "Cannot access Docker"
    fi
}

# Function to restart Docker services
restart_docker() {
    print_status "Restarting Docker services..."
    stop_docker
    sleep 5
    run_docker
}

# Function to check Docker service status
check_status() {
    print_status "Checking Docker service status..."
    
    if check_docker; then
        sudo docker compose ps
        echo ""
        print_status "Docker service logs (last 10 lines):"
        sudo docker compose logs --tail=10
    else
        print_error "Cannot access Docker"
    fi
}

# Function to show Docker logs
show_logs() {
    print_status "Showing Docker service logs..."
    
    if check_docker; then
        sudo docker compose logs -f
    else
        print_error "Cannot access Docker"
    fi
}

# Function to clean up Docker resources
clean_up() {
    print_status "Cleaning up Docker resources..."
    
    if check_docker; then
        stop_docker
        
        # Remove containers and images
        sudo docker compose down --rmi all --volumes --remove-orphans 2>/dev/null || true
        
        # Clean up Docker system
        sudo docker system prune -f 2>/dev/null || true
        
        print_success "Docker cleanup completed"
    else
        print_error "Cannot access Docker"
    fi
}

# Function to show URLs
show_urls() {
    echo ""
    print_success "🎉 VoiceAgent Project is Running with Docker!"
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
    echo "   Restart services: $0 restart"
    echo ""
}

# Main script logic
case "${1:-help}" in
    "start")
        run_docker
        ;;
    "stop")
        stop_docker
        ;;
    "restart")
        restart_docker
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
    "help"|*)
        show_help
        ;;
esac

