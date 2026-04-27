#!/usr/bin/env bash

#MISE description="macOS launchd の HTTP server 登録を削除する"
#MISE hide=true

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
require_launchctl

LABEL="$(brain_label)"
PLIST_OUT="$HOME/Library/LaunchAgents/${LABEL}.plist"

launchctl unload "$PLIST_OUT" 2>/dev/null || true
rm -f "$PLIST_OUT"

echo "削除しました: $PLIST_OUT"
