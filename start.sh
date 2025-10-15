#!/bin/bash

# ITCurves Widget Docker Startup Script

echo "🐳 Starting ITCurves Widget with Docker Compose..."

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
    echo "❌ Docker is not running or you don't have permission."
    echo "   Please run: sudo systemctl start docker"
    echo "   And add your user to docker group: sudo usermod -aG docker $USER"
    echo "   Then logout and login again."
    exit 1
fi

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
docker-compose ps

echo ""
echo "🎉 ITCurves Widget is starting up!"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🤖 Backend:  http://localhost:11000"
echo "🧪 Widget Test: http://localhost:3000/livekit-widget-test"
echo ""
echo "📊 To view logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 To stop:"
echo "   docker-compose down"
echo ""
echo "🔄 To restart:"
echo "   docker-compose restart"
