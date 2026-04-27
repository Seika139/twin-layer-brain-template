#!/usr/bin/env bash

#MISE description="macOS launchd service と /api/health の状態を確認する"
#MISE hide=true

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
require_launchctl

LABEL="$(brain_label)"
PORT="$(brain_port)"
SERVICE_TARGET="gui/$(id -u)/${LABEL}"

raw="$(launchctl print "$SERVICE_TARGET" 2>/dev/null)" || {
  echo "launchd service は登録されていません: $LABEL"
  echo "  install: mise run serve-install"
  exit 1
}

if [[ "${VERBOSE:-0}" == "1" ]]; then
  printf '%s\n' "$raw"
  echo ""
fi

field() {
  printf '%s\n' "$raw" | awk -F'= ' -v key="$1" '
    $0 ~ "^[[:space:]]*" key "[[:space:]]*=" {
      sub(/^[[:space:]]+/, "", $2)
      print $2
      exit
    }
  '
}

state="$(field state)"
pid="$(field pid)"
runs="$(field runs)"
last_exit="$(field 'last exit code')"

printf 'label     : %s\n' "$LABEL"
printf 'state     : %s\n' "${state:-unknown}"
printf 'pid       : %s\n' "${pid:-(none)}"
printf 'runs      : %s\n' "${runs:-0}"
printf 'last exit : %s\n' "${last_exit:-(none)}"
printf 'port      : %s\n' "$PORT"

printf 'health    : '
if curl -sf -m 2 "http://localhost:${PORT}/api/health" >/dev/null; then
  echo "200 OK"
else
  echo "(no response on :${PORT})"
fi

if [[ "${VERBOSE:-0}" != "1" ]]; then
  echo ""
  echo "詳細を見る場合: VERBOSE=1 mise run serve-status"
fi
