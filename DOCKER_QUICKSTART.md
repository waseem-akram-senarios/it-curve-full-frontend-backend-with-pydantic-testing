# 🐳 Docker Quick Start Guide

Run your Voice Agent application with Docker in 3 simple steps!

## Prerequisites

- Docker installed
- Docker Compose installed

## Quick Start

### 1. Start Everything

```bash
# Build and start all services
make up

# Or using docker-compose directly
docker-compose up -d
```

### 2. Access Services

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:11000

### 3. View Logs

```bash
# View all logs
make logs

# View backend only
make logs-backend

# View frontend only
make logs-frontend
```

## Common Commands

```bash
# Check status
make ps

# Restart services
make restart

# Rebuild after code changes
make rebuild

# Stop everything
make down

# Clean up (removes volumes)
make clean
```

## Available Commands

| Command | Description |
|---------|-------------|
| `make up` | Start all services |
| `make down` | Stop all services |
| `make logs` | View all logs |
| `make logs-backend` | View backend logs |
| `make logs-frontend` | View frontend logs |
| `make restart` | Restart all services |
| `make rebuild` | Rebuild and restart |
| `make clean` | Stop and remove volumes |
| `make ps` | Show service status |
| `make shell-backend` | Open backend shell |
| `make shell-frontend` | Open frontend shell |

## File Structure

```
VoiceAgent8.1/
├── IT_Curves_Bot/
│   ├── Dockerfile              # Backend Docker image
│   ├── .dockerignore
│   ├── .env                    # Backend environment
│   └── requirements.txt
├── ncs_pvt-virtual-agent-frontend-2c4b49def913/
│   ├── Dockerfile              # Frontend Docker image
│   ├── .dockerignore
│   ├── .env.local              # Frontend environment
│   └── package.json
├── docker-compose.yml          # Main orchestration file
├── Makefile                     # Easy commands
└── DOCKER_SETUP.md             # Detailed documentation
```

## Troubleshooting

### Services won't start

```bash
# Check environment files exist
ls IT_Curves_Bot/.env
ls ncs_pvt-virtual-agent-frontend-2c4b49def913/.env.local

# View logs for errors
docker-compose logs
```

### Rebuild after code changes

```bash
make rebuild
```

### Ports already in use

Edit `docker-compose.yml` to change ports:

```yaml
ports:
  - "3001:3000"  # Frontend on port 3001
  - "11001:11000" # Backend on port 11001
```

## Development vs Production

The current setup runs in **development mode**:
- Hot reload enabled for both services
- Debug logs enabled
- Auto-restart on code changes

For production:
- Update Dockerfiles to use production builds
- Configure proper security
- Set up reverse proxy (nginx/traefik)
- Use Docker secrets for sensitive data

## Next Steps

1. Read `DOCKER_SETUP.md` for detailed documentation
2. Configure environment variables
3. Set up monitoring and logging
4. Configure CI/CD pipeline

