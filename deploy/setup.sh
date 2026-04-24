#!/usr/bin/env bash
# VPS 初回セットアップスクリプト (twin-layer-brain インスタンス用)
# root または sudo 権限で実行する
#
# 使い方:
#   sudo ./deploy/setup.sh                          # デフォルト: /opt/brain
#   sudo ./deploy/setup.sh /home/user/my-brain      # 任意のパスを指定
#   sudo SERVICE_NAME=brain-personal ./deploy/setup.sh /opt/brain-personal
#                                                    # systemd サービス名を変える場合
#
# 複数ブレインを同一サーバーで運用する場合は、各インスタンスで SERVICE_NAME を
# 別の値にしてポートも別々にすること (BRAIN_PORT 環境変数)。
set -euo pipefail

INSTALL_DIR="${1:-/opt/brain}"
SERVICE_NAME="${SERVICE_NAME:-brain}"
SERVICE_USER="${SUDO_USER:-$(whoami)}"

echo "=== twin-layer-brain VPS setup ==="
echo "Install dir:  $INSTALL_DIR"
echo "Service name: $SERVICE_NAME (systemd)"
echo "Service user: $SERVICE_USER"

# 1. .env ファイルの作成（テンプレート）
if [ ! -f "$INSTALL_DIR/.env" ]; then
  cat > "$INSTALL_DIR/.env" << 'ENVEOF'
BRAIN_API_TOKEN=changeme
GITHUB_WEBHOOK_SECRET=changeme
# OPENAI_API_KEY=sk-...
# GEMINI_API_KEY=
# ANTHROPIC_API_KEY=
# BRAIN_LLM_PRIORITY=openai,gemini,anthropic
# BRAIN_PORT=15200
# BRAIN_HOST=127.0.0.1
ENVEOF
  chmod 600 "$INSTALL_DIR/.env"
  chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.env"
  echo "Created .env template at $INSTALL_DIR/.env — edit before starting"
fi

# 2. mise + uv で依存をインストール
sudo -u "$SERVICE_USER" bash -c "cd $INSTALL_DIR && mise install && mise run init"

# 3. systemd ユニットを生成・配置
sed \
  -e "s|/opt/brain|$INSTALL_DIR|g" \
  -e "s|User=%USER%|User=$SERVICE_USER|" \
  -e "s|Group=%USER%|Group=$SERVICE_USER|" \
  -e "s|Description=twin-layer-brain knowledge server|Description=twin-layer-brain ($SERVICE_NAME)|" \
  "$INSTALL_DIR/deploy/brain.service" \
  > "/etc/systemd/system/${SERVICE_NAME}.service"

# ホームディレクトリ配下の場合は ProtectHome を無効化
case "$INSTALL_DIR" in
  /home/*|/root/*)
    sed -i 's/ProtectHome=true/ProtectHome=false/' "/etc/systemd/system/${SERVICE_NAME}.service"
    ;;
esac

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
echo "systemd unit installed and enabled as ${SERVICE_NAME}.service"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Edit $INSTALL_DIR/.env with real values"
echo "  2. Configure Caddy (see deploy/Caddyfile)"
echo "  3. systemctl start $SERVICE_NAME"
echo "  4. Set up GitHub webhook pointing to https://your-domain/api/sync/webhook"
