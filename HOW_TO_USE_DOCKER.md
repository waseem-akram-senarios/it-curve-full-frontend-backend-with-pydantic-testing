# 🐳 How to Use Docker with Your Voice Agent

## ⚠️ IMPORTANT: Permission Issue

Your containers ARE running, but you need to access Docker with proper permissions.

## ✅ Quick Solution

### Method 1: Use New Shell with Docker Group
```bash
# Start a new shell with docker permissions
newgrp docker

# Then run docker commands
docker compose ps
docker compose logs -f
docker compose up -d
```

### Method 2: Use Sudo (Temporary)
```bash
sudo docker compose ps
sudo docker compose logs -f
sudo docker compose down
sudo docker compose up -d
```

## 🎯 Your Services Status

Your containers are **currently running**:

- ✅ **Backend**: Port 11000
- ✅ **Frontend**: Port 3000

You can access them at:
- Frontend: http://localhost:3000
- Backend: http://localhost:11000

## 📝 Common Commands

### View Running Containers
```bash
newgrp docker << 'EOF'
docker compose ps
EOF

# Or with sudo
sudo docker compose ps
```

### View Logs
```bash
newgrp docker << 'EOF'
docker compose logs -f
EOF

# Or with sudo
sudo docker compose logs -f
```

### Restart Services
```bash
newgrp docker << 'EOF'
docker compose restart
EOF
```

### Stop Services
```bash
newgrp docker << 'EOF'
docker compose down
EOF
```

## 🔧 Permanent Fix

To avoid typing `newgrp docker` every time:

1. **Logout and Login Again** (after adding to docker group)
2. Or create an alias in your `.bashrc`:
   ```bash
   echo 'alias docker="newgrp docker <<< docker"' >> ~/.bashrc
   source ~/.bashrc
   ```

## 🎯 Most Common Workflow

```bash
# 1. Enter docker group
newgrp docker

# 2. Start services (they're already running)
docker compose up -d

# 3. View logs
docker compose logs -f

# 4. Check status
docker compose ps

# 5. When done
docker compose down
```

## 💡 Quick Tips

- Use `docker compose` (space) not `docker-compose` (hyphen)
- Containers are already running on ports 3000 and 11000
- Use `newgrp docker` to get proper permissions in current session
- Or logout/login to make docker permissions permanent
