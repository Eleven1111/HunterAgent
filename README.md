# HuntFlow vNext

HuntFlow is a local-first headhunter agent workbench.

This repository is meant to run on a single Mac, especially an older machine, with:

- no Docker
- no cloud deployment required
- `file` storage by default
- `memory` runtime by default
- optional web UI
- direct local use from OpenClaw or Hermes

If you are an agent reading this repository from GitHub, start here and follow the commands exactly.

## Agent Goal

Bring up a local HuntFlow API on the same Mac so the host agent can call it.

Primary success criteria:

1. `http://127.0.0.1:8000/health` responds
2. `python3 scripts/huntflow_local_cli.py health` succeeds
3. `python3 scripts/huntflow_local_cli.py today` succeeds

Do not redefine the task as cloud deployment.
Do not switch the default path to Docker.
Do not require Postgres or Redis for the first local install.

## Fastest Path

From the repo root:

```bash
npm run local:setup
cp .env.local-mac.example .env.local-mac
npm run local:start:api
python3 scripts/local_login.py --shell
python3 scripts/huntflow_local_cli.py health
python3 scripts/huntflow_local_cli.py today
```

If the API path is healthy and you also need the UI:

```bash
npm run local:start
```

To stop local services:

```bash
npm run local:stop
```

To install background services with macOS `launchd`:

```bash
npm run local:launchd:install
```

To install API + web as background services:

```bash
npm run local:launchd:install:web
```

To remove background services:

```bash
npm run local:launchd:remove
```

## Required Local Prerequisites

- `python3`
- `npm`

Optional:

- web browser, if you want the workbench UI

## Default Local Mode

The single-machine defaults live in [/.env.local-mac.example](/Users/na/na/xcode/HunterAgent/.env.local-mac.example).

Key defaults:

- `STORE_BACKEND=file`
- `STORE_FILE_PATH=storage/local-store.json`
- `RUNTIME_BACKEND=memory`
- `ENABLE_EXPERIMENTAL_SOURCING=false`
- API on `127.0.0.1:8000`
- Web on `127.0.0.1:3000`
- Public experimental contract is `structured-import -> review -> promote` only (browser prototype capture is not a public capability).

This is the intended first-run mode for old Macs.

## Repo Scripts

Local setup:

```bash
npm run local:setup
```

Start API only:

```bash
npm run local:start:api
```

Start API + web:

```bash
npm run local:start
```

Stop local services:

```bash
npm run local:stop
```

Print shell exports for local auth:

```bash
npm run local:token
```

Show bridge CLI help:

```bash
npm run local:bridge
```

## OpenClaw / Hermes Integration

The recommended integration surface is the local bridge CLI, not ad-hoc `curl`.
The bridge CLI contract is covered by automated tests; keep integrations on the documented stable commands.

Bridge CLI:

[/Users/na/na/xcode/HunterAgent/scripts/huntflow_local_cli.py](/Users/na/na/xcode/HunterAgent/scripts/huntflow_local_cli.py)

Typical commands:

```bash
python3 scripts/huntflow_local_cli.py health
python3 scripts/huntflow_local_cli.py dashboard
python3 scripts/huntflow_local_cli.py today
python3 scripts/huntflow_local_cli.py create-client --name "Northstar" --industry "Fintech"
python3 scripts/huntflow_local_cli.py create-job --client-id client_x --title "CFO" --must-have finance
python3 scripts/huntflow_local_cli.py import-candidate --job-order-id job_x --full-name "Lina Chen" --resume-text "Fintech CFO"
python3 scripts/huntflow_local_cli.py score job_x candidate_y
python3 scripts/huntflow_local_cli.py draft job_x candidate_y
```

Local auth helper:

[/Users/na/na/xcode/HunterAgent/scripts/local_login.py](/Users/na/na/xcode/HunterAgent/scripts/local_login.py)

Token examples:

```bash
python3 scripts/local_login.py --shell
python3 scripts/local_login.py --token-only
```

Integration-specific docs:

- [Single-Mac OpenClaw/Hermes Guide](/Users/na/na/xcode/HunterAgent/docs/single-mac-openclaw-hermes.md)
- [OpenClaw Integration](/Users/na/na/xcode/HunterAgent/integrations/openclaw/README.md)
- [Hermes Integration](/Users/na/na/xcode/HunterAgent/integrations/hermes/README.md)

## Demo Credentials

When `ENABLE_DEMO_SEED=true`, local startup seeds:

- `owner@huntflow.local` / `hunter-owner`
- `consultant@huntflow.local` / `hunter-consultant`

For OpenClaw or Hermes, start with the owner account unless you explicitly want consultant-scope behavior.

## What This Repo Includes

- `apps/api`: FastAPI backend
- `apps/web`: optional Next.js workbench
- `openapi/openapi.yaml`: API contract
- `docs/prd-v5.md`: product scope
- `docs/adr-001.md`: architecture decisions
- `scripts/`: local lifecycle, auth, bridge, migration, and backup helpers

## Main Local API Surface

Health:

```text
GET /health
```

Agent endpoint:

```text
POST /api/v1/agent/chat
```

Formal submission flow (token-gated):

```text
POST /api/v1/approvals
PATCH /api/v1/approvals/{approval_id}
POST /api/v1/submissions/{submission_id}/submit
```

Use this as a three-step workbench flow:
`request approval -> approve -> submit with approval_token`.
Approval decisions do not submit recommendations by themselves.

Public experimental sourcing flow:
`structured-import -> review -> promote`.

Primary local commands supported through the shared runtime:

- `/today`
- `/score <job_id> <candidate_id>`
- `/draft <job_id> <candidate_id>`
- `/screen <job_id> <candidate_id>` for owner/admin
- `/assess <job_id> <candidate_id>` for owner/admin
- `/interview <job_id> <candidate_id> <interviewer>` for owner/admin
- `/invoice <client_id> <amount> [job_id]` for owner/admin

## Formal Submission Flow (Approval-Gated)

Formal submission is a 3-step write flow:

1. request approval
2. approve the request
3. submit with the returned `approval_token`

Example:

```bash
TOKEN="$(python3 scripts/local_login.py --token-only)"
SUBMISSION_ID="submission_x"

# 1) request approval
APPROVAL_ID="$(curl -s http://127.0.0.1:8000/api/v1/approvals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"SUBMIT_RECOMMENDATION\",\"resource_type\":\"submission\",\"resource_id\":\"$SUBMISSION_ID\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"id\"])')"

# 2) approve
APPROVAL_TOKEN="$(curl -s http://127.0.0.1:8000/api/v1/approvals/$APPROVAL_ID \
  -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"decision":"APPROVED","reason":"looks good"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"token\"])')"

# 3) submit with token
curl -s http://127.0.0.1:8000/api/v1/submissions/$SUBMISSION_ID/submit \
  -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"approval_token\":\"$APPROVAL_TOKEN\"}"
```

## Troubleshooting

If startup fails:

1. Read [tmp/local-api.log](/Users/na/na/xcode/HunterAgent/tmp/local-api.log)
2. Confirm `.env.local-mac` exists
3. Confirm `python3` and `npm` are installed
4. Re-run `npm run local:setup`
5. Keep the install in `file + memory` mode unless you intentionally need something heavier

If the agent can run shell commands but not HTTP directly, use the bridge CLI and let it talk to the API for you.

If you are an agent and need the shortest possible instruction set, use this:

```bash
cd /Users/na/na/xcode/HunterAgent
npm run local:setup
cp .env.local-mac.example .env.local-mac
npm run local:start:api
python3 scripts/local_login.py --shell
python3 scripts/huntflow_local_cli.py health
python3 scripts/huntflow_local_cli.py today
```
