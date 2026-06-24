#!/usr/bin/env bash
# Start the apfel OpenAI-compatible server as a managed LaunchAgent.
# Idempotent: stops an existing instance first, generates+stores a token in
# the macOS Keychain, and bootstraps a fresh plist.
set -euo pipefail

PLIST_LABEL="com.openclaw.apfel"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
APFEL_BIN="/opt/homebrew/opt/apfel/bin/apfel"
APFEL_PORT="${APFEL_PORT:-11435}"
KEYCHAIN_SERVICE="openclaw/apfel/token"
KEYCHAIN_ACCOUNT="value"

# Verify apfel is installed
if [[ ! -x "$APFEL_BIN" ]]; then
  echo "apfel is not installed at $APFEL_BIN" >&2
  echo "Install it with: brew install apfel" >&2
  exit 1
fi

# Pick a free port if the requested one is taken
if lsof -i ":$APFEL_PORT" >/dev/null 2>&1; then
  echo "Port $APFEL_PORT is busy; picking a free one" >&2
  APFEL_PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("",0)); print(s.getsockname()[1]); s.close()')
fi

# Get or create the token
TOKEN=$(security find-generic-password -a "$KEYCHAIN_ACCOUNT" -s "$KEYCHAIN_SERVICE" -w 2>/dev/null || true)
if [[ -z "$TOKEN" ]]; then
  TOKEN=$(uuidgen)
  security add-generic-password -a "$KEYCHAIN_ACCOUNT" -s "$KEYCHAIN_SERVICE" -w "$TOKEN" >/dev/null
  echo "Stored new apfel token in Keychain ($KEYCHAIN_SERVICE)"
else
  echo "Reusing existing apfel token from Keychain"
fi

# Write the plist
cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${APFEL_BIN}</string>
    <string>--serve</string>
    <string>--port</string>
    <string>${APFEL_PORT}</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>APFEL_TOKEN</key>
    <string>${TOKEN}</string>
    <key>APFEL_HOST</key>
    <string>127.0.0.1</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/apfel.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/apfel.log</string>
  <key>WorkingDirectory</key>
  <string>/tmp</string>
</dict>
</plist>
EOF

# Reload (bootout if already loaded, then bootstrap)
UID_VAL=$(id -u)
launchctl bootout "gui/${UID_VAL}/${PLIST_LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/${UID_VAL}" "$PLIST_PATH"

echo "apfel started on http://127.0.0.1:${APFEL_PORT}/v1"
echo "  plist:  $PLIST_PATH"
echo "  log:    /tmp/apfel.log"
echo "  token:  $(security find-generic-password -a "$KEYCHAIN_ACCOUNT" -s "$KEYCHAIN_SERVICE" -w | head -c 8)…"
