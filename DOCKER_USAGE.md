# 🚀 Docker Compose - Run Both Services Together

Your `docker-compose.yml` is configured to run **both Dockerfiles simultaneously**!

## ✅ Current Configuration

### What Happens When You Run `docker-compose up`:

1. **Backend starts first** → Port 11000
2. **Frontend starts after backend is ready** → Port 3000
3. **Both run in parallel** once started
4. **Same network** for communication

## 🎯 Quick Start

```bash
# Start both services at the same time
docker-compose up -d

# Watch both logs simultaneously
docker-compose logs -f

# Stop both services
docker-compose down
```

## 📋 What Makes Them Run Together

Your `docker-compose.yml` includes:

### Backend Service
```yaml
backend:
  build:
    context: ./IT_Curves_Bot        # Uses your Dockerfile
    dockerfile: Dockerfile
  ports:
    - "11000:11000"
```

### Frontend Service
```yaml
frontend:
  build:
    context: ./ncs_pvt-virtual-agent-frontend-2c4b49def913
    dockerfile: Dockerfile
  ports:
    - "3000:3000"
  depends_on:
    backend:
      condition: service_started     # Starts after backend starts
```

### Shared Network
```yaml
networks:
  voice-agent-network:
    driver: bridge                   # Both services can communicate
```

## 🔄 How It Works

1. **Backend starts** → Builds from `IT_Curves_Bot/Dockerfile`
2. **Frontend waits** → Waits for backend to be ready
3. **Frontend starts** → Builds from `ncs_pvt-virtual-agent-frontend-2c4b49def913/Dockerfile`
4. **Both run** → Side by side on ports 11000 and 3000

## 📝 Commands

```bash
# Build both Dockerfiles at once
docker-compose build

# Build and start both services
docker-compose up -d

# Build specific service
docker-compose build backend
docker-compose build frontend

# Start just one service (with dependencies)
docker-compose up backend        # Starts only backend
docker-compose up frontend      # Starts backend + frontend

# View logs from both
docker-compose logs -f

# View logs from one
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop both services
docker-compose down

# Restart both services
docker-compose restart
```

## 🎨 Using Makefile (Easier)

```bash
make build          # Build both Dockerfiles
make up            # Start both services
make logs          # View logs from both
make ps            # Check status of both
make down          # Stop both services
make rebuild       # Rebuild and restart both
```

## 📊 Service Status

Check what's running:
```bash
docker-compose ps

# Or
make ps
```

Expected output:
```
        Name                       Command               State           Ports
------------------------------------------------------------------------------------
voice-agent-backend   python3 main.py dev               Up      0.0.0.0:11000->11000/tcp
voice-agent-frontend  node server.js                    Up      0.0.0.0:3000->3000/tcp
```

## 🔗 Access Services

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:11000

## 🛠️ Troubleshooting

### Both services won't start?

```bash
# Check configuration
docker-compose config

# See what's wrong
docker-compose logs
```

### Only one service starts?

```bash
# Check status
docker-compose ps

# View logs for failed service
docker-compose logs <service-name>
```

### Rebuild after code changes?

```bash
docker-compose up -d --build
```

## ✨ Summary

Your setup is **already configured** to run both Dockerfiles simultaneously!

✅ Both Dockerfiles will be built  
✅ Both services will start together  
✅ Both will be on the same network  
✅ Both can communicate with each other  

Just run: `make up` or `docker-compose up -d`

