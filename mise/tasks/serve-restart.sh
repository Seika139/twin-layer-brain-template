#!/usr/bin/env bash

#MISE description="OS に応じて HTTP server の常駐 service を再起動する"

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
dispatch_server_task restart
