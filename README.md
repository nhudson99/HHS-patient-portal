# HHS-patient-portal
Out of the box Hudson Health System Patient Portal

## Production hardening checklist

- Use non-local DB values in `.env` for cloud deploy (`DB_HOST`, `DB_PORT`, `DB_SSLMODE=require`).
- Set strong `SESSION_SECRET` and `JWT_SECRET` (64+ random bytes).
- Configure `ALLOWED_ORIGINS` to exact production domains only.
- For multi-replica deployments, set `RATELIMIT_STORAGE_URI` to Redis instead of `memory://`.
- Keep `FORCE_HTTPS=false` in Azure Container Apps if TLS terminates at ingress.
- Store sensitive values in Azure secrets; never commit `.env`.

## HIPAA compliance and security review

The app includes baseline controls aligned to HIPAA Security Rule safeguards:

- Administrative: audit logging retention controls via `AUDIT_LOG_RETENTION_DAYS`.
- Technical: role-based auth, session timeout, account lockout, password policy, request rate limiting.
- Transmission/storage: TLS at ingress, DB SSL mode support, server-side secret usage.

Before go-live, validate these required controls in your environment:

1. Encrypt backups and database storage at rest.
2. Enable centralized immutable audit log export (SIEM/Sentinel).
3. Enforce MFA for all clinical/admin users.
4. Run quarterly access reviews and least-privilege checks.
5. Maintain BAA coverage for all vendors handling PHI.
6. Establish incident response and breach notification runbooks.

See `DEPLOYMENT.md` and `.env.example` for deployment/runtime settings.

### Apply incremental DB hardening (existing environments)

Run after deploy to backfill new constraints/indexes without recreating schema:

```bash
psql "$DATABASE_URL" -f server/db/03-hardening.sql
```

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

