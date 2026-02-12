#!/bin/bash

# Stop and remove all containers
echo "🛑 Stopping and removing containers..."
docker-compose down -v

echo "✅ Docker environment cleaned up"
