#!/usr/bin/env bash
# git pull every repo under raw/repos/ and report which ones changed.
# Usage: mise run update-repos

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPOS_DIR="$ROOT_DIR/raw/repos"

if [[ ! -d "$REPOS_DIR" ]]; then
    echo "No $REPOS_DIR — nothing to update."
    exit 0
fi

changed=()
unchanged=()
failed=()

for d in "$REPOS_DIR"/*/; do
    [[ -d "$d/.git" ]] || continue
    name="$(basename "$d")"
    before="$(git -C "$d" rev-parse HEAD 2>/dev/null || echo none)"
    if git -C "$d" pull --ff-only >/dev/null 2>&1; then
        after="$(git -C "$d" rev-parse HEAD)"
        if [[ "$before" != "$after" ]]; then
            changed+=("$name")
        else
            unchanged+=("$name")
        fi
    else
        failed+=("$name")
    fi
done

echo "=== update-repos ==="
echo "changed:   ${#changed[@]} (${changed[*]:-})"
echo "unchanged: ${#unchanged[@]}"
echo "failed:    ${#failed[@]} (${failed[*]:-})"
echo ""

if [[ ${#changed[@]} -gt 0 ]]; then
    echo "Next: consider re-ingesting the changed repos:"
    for name in "${changed[@]}"; do
        echo "  > re-ingest raw/repos/$name"
    done
fi
