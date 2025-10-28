# Docker Setup Guide

This project consists of two services that can be containerized using Docker:
- **Backend**: Python-based LiveKit voice agent
- **Frontend**: Next.js web application

## Prerequisites

- Docker installed on your system
- Docker Compose installed
- Environment variables configured

## Quick Start

### 1. Build and Run with Docker Compose

```bash
# Start both services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 2. Access the Services

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:11000

## Individual Service Deployment

### Backend Only

```bash
cd IT_Curves_Bot
docker build -t voice-agent-backend .
docker run -p 11000:11000 --env-file .env voice-agent-backend
```

### Frontend Only

```bash
cd ncs_pvt-virtual-agent-frontend-2c4b49def913
docker build -t voice-agent-frontend .
docker run -p 3000:3000 --env-file .env.local voice-agent-frontend
```

## Environment Variables

### Backend (.env)
Ensure your `IT_Curves_Bot/.env` file contains:
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENAI_API_KEY`
- `DEEPGRAM_API_KEY`
- `MONGODB_URI`
- And other required variables

### Frontend (.env.local)
Ensure your `ncs_pvt-virtual-agent-frontend-2c4b49def913/.env.local` contains:
- `NEXT_PUBLIC_LIVEKIT_URL`
- `NEXT_PUBLIC_DID_API_KEY`

## Docker Commands

### View Running Containers
```bash
docker-compose ps
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restart Services
```bash
docker-compose restart
```

### Rebuild After Changes
```bash
docker-compose up -d --build
```

### Stop Services
```bash
docker-compose down
```

### Clean Up (Remove Volumes)
```bash
docker-compose down -v
```

## Development vs Production

### Development Mode
The Docker setup runs the services in development mode:
- Backend runs with hot reload via `python main.py dev`
- Frontend uses the standalone Next.js output

### Production Mode

For production deployment:

1. **Backend**: Modify the Dockerfile CMD to:
   ```dockerfile
   CMD ["python3", "main.py"]
   ```

2. **Frontend**: The Dockerfile already uses production build with standalone output

## Troubleshooting

### Check Container Status
```bash
docker-compose ps
docker ps
```

### Check Logs
```bash
docker-compose logs backend
docker-compose logs frontend
```

### Rebuild Everything
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Access Container Shell
```bash
docker-compose exec backend bash
docker-compose exec frontend sh
```

## Network Configuration

The services communicate through a Docker network (`voice-agent-network`):
- Frontend should configure backend URL as `http://backend:11000`
- Update environment variables as needed

## Volume Mounts

The current setup mounts:
- `./IT_Curves_Bot/logs` → `/app/logs` (backend logs)
- `./IT_Curves_Bot/cache` → `/app/cache` (backend cache)

## Health Checks

Both services include health checks:
- Backend: Checks `/health` endpoint (you may need to add this)
- Frontend: Basic port check

## Performance Notes

- The backend uses PyTorch for some models (consider GPU support for production)
- Frontend builds are optimized for production with standalone output
- Adjust resource limits in docker-compose.yml for your needs

## Security Notes

- Never commit `.env` files
- Use Docker secrets in production
- Implement proper authentication
- Use HTTPS in production

