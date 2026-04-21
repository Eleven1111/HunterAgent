#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
. "$ROOT_DIR/scripts/local_env.sh"

PID_FILE="$ROOT_DIR/tmp/local-web.pid"
LOG_FILE="$ROOT_DIR/tmp/local-web.log"

if ! command -v npm >/dev/null 2>&1; then
  printf 'npm is missing. Web is optional; install Node.js if you need the workbench.\n' >&2
  exit 1
fi

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  printf 'Local web already running on pid %s\n' "$(cat "$PID_FILE")"
  exit 0
fi

cd "$ROOT_DIR"
nohup npm --workspace apps/web run dev -- --hostname 127.0.0.1 --port "$WEB_PORT" >"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${WEB_PORT}/login" >/dev/null 2>&1; then
    printf 'Local web ready: http://127.0.0.1:%s\n' "$WEB_PORT"
    exit 0
  fi
  sleep 1
done

printf 'Local web failed to become ready. See %s\n' "$LOG_FILE" >&2
exit 1
