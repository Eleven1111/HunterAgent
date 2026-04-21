#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${HUNTFLOW_ENV_FILE:-$ROOT_DIR/.env.local-mac}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

: "${APP_ENV:=development}"
: "${APP_SECRET:=change-me-local}"
: "${ENABLE_DEMO_SEED:=true}"
: "${NEXT_PUBLIC_ENABLE_DEMO_SEED:=true}"
: "${STORE_BACKEND:=file}"
: "${STORE_FILE_PATH:=storage/local-store.json}"
: "${RUNTIME_BACKEND:=memory}"
: "${ENABLE_EXPERIMENTAL_SOURCING:=false}"
: "${API_PORT:=8000}"
: "${WEB_PORT:=3000}"
: "${NEXT_PUBLIC_API_URL:=http://127.0.0.1:${API_PORT}}"
: "${API_BASE_URL:=http://127.0.0.1:${API_PORT}}"
: "${ALLOWED_ORIGINS:=http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}}"
: "${SESSION_COOKIE_NAME:=huntflow_session}"
: "${SESSION_COOKIE_SECURE:=false}"
: "${SESSION_COOKIE_SAMESITE:=lax}"
: "${SESSION_COOKIE_DOMAIN:=}"

export APP_ENV
export APP_SECRET
export ENABLE_DEMO_SEED
export NEXT_PUBLIC_ENABLE_DEMO_SEED
export STORE_BACKEND
export STORE_FILE_PATH
export RUNTIME_BACKEND
export ENABLE_EXPERIMENTAL_SOURCING
export API_PORT
export WEB_PORT
export NEXT_PUBLIC_API_URL
export API_BASE_URL
export ALLOWED_ORIGINS
export SESSION_COOKIE_NAME
export SESSION_COOKIE_SECURE
export SESSION_COOKIE_SAMESITE
export SESSION_COOKIE_DOMAIN
export PYTHONPATH="${ROOT_DIR}/apps/api"

mkdir -p "$ROOT_DIR/tmp" "$ROOT_DIR/storage"
