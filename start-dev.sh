#!/bin/bash

# ITCurves Widget Development Startup Script

echo "🚀 Starting ITCurves Widget in Development Mode..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp env.example .env
    echo "📝 Please edit .env file with your actual API keys and configuration"
    echo "   Then run this script again."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Build and start development services
echo "🔨 Building and starting development services..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

echo ""
echo "🎉 Development environment is ready!"
echo ""
echo "📱 Frontend: http://localhost:3000 (with hot reload)"
echo "🤖 Backend:  http://localhost:11000"
echo "🧪 Widget Test: http://localhost:3000/livekit-widget-test"



