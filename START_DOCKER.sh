#!/bin/bash

echo "🐳 Starting Voice Agent Docker Services..."
echo ""

cd /home/senarios/VoiceAgent8.1

# Run with docker group permissions
newgrp docker << 'DOCKER_EOF'
    echo "📊 Current status:"
    docker compose ps
    
    echo ""
    echo "🚀 Starting services..."
    docker compose up -d
    
    echo ""
    echo "✅ Services started!"
    echo "📊 Status:"
    docker compose ps
    
    echo ""
    echo "🌐 Access your services:"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend:  http://localhost:11000"
    echo ""
    echo "📝 View logs: newgrp docker << 'EOF' && docker compose logs -f && EOF"
DOCKER_EOF
