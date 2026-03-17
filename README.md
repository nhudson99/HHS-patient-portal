# HHS-patient-portal
Out of the box Hudson Health System Patient Portal

## Azure production deploy (terminal)

This repo includes `azure-deploy.sh` to deploy API + web to Azure Container Apps.

### 1) Connect terminal to Azure

```bash
az login
az account list -o table
az account set --subscription "<YOUR_SUBSCRIPTION_ID_OR_NAME>"
```

### 2) Set Azure resource names (optional)

```bash
export AZ_SUBSCRIPTION_ID="<YOUR_SUBSCRIPTION_ID>"
export AZ_LOCATION="eastus"
export AZ_RESOURCE_GROUP="hhs-prod-rg"
export AZ_ACR_NAME="hhsprodacr123"   # must be globally unique
export AZ_CONTAINERAPPS_ENV="hhs-prod-env"
export AZ_API_APP_NAME="hhs-api"
export AZ_WEB_APP_NAME="hhs-web"
```

### 3) Run deploy script

```bash
chmod +x ./azure-deploy.sh
./azure-deploy.sh
```

### 4) Required env vars

`azure-deploy.sh` reads from `.env` by default and requires at minimum:

- `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `SESSION_SECRET`, `JWT_SECRET`
- `ALLOWED_ORIGINS`
- `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`

### 5) Post-deploy Azure AD callback

After deploy, add this redirect URI to your Azure app registration (SPA platform):

- `https://<WEB_FQDN>/admin`

