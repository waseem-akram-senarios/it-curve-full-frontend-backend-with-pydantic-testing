# 🐳 Docker Compose Commands Guide

Complete reference guide for running your Voice Agent application with Docker Compose.

## 📑 Table of Contents

- [Quick Start](#quick-start)
- [Basic Commands](#basic-commands)
- [Service Management](#service-management)
- [Build Commands](#build-commands)
- [Logs & Debugging](#logs--debugging)
- [Network & Volumes](#network--volumes)
- [Environment Configuration](#environment-configuration)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Start Both Services
```bash
docker-compose up -d
```
Starts both backend and frontend containers in detached mode.

### View Logs
```bash
docker-compose logs -f
```
Follows logs from both services in real-time.

### Stop Services
```bash
docker-compose down
```
Stops and removes all containers.

---

## 📋 Basic Commands

### Start Services
```bash
# Start in foreground (see logs)
docker-compose up

# Start in background (detached)
docker-compose up -d

# Start specific service
docker-compose up backend
docker-compose up frontend
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop without removing containers
docker-compose stop
```

### Restart Services
```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart backend
docker-compose restart frontend
```

### Check Status
```bash
# Show running containers
docker-compose ps

# Show all containers (including stopped)
docker-compose ps -a
```

---

## 🔨 Service Management

### Start Individual Services
```bash
# Start only backend
docker-compose up -d backend

# Start only frontend (will also start backend if not running)
docker-compose up -d frontend
```

### Stop Individual Services
```bash
# Stop backend only
docker-compose stop backend

# Stop frontend only
docker-compose stop frontend
```

### Remove Containers
```bash
# Remove stopped containers
docker-compose rm

# Force remove (even if running)
docker-compose rm -f
```

### Force Recreate
```bash
# Recreate containers (useful after code changes)
docker-compose up -d --force-recreate
```

---

## 🏗️ Build Commands

### Build Images
```bash
# Build all images
docker-compose build

# Build without cache
docker-compose build --no-cache

# Build specific service
docker-compose build backend
docker-compose build frontend
```

### Build and Start
```bash
# Build and start in one command
docker-compose up -d --build

# Force rebuild and start
docker-compose up -d --build --force-recreate
```

### Rebuild After Code Changes
```bash
# Pull latest code, then:
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 📊 Logs & Debugging

### View Logs
```bash
# Follow all logs
docker-compose logs -f

# View all logs (no follow)
docker-compose logs

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# View last N lines
docker-compose logs --tail=100
```

### Debug Services
```bash
# See detailed logs
docker-compose logs --timestamps

# View service status
docker-compose ps

# Inspect specific service
docker-compose top backend
docker-compose top frontend
```

### Execute Commands in Containers
```bash
# Open shell in backend
docker-compose exec backend bash

# Open shell in frontend
docker-compose exec frontend sh

# Run command in backend
docker-compose exec backend python --version

# Run command in frontend
docker-compose exec frontend node --version
```

---

## 🌐 Network & Volumes

### Inspect Network
```bash
# Show network details
docker network inspect voiceagent8.1_voice-agent-network

# List networks
docker network ls
```

### Volume Management
```bash
# List volumes
docker volume ls

# Inspect volumes
docker volume inspect voiceagent8.1_backend-logs
docker volume inspect voiceagent8.1_backend-cache

# Remove volumes
docker-compose down -v
```

---

## ⚙️ Environment Configuration

### Environment Files
Your docker-compose.yml uses these env files:
- Backend: `IT_Curves_Bot/.env`
- Frontend: `ncs_pvt-virtual-agent-frontend-2c4b49def913/.env.local`

### Override Environment
```bash
# Use different env file
docker-compose --env-file .env.production up -d

# Pass environment variables
docker-compose run -e DEBUG=1 backend python main.py dev
```

### Export Environment
```bash
# Show full configuration with env variables
docker-compose config
```

---

## 🔍 Troubleshooting

### Containers Won't Start
```bash
# Check configuration
docker-compose config

# See detailed errors
docker-compose up --verbose

# Check logs before starting
docker-compose logs
```

### Service Health Issues
```bash
# Check health status
docker-compose ps

# Inspect container
docker-compose inspect backend
docker-compose inspect frontend
```

### Rebuild Everything
```bash
# Complete clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Port Conflicts
```bash
# Check what's using the ports
sudo lsof -i :11000
sudo lsof -i :3000

# Change ports in docker-compose.yml
# Then rebuild
docker-compose up -d --build
```

### View Resource Usage
```bash
# Show resource stats
docker stats

# For specific containers
docker stats voice-agent-backend voice-agent-frontend
```

---

## 🎯 Using with Makefile

For easier command management, use the Makefile:

### Quick Commands
```bash
make help          # Show all available commands
make up            # Start both services
make down          # Stop both services
make logs          # View logs from both
make ps            # Check status
make restart       # Restart both
make rebuild       # Rebuild and restart
make clean         # Stop and remove volumes
```

### Individual Services
```bash
make backend       # Start only backend
make frontend      # Start only frontend
make logs-backend  # View backend logs
make logs-frontend # View frontend logs
make build-backend # Build only backend
make build-frontend # Build only frontend
```

### Debug Commands
```bash
make shell-backend   # Open backend shell
make shell-frontend  # Open frontend shell
```

---

## 📝 Configuration Reference

### docker-compose.yml Structure

```yaml
services:
  backend:
    build: ./IT_Curves_Bot
    ports: ["11000:11000"]
    environment: [from .env]
    networks: [voice-agent-network]
    
  frontend:
    build: ./ncs_pvt-virtual-agent-frontend-2c4b49def913
    ports: ["3000:3000"]
    depends_on: [backend]
    networks: [voice-agent-network]
```

### Key Settings

- **Ports**: Backend (11000), Frontend (3000)
- **Restart**: `unless-stopped` (auto-restart)
- **Network**: Shared `voice-agent-network`
- **Volumes**: Logs and cache persistence

---

## 🚦 Common Workflows

### Development Workflow
```bash
# 1. Start both services
docker-compose up -d

# 2. Make code changes

# 3. Rebuild affected service
docker-compose up -d --build

# 4. Check logs
docker-compose logs -f

# 5. Stop when done
docker-compose down
```

### Debugging Workflow
```bash
# 1. Start services
docker-compose up

# 2. In another terminal, check logs
docker-compose logs -f

# 3. If issue, enter container
docker-compose exec backend bash

# 4. Fix issue

# 5. Restart
docker-compose restart
```

### Production Deployment
```bash
# 1. Set production environment
export COMPOSE_ENV=production

# 2. Build and start
docker-compose up -d --build

# 3. Monitor
docker-compose logs -f

# 4. Scale if needed
docker-compose up -d --scale backend=2
```

---

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- See `DOCKER_SETUP.md` for detailed configuration
- See `DOCKER_USAGE.md` for usage patterns

---

## 🎓 Quick Reference Card

```bash
# ESSENTIAL COMMANDS
docker-compose up -d          # Start both services
docker-compose down           # Stop both services
docker-compose logs -f        # View logs
docker-compose ps             # Check status
docker-compose restart        # Restart services

# BUILD COMMANDS
docker-compose build          # Build images
docker-compose build --no-cache # Clean build
docker-compose up -d --build  # Build and start

# MANAGEMENT COMMANDS
docker-compose exec backend bash    # Backend shell
docker-compose exec frontend sh     # Frontend shell
docker-compose down -v              # Remove volumes
docker-compose config               # Validate config
```

---

**Need help?** Check `DOCKER_SETUP.md` or `DOCKER_USAGE.md` for more details!
