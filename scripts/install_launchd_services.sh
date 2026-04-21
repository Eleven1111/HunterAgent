#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCHD_DIR"

install_api() {
  cat >"$LAUNCHD_DIR/com.huntflow.local-api.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.huntflow.local-api</string>
    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>${ROOT_DIR}/scripts/run_local_api_foreground.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${ROOT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${ROOT_DIR}/tmp/local-api.log</string>
    <key>StandardErrorPath</key>
    <string>${ROOT_DIR}/tmp/local-api.log</string>
  </dict>
</plist>
PLIST
  launchctl unload "$LAUNCHD_DIR/com.huntflow.local-api.plist" >/dev/null 2>&1 || true
  launchctl load "$LAUNCHD_DIR/com.huntflow.local-api.plist"
}

install_web() {
  cat >"$LAUNCHD_DIR/com.huntflow.local-web.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.huntflow.local-web</string>
    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>${ROOT_DIR}/scripts/run_local_web_foreground.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${ROOT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${ROOT_DIR}/tmp/local-web.log</string>
    <key>StandardErrorPath</key>
    <string>${ROOT_DIR}/tmp/local-web.log</string>
  </dict>
</plist>
PLIST
  launchctl unload "$LAUNCHD_DIR/com.huntflow.local-web.plist" >/dev/null 2>&1 || true
  launchctl load "$LAUNCHD_DIR/com.huntflow.local-web.plist"
}

install_api

if [ "${1:-}" = "--with-web" ]; then
  install_web
fi

printf 'launchd services installed in %s\n' "$LAUNCHD_DIR"
