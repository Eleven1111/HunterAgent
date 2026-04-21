#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
. "$ROOT_DIR/.venv/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if command -v npm >/dev/null 2>&1; then
  npm install
fi

if [ ! -f ".env.local-mac" ]; then
  cp .env.local-mac.example .env.local-mac
fi

printf 'Local setup complete. Env file: %s\n' "$ROOT_DIR/.env.local-mac"
