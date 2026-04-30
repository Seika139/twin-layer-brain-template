#!/usr/bin/env bash

#MISE description="MITM プロキシ環境向けに certifi + 社内 CA の合成 bundle を作成し .env に設定する"
#MISE quiet=true

set -euo pipefail

# 使い方:
#   mise run setup-ca-bundle              # 既知の社内 CA を自動検出
#   mise run setup-ca-bundle -- --ca <path>  # 社内 CA を明示指定
#   mise run setup-ca-bundle -- --out <path> # 出力先を明示指定（既定: $HOME/.config/ssl/ca-bundle-with-corp.pem）

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
EXAMPLE_FILE="$ROOT_DIR/.env.example"
DEFAULT_OUT="$HOME/.config/ssl/ca-bundle-with-corp.pem"

CA_PATH=""
OUT_PATH="$DEFAULT_OUT"

# 既知の MITM プロキシ CA 配布パス候補（見つかった最初の 1 つを採用）
CA_CANDIDATES=(
  "/Library/Application Support/Netskope/STAgent/data/nscacert.pem"
  "/Library/Application Support/Zscaler/cacerts/ZscalerRootCA.pem"
  "/Library/Application Support/Zscaler/cacert.pem"
  "/usr/local/share/ca-certificates/netskope.crt"
  "/usr/local/share/ca-certificates/zscaler.crt"
  "/etc/ssl/certs/netskope.pem"
  "/etc/ssl/certs/zscaler.pem"
)

while [[ $# -gt 0 ]]; do
  case "$1" in
  --ca)
    CA_PATH="${2:-}"
    shift 2
    ;;
  --out)
    OUT_PATH="${2:-}"
    shift 2
    ;;
  -h | --help)
    sed -n '8,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  *)
    echo "不明な引数: $1" >&2
    echo "使い方: mise run setup-ca-bundle [-- --ca <path>] [--out <path>]" >&2
    exit 2
    ;;
  esac
done

# --- 1. 社内 CA を探す ------------------------------------------------------

if [[ -z "$CA_PATH" ]]; then
  for candidate in "${CA_CANDIDATES[@]}"; do
    if [[ -f "$candidate" ]]; then
      CA_PATH="$candidate"
      echo "[検出] 社内 CA: $CA_PATH"
      break
    fi
  done
fi

if [[ -z "$CA_PATH" ]]; then
  echo "社内 CA 証明書が見つかりません。" >&2
  echo "候補を確認した場所:" >&2
  for candidate in "${CA_CANDIDATES[@]}"; do
    echo "  - $candidate" >&2
  done
  echo "" >&2
  echo "明示指定する場合: mise run setup-ca-bundle -- --ca /path/to/corp-ca.pem" >&2
  exit 1
fi

if [[ ! -r "$CA_PATH" ]]; then
  echo "社内 CA が読めません: $CA_PATH" >&2
  exit 1
fi

# --- 2. CA の subject / 期限を表示 -----------------------------------------

if command -v openssl >/dev/null 2>&1; then
  echo ""
  echo "[CA 情報]"
  openssl x509 -in "$CA_PATH" -noout -subject -issuer -dates |
    sed 's/^/  /'

  # notAfter を取り出して期限切れを警告
  NOT_AFTER_EPOCH="$(openssl x509 -in "$CA_PATH" -noout -enddate 2>/dev/null |
    sed -n 's/^notAfter=//p' |
    {
      read -r date_str
      date -j -f "%b %e %H:%M:%S %Y %Z" "$date_str" +%s 2>/dev/null || date -d "$date_str" +%s 2>/dev/null || echo ""
    })"
  if [[ -n "$NOT_AFTER_EPOCH" ]]; then
    NOW_EPOCH="$(date +%s)"
    if ((NOT_AFTER_EPOCH < NOW_EPOCH)); then
      echo "  [警告] この CA は期限切れです。情シスに新しい CA を確認してください。" >&2
    fi
  fi
fi

# --- 3. certifi bundle path を取得 -----------------------------------------

CERTIFI_PATH="$(uv run python -c 'import certifi; print(certifi.where())')"
if [[ ! -f "$CERTIFI_PATH" ]]; then
  echo "certifi bundle が見つかりません: $CERTIFI_PATH" >&2
  exit 1
fi

# --- 4. 合成 bundle を書き出す ---------------------------------------------

mkdir -p "$(dirname "$OUT_PATH")"
cat "$CERTIFI_PATH" "$CA_PATH" >"$OUT_PATH"
chmod 644 "$OUT_PATH"
echo ""
echo "[作成] 合成 bundle: $OUT_PATH"
echo "  certifi: $CERTIFI_PATH"
echo "  corp CA: $CA_PATH"

# --- 5. .env に SSL_CERT_FILE / REQUESTS_CA_BUNDLE を書き込む --------------

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

upsert_env_var() {
  local key="$1"
  local value="$2"
  local file="$3"

  if grep -qE "^[[:space:]]*#?[[:space:]]*${key}=" "$file"; then
    awk -v key="$key" -v value="$value" '
      BEGIN { done = 0 }
      {
        if (!done && match($0, "^[[:space:]]*#?[[:space:]]*" key "=")) {
          print key "=" value
          done = 1
          next
        }
        print
      }
    ' "$file" >"$TMP_FILE"
    mv "$TMP_FILE" "$file"
  else
    if [[ -s "$file" ]] && [[ "$(tail -c1 "$file" | od -An -c | tr -d ' ')" != "\\n" ]]; then
      printf "\n" >>"$file"
    fi
    printf "%s=%s\n" "$key" "$value" >>"$file"
  fi
}

upsert_env_var "SSL_CERT_FILE" "$OUT_PATH" "$ENV_FILE"
upsert_env_var "REQUESTS_CA_BUNDLE" "$OUT_PATH" "$ENV_FILE"

trap - EXIT
chmod 600 "$ENV_FILE" 2>/dev/null || true

echo ""
echo "[更新] .env に書き込みました:"
echo "  SSL_CERT_FILE=$OUT_PATH"
echo "  REQUESTS_CA_BUNDLE=$OUT_PATH"

# --- 6. 次のアクション案内 -------------------------------------------------

echo ""
echo "次に行うこと:"
echo "  1. 'mise run check-keys-live' で probe が OK になることを確認します。"
echo "  2. 'mise run serve' が起動中なら再起動してください (古い環境変数を保持しているため)。"
echo ""
echo "社内 CA が更新された場合は、このコマンドを再実行すれば合成 bundle を作り直せます。"
