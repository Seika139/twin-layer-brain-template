#!/usr/bin/env bash

#MISE description="repos.json に従って raw/repos/ を同期する（未 clone は clone、既存は git pull --ff-only、--prune で孤立 repo を退避）"

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST_HELPER="$ROOT_DIR/mise/tasks/lib/repos_manifest.py"
REPOS_DIR="$ROOT_DIR/raw/repos"
TRASH_DIR="$REPOS_DIR/.trash"

PRUNE=0
for arg in "$@"; do
  case "$arg" in
  --prune)
    PRUNE=1
    ;;
  -h | --help)
    cat <<'EOF'
使い方: mise run update-repos [--prune]

repos.json に従って raw/repos/ 配下を同期します。

  - マニフェストにあるが未 clone の repo を clone する。
  - 既存 repo は git pull --ff-only で更新する。
  - マニフェストに載っていない repo (orphan) を一覧表示する。
  - --prune を付けると orphan を raw/repos/.trash/ に退避し、最終削除用の
    rm コマンドを stdout に表示する。
EOF
    exit 0
    ;;
  *)
    echo "未知の引数: $arg" >&2
    echo "使い方: mise run update-repos [--prune]" >&2
    exit 2
    ;;
  esac
done

mkdir -p "$REPOS_DIR"

cloned=()
updated=()
unchanged=()
failed=()

# 1. マニフェストに基づいて clone / pull する。
while IFS=$'\t' read -r NAME SPEC BRANCH; do
  [[ -z "$NAME" ]] && continue
  TARGET="$REPOS_DIR/$NAME"

  if [[ "$SPEC" == git@* || "$SPEC" == https://* || "$SPEC" == ssh://* ]]; then
    URL="$SPEC"
  else
    URL="git@github.com:${SPEC}.git"
  fi

  if [[ ! -d "$TARGET/.git" ]]; then
    echo "[clone] $NAME ($URL)"
    if [[ -n "$BRANCH" ]]; then
      if git clone --branch "$BRANCH" --single-branch "$URL" "$TARGET" >/dev/null 2>&1; then
        cloned+=("$NAME")
      else
        failed+=("$NAME (clone 失敗)")
      fi
    else
      if git clone "$URL" "$TARGET" >/dev/null 2>&1; then
        cloned+=("$NAME")
      else
        failed+=("$NAME (clone 失敗)")
      fi
    fi
    continue
  fi

  before="$(git -C "$TARGET" rev-parse HEAD 2>/dev/null || echo none)"
  if git -C "$TARGET" pull --ff-only >/dev/null 2>&1; then
    after="$(git -C "$TARGET" rev-parse HEAD)"
    if [[ "$before" != "$after" ]]; then
      updated+=("$NAME")
    else
      unchanged+=("$NAME")
    fi
  else
    failed+=("$NAME (pull 失敗)")
  fi
done < <(BRAIN_ROOT="$ROOT_DIR" python3 "$MANIFEST_HELPER" list)

# 2. orphan 検出 (raw/repos/ にあるが repos.json に無い)。
orphans=()
while IFS= read -r name; do
  [[ -z "$name" ]] && continue
  orphans+=("$name")
done < <(BRAIN_ROOT="$ROOT_DIR" python3 "$MANIFEST_HELPER" orphans)

# 3. 結果を表示する。
echo "=== update-repos ==="
echo "clone 済み: ${#cloned[@]}${cloned[*]:+ (${cloned[*]})}"
echo "更新あり:   ${#updated[@]}${updated[*]:+ (${updated[*]})}"
echo "更新なし:   ${#unchanged[@]}"
echo "失敗:       ${#failed[@]}${failed[*]:+ (${failed[*]})}"
echo "孤立 repo:  ${#orphans[@]}${orphans[*]:+ (${orphans[*]})}"
echo ""

if [[ ${#updated[@]} -gt 0 || ${#cloned[@]} -gt 0 ]]; then
  echo "更新があった repo は再 ingest を検討してください:"
  for name in "${cloned[@]}" "${updated[@]}"; do
    echo "  > re-ingest raw/repos/$name"
  done
  echo ""
fi

# 4. orphan の処理。
if [[ ${#orphans[@]} -eq 0 ]]; then
  exit 0
fi

if [[ "$PRUNE" -eq 0 ]]; then
  echo "孤立 repo を退避するには --prune を付けて再実行してください:"
  echo "  mise run update-repos --prune"
  exit 0
fi

# --prune: orphan を .trash/ へ mv する。
mkdir -p "$TRASH_DIR"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
trashed=()
for name in "${orphans[@]}"; do
  src="$REPOS_DIR/$name"
  dst="$TRASH_DIR/${name}-${TIMESTAMP}"
  if mv "$src" "$dst"; then
    trashed+=("$dst")
    echo "[退避] $name -> $dst"
  else
    echo "[失敗] $name の退避に失敗しました" >&2
  fi
done

if [[ ${#trashed[@]} -gt 0 ]]; then
  echo ""
  echo "退避した repo は $TRASH_DIR/ 配下に残っています。"
  echo "内容を確認した上で、不要であれば以下のコマンドで完全に削除してください:"
  echo ""
  for dst in "${trashed[@]}"; do
    echo "  rm -rf \"$dst\""
  done
  echo ""
  echo "まとめて削除する場合:"
  echo "  rm -rf \"$TRASH_DIR\""
fi
