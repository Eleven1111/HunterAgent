#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
. "$ROOT_DIR/scripts/local_env.sh"

PID_FILE="$ROOT_DIR/tmp/local-api.pid"
LOG_FILE="$ROOT_DIR/tmp/local-api.log"

if [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  . "$ROOT_DIR/.venv/bin/activate"
fi

if ! python3 -c "import uvicorn" >/dev/null 2>&1; then
  printf 'uvicorn is missing. Run scripts/setup_local_mac.sh first.\n' >&2
  exit 1
fi

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  printf 'Local API already running on pid %s\n' "$(cat "$PID_FILE")"
  exit 0
fi

cd "$ROOT_DIR"
nohup python3 -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" >"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

for _ in $(seq 1 20); do
  if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
    printf 'Local API ready: http://127.0.0.1:%s\n' "$API_PORT"
    exit 0
  fi
  sleep 1
done

printf 'Local API failed to become ready. See %s\n' "$LOG_FILE" >&2
exit 1
