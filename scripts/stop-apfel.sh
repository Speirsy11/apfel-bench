#!/usr/bin/env bash
# Stop the apfel LaunchAgent.
set -euo pipefail
UID_VAL=$(id -u)
launchctl bootout "gui/${UID_VAL}/com.openclaw.apfel" 2>/dev/null || true
echo "apfel stopped"
