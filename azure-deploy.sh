#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

AZ_LOCATION="${AZ_LOCATION:-eastus}"
AZ_RESOURCE_GROUP="${AZ_RESOURCE_GROUP:-hhs-prod-rg}"
AZ_CONTAINERAPPS_ENV="${AZ_CONTAINERAPPS_ENV:-hhs-prod-env}"
AZ_API_APP_NAME="${AZ_API_APP_NAME:-hhs-api}"
AZ_ACR_NAME="${AZ_ACR_NAME:-hhsprodreg}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
APP_DOMAIN="${APP_DOMAIN:-}"

is_local_db_host() {
  local host="${1:-}"
  [[ -z "$host" || "$host" == "localhost" || "$host" == "127.0.0.1" ]]
}

required_bins=(az docker)
for bin in "${required_bins[@]}"; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "❌ Missing required command: $bin"
    exit 1
  fi
done

if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ Env file not found at $ENV_FILE"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

required_env=(
  DB_NAME
  DB_USER
  DB_PASSWORD
  SESSION_SECRET
  JWT_SECRET
  ALLOWED_ORIGINS
  AZURE_TENANT_ID
  AZURE_CLIENT_ID
)

for key in "${required_env[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    echo "❌ Missing required env var in $ENV_FILE: $key"
    exit 1
  fi
done

if ! az extension show --name containerapp >/dev/null 2>&1; then
  az extension add --name containerapp >/dev/null
else
  az extension update --name containerapp >/dev/null || true
fi

if ! az account show >/dev/null 2>&1; then
  echo "🔐 No Azure session found. Opening login..."
  az login >/dev/null
fi

if [[ -n "${AZ_SUBSCRIPTION_ID:-}" ]]; then
  az account set --subscription "$AZ_SUBSCRIPTION_ID"
fi

echo "📦 Ensuring resource group + registry + environment..."
az group create --name "$AZ_RESOURCE_GROUP" --location "$AZ_LOCATION" >/dev/null

if ! az acr show --name "$AZ_ACR_NAME" --resource-group "$AZ_RESOURCE_GROUP" >/dev/null 2>&1; then
  az acr create --resource-group "$AZ_RESOURCE_GROUP" --name "$AZ_ACR_NAME" --sku Basic >/dev/null
fi

az acr update --name "$AZ_ACR_NAME" --admin-enabled true >/dev/null
ACR_LOGIN_SERVER="$(az acr show --name "$AZ_ACR_NAME" --resource-group "$AZ_RESOURCE_GROUP" --query loginServer -o tsv)"
ACR_USERNAME="$(az acr credential show --name "$AZ_ACR_NAME" --query username -o tsv)"
ACR_PASSWORD="$(az acr credential show --name "$AZ_ACR_NAME" --query 'passwords[0].value' -o tsv)"

if ! az containerapp env show --name "$AZ_CONTAINERAPPS_ENV" --resource-group "$AZ_RESOURCE_GROUP" >/dev/null 2>&1; then
  az containerapp env create \
    --name "$AZ_CONTAINERAPPS_ENV" \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --location "$AZ_LOCATION" >/dev/null
fi

APP_EXISTS=false
if az containerapp show --name "$AZ_API_APP_NAME" --resource-group "$AZ_RESOURCE_GROUP" >/dev/null 2>&1; then
  APP_EXISTS=true
fi

DEPLOY_DB_HOST="${DB_HOST:-}"
DEPLOY_DB_PORT="${DB_PORT:-5432}"
DEPLOY_DB_NAME="$DB_NAME"
DEPLOY_DB_USER="$DB_USER"
DEPLOY_DB_SSLMODE="${DB_SSLMODE:-require}"

if [[ "$APP_EXISTS" == "true" ]]; then
  EXISTING_DB_HOST="$(az containerapp show --name "$AZ_API_APP_NAME" --resource-group "$AZ_RESOURCE_GROUP" --query "properties.template.containers[0].env[?name=='DB_HOST'].value | [0]" -o tsv 2>/dev/null || true)"
  EXISTING_DB_PORT="$(az containerapp show --name "$AZ_API_APP_NAME" --resource-group "$AZ_RESOURCE_GROUP" --query "properties.template.containers[0].env[?name=='DB_PORT'].value | [0]" -o tsv 2>/dev/null || true)"
  EXISTING_DB_NAME="$(az containerapp show --name "$AZ_API_APP_NAME" --resource-group "$AZ_RESOURCE_GROUP" --query "properties.template.containers[0].env[?name=='DB_NAME'].value | [0]" -o tsv 2>/dev/null || true)"
  EXISTING_DB_USER="$(az containerapp show --name "$AZ_API_APP_NAME" --resource-group "$AZ_RESOURCE_GROUP" --query "properties.template.containers[0].env[?name=='DB_USER'].value | [0]" -o tsv 2>/dev/null || true)"
  EXISTING_DB_SSLMODE="$(az containerapp show --name "$AZ_API_APP_NAME" --resource-group "$AZ_RESOURCE_GROUP" --query "properties.template.containers[0].env[?name=='DB_SSLMODE'].value | [0]" -o tsv 2>/dev/null || true)"

  if is_local_db_host "$DEPLOY_DB_HOST" && ! is_local_db_host "$EXISTING_DB_HOST"; then
    echo "ℹ️ Reusing existing non-local DB settings from deployed container app."
    DEPLOY_DB_HOST="$EXISTING_DB_HOST"
    DEPLOY_DB_PORT="${EXISTING_DB_PORT:-$DEPLOY_DB_PORT}"
    DEPLOY_DB_NAME="${EXISTING_DB_NAME:-$DEPLOY_DB_NAME}"
    DEPLOY_DB_USER="${EXISTING_DB_USER:-$DEPLOY_DB_USER}"
    DEPLOY_DB_SSLMODE="${EXISTING_DB_SSLMODE:-$DEPLOY_DB_SSLMODE}"
  fi
fi

if is_local_db_host "$DEPLOY_DB_HOST"; then
  echo "❌ Refusing Azure deploy with local DB host ($DEPLOY_DB_HOST)."
  echo "   Set DB_HOST to your managed PostgreSQL host before running ./azure-deploy.sh"
  exit 1
fi

UPDATE_DB_PASSWORD_SECRET=true
if [[ -z "${DB_PASSWORD:-}" || "${DB_PASSWORD:-}" == "postgres" ]]; then
  UPDATE_DB_PASSWORD_SECRET=false
fi

GITHUB_TOKEN_SECRET_VALUE="${GITHUB_TOKEN:-}"
if [[ -z "$GITHUB_TOKEN_SECRET_VALUE" ]]; then
  echo "ℹ️ GITHUB_TOKEN is not set; using disabled placeholder for github-token secret."
  GITHUB_TOKEN_SECRET_VALUE="disabled"
fi

echo "🔐 Authenticating Docker with ACR..."
az acr login --name "$AZ_ACR_NAME" >/dev/null

echo "🐳 Building and pushing API image..."
docker build \
  --build-arg VITE_AZURE_CLIENT_ID="$AZURE_CLIENT_ID" \
  --build-arg VITE_AZURE_TENANT_ID="$AZURE_TENANT_ID" \
  --build-arg VITE_AZURE_REDIRECT_URI="${VITE_AZURE_REDIRECT_URI:-}" \
  -t "$ACR_LOGIN_SERVER/$AZ_API_APP_NAME:$IMAGE_TAG" \
  -f "$ROOT_DIR/Dockerfile" \
  "$ROOT_DIR"
docker push "$ACR_LOGIN_SERVER/$AZ_API_APP_NAME:$IMAGE_TAG"

echo "🚀 Deploying API container app..."
if [[ "$APP_EXISTS" != "true" ]]; then
  az containerapp create \
    --name "$AZ_API_APP_NAME" \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --environment "$AZ_CONTAINERAPPS_ENV" \
    --image "$ACR_LOGIN_SERVER/$AZ_API_APP_NAME:$IMAGE_TAG" \
    --registry-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_USERNAME" \
    --registry-password "$ACR_PASSWORD" \
    --target-port 80 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --secrets \
      db-password="$DB_PASSWORD" \
      session-secret="$SESSION_SECRET" \
      jwt-secret="$JWT_SECRET" \
      github-token="$GITHUB_TOKEN_SECRET_VALUE" \
    --env-vars \
      FLASK_ENV=production \
      NODE_ENV=production \
      FORCE_HTTPS="${FORCE_HTTPS:-false}" \
      PORT=3000 \
      PYTHONPATH=/app \
      API_UPSTREAM="http://127.0.0.1:3000" \
      GUNICORN_WORKERS="${GUNICORN_WORKERS:-1}" \
      GUNICORN_THREADS="${GUNICORN_THREADS:-2}" \
      GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-180}" \
      DB_HOST="$DEPLOY_DB_HOST" \
      DB_PORT="$DEPLOY_DB_PORT" \
      DB_NAME="$DEPLOY_DB_NAME" \
      DB_USER="$DEPLOY_DB_USER" \
      DB_SSLMODE="$DEPLOY_DB_SSLMODE" \
      DB_PASSWORD=secretref:db-password \
      REDIS_URL="${REDIS_URL:-}" \
      SESSION_SECRET=secretref:session-secret \
      JWT_SECRET=secretref:jwt-secret \
      ALLOWED_ORIGINS="$ALLOWED_ORIGINS" \
      MAX_LOGIN_ATTEMPTS="${MAX_LOGIN_ATTEMPTS:-5}" \
      ACCOUNT_LOCKOUT_MINUTES="${ACCOUNT_LOCKOUT_MINUTES:-30}" \
      SESSION_TIMEOUT_MINUTES="${SESSION_TIMEOUT_MINUTES:-15}" \
      GITHUB_REPO="${GITHUB_REPO:-}" \
      GITHUB_FEATURE_REQUEST_LABELS="${GITHUB_FEATURE_REQUEST_LABELS:-feature-request}" \
      GITHUB_TOKEN=secretref:github-token \
      AZURE_TENANT_ID="$AZURE_TENANT_ID" \
      AZURE_CLIENT_ID="$AZURE_CLIENT_ID" >/dev/null
else
  az containerapp update \
    --name "$AZ_API_APP_NAME" \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --image "$ACR_LOGIN_SERVER/$AZ_API_APP_NAME:$IMAGE_TAG" \
    --set-env-vars \
      FLASK_ENV=production \
      NODE_ENV=production \
      FORCE_HTTPS="${FORCE_HTTPS:-false}" \
      PORT=3000 \
      PYTHONPATH=/app \
      API_UPSTREAM="http://127.0.0.1:3000" \
      GUNICORN_WORKERS="${GUNICORN_WORKERS:-1}" \
      GUNICORN_THREADS="${GUNICORN_THREADS:-2}" \
      GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-180}" \
      DB_HOST="$DEPLOY_DB_HOST" \
      DB_PORT="$DEPLOY_DB_PORT" \
      DB_NAME="$DEPLOY_DB_NAME" \
      DB_USER="$DEPLOY_DB_USER" \
      DB_SSLMODE="$DEPLOY_DB_SSLMODE" \
      REDIS_URL="${REDIS_URL:-}" \
      ALLOWED_ORIGINS="$ALLOWED_ORIGINS" \
      MAX_LOGIN_ATTEMPTS="${MAX_LOGIN_ATTEMPTS:-5}" \
      ACCOUNT_LOCKOUT_MINUTES="${ACCOUNT_LOCKOUT_MINUTES:-30}" \
      SESSION_TIMEOUT_MINUTES="${SESSION_TIMEOUT_MINUTES:-15}" \
      GITHUB_REPO="${GITHUB_REPO:-}" \
      GITHUB_FEATURE_REQUEST_LABELS="${GITHUB_FEATURE_REQUEST_LABELS:-feature-request}" \
      AZURE_TENANT_ID="$AZURE_TENANT_ID" \
      AZURE_CLIENT_ID="$AZURE_CLIENT_ID" >/dev/null

  if [[ "$UPDATE_DB_PASSWORD_SECRET" == "true" ]]; then
    az containerapp secret set \
      --name "$AZ_API_APP_NAME" \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --secrets \
        db-password="$DB_PASSWORD" \
        session-secret="$SESSION_SECRET" \
        jwt-secret="$JWT_SECRET" \
        github-token="$GITHUB_TOKEN_SECRET_VALUE" >/dev/null
  else
    az containerapp secret set \
      --name "$AZ_API_APP_NAME" \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --secrets \
        session-secret="$SESSION_SECRET" \
        jwt-secret="$JWT_SECRET" \
        github-token="$GITHUB_TOKEN_SECRET_VALUE" >/dev/null
  fi

  az containerapp update \
    --name "$AZ_API_APP_NAME" \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --set-env-vars \
      DB_PASSWORD=secretref:db-password \
      SESSION_SECRET=secretref:session-secret \
      JWT_SECRET=secretref:jwt-secret \
      GITHUB_TOKEN=secretref:github-token >/dev/null
fi

API_FQDN="$(az containerapp show --name "$AZ_API_APP_NAME" --resource-group "$AZ_RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv)"

echo "✅ API Deployment complete!"
echo "API FQDN: $API_FQDN"
echo ""
echo "🎉 Your application is now live!"
echo "   API + Web: https://$API_FQDN"
echo ""
echo "⚠️  Next steps in Azure Portal:"
echo "   1) Add redirect URI to Azure AD app: https://$API_FQDN/admin"
echo "   2) (Optional) Configure custom domain for $APP_DOMAIN"

if [[ -n "$APP_DOMAIN" ]]; then
  echo "   and: https://$APP_DOMAIN/admin"
fi
