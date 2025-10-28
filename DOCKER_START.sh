#!/bin/bash

echo "🚀 Starting Voice Agent with Docker Compose..."
echo ""

# Check if running in docker group
if groups | grep -q docker; then
    echo "✅ User is in docker group"
    
    # Start services
    echo "📦 Building and starting services..."
    docker compose up -d --build
    
    echo ""
    echo "✅ Services are starting!"
    echo ""
    echo "📊 View logs: docker compose logs -f"
    echo "🌐 Frontend: http://localhost:3000"
    echo "🔧 Backend:  http://localhost:11000"
    echo "📝 Status:   docker compose ps"
else
    echo "❌ User not in docker group"
    echo "Run: sudo usermod -aG docker $USER"
    echo "Then logout and login again"
fi
