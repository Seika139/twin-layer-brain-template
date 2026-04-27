#!/usr/bin/env bash

#MISE description="Linux systemd --user の HTTP server 登録を削除する"
#MISE hide=true

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
require_systemctl_user

SERVICE="$(systemd_service_name)"
UNIT_FILE="$HOME/.config/systemd/user/${SERVICE}.service"

systemctl --user disable --now "$SERVICE" 2>/dev/null || true
rm -f "$UNIT_FILE"
systemctl --user daemon-reload

echo "削除しました: $UNIT_FILE"
