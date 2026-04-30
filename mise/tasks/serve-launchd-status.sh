#!/usr/bin/env bash

#MISE description="Linux systemd --user service と /api/health の状態を確認する"
#MISE hide=true

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
require_systemctl_user

verbose=0
while [[ $# -gt 0 ]]; do
  case "$1" in
  -v | --verbose)
    verbose=1
    ;;
  *)
    echo "unknown argument: $1" >&2
    echo "usage: mise run serve-status [-v|--verbose]" >&2
    exit 2
    ;;
  esac
  shift
done
[[ "${VERBOSE:-0}" == "1" ]] && verbose=1

SERVICE="$(systemd_service_name)"
PORT="$(brain_port)"

if ! systemctl --user cat "$SERVICE" >/dev/null 2>&1; then
  echo "systemd --user service は登録されていません: $SERVICE"
  echo "  install: mise run serve-install"
  exit 1
fi

if [[ "$verbose" == "1" ]]; then
  systemctl --user status "$SERVICE" --no-pager || true
  echo ""
  echo "--- recent journal (last 20) ---"
  journalctl --user -u "$SERVICE" -n 20 --no-pager || true
  echo ""
fi

active_state=""
sub_state=""
main_pid=""
n_restarts=""
exec_status=""
while IFS='=' read -r key value; do
  case "$key" in
  ActiveState) active_state="$value" ;;
  SubState) sub_state="$value" ;;
  MainPID) main_pid="$value" ;;
  NRestarts) n_restarts="$value" ;;
  ExecMainStatus) exec_status="$value" ;;
  esac
done < <(systemctl --user show "$SERVICE" \
  -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus 2>/dev/null)

printf 'service   : %s\n' "$SERVICE"
printf 'state     : %s/%s\n' "${active_state:-unknown}" "${sub_state:-unknown}"
printf 'pid       : %s\n' "${main_pid:-(none)}"
printf 'restarts  : %s\n' "${n_restarts:-0}"
printf 'last exit : %s\n' "${exec_status:-(none)}"
printf 'port      : %s\n' "$PORT"

# service が active でないとき /api/health を叩くと、別 brain が同じ port で
# 応答している場合に健全と誤診する。active 時だけ health check を行う。
if [[ "$active_state" == "active" ]]; then
  if curl -sf -m 2 "http://localhost:${PORT}/api/health" >/dev/null; then
    health_ok=1
    health_msg="200 OK"
  else
    health_ok=0
    health_msg="(no response on :${PORT})"
  fi
else
  health_ok=0
  health_msg="(skipped: service not active)"
fi
printf 'health    : %s\n' "$health_msg"

print_port_conflict_if_any "$PORT" "$main_pid"

if [[ "$verbose" != "1" ]]; then
  echo ""
  echo "詳細を見る場合: mise run serve-status -v"
fi

# Exit non-zero so this task can act as a readiness/health gate when invoked
# from scripts. Display logic above always runs for human diagnosis.
if [[ "$active_state" != "active" || "$health_ok" != "1" ]]; then
  exit 1
fi
