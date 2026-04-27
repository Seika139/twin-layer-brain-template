#!/usr/bin/env bash

#MISE description="macOS launchd に HTTP server を登録する"
#MISE hide=true

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
require_launchctl

ROOT="$(brain_root)"
LABEL="$(brain_label)"
PLIST_OUT="$HOME/Library/LaunchAgents/${LABEL}.plist"

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/index"
sed -e "s|%BRAIN_LABEL%|${LABEL}|g" \
  -e "s|%BRAIN_ROOT%|${ROOT}|g" \
  "$ROOT/deploy/local.brain.plist" >"$PLIST_OUT"

launchctl unload "$PLIST_OUT" 2>/dev/null || true
launchctl load "$PLIST_OUT"

echo "登録しました: $PLIST_OUT"
echo "service label: $LABEL"
