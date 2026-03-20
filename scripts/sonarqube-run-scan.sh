#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "${SONAR_HOST_URL:-}" || -z "${SONAR_TOKEN:-}" ]]; then
  echo "SONAR_HOST_URL and SONAR_TOKEN must be set before scanning."
  exit 1
fi

if command -v sonar-scanner >/dev/null 2>&1; then
  echo "Using local sonar-scanner binary"
  exec sonar-scanner
fi

if command -v docker >/dev/null 2>&1; then
  echo "Using Docker SonarScanner CLI image"
  exec docker run --rm \
    --network host \
    -e SONAR_HOST_URL \
    -e SONAR_TOKEN \
    -v "$ROOT_DIR:/usr/src" \
    sonarsource/sonar-scanner-cli
fi

if command -v npx >/dev/null 2>&1; then
  echo "Local sonar-scanner not found; using npx sonar-scanner"
  exec npx --yes sonar-scanner
fi

echo "No scanner runtime found (sonar-scanner, npx, or docker)."
exit 1
