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

# 127.0.0.1:<port> に listener がいれば 0, いなければ非ゼロを返す。
# bash 組み込みの /dev/tcp を使うので、lsof / ss / nc / python などに依存しない。
port_in_use() {
  local port="$1"
  (exec 3<>"/dev/tcp/127.0.0.1/${port}") 2>/dev/null || return 1
  exec 3>&- 3<&-
  return 0
}

# ${1:-15200} から順に空きポートを探す。${2:-100} 回試しても見つからなければ非ゼロ。
find_available_port() {
  local start="${1:-15200}"
  local max_tries="${2:-100}"
  local i p
  for ((i = 0; i < max_tries; i++)); do
    p=$((start + i))
    if ! port_in_use "$p"; then
      echo "$p"
      return 0
    fi
  done
  echo "[find_available_port] ${start}..$((start + max_tries - 1)) は全て使用中です" >&2
  return 1
}

# 127.0.0.1:<port> で listen している process の pid を 1 つだけ返す。
# Linux は ss, macOS は lsof を使う。どちらも無ければ空文字。
listener_pid_for_port() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -tlnpH "sport = :${port}" 2>/dev/null |
      grep -oE 'pid=[0-9]+' |
      head -n1 |
      sed 's/pid=//'
    return
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null | head -n1
  fi
}

# pid の cwd を絶対 path で返す。/proc が無い macOS は lsof fallback。
listener_cwd_for_pid() {
  local pid="$1"
  [[ -n "$pid" ]] || return 0
  if [[ -L "/proc/${pid}/cwd" ]]; then
    readlink "/proc/${pid}/cwd" 2>/dev/null
    return
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -p "$pid" 2>/dev/null | awk '$4 == "cwd" {print $NF; exit}'
  fi
}

# listener pid が service の MainPID と食い違っていたら警告行を出力する。
# 一致 / listener 不在 / service_pid 不明のときは何も出さない。
print_port_conflict_if_any() {
  local port="$1" service_pid="$2"
  local listener_pid listener_cwd
  listener_pid="$(listener_pid_for_port "$port")"
  [[ -n "$listener_pid" ]] || return 0
  [[ "$listener_pid" == "$service_pid" ]] && return 0
  listener_cwd="$(listener_cwd_for_pid "$listener_pid")"
  printf 'conflict  : port :%s は別プロセス pid %s が保持しています' \
    "$port" "$listener_pid"
  [[ -n "$listener_cwd" ]] && printf ' (cwd: %s)' "$listener_cwd"
  printf '\n'
  printf '            この service は bind できません。別プロセスを止めるか、.env の BRAIN_PORT を変更してください。\n'
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
