# HuntFlow vNext PRD v5

## Positioning

HuntFlow vNext is a dual-track headhunter agent workbench:

- The mainline product delivers a thin-core operating system for consultants.
- The experimental sourcing track captures external lead data into a review buffer without becoming a hard dependency for the closed loop.

The first shippable slice is the auditable mainline loop:

`Client -> Job -> Candidate Import -> Match Score -> Submission Draft -> Approval -> Replay`

## Product principles

1. The workbench and chat surfaces are two entry points to one service layer.
2. AI can read, explain, draft, and recommend, but formal writes remain policy-aware.
3. Auditability is a feature, not a support function.
4. Experimental sourcing must degrade to zero without harming the core system.
5. Public product scope excludes stealth or bypass-oriented collection logic.

## First delivery scope

### Mainline resources

- `clients`
- `job_orders`
- `candidates`
- `resume_assets`
- `pipelines`
- `match_scores`
- `submissions`
- `approvals`
- `agent_runs`
- `audit_logs`
- `automation_events`

### Experimental resources

- `source_runs`
- `source_items_raw`
- `source_item_reviews`

### Mainline endpoints

- `POST /api/v1/auth/login`
- `GET /health`
- `GET|POST /api/v1/clients`
- `GET|POST /api/v1/job-orders`
- `GET /api/v1/candidates`
- `POST /api/v1/candidates/import`
- `POST /api/v1/match-scores/run`
- `POST /api/v1/submissions/draft`
- `GET /api/v1/submissions/{id}`
- `POST /api/v1/approvals`
- `GET /api/v1/approvals`
- `PATCH /api/v1/approvals/{id}`
- `GET /api/v1/runs/{id}/replay`
- `GET /api/v1/audit-logs`
- `POST /api/v1/agent/chat`

### Experimental endpoints

- `GET /api/v1/source-adapters`
- `POST /api/v1/source-runs`
- `GET /api/v1/source-runs/{id}`
- `POST /api/v1/source-items/{id}/review`
- `POST /api/v1/source-items/{id}/promote`

### Pilot endpoints added from Phase 6

- `GET|POST /api/v1/phone-screens`
- `PATCH /api/v1/phone-screens/{id}`
- `GET|POST /api/v1/assessment-reports`
- `GET|POST /api/v1/interview-plans`
- `PATCH /api/v1/interview-plans/{id}`
- `GET|POST /api/v1/invoices`
- `PATCH /api/v1/invoices/{id}`

## Stage map

### Phase 0

- Freeze product scope, architecture, and API contract.
- Define a shared naming system across workbench and chat.

### Phase 1

- Stand up monorepo, API shell, web shell, docker scaffolding, auth, and feature flags.

### Phase 2

- Deliver the mainline loop with deterministic scoring and structured draft generation.

### Phase 3

- Route the same services through agent runtime and chat SSE responses.

### Phase 4

- Add approvals, audit replay, todo aggregation, and model/version governance.

### Phase 5

- Add raw-source buffering and human review lane behind a feature flag.

### Phase 6

- Add phone screen, evaluation, scheduling, and invoice-lite based on live pilot evidence.

### Current implementation status

- Phase 0 through Phase 6 are implemented as a pilot-grade MVP in the current monorepo.
- Mainline and experimental sourcing flows are both available in workbench.
- Chat supports mainline commands plus Phase 6 commands for screen, assess, interview, and invoice creation.
- Storage currently supports `memory`, `file`, and `postgres`, with `redis` runtime state for production-oriented deployment.
- The web workbench now authenticates through a server-managed session cookie while API clients can still use bearer tokens.
- The public experimental sourcing surface is a controlled `structured-import -> review -> promote` lane. Prototype browser-capture aliases are not part of the release contract.

## Acceptance criteria

- The mainline loop is runnable end-to-end by API.
- Workbench and chat paths call the same scoring and draft services.
- Writes require approval decisions.
- Replay shows run metadata, steps, and related audit events.
- Raw source items cannot be promoted before review approval.
- The app still works when experimental sourcing is disabled.
