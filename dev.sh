#!/bin/bash
# dev.sh — quick commands for local development
# Usage: ./dev.sh [command]

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

SUDO_CMD=""
docker ps &>/dev/null 2>&1 || SUDO_CMD="sudo"

case "${1:-help}" in

  # ── Start everything in dev mode ───────────────────────────────────────────
  up)
    echo -e "${BLUE}🚀 Starting dev stack (Vue build + live Python reload)...${NC}"
    # Force-recreate the one-shot frontend builder so ./dist matches current source.
    # Plain `docker compose up` will not re-run an already-exited frontend container.
    echo -e "${BLUE}⚡ Building Vue frontend (compose service: frontend)...${NC}"
    $SUDO_CMD docker compose up --force-recreate --no-deps frontend
    $SUDO_CMD docker compose up -d
    echo -e "${GREEN}✅ Running at http://localhost:80${NC}"
    echo -e "${YELLOW}   Python changes: save the file → Flask auto-reloads (no rebuild)${NC}"
    echo -e "${YELLOW}   Vue changes:    ./dev.sh up  (or ./dev.sh frontend) to rebuild dist/${NC}"
    ;;

  # ── Rebuild + reload only the API container (e.g. new pip package) ─────────
  api)
    echo -e "${BLUE}🔨 Rebuilding API image (use after requirements.txt changes)...${NC}"
    $SUDO_CMD docker compose build api
    $SUDO_CMD docker compose up -d api
    echo -e "${GREEN}✅ API restarted${NC}"
    ;;

  # ── Restart API without rebuilding (picks up mounted code changes) ─────────
  reload)
    echo -e "${BLUE}🔄 Recreating API container (applies .env + mounted code changes)...${NC}"
    $SUDO_CMD docker compose up -d --force-recreate api
    echo -e "${GREEN}✅ API recreated${NC}"
    ;;

  # ── Rebuild Vue frontend, then reload nginx ────────────────────────────────
  frontend)
    echo -e "${BLUE}⚡ Building Vue frontend (compose service: frontend)...${NC}"
    $SUDO_CMD docker compose up --force-recreate --no-deps frontend
    if $SUDO_CMD docker compose ps --status running --services 2>/dev/null | grep -qx nginx; then
      echo -e "${BLUE}🔄 Reloading nginx...${NC}"
      $SUDO_CMD docker compose exec nginx nginx -s reload
    fi
    echo -e "${GREEN}✅ Frontend updated at http://localhost:80${NC}"
    ;;

  # ── Rebuild both frontend AND backend from scratch ─────────────────────────
  rebuild)
    echo -e "${BLUE}🔨 Full rebuild (frontend via compose + API image)...${NC}"
    $SUDO_CMD docker compose build api
    $SUDO_CMD docker compose up --force-recreate --no-deps frontend
    $SUDO_CMD docker compose up -d
    echo -e "${GREEN}✅ Full rebuild complete${NC}"
    ;;

  # ── Show live logs ──────────────────────────────────────────────────────────
  logs)
    $SUDO_CMD docker compose logs -f "${2:-api}"
    ;;

  # ── Stop everything ─────────────────────────────────────────────────────────
  down)
    $SUDO_CMD docker compose down
    echo -e "${GREEN}✅ Stack stopped${NC}"
    ;;

  # ── Service status ──────────────────────────────────────────────────────────
  status)
    $SUDO_CMD docker compose ps
    ;;

  # ── Help ────────────────────────────────────────────────────────────────────
  *)
    echo -e "${BLUE}Usage: ./dev.sh <command>${NC}"
    echo ""
    echo "  up          Start stack (rebuilds Vue dist/, live Python reload)"
    echo "  reload      Recreate API container only (applies .env changes)"
    echo "  frontend    Rebuild Vue via compose → reload nginx"
    echo "  api         Rebuild API image           (for requirements.txt changes)"
    echo "  rebuild     Full rebuild (frontend via compose + API image)"
    echo "  logs [svc]  Tail logs (default: api)"
    echo "  down        Stop everything"
    echo "  status      Show container status"
    echo ""
    echo -e "${YELLOW}Cheat-sheet:${NC}"
    echo "  Python file changed?  →  just save — Flask auto-reloads"
    echo "  Vue file changed?     →  ./dev.sh frontend   (or ./dev.sh up)"
    echo "  Added a pip package?  →  ./dev.sh api"
    echo "  Changed .env values?  →  ./dev.sh reload"
    echo "  Clean slate?          →  ./dev.sh rebuild"
    ;;
esac
