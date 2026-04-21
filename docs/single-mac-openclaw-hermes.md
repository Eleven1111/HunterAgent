# Single-Mac OpenClaw / Hermes Guide

This project is designed to run on one local Mac without Docker.

## Recommended mode

- API on `127.0.0.1:8000`
- `STORE_BACKEND=file`
- `RUNTIME_BACKEND=memory`
- optional workbench on `127.0.0.1:3000`

The local defaults live in [.env.local-mac.example](/Users/na/na/xcode/HunterAgent/.env.local-mac.example).

## Setup

```bash
cd /Users/na/na/xcode/HunterAgent
npm run local:setup
cp .env.local-mac.example .env.local-mac
```

## Start

API only:

```bash
npm run local:start:api
```

API plus workbench:

```bash
npm run local:start
```

Stop:

```bash
npm run local:stop
```

Install launchd background services:

```bash
npm run local:launchd:install
```

Install API + web background services:

```bash
npm run local:launchd:install:web
```

Remove launchd services:

```bash
npm run local:launchd:remove
```

Logs and pid files:

- API log: [tmp/local-api.log](/Users/na/na/xcode/HunterAgent/tmp/local-api.log)
- Web log: [tmp/local-web.log](/Users/na/na/xcode/HunterAgent/tmp/local-web.log)
- Store file: [storage/local-store.json](/Users/na/na/xcode/HunterAgent/storage/local-store.json)

## Get a bearer token for OpenClaw / Hermes

Owner token:

```bash
python3 scripts/local_login.py --shell
```

Consultant token:

```bash
python3 scripts/local_login.py \
  --email consultant@huntflow.local \
  --password hunter-consultant \
  --shell
```

Token only:

```bash
python3 scripts/local_login.py --token-only
```

## Minimal integration contract

Base URL:

```text
http://127.0.0.1:8000
```

Auth header:

```text
Authorization: Bearer <token>
```

Primary agent endpoint:

```text
POST /api/v1/agent/chat
```

Example request:

```bash
TOKEN="$(python3 scripts/local_login.py --token-only)"

curl -s http://127.0.0.1:8000/api/v1/agent/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"local-agent","message":"/today"}'
```

Bridge CLI for OpenClaw / Hermes terminal mode:

```bash
python3 scripts/huntflow_local_cli.py health
python3 scripts/huntflow_local_cli.py dashboard
python3 scripts/huntflow_local_cli.py today
python3 scripts/huntflow_local_cli.py score job_x candidate_y
python3 scripts/huntflow_local_cli.py draft job_x candidate_y
```

Integration-specific guides:

- [OpenClaw Integration](/Users/na/na/xcode/HunterAgent/integrations/openclaw/README.md)
- [Hermes Integration](/Users/na/na/xcode/HunterAgent/integrations/hermes/README.md)

Main work commands currently supported by the local agent surface:

- `/today`
- `/score <job_id> <candidate_id>`
- `/draft <job_id> <candidate_id>`
- `/screen <job_id> <candidate_id>` for owner/admin
- `/assess <job_id> <candidate_id>` for owner/admin
- `/interview <job_id> <candidate_id> <interviewer>` for owner/admin
- `/invoice <client_id> <amount> [job_id]` for owner/admin

## Notes for old Macs

- Start with API-only mode unless you actually need the web UI.
- Keep `ENABLE_EXPERIMENTAL_SOURCING=false` unless you are actively using the buffered import lane.
- `file + memory` is the lightest supported mode and avoids needing Postgres or Redis.
