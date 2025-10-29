#!/bin/bash
# Script to rebuild Docker with the x_call_id fix

echo "🔧 Applying fix for 'Thinking' mode issue..."
echo ""

cd /home/senarios/VoiceAgent8.1

echo "📦 Step 1: Stopping containers..."
sudo docker compose down --volumes --remove-orphans

echo ""
echo "🔨 Step 2: Rebuilding backend with --no-cache..."
sudo docker compose build backend --no-cache

echo ""
echo "🚀 Step 3: Starting containers..."
sudo docker compose up -d

echo ""
echo "✅ Step 4: Checking status..."
sudo docker compose ps

echo ""
echo "📋 Step 5: Viewing logs (Ctrl+C to exit)..."
echo ""
sudo docker compose logs -f backend


