#!/usr/bin/env bash
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
#   - Leaves CLAUDE.md, AGENTS.md, README.md, GUIDE.md, the skill packages,
#     and compiler/server infra untouched (you edit the Scope line in
#     README.md and CLAUDE.md by hand).
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

# 3. Reset index.md and log.md to frontmatter-only skeletons.
TODAY="$(date +%Y-%m-%d)"

cat > "$ROOT_DIR/wiki/index.md" <<EOF
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

cat > "$ROOT_DIR/wiki/log.md" <<EOF
---
title: Log
type: log
created: ${TODAY}
updated: ${TODAY}
sources: []
tags: [meta]
---

Append-only. Entry header format: \`## [YYYY-MM-DD] <type> | <one-line subject>\`. Parseable with \`grep "^## \[" log.md\`.

Entry types: \`ingest\`, \`query\`, \`lint\`, \`refactor\`.

---

## [${TODAY}] refactor | initialise brain from template

- Scaffolded from the twin-layer-brain template.
- Next: rewrite the Scope line in README.md and CLAUDE.md, then ingest the first source.
EOF
echo "  - reset wiki/log.md"

echo ""
echo "Next steps:"
echo "  1. Rewrite the Scope line in README.md and CLAUDE.md."
echo "  2. git add -A && git commit -m \"ブレインの初期スコープを設定\""
echo "  3. Drop a source into raw/notes/ (or run \`mise run clone-repo\`) and ingest it."
