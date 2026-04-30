#!/usr/bin/env bash

#MISE description="format を実行する（既定: Markdown のみ、--all/-a: Markdown + ruff + shfmt + taplo）"
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
    print_red "Usage: mise run format [--all|-a]" >&2
    exit 2
    ;;
  esac
done

print_blue "Formatting Markdown files"$'\n'
rumdl check --fix .
markdownlint-cli2 --fix

if [[ "$all" == "1" ]]; then
  print_blue "Format Python files with ruff"$'\n'
  uv run ruff format compiler server tests mise/tasks/lib
  uv run ruff check --fix compiler server tests mise/tasks/lib

  print_blue "Format shell scripts with shfmt"$'\n'
  shfmt -w mise/tasks/*.sh mise/tasks/lib/*.sh

  print_blue "Format toml with taplo"$'\n'
  taplo fmt

  print_blue "Format YAML files with yamllint"$'\n'
  yamllint -f parsable . | while IFS= read -r line; do
    # yamllint の出力をパースして、ファイル名と行番号を抽出
    if [[ "$line" =~ ^([^:]+):([0-9]+):([0-9]+):\ (.*)$ ]]; then
      file="${BASH_REMATCH[1]}"
      line_num="${BASH_REMATCH[2]}"
      col_num="${BASH_REMATCH[3]}"
      message="${BASH_REMATCH[4]}"
      # sed を使って該当行を修正（ここでは単純に行末のスペースを削除する例）
      sed -i '' "${line_num}s/[[:space:]]\+$//" "$file"
      print_green "Fixed $file:${line_num}:${col_num}: $message"$'\n'
    fi
  done
fi
