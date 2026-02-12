#!/bin/bash

# HHS Patient Portal Docker Build Script
# This script builds and runs the complete application stack

set -e

echo "🏥 Building HHS Patient Portal Docker Image..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update .env with your configuration"
fi

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t hhs-patient-portal:latest .

# Start the services
echo "🚀 Starting services with Docker Compose..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are healthy
echo "✅ Checking service health..."
docker-compose ps

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
