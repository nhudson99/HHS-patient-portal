#!/bin/bash

# HHS Patient Portal Docker Build Script
# This script builds and runs the complete application stack

set -e

echo "🏥 Building HHS Patient Portal Docker Image..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo ""
    echo "💡 For WSL 2 integration with Docker Desktop:"
    echo "   1. Open Docker Desktop on Windows"
    echo "   2. Go to Settings → Resources → WSL Integration"
    echo "   3. Enable integration for your distro"
    echo "   4. Click Apply & Restart"
    echo ""
    echo "💡 Or install Docker natively in WSL:"
    echo "   sudo apt-get update && sudo apt-get install docker.io docker-compose"
    echo "   sudo usermod -aG docker \$USER"
    echo "   Log out and back in, then try again"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed."
    echo "💡 Install with: sudo apt-get install docker-compose"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update .env with your configuration"
fi

# Determine if we need to use sudo
DOCKER_CMD="docker"
if ! docker ps &> /dev/null; then
    echo "💡 Using sudo for Docker commands..."
    DOCKER_CMD="sudo docker"
fi

# Build the Docker image
echo "🔨 Building Docker image..."
$DOCKER_CMD build -t hhs-patient-portal:latest .

# Start the services
echo "🚀 Starting services with Docker Compose..."
if [[ $DOCKER_CMD == *"sudo"* ]]; then
    sudo docker-compose up -d
else
    docker-compose up -d
fi

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are healthy
echo "✅ Checking service health..."
if [[ $DOCKER_CMD == *"sudo"* ]]; then
    sudo docker-compose ps
else
    docker-compose ps
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║       🏥 HHS Patient Portal - Docker Setup Complete    ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║                                                        ║"
echo "║  API:             http://localhost:3000               ║"
echo "║  Web Portal:      http://localhost:80                 ║"
echo "║  Database:        localhost:5432                      ║"
echo "║  Redis:           localhost:6379                      ║"
echo "║                                                        ║"
echo "║  Test Credentials:                                    ║"
echo "║  Patient:         patient1 / Patient123!              ║"
echo "║  Doctor:          doctor1 / Doctor123!                ║"
echo "║                                                        ║"
echo "║  Docker Commands:                                     ║"
echo "║  - View logs:      docker-compose logs -f             ║"
echo "║  - Stop:           docker-compose down                ║"
echo "║  - Restart:        docker-compose restart             ║"
echo "║  - Shell into API: docker exec -it hhs-api bash       ║"
echo "║                                                        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
