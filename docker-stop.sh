#!/bin/bash

# HHS Patient Portal Docker Stop Script
# Stops all containers cleanly

set -e

echo "🏥 Stopping HHS Patient Portal..."

# Determine if we need to use sudo
DOCKER_CMD="docker"
if ! docker ps &> /dev/null; then
    echo "💡 Using sudo for Docker commands..."
    DOCKER_CMD="sudo docker"
fi

# Stop the services
echo "⏹️  Stopping services..."
if [[ $DOCKER_CMD == *"sudo"* ]]; then
    sudo docker-compose down 2>/dev/null || true
else
    docker-compose down 2>/dev/null || true
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║       🏥 HHS Patient Portal - Services Stopped        ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║                                                        ║"
echo "║  ✅ All containers have been stopped                   ║"
echo "║                                                        ║"
echo "║  To start again:  ./docker-start.sh                   ║"
echo "║  To rebuild:      ./docker-build.sh                   ║"
echo "║                                                        ║"
echo "╚════════════════════════════════════════════════════════╝"
