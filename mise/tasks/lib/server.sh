#!/usr/bin/env bash

set -euo pipefail

brain_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd
}

brain_name() {
  basename "$(brain_root)"
}

brain_label() {
  echo "local.$(brain_name)"
}

systemd_service_name() {
  brain_label
}

brain_port() {
  local root env_file port
  root="$(brain_root)"
  env_file="$root/.env"
  port="${BRAIN_PORT:-}"
  if [[ -z "$port" && -f "$env_file" ]]; then
    port="$(
      awk -F= '
        /^[[:space:]]*BRAIN_PORT[[:space:]]*=/ {
          value = $2
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
          gsub(/^["'\'']|["'\'']$/, "", value)
          print value
          exit
        }
      ' "$env_file"
    )"
  fi
  echo "${port:-15200}"
}

dispatch_server_task() {
  local action os
  action="$1"
  shift
  os="$(uname -s)"
  case "$os" in
  Darwin)
    exec "$(brain_root)/mise/tasks/serve-launchd-${action}.sh" "$@"
    ;;
  Linux)
    exec "$(brain_root)/mise/tasks/serve-systemd-${action}.sh" "$@"
    ;;
  *)
    echo "未対応 OS です: $os" >&2
    exit 2
    ;;
  esac
}

require_launchctl() {
  if ! command -v launchctl >/dev/null 2>&1; then
    echo "launchctl が見つかりません。この task は macOS launchd 用です。" >&2
    exit 2
  fi
}

require_systemctl_user() {
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl が見つかりません。この task は Linux systemd --user 用です。" >&2
    exit 2
  fi
  if ! systemctl --user show-environment >/dev/null 2>&1; then
    cat >&2 <<'EOF'
systemd --user に接続できません。
Linux では user service を使う想定です。

WSL の場合は /etc/wsl.conf に以下を設定して WSL を再起動してください。

[boot]
systemd=true

VPS で system service として運用する場合は deploy/setup.sh と systemctl を使ってください。
EOF
    exit 2
  fi
}
