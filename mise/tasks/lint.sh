#!/usr/bin/env bash

#MISE description="lint を実行する（既定: Markdown のみ、--all/-a: Markdown + ruff + shfmt + taplo）"
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

print_blue "Linting Markdown files"$'\n'
rumdl check .
markdownlint-cli2

if [[ "$all" == "1" ]]; then
  print_blue "Lint Python files with ruff"$'\n'
  uv run ruff check compiler server tests mise/tasks/lib
  print_blue "Lint shell scripts with shfmt"$'\n'
  shfmt -d mise/tasks/*.sh mise/tasks/lib/*.sh
  print_blue "Lint toml with taplo"$'\n'
  taplo fmt --check --diff
fi
