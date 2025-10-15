#!/bin/bash

echo "🔧 Fixing Docker permissions..."

# Add user to docker group
echo "Adding user to docker group..."
sudo usermod -aG docker $USER

# Start Docker service if not running
echo "Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker

# Apply group changes immediately
echo "Applying group changes..."
newgrp docker

echo "✅ Docker permissions fixed!"
echo "You may need to logout and login again for changes to take effect."
echo ""
echo "Testing Docker access..."
docker ps

echo ""
echo "If the above command works without 'permission denied', you can now run:"
echo "  docker compose up --build -d"
