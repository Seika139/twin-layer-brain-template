#!/usr/bin/env bash

#MISE description="ingest 用に GitHub repo を raw/repos/ へ clone し、repos.json に記録する（引数: <owner>/<repo> [branch]）"
#MISE quiet=true

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "使い方: mise run clone-repo <owner>/<repo> [branch]" >&2
  exit 2
fi

REPO_SPEC="$1"
BRANCH="${2:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST_HELPER="$ROOT_DIR/mise/tasks/lib/repos_manifest.py"

cd "$ROOT_DIR"
# shellcheck disable=SC1091
source "$ROOT_DIR/mise/tasks/common.sh"

# spec から URL と repo 名を導出する。
# "owner/repo" 形式と "git@github.com:owner/repo.git" / "https://..." 形式の両方に対応。
if [[ "$REPO_SPEC" == git@* || "$REPO_SPEC" == https://* || "$REPO_SPEC" == ssh://* ]]; then
  URL="$REPO_SPEC"
else
  URL="git@github.com:${REPO_SPEC}.git"
fi

NAME="$(BRAIN_ROOT="$ROOT_DIR" python3 "$MANIFEST_HELPER" derive-name "$REPO_SPEC")"
TARGET_DIR="$ROOT_DIR/raw/repos/$NAME"

mkdir -p "$ROOT_DIR/raw/repos"

if [[ -d "$TARGET_DIR/.git" ]]; then
  print_dim "[skip] "
  echo "$NAME は既に $TARGET_DIR に clone 済みです"
else
  print_blue "[clone] "
  echo "$URL -> $TARGET_DIR"
  if [[ -n "$BRANCH" ]]; then
    git clone --branch "$BRANCH" --single-branch "$URL" "$TARGET_DIR"
  else
    git clone "$URL" "$TARGET_DIR"
  fi
fi

# repos.json に記録する（既に同名エントリがあれば spec / branch を更新）。
if [[ -n "$BRANCH" ]]; then
  BRAIN_ROOT="$ROOT_DIR" python3 "$MANIFEST_HELPER" add "$REPO_SPEC" --branch "$BRANCH"
else
  BRAIN_ROOT="$ROOT_DIR" python3 "$MANIFEST_HELPER" add "$REPO_SPEC"
fi

echo ""
echo "次のステップ: Claude Code / Codex で以下を実行してください。"
echo "  > ingest raw/repos/$NAME"
