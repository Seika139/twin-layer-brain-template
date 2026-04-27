#!/usr/bin/env bash

#MISE description="macOS launchd の HTTP server を再起動する"
#MISE hide=true

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
require_launchctl

LABEL="$(brain_label)"
launchctl kickstart -k "gui/$(id -u)/${LABEL}"
echo "再起動しました: $LABEL"
