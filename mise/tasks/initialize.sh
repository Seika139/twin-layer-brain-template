#!/usr/bin/env bash

#MISE description="brain instance の初期化（ディレクトリ作成、依存同期、index .env 作成）"
#MISE quiet=true
#MISE hide=true

# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

mkdir -p raw/notes raw/articles raw/assets wiki/sources \
  wiki/entities wiki/concepts wiki/topics wiki/analyses index

print_blue "pnpm install"$'\n'
pnpm install

print_blue "uv sync"$'\n'
uv sync

print_blue "uv run kc index"$'\n'
uv run kc index

if [ ! -f .env ]; then
  print_blue "Creating .env file from .env.example"$'\n'
  cp .env.example .env
fi
