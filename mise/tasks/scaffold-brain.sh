#!/usr/bin/env bash

#MISE description="コピー直後の brain を空の状態に初期化する（template repo 本体では拒否）"

# Scaffold a fresh brain in the current directory by emptying inherited
# template content and restoring index.md / log.md to their frontmatter
# skeletons. Run this right after copying the twin-layer-brain-template
# into a new directory (or cloning from the template on GitHub).
#
# Usage:
#   cd ~/programs/brains/twin-layer-brain-<topic>
#   mise run scaffold-brain                    # TTY: prompt / non-TTY: error
#   mise run scaffold-brain -- -n my-brain     # explicit name
#
# Flags:
#   -n, --name <name>   brain name (pyproject project.name と
#                       chrome-extension/manifest.json の "name" に代入)。
#                       未指定かつ TTY は対話入力、非対話は exit 2。
#                       default: basename of the repo dir.
#
# Env:
#   SCAFFOLD_ICON_COLOR=#RRGGBB  chrome-extension/icon{48,128}.png を塗り替え
#   FORCE=1                      template repo 本体でも実行する
#
# What it does:
#   - Removes all files under raw/{notes,articles,assets}/ and
#     wiki/{sources,entities,concepts,topics,analyses}/ except .gitkeep markers.
#   - Rewrites wiki/index.md and wiki/log.md to empty frontmatter-only form.
#   - Sets pyproject.toml / manifest.json の name = <brain name>, version = 0.0.0.
#   - Leaves CLAUDE.md, AGENTS.md, README.md, docs/, the skill packages,
#     and compiler/server infra untouched (you edit the Scope line in
#     CLAUDE.md, AGENTS.md, and README.md by hand).
#
# Safety: refuses to run in a directory literally named twin-layer-brain-template
# (the template itself) unless FORCE=1 is set.

set -euo pipefail

# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/server.sh"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASENAME="$(basename "$ROOT_DIR")"

if [[ "$BASENAME" == "twin-layer-brain-template" && "${FORCE:-}" != "1" ]]; then
  echo "[refuse] Running in the template repo ($BASENAME)." >&2
  echo "         scaffold-brain is for freshly cloned derivative brains." >&2
  echo "         If you really mean it, re-run with FORCE=1." >&2
  exit 2
fi

# --- Parse CLI: only -n / --name is recognised; other args are errors -------
BRAIN_NAME_ARG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
  -n | --name)
    if [[ $# -lt 2 ]]; then
      echo "[scaffold] $1 に値がありません" >&2
      exit 2
    fi
    BRAIN_NAME_ARG="$2"
    shift 2
    ;;
  -h | --help)
    sed -n '4,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  *)
    echo "[scaffold] unknown argument: $1" >&2
    echo "usage: mise run scaffold-brain -- [-n <name>]" >&2
    exit 2
    ;;
  esac
done

# --- Resolve brain name: explicit flag > TTY prompt > non-TTY error ---------
# BASENAME は repo dir 名なので、大抵のケースでそのまま brain name にしたい。
# ただし「手が滑って twin-layer-brain-template を複製したままの dir 名」を
# 無確認で使われたくないので、対話では必ず確認プロンプトを挟む。
DEFAULT_NAME="$BASENAME"
if [[ -n "$BRAIN_NAME_ARG" ]]; then
  BRAIN_NAME="$BRAIN_NAME_ARG"
elif [[ -t 0 ]]; then
  read -r -p "brain name [${DEFAULT_NAME}]: " BRAIN_NAME
  BRAIN_NAME="${BRAIN_NAME:-$DEFAULT_NAME}"
else
  echo "[scaffold] brain name が指定されていません。" >&2
  echo "           対話実行するか、-n <name> で明示的に指定してください。" >&2
  echo "           例: mise run scaffold-brain -- -n my-brain" >&2
  exit 2
fi

# PEP 508 project.name と chrome manifest の両方で安全な文字集合に絞る。
# 空白や記号が入ると TOML/JSON の quote を壊したり systemd unit 名と衝突する。
if [[ ! "$BRAIN_NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "[scaffold] 不正な brain name: ${BRAIN_NAME}" >&2
  echo "           使用可能な文字: A-Z a-z 0-9 . _ -" >&2
  exit 2
fi

echo "[scaffold] Initialising brain in $ROOT_DIR (name: ${BRAIN_NAME})"
echo ""

# 1. Empty raw/ content directories (keep the dirs themselves via .gitkeep).
for d in raw/notes raw/articles raw/assets; do
  if [[ -d "$ROOT_DIR/$d" ]]; then
    find "$ROOT_DIR/$d" -mindepth 1 ! -name '.gitkeep' -delete
    echo "  - emptied $d/"
  fi
done

# 2. Empty wiki/ content directories.
for d in wiki/sources wiki/entities wiki/concepts wiki/topics wiki/analyses; do
  if [[ -d "$ROOT_DIR/$d" ]]; then
    find "$ROOT_DIR/$d" -mindepth 1 ! -name '.gitkeep' -delete
    echo "  - emptied $d/"
  fi
done

# 3. Reset repos.json to an empty manifest (only if it already exists — a freshly
#    copied template ships with the file; we just empty its entries here).
if [[ -f "$ROOT_DIR/repos.json" ]]; then
  cat >"$ROOT_DIR/repos.json" <<'EOF'
{
  "repos": []
}
EOF
  echo "  - reset repos.json"
fi

# 4. Reset index.md and log.md to frontmatter-only skeletons.
TODAY="$(date +%Y-%m-%d)"

cat >"$ROOT_DIR/wiki/index.md" <<EOF
---
title: Index
type: index
created: ${TODAY}
updated: ${TODAY}
sources: []
tags: [meta]
---

## Topics

_(none yet — promote analyses or recurring claims via the sublime skill)_

## Entities

_(none yet — ingest a source to populate)_

## Concepts

_(none yet)_

## Sources

_(none yet)_
EOF
echo "  - reset wiki/index.md"

cat >"$ROOT_DIR/wiki/log.md" <<EOF
---
title: Log
type: log
created: ${TODAY}
updated: ${TODAY}
sources: []
tags: [meta]
---

Append-only. Entry header format: \`## [YYYY-MM-DD] <type> | <one-line subject>\`. Parseable with \`grep "^## \[" log.md\`.

Entry types: \`ingest\`, \`query\`, \`sublime\`, \`dive\`, \`lint\`, \`refactor\`.

---

## [${TODAY}] refactor | initialise brain from template

- Scaffolded from the twin-layer-brain template.
- Next: rewrite the Scope line in CLAUDE.md, AGENTS.md, and README.md, then ingest the first source.
EOF
echo "  - reset wiki/log.md"

echo ""

# 4. Scan the three Scope-bearing files for placeholder strings the user must
#    rewrite. Surfacing them at scaffold time prevents the AGENTS.md-was-missed
#    incident where one of the three files silently kept its template marker.
remaining=()
for f in CLAUDE.md AGENTS.md README.md; do
  if [[ -f "$ROOT_DIR/$f" ]] && grep -q -e "<このブレインが扱う範囲" -e "<ここにこのブレインが" "$ROOT_DIR/$f"; then
    remaining+=("$f")
  fi
done
if ((${#remaining[@]} > 0)); then
  echo "[warn] Scope placeholder still present in: ${remaining[*]}" >&2
  echo "       Open each file and replace the placeholder with this brain's scope." >&2
  echo ""
fi

# 4.5. Stamp the brain name into pyproject.toml and chrome-extension/manifest.json.
#      Both files are edited line-by-line (not round-tripped) so the rest of the
#      file's formatting and comments stay intact — this keeps diff-template
#      comparisons with the upstream template minimal.
rewrite_line_in_place() {
  # rewrite_line_in_place <file> <awk match pattern> <replacement line>
  # Replaces the FIRST matching line with the given replacement.
  local file="$1" pattern="$2" replacement="$3"
  local tmp
  tmp="$(mktemp)"
  awk -v pat="$pattern" -v repl="$replacement" '
    !done && $0 ~ pat { print repl; done = 1; next }
    { print }
  ' "$file" >"$tmp"
  mv "$tmp" "$file"
}

PYPROJECT="$ROOT_DIR/pyproject.toml"
if [[ -f "$PYPROJECT" ]]; then
  rewrite_line_in_place "$PYPROJECT" \
    '^[[:space:]]*name[[:space:]]*=' \
    "name = \"${BRAIN_NAME}\""
  rewrite_line_in_place "$PYPROJECT" \
    '^[[:space:]]*version[[:space:]]*=' \
    'version = "0.0.0"'
  echo "  - stamped pyproject.toml (name=${BRAIN_NAME}, version=0.0.0)"
fi

MANIFEST="$ROOT_DIR/chrome-extension/manifest.json"
if [[ -f "$MANIFEST" ]]; then
  rewrite_line_in_place "$MANIFEST" \
    '^[[:space:]]*"name"[[:space:]]*:' \
    "  \"name\": \"${BRAIN_NAME}\","
  rewrite_line_in_place "$MANIFEST" \
    '^[[:space:]]*"version"[[:space:]]*:' \
    '  "version": "0.0.0",'
  echo "  - stamped chrome-extension/manifest.json (name=${BRAIN_NAME}, version=0.0.0)"
fi

# 5. Pick a free BRAIN_PORT so this brain doesn't collide with siblings already
#    listening on 15200. Probing the OS (bash /dev/tcp) avoids hardcoding
#    "scan ~/programs/brains/*/.env" — works even if brains live elsewhere.
ENV_FILE="$ROOT_DIR/.env"
ENV_EXAMPLE="$ROOT_DIR/.env.example"
if [[ ! -f "$ENV_FILE" && -f "$ENV_EXAMPLE" ]]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "  - created .env from .env.example"
fi

if [[ -f "$ENV_FILE" ]]; then
  # Treat an uncommented BRAIN_PORT= line as user-configured and leave it.
  if grep -qE '^[[:space:]]*BRAIN_PORT[[:space:]]*=' "$ENV_FILE"; then
    existing_port="$(brain_port)"
    echo "  - BRAIN_PORT は .env で既に設定されています (${existing_port})"
  else
    if port="$(find_available_port 15200 100)"; then
      # Replace the commented template line if present, otherwise append.
      if grep -qE '^[[:space:]]*#[[:space:]]*BRAIN_PORT[[:space:]]*=' "$ENV_FILE"; then
        # Portable in-place edit: avoids GNU/BSD sed -i flag divergence.
        tmp="$(mktemp)"
        awk -v port="$port" '
          /^[[:space:]]*#[[:space:]]*BRAIN_PORT[[:space:]]*=/ && !done {
            print "BRAIN_PORT=" port
            done = 1
            next
          }
          { print }
        ' "$ENV_FILE" >"$tmp"
        mv "$tmp" "$ENV_FILE"
      else
        printf '\nBRAIN_PORT=%s\n' "$port" >>"$ENV_FILE"
      fi
      echo "  - set BRAIN_PORT=${port} in .env (15200 から順に空きを検出)"
    else
      echo "[warn] 空きポートが見つかりませんでした。.env の BRAIN_PORT を手動で設定してください。" >&2
    fi
  fi
fi

# 6. Recolor the chrome-extension icons so brain identity is visible in the
#    browser toolbar. Only the teal accent pixels are swapped; white text and
#    black outline are preserved. Set SCAFFOLD_ICON_COLOR=#RRGGBB to choose a
#    color; unset leaves the template teal as-is.
if [[ -n "${SCAFFOLD_ICON_COLOR:-}" ]]; then
  if [[ -d "$ROOT_DIR/chrome-extension" ]]; then
    icons=("$ROOT_DIR/chrome-extension/icon48.png" "$ROOT_DIR/chrome-extension/icon128.png")
    existing_icons=()
    for i in "${icons[@]}"; do
      [[ -f "$i" ]] && existing_icons+=("$i")
    done
    if ((${#existing_icons[@]} > 0)); then
      if command -v uv >/dev/null 2>&1; then
        if uv run --with pillow --quiet python \
          "$ROOT_DIR/mise/tasks/lib/recolor-icon.py" \
          --target "$SCAFFOLD_ICON_COLOR" \
          "${existing_icons[@]}"; then
          echo "  - recolored chrome-extension icons to $SCAFFOLD_ICON_COLOR"
        else
          echo "[warn] アイコンの recolor に失敗しました。SCAFFOLD_ICON_COLOR の値を確認してください。" >&2
        fi
      else
        echo "[warn] uv が見つからないため SCAFFOLD_ICON_COLOR を適用できませんでした。" >&2
      fi
    fi
  fi
else
  echo "  - chrome-extension icons left unchanged (set SCAFFOLD_ICON_COLOR=#RRGGBB to recolor)"
fi

echo ""
echo "Next steps:"
echo "  1. Rewrite the Scope line in CLAUDE.md, AGENTS.md, and README.md."
echo "  2. git add -A && git commit -m \"ブレインの初期スコープを設定\""
echo "  3. Drop a source into raw/notes/ (or run \`mise run clone-repo\`) and ingest it."
