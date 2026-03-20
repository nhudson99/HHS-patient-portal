#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${SONAR_ENV_FILE:-$ROOT_DIR/.env.sonarqube}"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT_DIR/.env.sonarqube.example" "$ENV_FILE"
  echo "Created $ENV_FILE from template. Update values if needed, then rerun if desired."
fi

docker compose \
  --env-file "$ENV_FILE" \
  -f "$ROOT_DIR/docker-compose.sonarqube.yml" \
  up -d

echo "SonarQube starting on http://localhost:${SONAR_PORT:-9000}"
