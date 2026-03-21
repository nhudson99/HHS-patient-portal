# Copilot Instructions — HHS Patient Portal

These instructions define how code changes should be made in this repository.
Apply these rules by default unless a direct user request overrides them.

## Project Context

- App type: Full-stack patient portal (clinical + patient workflows).
- Frontend: Vue 3 + TypeScript + Vite.
- Backend: Python Flask API (`api/`) + PostgreSQL.
- Infra: Docker + Azure Container Apps + Azure PostgreSQL Flexible Server.
- Security domain: PHI-adjacent healthcare workflows; treat all user/clinical data as sensitive.

## Global Engineering Principles

1. Make minimal, focused changes that solve root causes.
2. Preserve existing behavior unless explicitly changing it.
3. Prefer readability over cleverness.
4. Keep security and deployability first-class in every change.
5. Never hardcode credentials, secrets, tokens, or PHI.

## Frontend Rules (Vue Best Practices)

- Use Composition API with `script setup` for new Vue code.
- Keep components focused; extract shared logic to utility/API layers when duplicated.
- Use strict TypeScript-friendly patterns (typed response objects, no `any` unless unavoidable).
- Centralize network calls through `src/api/index.ts`; avoid ad hoc `fetch` in views unless existing pattern requires it.
- Handle async UI states consistently: loading, success, empty, error.
- Validate user input on client side for UX, but enforce all security validation server side.
- Avoid exposing sensitive details in UI error messages.
- Keep route guards and auth flows consistent with `src/router/index.ts` and `src/store.ts`.

## Backend Rules (Python/Flask Best Practices)

- Follow existing blueprint structure in `api/routes/`.
- Use parameterized SQL only (`%s` placeholders); never string-concatenate SQL.
- Prefer structured logging (`current_app.logger`) over `print`.
- Fail safely: return generic user-facing errors in production; keep actionable server logs.
- Validate request payloads defensively (`request.get_json(silent=True) or {}`).
- Enforce authz/authn with middleware decorators (`@authenticate`, role checks) for protected resources.
- Keep password/session logic centralized in `api/utils/security.py` and `api/utils/session_manager.py`.
- For security-sensitive comparisons, use constant-time approaches when possible.
- Avoid introducing breaking API response shape changes unless requested.

## Database Rules (PostgreSQL Best Practices)

- Keep schema changes additive and migration-safe where possible.
- Add constraints for data integrity (CHECK, FK, UNIQUE) when introducing new data paths.
- Add indexes for hot query paths; avoid speculative over-indexing.
- Use `CREATE ... IF NOT EXISTS` and idempotent migration patterns for production safety.
- Prefer `UUID` + `gen_random_uuid()` (`pgcrypto`) as established in this project.
- Keep audit/session tables performant with appropriate time/user/token indexes.
- Do not drop/rename columns used in active APIs without explicit migration plan.

## Deployability Rules

- Assume cloud deployment target is Azure Container Apps.
- Keep configs env-driven (`.env` / secret refs), not hardcoded.
- Preserve compatibility with existing deploy scripts (`azure-deploy.sh`, Dockerfile, startup scripts).
- Ensure production-safe defaults:
  - no localhost DB for cloud deploys,
  - explicit CORS origins,
  - TLS-aware behavior behind ingress,
  - stable worker settings for constrained containers.
- Update `.env.example` when adding new runtime env vars.
- Update `README.md`/deploy docs when behavior or setup steps change.

## HIPAA & Security Guardrails

- Treat all patient/account/event/document data as sensitive.
- Enforce least privilege in route access and DB operations.
- Never log secrets, raw passwords, session tokens, or PHI payloads.
- Maintain audit logging for security-relevant actions (login, logout, password change, access-sensitive operations).
- Keep account lockout, session timeout, and password policy controls intact.
- Prefer secure defaults (SSL DB mode in production, strong secrets, strict origin controls).
- If a security gap is found, fix it at root cause and call it out clearly in summary.

## Testing & Validation Requirements

When code changes are made:

1. Run the narrowest relevant checks first.
2. Then run broader verification when feasible.

Typical commands:

```bash
npm run build
python3 -m compileall api
```

SonarQube for IDE process (required when files are modified):

1. Run Sonar analysis on each changed source file using IDE Sonar tooling.
2. Review Security Hotspots / Taint issues first, then reliability/maintainability issues.
3. Fix all issues introduced by the current change.
4. Also fix at least 5 additional pre-existing Sonar issues in touched areas when feasible and safe.
5. Re-run Sonar analysis on edited files to confirm issue count decreases and no new issues remain for changed code.
6. If Sonar tooling is unavailable or fails in the environment, explicitly report that blocker and continue with best-effort static checks (`npm run build`, `python3 -m compileall api`, and targeted lint/error checks).

If DB schema changes are made, include or update an idempotent SQL migration file under `server/db/` and document how to apply it.

## Change Management

- Do not refactor unrelated areas in the same change.
- Keep naming/style consistent with surrounding code.
- Keep commits easy to review (small, scoped diffs).
- Summaries should include:
  - files changed,
  - behavioral impact,
  - validation performed,
  - any required post-deploy/manual steps.

## Explicit Prohibitions

- Do not commit `.env` or secret material.
- Do not add demo credentials in production-facing UI.
- Do not bypass auth checks for convenience.
- Do not weaken password/session/security controls without explicit approval.

## Technical Debt

- Prioritize incremental reduction of existing Sonar issues in files being actively modified.
- Prefer small, safe cleanups that do not change API contracts or security behavior.