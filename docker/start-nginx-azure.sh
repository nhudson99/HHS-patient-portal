#!/usr/bin/env bash
set -euo pipefail

# Default to localhost if not provided (local dev) or use external upstream if provided
API_UPSTREAM="${API_UPSTREAM:-http://127.0.0.1:3000}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-1}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-180}"
GUNICORN_THREADS="${GUNICORN_THREADS:-2}"

# Create nginx config from template
envsubst '${API_UPSTREAM}' < /etc/nginx/templates/default.conf.template > /etc/nginx/sites-enabled/default

# Start gunicorn in background
gunicorn \
  --bind 0.0.0.0:3000 \
  --workers "$GUNICORN_WORKERS" \
  --threads "$GUNICORN_THREADS" \
  --worker-class sync \
  --timeout "$GUNICORN_TIMEOUT" \
  --access-logfile - \
  --error-logfile - \
  api.app:app &

# Give gunicorn time to start
sleep 2

# Run nginx in foreground
nginx -g 'daemon off;'
