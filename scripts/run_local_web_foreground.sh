#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
. "$ROOT_DIR/scripts/local_env.sh"

cd "$ROOT_DIR"
exec npm --workspace apps/web run dev -- --hostname 127.0.0.1 --port "$WEB_PORT"
