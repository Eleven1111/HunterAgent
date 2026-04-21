# HuntFlow vNext

HuntFlow vNext is a dual-track headhunter agent workbench:

- Mainline product: a thin-core, auditable workbench and chat surface.
- Experimental sourcing track: buffered raw-source ingestion behind a feature flag.

This repository currently includes:

- `docs/prd-v5.md`: product scope and staged roadmap.
- `docs/adr-001.md`: architecture decision record.
- `openapi/openapi.yaml`: shared API contract for the first delivery slice.
- `apps/api`: FastAPI MVP backend with auth, scoring, draft generation, approvals, audit replay, and experimental source review flow.
- `apps/web`: Next.js app-router workbench and chat shell.
- `workers`: placeholder entrypoint for later queue-based jobs.
- `scripts`: migration, backup, restore, and deploy helpers for the local and release lanes.

## Current implementation slice

This first implementation focuses on the executable foundation:

- Repo structure and contracts
- Backend MVP for the mainline closed loop
- Frontend workbench and chat skeleton
- CI, Docker, and local verification scaffolding

The backend now supports:

- `memory` for fast local tests
- `file` for single-node pilot persistence
- `postgres` plus Redis runtime state for release-oriented deployment
- server-side auth sessions with `HttpOnly` cookie support for the web workbench

## Single old Mac / local agent mode

The primary deployment target for this repo is a single local machine:

- API-first, no Docker required
- `file` storage so data survives restarts
- `memory` runtime so Redis is optional
- optional web workbench
- OpenClaw / Hermes can call the local API directly

One-time setup:

```bash
npm run local:setup
cp .env.local-mac.example .env.local-mac
```

API only:

```bash
npm run local:start:api
python3 scripts/local_login.py --shell
python3 scripts/huntflow_local_cli.py today
```

API + workbench:

```bash
npm run local:start
```

Stop local services:

```bash
npm run local:stop
```

Install background launchd services on macOS:

```bash
npm run local:launchd:install
```

Remove them:

```bash
npm run local:launchd:remove
```

Detailed local-agent instructions:

- [Single-Mac OpenClaw/Hermes Guide](/Users/na/na/xcode/HunterAgent/docs/single-mac-openclaw-hermes.md)
- [OpenClaw Integration](/Users/na/na/xcode/HunterAgent/integrations/openclaw/README.md)
- [Hermes Integration](/Users/na/na/xcode/HunterAgent/integrations/hermes/README.md)

## Local run

### API

```bash
PYTHONPATH=apps/api uvicorn app.main:app --reload
```

### Tests

```bash
pytest apps/api/tests
```

### Web

Install dependencies when network access is available:

```bash
cd apps/web
npm install
npm run dev
```

## Demo credentials

When `ENABLE_DEMO_SEED=true`, the API seeds two demo users on startup:

- `owner@huntflow.local` / `hunter-owner`
- `consultant@huntflow.local` / `hunter-consultant`

The web workbench now uses the server session cookie rather than storing bearer tokens in the browser.

## Experimental sourcing release lane

The public release lane is a controlled manual import flow:

- create a `structured-import` source run
- review buffered raw items
- approve or reject each item
- promote approved items into candidates and pipelines

Prototype browser-capture aliases remain hidden from the public adapter list and are not part of the release contract.

## Postgres release helpers

Apply migrations:

```bash
python scripts/postgres_migrate.py
```

Backup:

```bash
scripts/backup.sh storage/backups/latest.json
```

Restore:

```bash
scripts/restore.sh storage/backups/latest.json
```
