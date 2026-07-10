# AGENTS.md

## Cursor Cloud specific instructions

This repo is the **HHS Patient Portal**, a full-stack app. **Local dev and production both use Docker Compose** (`docker-compose.yml` + `docker-compose.override.yml`).

| Service | Port | How it runs | Notes |
| --- | --- | --- | --- |
| PostgreSQL 16 | 5432 | `db` service | Schema + seed applied by `db-init` on first boot |
| Redis 7 | 6379 | `redis` service | Session/cache backing |
| Flask API (Python) | 3000 | `api` service | Dev override mounts `./api` and runs Flask with `--reload` |
| Nginx + Vue build | 80 | `nginx` service | Serves `dist/` and proxies `/api` → API |

### Cloud agent environment

Cloud agents use [`.cursor/environment.json`](.cursor/environment.json):

- **Build**: [`.cursor/Dockerfile`](.cursor/Dockerfile) installs Node, Python, and Docker-in-Docker (with `fuse-overlayfs` + `iptables-legacy`)
- **Install** ([`.cursor/install.sh`](.cursor/install.sh)): `npm install`, Python venv (for host-side pytest), `npm run build` — idempotent, no `docker compose up`
- **Start** ([`.cursor/start.sh`](.cursor/start.sh)): `sudo service docker start` then `docker compose up -d --build`

Do **not** use the legacy native-Postgres workflow (`pg_ctlcluster`, `./run-api.sh`, `npm run dev`) in cloud agents unless Docker is unavailable.

### First-time / manual local setup

```bash
cp .env.docker.example .env   # or: cp .env.docker.example .env
./dev.sh up                   # or: docker compose up -d --build
```

- App: http://localhost:80
- API health: http://localhost:3000/health
- Test logins (from `server/db/seed.sql`): patient `patient1` / `Patient123!`, doctor `doctor1` / `Doctor123!`

### Day-to-day commands (`./dev.sh`)

| Command | When to use |
| --- | --- |
| `./dev.sh up` | Start the full stack |
| `./dev.sh reload` | Recreate API after `.env` changes |
| `./dev.sh frontend` | Rebuild Vue (`npm run build`) and reload nginx |
| `./dev.sh api` | Rebuild API image after `requirements.txt` changes |
| `./dev.sh logs api` | Tail API logs |
| `./dev.sh down` | Stop stack |

Python file changes under `api/` auto-reload via the dev override. Vue changes require `./dev.sh frontend` (or `npm run build` + nginx reload).

### `.env`

- **Required and git-ignored.** Copy from [`.env.docker.example`](.env.docker.example) for compose-based dev.
- `DB_HOST=localhost` is correct for **host-side** tools (pytest, `psql`) because compose publishes port 5432.
- Inside the `api` container, compose sets `DB_HOST=db` automatically.

### Database bootstrap

On a fresh compose volume, `db-init` runs `server/db/schema.sql` and `server/db/seed.sql` automatically. To re-apply schema on an existing volume:

```bash
docker compose exec db psql -U postgres -d hhs_patient_portal -f /docker-entrypoint-initdb.d/schema.sql
```

(`seed.sql` is also in that mount; re-run only if you need seed data restored.)

### Tests and build (from repo root, stack running)

- Backend: `npm run test:backend` (pytest via `./venv` on host; needs DB on `localhost:5432`)
- Frontend: `npm run test:frontend` (vitest)
- Production build check: `npm run build`

### Architecture notes

- **`server/` is legacy TypeScript** — live backend is Python Flask under `api/`. `.gitignore` keeps only `server/db/*.sql`.
- **`docker-compose.override.yml`** is applied automatically in dev (Flask dev server, live API mounts).
