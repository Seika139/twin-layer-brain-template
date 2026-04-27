#!/usr/bin/env bash

#MISE description="Linux systemd --user service と /api/health の状態を確認する"
#MISE hide=true

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
require_systemctl_user

SERVICE="$(systemd_service_name)"
PORT="$(brain_port)"

systemctl --user status "$SERVICE" --no-pager
curl -sf "http://localhost:${PORT}/api/health"
echo ""
