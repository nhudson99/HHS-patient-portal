#!/bin/bash

# HHS Patient Portal Docker Build Script
# Uses Docker Compose v2 (plugin) for modern, reliable container management

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🏥 HHS Patient Portal - Docker Setup${NC}"

# Check Docker and Docker Compose v2 installation
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found${NC}"
    echo "Install from: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose v2 plugin not found${NC}"
    echo "Install with: apt install docker-compose-plugin (Linux) or brew install docker-compose (macOS)"
    exit 1
fi

# Create .env if missing
if [ ! -f .env ]; then
    echo -e "${BLUE}📝 Creating .env...${NC}"
    cp .env.example .env || { echo -e "${RED}❌ .env.example not found${NC}"; exit 1; }
fi

# Test Docker access
SUDO_CMD=""
if ! docker ps &> /dev/null 2>&1; then
    SUDO_CMD="sudo"
fi

# Helper functions
build() {
    echo -e "${BLUE}🔨 Building Docker image...${NC}"
    $SUDO_CMD docker compose build --pull
    echo -e "${GREEN}✅ Build complete${NC}"
}

start() {
    echo -e "${BLUE}🚀 Starting services...${NC}"
    $SUDO_CMD docker compose up -d
    sleep 2
    echo -e "${BLUE}✅ Services started - checking health...${NC}"
    $SUDO_CMD docker compose ps
}

stop() {
    echo -e "${BLUE}⏹️  Stopping...${NC}"
    $SUDO_CMD docker compose down
    echo -e "${GREEN}✅ Stopped${NC}"
}

logs() {
    $SUDO_CMD docker compose logs -f "${1:-.}"
}

status() {
    echo -e "${BLUE}📊 Service status:${NC}"
    $SUDO_CMD docker compose ps
}

clean() {
    echo -e "${YELLOW}🧹 Removing volumes...${NC}"
    $SUDO_CMD docker compose down -v
    echo -e "${GREEN}✅ Cleaned${NC}"
}

reset() {
    echo -e "${YELLOW}⚠️  Hard reset - remove all containers/volumes/images${NC}"
    read -p "Continue? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        $SUDO_CMD docker compose down -v --remove-orphans
        $SUDO_CMD docker rmi hhs-patient-portal:latest 2>/dev/null || true
        echo -e "${GREEN}✅ Reset${NC}"
    fi
}

show_help() {
    echo "Commands:"
    echo "  build              Build images"
    echo "  start              Start services"
    echo "  stop               Stop services"
    echo "  restart            Restart services"
    echo "  logs [svc]         View logs"
    echo "  status             Service status"
    echo "  clean              Remove volumes"
    echo "  reset              Hard reset"
    echo "  help               Show this"
}

# Main
case "${1:-build}" in
    build) build ;;
    start) start ;;
    stop) stop ;;
    restart) stop; sleep 1; start ;;
    logs) logs "$2" ;;
    status) status ;;
    clean) clean ;;
    reset) reset ;;
    help|--help|-h) show_help ;;
    "") build; echo ""; start ;;
    *)
        echo -e "${RED}Unknown: $1${NC}"
        show_help
        exit 1
        ;;
esac

# Summary
if [[ "${1:-}" == "start" ]] || [[ "${1:-}" == "build" ]] || [[ "${1:-}" == "" ]]; then
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  🏥 HHS Patient Portal - Setup Complete  ║${NC}"
    echo -e "${GREEN}╠════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║  API:        http://localhost:3000        ║${NC}"
    echo -e "${GREEN}║  Web:        http://localhost:80          ║${NC}"
    echo -e "${GREEN}║  DB:         localhost:5432              ║${NC}"
    echo -e "${GREEN}║  Redis:      localhost:6379              ║${NC}"
    echo -e "${GREEN}║                                            ║${NC}"
    echo -e "${GREEN}║  Patient:    patient1 / Patient123!       ║${NC}"
    echo -e "${GREEN}║  Doctor:     doctor1 / Doctor123!         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
fi
