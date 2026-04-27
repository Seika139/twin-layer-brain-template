#!/usr/bin/env bash

#MISE description="macOS launchd service と /api/health の状態を確認する"
#MISE hide=true

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
require_launchctl

LABEL="$(brain_label)"
PORT="$(brain_port)"

launchctl print "gui/$(id -u)/${LABEL}" 2>/dev/null || {
  echo "launchd service は登録されていません: $LABEL"
  exit 1
}

curl -sf "http://localhost:${PORT}/api/health"
echo ""
