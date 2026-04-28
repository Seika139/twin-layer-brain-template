#!/usr/bin/env bash

#MISE description="lint を実行する（既定: Markdown のみ、--all/-a: Markdown + ruff + shfmt）"
#MISE quiet=true

set -euo pipefail

# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

all=0

for arg in "$@"; do
  case "$arg" in
  --all | -a)
    all=1
    ;;
  *)
    print_red "Usage: mise run lint [--all|-a]" >&2
    exit 2
    ;;
  esac
done

print_blue "Linting Markdown files"
rumdl check .
markdownlint-cli2

if [[ "$all" == "1" ]]; then
  print_blue "Markdown の Lint に加えて ruff と shfmt も実行します"$'\n'
  uv run ruff check compiler server tests mise/tasks/lib
  shfmt -d mise/tasks/*.sh mise/tasks/lib/*.sh
fi
