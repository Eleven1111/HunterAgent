#!/usr/bin/env bash
set -euo pipefail

target_path="${1:-storage/backups/huntflow-$(date +%Y%m%d-%H%M%S).json}"
mkdir -p "$(dirname "$target_path")"
python3 "$(dirname "$0")/postgres_backup.py" "$target_path"
