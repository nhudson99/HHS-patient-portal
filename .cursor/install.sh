#!/bin/bash
# Idempotent cloud-agent install: deps + frontend build (no docker compose up here).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  cp .env.docker.example .env
  echo "Created .env from .env.docker.example"
fi

npm install

if [ ! -d venv ]; then
  python3 -m venv venv
fi
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt -r requirements-dev.txt

npm run build
