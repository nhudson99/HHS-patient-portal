#!/bin/bash

# HHS Patient Portal Docker Start Script
# Starts the application containers without rebuilding

set -e

echo "🏥 Starting HHS Patient Portal..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    exit 1
fi

# Determine if we need to use sudo
DOCKER_CMD="docker"
if ! docker ps &> /dev/null; then
    echo "💡 Using sudo for Docker commands..."
    DOCKER_CMD="sudo docker"
fi

# Start the services
echo "🚀 Starting services with Docker Compose..."
if [[ $DOCKER_CMD == *"sudo"* ]]; then
    sudo docker-compose up -d
else
    docker-compose up -d
fi

# Wait for services to stabilize
echo "⏳ Waiting for services to stabilize..."
sleep 5

# Check if services are healthy
echo "✅ Checking service health..."
if [[ $DOCKER_CMD == *"sudo"* ]]; then
    sudo docker-compose ps
else
    docker-compose ps
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║       🏥 HHS Patient Portal - Services Started        ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║                                                        ║"
echo "║  Web Portal:      http://localhost                    ║"
echo "║  API:             http://localhost:3000               ║"
echo "║  Database:        localhost:5432                      ║"
echo "║                                                        ║"
echo "║  Test Credentials:                                     ║"
echo "║    Patient:  patient1 / Patient123!                   ║"
echo "║    Doctor:   doctor1 / Doctor123!                     ║"
echo "║                                                        ║"
echo "║  View logs:  docker-compose logs -f [service]         ║"
echo "║  Stop:       ./docker-stop.sh                         ║"
echo "║                                                        ║"
echo "╚════════════════════════════════════════════════════════╝"
