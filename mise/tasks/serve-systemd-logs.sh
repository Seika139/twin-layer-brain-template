#!/usr/bin/env bash

#MISE description="Linux systemd --user の HTTP server log を表示する"
#MISE hide=true

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
require_systemctl_user

SERVICE="$(systemd_service_name)"
journalctl --user -u "$SERVICE" -f
