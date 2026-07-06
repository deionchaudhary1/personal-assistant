#!/bin/bash
# Rebuild the frontend and restart the background LaunchAgent service so
# code changes take effect. Run after pulling/editing code.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LABEL="com.personalassistant.backend"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

echo "==> Building frontend"
(cd "$REPO_ROOT/frontend" && npm run build)

echo "==> Restarting $LABEL"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "==> Done. Checking health..."
sleep 1
curl -s -o /dev/null -w "http status: %{http_code}\n" http://localhost:8000/api/health
