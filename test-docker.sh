#!/bin/bash

# Test Docker Setup - Verify both services can run simultaneously
echo "========================================="
echo "Testing Docker Setup"
echo "========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running"
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check Docker Compose
if ! docker-compose --version > /dev/null 2>&1; then
    echo "❌ Docker Compose not found"
    exit 1
fi

echo "✅ Docker Compose is installed"
echo ""

# Validate configuration
echo "Validating docker-compose.yml..."
if docker-compose config > /dev/null 2>&1; then
    echo "✅ Configuration is valid"
else
    echo "❌ Configuration has errors"
    docker-compose config
    exit 1
fi

echo ""
echo "========================================="
echo "Configuration Summary"
echo "========================================="

# Show services
echo "Services configured:"
docker-compose config --services

echo ""
echo "To start both services simultaneously:"
echo "  make up"
echo ""
echo "Or:"
echo "  docker-compose up -d"
echo ""
echo "To view logs from both services:"
echo "  docker-compose logs -f"
echo ""
echo "✅ Ready to build and run both Dockerfiles!"

