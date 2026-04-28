#!/usr/bin/env bash

#MISE description="コピー直後の brain を空の状態に初期化する（template repo 本体では拒否）"

# Scaffold a fresh brain in the current directory by emptying inherited
# template content and restoring index.md / log.md to their frontmatter
# skeletons. Run this right after copying the twin-layer-brain-template
# into a new directory (or cloning from the template on GitHub).
#
# Usage: cd ~/programs/brains/twin-layer-brain-<topic> && mise run scaffold-brain
#
# What it does:
#   - Removes all files under raw/{notes,articles,assets}/ and
#     wiki/{sources,entities,concepts,topics,analyses}/ except .gitkeep markers.
#   - Rewrites wiki/index.md and wiki/log.md to empty frontmatter-only form.
#   - Leaves CLAUDE.md, AGENTS.md, README.md, docs/, the skill packages,
#     and compiler/server infra untouched (you edit the Scope line in
#     CLAUDE.md, AGENTS.md, and README.md by hand).
#
# Safety: refuses to run in a directory literally named twin-layer-brain-template
# (the template itself) unless FORCE=1 is set.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASENAME="$(basename "$ROOT_DIR")"

if [[ "$BASENAME" == "twin-layer-brain-template" && "${FORCE:-}" != "1" ]]; then
  echo "[refuse] Running in the template repo ($BASENAME)." >&2
  echo "         scaffold-brain is for freshly cloned derivative brains." >&2
  echo "         If you really mean it, re-run with FORCE=1." >&2
  exit 2
fi

echo "[scaffold] Initialising brain in $ROOT_DIR"
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

echo "Next steps:"
echo "  1. Rewrite the Scope line in CLAUDE.md, AGENTS.md, and README.md."
echo "  2. git add -A && git commit -m \"ブレインの初期スコープを設定\""
echo "  3. Drop a source into raw/notes/ (or run \`mise run clone-repo\`) and ingest it."
