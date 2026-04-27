#!/usr/bin/env bash

#MISE description="Linux systemd --user に HTTP server を登録する"
#MISE hide=true

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
require_systemctl_user

ROOT="$(brain_root)"
SERVICE="$(systemd_service_name)"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_FILE="$UNIT_DIR/${SERVICE}.service"
MISE_BIN="$(command -v mise || true)"

if [[ -z "$MISE_BIN" ]]; then
  echo "mise が見つかりません。mise を install してから再実行してください。" >&2
  exit 2
fi

mkdir -p "$UNIT_DIR" "$ROOT/index"
cat >"$UNIT_FILE" <<EOF
[Unit]
Description=twin-layer-brain HTTP server (${SERVICE})
After=network.target

[Service]
Type=simple
WorkingDirectory=${ROOT}
ExecStart=${MISE_BIN} run serve
Restart=on-failure
RestartSec=5
StandardOutput=append:${ROOT}/index/server.log
StandardError=append:${ROOT}/index/server.log

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable "$SERVICE"

echo "登録しました: $UNIT_FILE"
echo "service name: $SERVICE"
echo "起動: mise run serve-systemd-restart"
