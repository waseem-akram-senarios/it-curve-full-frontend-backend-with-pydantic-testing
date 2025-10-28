#!/bin/bash

echo "🐳 Voice Agent - Docker Compose Control Script"
echo "=============================================="
echo ""

cd /home/senarios/VoiceAgent8.1

# Parse command
case "$1" in
    start|up)
        echo "🚀 Starting services with Docker Compose..."
        newgrp docker << EOF
cd /home/senarios/VoiceAgent8.1
docker compose up -d
EOF
        echo ""
        echo "✅ Check status: ./RUN_DOCKER_COMPOSE.sh status"
        ;;
    stop|down)
        echo "🛑 Stopping services..."
        newgrp docker << EOF
cd /home/senarios/VoiceAgent8.1
docker compose down
EOF
        echo "✅ Services stopped"
        ;;
    restart)
        echo "🔄 Restarting services..."
        newgrp docker << EOF
cd /home/senarios/VoiceAgent8.1
docker compose restart
EOF
        echo "✅ Services restarted"
        ;;
    logs)
        echo "📋 Viewing logs (Ctrl+C to exit)..."
        newgrp docker << EOF
cd /home/senarios/VoiceAgent8.1
docker compose logs -f
EOF
        ;;
    status|ps)
        echo "📊 Service Status:"
        newgrp docker << EOF
cd /home/senarios/VoiceAgent8.1
docker compose ps
EOF
        ;;
    build)
        echo "🏗️  Building images..."
        newgrp docker << EOF
cd /home/senarios/VoiceAgent8.1
docker compose build
EOF
        ;;
    rebuild)
        echo "🔄 Rebuilding and starting..."
        newgrp docker << EOF
cd /home/senarios/VoiceAgent8.1
docker compose up -d --build
EOF
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status|build|rebuild}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all services"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - View logs"
        echo "  status  - Check service status"
        echo "  build   - Build images"
        echo "  rebuild - Rebuild and start"
        ;;
esac