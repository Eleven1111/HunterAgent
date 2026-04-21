#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT_DIR/scripts/start_local_api.sh"

if [ "${1:-}" = "--api-only" ]; then
  exit 0
fi

"$ROOT_DIR/scripts/start_local_web.sh"
