#!/usr/bin/env bash
set -euo pipefail

backup_file="${1:-}"
if [[ -z "$backup_file" || ! -f "$backup_file" ]]; then
  echo "usage: scripts/restore.sh path/to/backup.json" >&2
  exit 1
fi

python3 "$(dirname "$0")/postgres_restore.py" "$backup_file"
