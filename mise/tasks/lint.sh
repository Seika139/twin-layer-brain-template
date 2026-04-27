#!/usr/bin/env bash

#MISE description="lint を実行する（既定: Markdown のみ、--all/-a: Markdown + ruff + shfmt）"

set -euo pipefail

all=0

for arg in "$@"; do
  case "$arg" in
  --all | -a)
    all=1
    ;;
  *)
    echo "Usage: mise run lint [--all|-a]" >&2
    exit 2
    ;;
  esac
done

rumdl check .
markdownlint-cli2

if [[ "$all" == "1" ]]; then
  echo "Markdown に加えて ruff と shfmt も実行します..."
  uv run ruff check compiler server tests
  shfmt -d mise/tasks/*.sh mise/tasks/lib/*.sh
fi
