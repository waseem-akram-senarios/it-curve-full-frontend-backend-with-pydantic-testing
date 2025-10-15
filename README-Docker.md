# ITCurves Widget - Docker Setup

This guide helps you run the ITCurves Widget application using Docker and Docker Compose.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Valid API keys and configuration

### 1. Setup Environment
```bash
# Copy environment template
cp env.example .env

# Edit .env with your actual API keys
nano .env
```

### 2. Start Production Environment
```bash
# Make script executable and run
chmod +x start.sh
./start.sh
```

### 3. Start Development Environment
```bash
# Make script executable and run
chmod +x start-dev.sh
./start-dev.sh
```

## 📋 Manual Commands

### Production Mode
```bash
# Build and start services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Development Mode
```bash
# Start with development overrides
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# View logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

## 🔧 Configuration

### Required Environment Variables
- `LIVEKIT_URL` - Your LiveKit server URL
- `LIVEKIT_API_KEY` - LiveKit API key
- `LIVEKIT_API_SECRET` - LiveKit API secret
- `OPENAI_API_KEY` - OpenAI API key
- `DEEPGRAM_API_KEY` - Deepgram API key
- `CARTESIA_API_KEY` - Cartesia API key

### Optional Environment Variables
- `MONGODB_URI` - MongoDB connection string
- `TWILIO_ACCOUNT_SID` - Twilio account SID
- `TWILIO_AUTH_TOKEN` - Twilio auth token

## 🌐 Access Points

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:11000
- **Widget Test**: http://localhost:3000/livekit-widget-test
- **Main Widget**: http://localhost:3000/widget

## 🐛 Troubleshooting

### Port Conflicts
If ports 3000 or 11000 are in use:
```bash
# Stop conflicting services
sudo lsof -ti:3000 | xargs kill -9
sudo lsof -ti:11000 | xargs kill -9
```

### Container Issues
```bash
# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check container logs
docker-compose logs backend
docker-compose logs frontend
```

### Health Checks
```bash
# Check service health
docker-compose ps

# Manual health check
curl http://localhost:3000/api/token?roomName=health-check
```

## 📊 Monitoring

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Container Status
```bash
# Check running containers
docker-compose ps

# Check resource usage
docker stats
```

## 🔄 Updates

### Rebuild After Code Changes
```bash
# Production
docker-compose up --build -d

# Development (with hot reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Update Dependencies
```bash
# Rebuild with no cache
docker-compose build --no-cache
docker-compose up -d
```

## 📁 File Structure
```
├── docker-compose.yml          # Production configuration
├── docker-compose.dev.yml      # Development overrides
├── start.sh                    # Production startup script
├── start-dev.sh               # Development startup script
├── env.example                # Environment template
├── VoiceAgent3/IT_Curves_Bot/
│   ├── Dockerfile             # Backend container
│   └── .dockerignore
└── ncs_pvt-virtual-agent-frontend-741b6d813bd5/
    ├── Dockerfile             # Frontend production container
    ├── Dockerfile.dev         # Frontend development container
    └── .dockerignore
```

## 🆘 Support

If you encounter issues:
1. Check the logs: `docker-compose logs -f`
2. Verify environment variables in `.env`
3. Ensure Docker is running and has sufficient resources
4. Try rebuilding containers: `docker-compose up --build`



