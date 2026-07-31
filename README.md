# HHS Patient Portal

Hudson Health System patient + provider portal (Vue 3 frontend, Flask API, PostgreSQL).

## Local Docker (recommended)

Easy stack with live API reload and a Compose-built Vue frontend:

```bash
cp .env.example .env   # set DB_PASSWORD=postgres for local
./dev.sh up            # builds Vue → ./dist, starts nginx/api/db/redis
```

Open **http://localhost**

| Command | What it does |
| --- | --- |
| `./dev.sh up` | Rebuild Vue + start stack |
| `./dev.sh frontend` | Rebuild Vue only, reload nginx |
| `./dev.sh logs` | Tail API logs |
| `./dev.sh down` | Stop stack |
| `./dev.sh help` | Full command list |

- **Python** under `api/` live-reloads (Flask `--reload`).
- **Vue** does not hot-reload — nginx serves `./dist`. After UI changes run `./dev.sh frontend` (or `./dev.sh up`).
- Schema/seed apply automatically via the `db-init` service (`server/db/schema.sql` + `seed.sql`).

### Test logins

| Role | Username | Password |
| --- | --- | --- |
| Patient | `patient1` | `Patient123!` |
| Provider | `doctor1` | `Doctor123!` |

(`patient2`–`patient8`, `doctor2`–`doctor4` use the same `*123!` pattern.)

## Project layout

```
api/                 Flask API (live-mounted in Docker)
src/                 Vue 3 + TypeScript frontend
server/db/           schema.sql + seed.sql
docker/              nginx configs
docker-compose.yml   prod-like stack
docker-compose.override.yml   local live-reload overrides
dev.sh               primary local Docker helper
```

## Tests

```bash
npm run test:frontend
# backend (host venv or in the api container — see AGENTS.md)
npm run test:backend
```

## Azure production

Production deploys use `azure-deploy.sh` (also on push to `main` via `.github/workflows/deploy-main.yml`).

```bash
az login
cp .env.example .env   # fill cloud DB/secrets — never commit .env
./azure-deploy.sh
```

Hardening checklist: strong `SESSION_SECRET` / `JWT_SECRET`, explicit `ALLOWED_ORIGINS`, `DB_SSLMODE=require`, `FORCE_HTTPS=true`, Redis for rate limits when multi-replica. See `.env.example` for all knobs.

## SonarQube (optional)

```bash
cp .env.sonarqube.example .env.sonarqube
npm run sonar:up       # http://localhost:9000
npm run sonar:scan
```
