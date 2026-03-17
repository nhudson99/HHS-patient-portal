#!/usr/bin/env bash
set -euo pipefail

# HHS Patient Portal - Azure deploy helper
# Deploys API + Web to Azure Container Apps using Azure CLI.
#
# Usage:
#   chmod +x ./azure-deploy.sh
#   ./azure-deploy.sh
#
# Optional env overrides before running:
#   export AZ_SUBSCRIPTION_ID="..."
#   export AZ_LOCATION="eastus"
#   export AZ_RESOURCE_GROUP="hhs-prod-rg"
#   export AZ_ACR_NAME="hhsprodacr123"   # must be globally unique
#   export AZ_CONTAINERAPPS_ENV="hhs-prod-env"
#   export AZ_API_APP_NAME="hhs-api"
#   export AZ_WEB_APP_NAME="hhs-web"
#   export APP_DOMAIN="portal.example.com" # optional custom domain

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

AZ_LOCATION="${AZ_LOCATION:-eastus}"
AZ_RESOURCE_GROUP="${AZ_RESOURCE_GROUP:-hhs-prod-rg}"
AZ_CONTAINERAPPS_ENV="${AZ_CONTAINERAPPS_ENV:-hhs-prod-env}"
AZ_API_APP_NAME="${AZ_API_APP_NAME:-hhs-api}"
AZ_WEB_APP_NAME="${AZ_WEB_APP_NAME:-hhs-web}"
AZ_ACR_NAME="${AZ_ACR_NAME:-hhsprodacr$RANDOM$RANDOM}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
APP_DOMAIN="${APP_DOMAIN:-}"

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

echo "🐳 Building and pushing API image..."
docker build -t "$ACR_LOGIN_SERVER/$AZ_API_APP_NAME:$IMAGE_TAG" -f "$ROOT_DIR/Dockerfile" "$ROOT_DIR"
docker push "$ACR_LOGIN_SERVER/$AZ_API_APP_NAME:$IMAGE_TAG"

echo "🚀 Deploying API container app..."
if ! az containerapp show --name "$AZ_API_APP_NAME" --resource-group "$AZ_RESOURCE_GROUP" >/dev/null 2>&1; then
  az containerapp create \
    --name "$AZ_API_APP_NAME" \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --environment "$AZ_CONTAINERAPPS_ENV" \
    --image "$ACR_LOGIN_SERVER/$AZ_API_APP_NAME:$IMAGE_TAG" \
    --registry-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_USERNAME" \
    --registry-password "$ACR_PASSWORD" \
    --target-port 3000 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --secrets \
      db-password="$DB_PASSWORD" \
      session-secret="$SESSION_SECRET" \
      jwt-secret="$JWT_SECRET" \
      github-token="${GITHUB_TOKEN:-}" \
    --env-vars \
      FLASK_ENV=production \
      NODE_ENV=production \
      FORCE_HTTPS=true \
      PORT=3000 \
      PYTHONPATH=/app \
      DB_HOST="${DB_HOST:-}" \
      DB_PORT="${DB_PORT:-5432}" \
      DB_NAME="$DB_NAME" \
      DB_USER="$DB_USER" \
      DB_SSLMODE="${DB_SSLMODE:-require}" \
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
      FORCE_HTTPS=true \
      PORT=3000 \
      PYTHONPATH=/app \
      DB_HOST="${DB_HOST:-}" \
      DB_PORT="${DB_PORT:-5432}" \
      DB_NAME="$DB_NAME" \
      DB_USER="$DB_USER" \
      DB_SSLMODE="${DB_SSLMODE:-require}" \
      REDIS_URL="${REDIS_URL:-}" \
      ALLOWED_ORIGINS="$ALLOWED_ORIGINS" \
      MAX_LOGIN_ATTEMPTS="${MAX_LOGIN_ATTEMPTS:-5}" \
      ACCOUNT_LOCKOUT_MINUTES="${ACCOUNT_LOCKOUT_MINUTES:-30}" \
      SESSION_TIMEOUT_MINUTES="${SESSION_TIMEOUT_MINUTES:-15}" \
      GITHUB_REPO="${GITHUB_REPO:-}" \
      GITHUB_FEATURE_REQUEST_LABELS="${GITHUB_FEATURE_REQUEST_LABELS:-feature-request}" \
      AZURE_TENANT_ID="$AZURE_TENANT_ID" \
      AZURE_CLIENT_ID="$AZURE_CLIENT_ID" >/dev/null

  az containerapp secret set \
    --name "$AZ_API_APP_NAME" \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --secrets \
      db-password="$DB_PASSWORD" \
      session-secret="$SESSION_SECRET" \
      jwt-secret="$JWT_SECRET" \
      github-token="${GITHUB_TOKEN:-}" >/dev/null

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
API_UPSTREAM="https://$API_FQDN"

echo "🐳 Building and pushing Web image..."
docker build -t "$ACR_LOGIN_SERVER/$AZ_WEB_APP_NAME:$IMAGE_TAG" -f "$ROOT_DIR/Dockerfile.web" "$ROOT_DIR"
docker push "$ACR_LOGIN_SERVER/$AZ_WEB_APP_NAME:$IMAGE_TAG"

echo "🚀 Deploying Web container app..."
if ! az containerapp show --name "$AZ_WEB_APP_NAME" --resource-group "$AZ_RESOURCE_GROUP" >/dev/null 2>&1; then
  az containerapp create \
    --name "$AZ_WEB_APP_NAME" \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --environment "$AZ_CONTAINERAPPS_ENV" \
    --image "$ACR_LOGIN_SERVER/$AZ_WEB_APP_NAME:$IMAGE_TAG" \
    --registry-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_USERNAME" \
    --registry-password "$ACR_PASSWORD" \
    --target-port 80 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --env-vars API_UPSTREAM="$API_UPSTREAM" >/dev/null
else
  az containerapp update \
    --name "$AZ_WEB_APP_NAME" \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --image "$ACR_LOGIN_SERVER/$AZ_WEB_APP_NAME:$IMAGE_TAG" \
    --set-env-vars API_UPSTREAM="$API_UPSTREAM" >/dev/null
fi

WEB_FQDN="$(az containerapp show --name "$AZ_WEB_APP_NAME" --resource-group "$AZ_RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv)"

echo ""
echo "✅ Deployment complete"
echo "API URL: https://$API_FQDN"
echo "WEB URL: https://$WEB_FQDN"

echo ""
echo "Next Azure portal steps:"
echo "1) Add custom domain to web app (optional): $APP_DOMAIN"
echo "2) Add TLS cert (managed)"
echo "3) In Azure AD app registration, add redirect URI: https://$WEB_FQDN/admin"
if [[ -n "$APP_DOMAIN" ]]; then
  echo "   and: https://$APP_DOMAIN/admin"
fi
