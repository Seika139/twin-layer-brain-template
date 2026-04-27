#!/usr/bin/env bash

#MISE description="OS に応じて HTTP server を常駐 service として登録する"

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
dispatch_server_task install
