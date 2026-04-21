#!/usr/bin/env bash
set -euo pipefail

LAUNCHD_DIR="$HOME/Library/LaunchAgents"

remove_service() {
  local plist="$1"
  if [ -f "$plist" ]; then
    launchctl unload "$plist" >/dev/null 2>&1 || true
    rm -f "$plist"
  fi
}

remove_service "$LAUNCHD_DIR/com.huntflow.local-api.plist"
remove_service "$LAUNCHD_DIR/com.huntflow.local-web.plist"

printf 'launchd services removed from %s\n' "$LAUNCHD_DIR"
