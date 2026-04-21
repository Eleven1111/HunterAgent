# HuntFlow Repo Guidance

## Project focus

- Treat the current API store as a replaceable runtime shim, not the final persistence layer.
- Keep business truth in services and repositories so Postgres migration is mechanical later.
- Preserve the three-lane model: `read`, `draft-write`, `write`.
- Any formal state mutation must remain approval-aware and audit-visible.

## Working rules

- Do not add stealth scraping, captcha bypass, or account-pool logic to the public product path.
- Experimental sourcing must stay behind feature flags and review queues.
- Reuse existing Pydantic models and repository helpers before adding new abstractions.
- Keep frontend pages dense, calm, and tool-like. The app is a workbench first, not a landing page.

## Verification

- Run `pytest apps/api/tests` after backend changes when dependencies are available.
- Keep API contract changes mirrored in `openapi/openapi.yaml`.
- Update `docs/prd-v5.md` when scope or stage gates change.

