#!/usr/bin/env bash
set -euo pipefail

: "${API_UPSTREAM:?API_UPSTREAM env var is required, e.g. https://hhs-api.<hash>.azurecontainerapps.io}"

envsubst '${API_UPSTREAM}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
