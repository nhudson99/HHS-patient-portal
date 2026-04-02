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

### 6) Persistent document storage (Azure Blob)

For production, configure documents to use Azure Blob storage instead of container-local disk:

- `DOCUMENTS_STORAGE_BACKEND=azure_blob`
- `DOCUMENTS_BLOB_CONTAINER=hhs-documents`
- `DOCUMENTS_BLOB_ENDPOINT` (recommended as secret)
- `DOCUMENTS_BLOB_CREDENTIAL` (required secret; account key or SAS)

Optional alternative secret:

- `DOCUMENTS_BLOB_CONNECTION_STRING` (if set, it is used instead of endpoint+credential)

Local development can keep:

- `DOCUMENTS_STORAGE_BACKEND=local`
- `DOCUMENTS_LOCAL_DIR=/tmp/hhs-documents`

## Azure deploy on `main` push

This repo now includes `.github/workflows/deploy-main.yml`, which runs `azure-deploy.sh` automatically on every push to `main` and also supports manual runs via GitHub Actions.

### Required GitHub Actions secret

- `AZURE_CREDENTIALS`: service principal JSON for `azure/login`
- `AZ_SUBSCRIPTION_ID`: Azure subscription to target
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`
- `SESSION_SECRET`, `JWT_SECRET`
- `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`
- `REDIS_URL` (optional, if used)
- `DEPLOY_GITHUB_TOKEN` (optional, if doctor feature requests should post to GitHub)
- `DOCUMENTS_BLOB_ENDPOINT` (if using endpoint+credential mode)
- `DOCUMENTS_BLOB_CREDENTIAL` (if using endpoint+credential mode)
- `DOCUMENTS_BLOB_CONNECTION_STRING` (optional alternative to endpoint+credential)

### Recommended GitHub Actions variables

- `DB_NAME`
- `ALLOWED_ORIGINS`
- `VITE_AZURE_REDIRECT_URI`
- `AZ_LOCATION`, `AZ_RESOURCE_GROUP`, `AZ_CONTAINERAPPS_ENV`, `AZ_API_APP_NAME`, `AZ_ACR_NAME`
- `DB_PORT`, `DB_SSLMODE`, `FORCE_HTTPS`
- `MAX_LOGIN_ATTEMPTS`, `ACCOUNT_LOCKOUT_MINUTES`, `SESSION_TIMEOUT_MINUTES`
- `GUNICORN_WORKERS`, `GUNICORN_THREADS`, `GUNICORN_TIMEOUT`
- `GITHUB_REPO`, `GITHUB_FEATURE_REQUEST_LABELS`, `APP_DOMAIN`
- `DOCUMENTS_STORAGE_BACKEND`, `DOCUMENTS_BLOB_CONTAINER`, `DOCUMENTS_LOCAL_DIR`

The workflow builds the frontend, runs backend tests, logs into Azure, writes a temporary env file for `azure-deploy.sh`, then deploys the app when `main` receives a push.

## Kiosk unregistered check-in alerts

The kiosk check-in flow now attempts patient + appointment lookup (name, DOB, and optional appointment time). If no matching patient or appointment is found, the API sends an alert email in this format:

- `Unregistered Check-In:`
- `Patient: <name>`
- `Appointment time: <time>`

Configure email delivery with these env vars:

- `CHECKIN_ALERT_EMAIL` (defaults to `nathan@hudsonitconsulting.com`)

Recommended (Microsoft Graph API):

- `GRAPH_TENANT_ID`
- `GRAPH_CLIENT_ID`
- `GRAPH_CLIENT_SECRET`
- `GRAPH_SENDER_USER` (licensed mailbox, e.g. `alerts@...` or `nathan@...`)

Fallback (SMTP):

- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`, `SMTP_USE_TLS`

If Graph is not configured, the API attempts SMTP fallback. If neither is configured, it logs a warning and continues returning the normal kiosk lookup/check-in response.

## Unit tests (frontend + backend)

Install backend test dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
```

Run unit tests with coverage:

```bash
npm run test:frontend
npm run test:backend
```

Or run both:

```bash
npm run test:unit
```

Coverage outputs:

- Frontend LCOV: `coverage/lcov.info`
- Backend coverage XML: `coverage-python.xml`

## SonarQube setup

This repo includes `sonar-project.properties` configured for `src/` + `api/` and both coverage reports.

For convenience, you can store scanner credentials in a local file that is ignored by git:

```bash
cp .env.sonarqube.local.example .env.sonarqube.local
```

Then edit `.env.sonarqube.local` with your real values. Sonar scripts automatically load it.

### Local SonarQube host (recommended for setup)

This repo includes a local SonarQube + PostgreSQL stack:

```bash
cp .env.sonarqube.example .env.sonarqube
npm run sonar:up
npm run sonar:status
```

Open SonarQube at:

- `http://localhost:9000`

Default login:

- username: `admin`
- password: `admin`

On first login, SonarQube will ask you to change the admin password.

Stop the stack with:

```bash
npm run sonar:down
```

1) Ensure tests have been run to generate coverage files.
2) Configure scanner auth in your shell.
3) Run sonar scan.

`npm run sonar:scan` now uses a wrapper script that automatically tries:

- local `sonar-scanner` binary,
- Docker scanner image fallback.

You do not need a global scanner installation.

```bash
export SONAR_HOST_URL="https://<your-sonarqube-host>"
export SONAR_TOKEN="<your-token>"
npm run sonar:scan
```

To run the full local flow in one command after setting the token:

```bash
export SONAR_HOST_URL="http://localhost:9000"
export SONAR_TOKEN="<your-token>"
npm run sonar:full
```

If your SonarQube uses self-signed certs or custom scanner options, pass them via your scanner environment/CLI as needed.

### VS Code quick-run Sonar workflow

This repo now includes ready-made VS Code tasks in `.vscode/tasks.json` so you can run Sonar without memorizing commands.

1. Open Command Palette and run `Tasks: Run Task`.
2. Choose one of:
	- `Sonar: Up`
	- `Sonar: Status`
	- `Sonar: Scan`
	- `Sonar: Full (tests + scan)`
3. Review scanner output in the terminal panel, then open your SonarQube project Issues page to triage findings.

For code-quality fallback checks when Sonar for IDE is unavailable, run:

```bash
npm run build
python3 -m compileall api -q
```

### Final manual steps in SonarQube UI

After `npm run sonar:up`, complete these once:

1. Sign in to `http://localhost:9000`.
2. Change the default admin password.
3. Create or confirm the project key `hhs-patient-portal`.
4. Generate a user token.
5. Export `SONAR_HOST_URL` and `SONAR_TOKEN` in your terminal.

### GitHub Actions integration

`/.github/workflows/quality.yml` runs frontend + backend unit tests and performs SonarQube scan when these repository secrets are configured:

- `SONAR_HOST_URL`
- `SONAR_TOKEN`

