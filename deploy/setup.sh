#!/usr/bin/env bash
# VPS 初回セットアップスクリプト
# root または sudo 権限で実行する
#
# 使い方:
#   sudo ./deploy/setup.sh                          # デフォルト: /opt/second-brain
#   sudo ./deploy/setup.sh /home/user/second-brain  # 任意のパスを指定
set -euo pipefail

INSTALL_DIR="${1:-/opt/second-brain}"
SERVICE_USER="${SUDO_USER:-$(whoami)}"

echo "=== second-brain VPS setup ==="
echo "Install dir: $INSTALL_DIR"
echo "Service user: $SERVICE_USER"

# 1. .env ファイルの作成（テンプレート）
if [ ! -f "$INSTALL_DIR/.env" ]; then
  cat > "$INSTALL_DIR/.env" << 'ENVEOF'
SECOND_BRAIN_API_TOKEN=changeme
GITHUB_WEBHOOK_SECRET=changeme
# OPENAI_API_KEY=sk-...
ENVEOF
  chmod 600 "$INSTALL_DIR/.env"
  chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.env"
  echo "Created .env template at $INSTALL_DIR/.env — edit before starting"
fi

# 2. mise + uv で依存をインストール
sudo -u "$SERVICE_USER" bash -c "cd $INSTALL_DIR && mise install && mise run init"

# 3. systemd ユニットを生成・配置
sed \
  -e "s|/opt/second-brain|$INSTALL_DIR|g" \
  -e "s|User=%USER%|User=$SERVICE_USER|" \
  -e "s|Group=%USER%|Group=$SERVICE_USER|" \
  "$INSTALL_DIR/deploy/second-brain.service" \
  > /etc/systemd/system/second-brain.service

# ホームディレクトリ配下の場合は ProtectHome を無効化
case "$INSTALL_DIR" in
  /home/*|/root/*)
    sed -i 's/ProtectHome=true/ProtectHome=false/' /etc/systemd/system/second-brain.service
    ;;
esac

systemctl daemon-reload
systemctl enable second-brain
echo "systemd unit installed and enabled"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Edit $INSTALL_DIR/.env with real values"
echo "  2. Configure Caddy (see deploy/Caddyfile)"
echo "  3. systemctl start second-brain"
echo "  4. Set up GitHub webhook pointing to https://your-domain/api/sync/webhook"
