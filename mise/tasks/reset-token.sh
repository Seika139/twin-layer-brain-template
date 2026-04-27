#!/usr/bin/env bash

#MISE description="BRAIN_API_TOKEN を .env に作成または更新する"

set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "使い方: mise run reset-token" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
EXAMPLE_FILE="$ROOT_DIR/.env.example"

if command -v openssl >/dev/null 2>&1; then
  TOKEN="$(openssl rand -hex 32)"
else
  TOKEN="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(48))')"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$EXAMPLE_FILE" ]]; then
    cp "$EXAMPLE_FILE" "$ENV_FILE"
    echo "[作成] .env.example から .env を作成しました"
  else
    touch "$ENV_FILE"
    echo "[作成] .env を作成しました"
  fi
fi

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

if grep -qE '^[[:space:]]*#?[[:space:]]*BRAIN_API_TOKEN=' "$ENV_FILE"; then
  awk -v token="$TOKEN" '
    /^[[:space:]]*#?[[:space:]]*BRAIN_API_TOKEN=/ {
      if (!done) {
        print "BRAIN_API_TOKEN=" token
        done = 1
      }
      next
    }
    { print }
  ' "$ENV_FILE" >"$TMP_FILE"
else
  cp "$ENV_FILE" "$TMP_FILE"
  if [[ -s "$TMP_FILE" ]]; then
    printf "\n" >>"$TMP_FILE"
  fi
  printf "BRAIN_API_TOKEN=%s\n" "$TOKEN" >>"$TMP_FILE"
fi

mv "$TMP_FILE" "$ENV_FILE"
trap - EXIT
chmod 600 "$ENV_FILE" 2>/dev/null || true

echo "[更新] BRAIN_API_TOKEN を $ENV_FILE に書き込みました"
echo ""
echo "BRAIN_API_TOKEN=$TOKEN"
echo ""
echo "次に行うこと:"
echo "  1. 'mise run serve' が起動中なら再起動してください。"
echo "  2. Chrome 拡張機能を使っている場合は、次の手順で保存済み token を更新してください。"
echo "     a. Chrome の拡張機能アイコンをクリックします。"
echo "     b. popup 下部の Settings を開きます。"
echo "     c. Bearer Token に上の token の値を貼ります。"
echo "     d. Save Settings を押します。"
echo ""
echo "補足:"
echo "  - DevTools で chrome.storage.local を直接編集する必要はありません。"
echo "  - Chrome 拡張機能は token を保存するため、通常の clip ごとに貼り直す必要はありません。"
