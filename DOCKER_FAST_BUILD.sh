#!/bin/bash

echo "🚀 Fast Docker Compose Start"
echo "============================"
echo ""
echo "This will use existing images or build quickly without full dependencies"
echo ""

cd /home/senarios/VoiceAgent8.1

newgrp docker << 'EOF'
echo "📦 Starting services..."
docker compose up -d

sleep 5

echo ""
echo "✅ Services started!"
echo ""
echo "📊 Status:"
docker compose ps

echo ""
echo "🌐 Access:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:11000"
echo ""
echo "📋 View logs: docker compose logs -f"
EOF
