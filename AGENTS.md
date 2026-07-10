# AGENTS.md

## Cursor Cloud specific instructions

This repo is the **HHS Patient Portal**, a full-stack app with three moving parts:

| Service | Port | Start command | Notes |
| --- | --- | --- | --- |
| PostgreSQL 16 | 5432 | `sudo pg_ctlcluster 16 main start` | Not auto-started on VM boot; start it before the API. |
| Flask API (Python) | 3000 | `./run-api.sh` (or `npm run api`) | Reads `.env`; hot-reloads on file save in dev. |
| Vue 3 + Vite frontend | 5173 | `npm run dev` | Proxies `/api` → `http://localhost:3000` (see `vite.config.ts`). |

Standard commands are documented in `README.md`, `QUICKSTART.md`, `DATABASE_SETUP.md`, and `package.json` scripts. Below are only the non-obvious caveats:

- **`.env` is required and git-ignored.** The API and `seed_users.py` need it. For local dev use `DB_HOST=localhost`, `DB_USER=postgres`, `DB_PASSWORD=postgres`, `DB_NAME=hhs_patient_portal`, and `DB_SSLMODE=disable` (the local PostgreSQL is not built with SSL, so `prefer`/`require` should be avoided). If `.env` is missing, recreate it with those values plus `ALLOWED_ORIGINS=http://localhost:5173` and `DOCUMENTS_STORAGE_BACKEND=local`.
- **Python runs from a venv at `./venv`** (git-ignored). `npm run api`/`run-api.sh` do `source venv/bin/activate`, and tests use `./venv/bin/python`. The update script recreates/refreshes this venv.
- **First-time DB bootstrap on a fresh database** (schema is idempotent, safe to re-run):
  - `sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='hhs_patient_portal'" | grep -q 1 || sudo -u postgres psql -c "CREATE DATABASE hhs_patient_portal;"`
  - `sudo -u postgres psql -d hhs_patient_portal -f server/db/schema.sql`
  - `PYTHONPATH=$(pwd) ./venv/bin/python seed_users.py` (creates test users; idempotent).
  - Note: `./setup-db.sh` also does this but prompts interactively for seed data, so it can block automation.
- **Test login credentials** (from `seed_users.py`): patient `patient1` / `Patient123!`, doctor `doctor1` / `Doctor123!`.
- **`server/` is legacy TypeScript and unused** — the live backend is the Python Flask API under `api/`. `.gitignore` intentionally keeps only `server/db/*.sql`.
- Tests/build: backend `npm run test:backend` (pytest, needs the DB running), frontend `npm run test:frontend` (vitest), build `npm run build` (`vue-tsc && vite build`).
