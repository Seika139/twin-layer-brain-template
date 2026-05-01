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
  print_blue "Lint Python files with ruff & mypy"$'\n'
  uv run ruff check compiler server tests mise/tasks/lib
  uv run mypy compiler server tests mise/tasks/lib

  print_blue "Lint shell scripts with shfmt & shellcheck"$'\n'
  shfmt -d mise/tasks/*.sh mise/tasks/lib/*.sh
  shellcheck_files=()
  while IFS= read -r -d '' file; do
    shellcheck_files+=("$file")
  done < <(find . -type f \( -name "*.sh" -o -name "*.bash" \) -not -path "./.venv/*" -not -path "./node_modules/*" -not -path "./.git/*" -not -path "./raw/*" -not -path "./tmp/*" -not -path "./.serena/*" -print0)
  if [ "${shellcheck_files[0]+_}" ]; then
    shellcheck -x -P SCRIPTDIR "${shellcheck_files[@]}"
  else
    print_red "No shell scripts found; skipping shellcheck."$'\n'
  fi

  print_blue "Lint toml with taplo"$'\n'
  taplo fmt --check --diff

  print_blue "Lint YAML files with yamllint"$'\n'
  yamllint .
fi
