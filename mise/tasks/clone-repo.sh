#!/usr/bin/env bash
# Clone a GitHub repo into raw/repos/ for later ingest.
# Usage: mise run clone-repo <owner>/<repo> [branch]
# Example: mise run clone-repo karpathy/nanoGPT
#          mise run clone-repo cyg-idpf/wiki main

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: mise run clone-repo <owner>/<repo> [branch]" >&2
    exit 2
fi

REPO_SPEC="$1"
BRANCH="${2:-}"

# Accept both "owner/repo" and "git@github.com:owner/repo.git" forms.
if [[ "$REPO_SPEC" == git@* || "$REPO_SPEC" == https://* ]]; then
    URL="$REPO_SPEC"
    NAME="$(basename "${REPO_SPEC%.git}")"
else
    URL="git@github.com:${REPO_SPEC}.git"
    NAME="${REPO_SPEC##*/}"
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="$ROOT_DIR/raw/repos/$NAME"

if [[ -d "$TARGET_DIR/.git" ]]; then
    echo "[skip] $NAME already cloned at $TARGET_DIR"
    exit 0
fi

mkdir -p "$ROOT_DIR/raw/repos"

echo "[clone] $URL -> $TARGET_DIR"
if [[ -n "$BRANCH" ]]; then
    git clone --branch "$BRANCH" --single-branch "$URL" "$TARGET_DIR"
else
    git clone "$URL" "$TARGET_DIR"
fi

echo ""
echo "Next: open Claude Code / Codex and say:"
echo "  > ingest raw/repos/$NAME"
