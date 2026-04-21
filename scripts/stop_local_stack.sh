#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

stop_pid_file() {
  local label="$1"
  local pid_file="$2"
  if [ ! -f "$pid_file" ]; then
    printf '%s not running\n' "$label"
    return
  fi
  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" || true
    printf 'Stopped %s pid %s\n' "$label" "$pid"
  else
    printf '%s pid file was stale\n' "$label"
  fi
  rm -f "$pid_file"
}

stop_pid_file "local web" "$ROOT_DIR/tmp/local-web.pid"
stop_pid_file "local api" "$ROOT_DIR/tmp/local-api.pid"
