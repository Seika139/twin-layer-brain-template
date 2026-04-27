#!/usr/bin/env bash

#MISE description="macOS launchd service と /api/health の状態を確認する"
#MISE hide=true

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"
require_launchctl

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

LABEL="$(brain_label)"
PORT="$(brain_port)"
SERVICE_TARGET="gui/$(id -u)/${LABEL}"

raw="$(launchctl print "$SERVICE_TARGET" 2>/dev/null)" || {
  echo "launchd service は登録されていません: $LABEL"
  echo "  install: mise run serve-install"
  exit 1
}

if [[ "$verbose" == "1" ]]; then
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

if curl -sf -m 2 "http://localhost:${PORT}/api/health" >/dev/null; then
  health_ok=1
  health_msg="200 OK"
else
  health_ok=0
  health_msg="(no response on :${PORT})"
fi
printf 'health    : %s\n' "$health_msg"

if [[ "$verbose" != "1" ]]; then
  echo ""
  echo "詳細を見る場合: mise run serve-status -v"
fi

# Exit non-zero so this task can act as a readiness/health gate when invoked
# from scripts. Display logic above always runs for human diagnosis.
if [[ "$state" != "running" || "$health_ok" != "1" ]]; then
  exit 1
fi
