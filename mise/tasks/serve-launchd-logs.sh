#!/usr/bin/env bash

#MISE description="macOS launchd の HTTP server log を表示する"
#MISE hide=true

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"

LOG_FILE="$(brain_root)/index/server.log"
touch "$LOG_FILE"
tail -n 100 -f "$LOG_FILE"
