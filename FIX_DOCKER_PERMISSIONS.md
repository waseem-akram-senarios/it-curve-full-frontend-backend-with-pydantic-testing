# 🔧 Fix Docker Permission Issues

## Problem
When running `docker compose up`, you get:
```
permission denied while trying to connect to the Docker daemon socket
```

## Solution

You need to add your user to the `docker` group.

### Option 1: Quick Fix (Requires Logout)
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again for changes to take effect
# Or use newgrp
newgrp docker
```

### Option 2: Use Sudo (Temporary)
```bash
# Run docker commands with sudo
sudo docker compose up -d
sudo docker compose logs -f
sudo docker compose down
```

### Option 3: Check and Fix Group Membership
```bash
# Check current groups
groups

# If docker group exists
sudo usermod -aG docker $USER

# Verify docker group exists
getent group docker

# Apply immediately without logout
newgrp docker
```

## After Fixing Permissions

### Use NEW docker compose syntax (without hyphen)
```bash
# START services
docker compose up -d

# VIEW logs
docker compose logs -f

# STOP services
docker compose down

# CHECK status
docker compose ps
```

## Why This Matters

- **Old**: `docker-compose` (version 1.x, deprecated)
- **New**: `docker compose` (version 2.x, recommended)

Your system has both, but use the newer syntax: **`docker compose`** (with space, not hyphen)

## Test

```bash
# Test Docker access
docker ps

# Test docker compose
docker compose version

# If both work, you're ready!
docker compose up -d
```

## Common Commands with Fixed Permissions

```bash
# Start both services
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild
docker compose up -d --build

# Stop
docker compose down

# Remove volumes
docker compose down -v
```

## Makefile (Works with sudo)

If you need to use sudo, the Makefile commands become:
```bash
sudo make up
sudo make down
sudo make logs
```

Or update the Makefile to use `sudo docker` for each command.

