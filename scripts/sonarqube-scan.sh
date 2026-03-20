#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "${SONAR_HOST_URL:-}" || -z "${SONAR_TOKEN:-}" ]]; then
  echo "SONAR_HOST_URL and SONAR_TOKEN must be set before scanning."
  exit 1
fi

npm run test:unit
npm run sonar:scan
