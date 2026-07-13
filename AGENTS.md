# AGENTS.md

## Cursor Cloud specific instructions

This repo is the **HHS Patient Portal**. The dev environment runs on **Docker Compose** so it mirrors production (nginx + Flask API + PostgreSQL + Redis). `docker compose up` automatically merges `docker-compose.yml` (prod-like) with `docker-compose.override.yml` (dev live-reload).

| Compose service | Container | Host port | Notes |
| --- | --- | --- | --- |
| `nginx` | hhs-nginx | 80 (+443) | **Main entry point** → `http://localhost`. Serves the host `./dist` mount and proxies `/api` + `/health` to the API. |
| `api` | hhs-api | 3000 | Flask; built from `Dockerfile`. Dev override live-mounts `./api` and runs `flask run --reload`. |
| `db` | hhs-postgres | 5432 | `postgres:16-alpine`; data in the `postgres_data` volume. |
| `redis` | hhs-redis | 6379 | Cache/session store. |
| `db-init` | hhs-db-init | – | One-shot; applies `server/db/schema.sql` + `seed.sql` (idempotent), then exits. |

Standard commands live in `DOCKER.md`, `DOCKER-QUICKSTART.md`, the `dev.sh` helper, and `package.json`. Non-obvious caveats:

- **Docker daemon is NOT running on VM boot.** Start it once per session, e.g. `sudo dockerd &` (log to a file if you want to watch it). Run all docker commands with `sudo`. The daemon config in `/etc/docker/daemon.json` (`fuse-overlayfs` storage driver + `containerd-snapshotter` disabled) is required for Docker-in-Docker here and is already in place — do not switch to `overlay2`.
- **Bring up the stack:** build the frontend first, then start compose:
  - `npm run build` (populates `./dist`, which nginx serves via a read-only mount)
  - `sudo docker compose up -d --build`
  - The `dev.sh` helper wraps this: `./dev.sh up|reload|frontend|api|logs|down` (it auto-uses `sudo` when needed).
- **Hot reload:** Python changes under `./api` auto-reload (Flask `--reload`). **Vue/frontend changes do NOT hot-reload** — nginx serves the prebuilt `./dist`, so re-run `npm run build` (then `./dev.sh frontend` to reload nginx, or just rebuild since the mount is live).
- **`.env` is required and git-ignored** — Compose reads it for variable substitution (DB creds, secrets). For local dev `DB_PASSWORD=postgres` is enough; the compose `api` service already sets `DB_HOST=db` and `DB_SSLMODE=disable` internally, overriding host-oriented `.env` values.
- **Port conflicts:** nothing else may bind 80/3000/5432/6379. If a host-level PostgreSQL was installed by an earlier non-Docker setup, stop it (`sudo pg_ctlcluster 16 main stop`) before `docker compose up`, or the `db` service can't bind 5432.
- **Test login credentials** (seeded by `server/db/seed.sql`): patient `patient1` / `Patient123!`, provider `doctor1` / `Doctor123!` (also `patient2`–`patient8`, `doctor2`–`doctor4`, all `*123!`).
- **Tests/build:** frontend runs on the host — `npm run test:frontend` (vitest) and `npm run build` (`vue-tsc && vite build`). Backend `pytest` deps are **not** in the prod API image, so either install them in the running container (`sudo docker compose exec api pip install pytest pytest-cov && sudo docker compose exec api python -m pytest api/tests`) or run them in a throwaway host venv (`python3 -m venv venv && ./venv/bin/pip install -r requirements.txt -r requirements-dev.txt && PYTHONPATH=$PWD ./venv/bin/python -m pytest api/tests`).
- **`server/` is legacy TypeScript and unused** — the live backend is the Python Flask API under `api/`. `.gitignore` intentionally keeps only `server/db/*.sql`.
