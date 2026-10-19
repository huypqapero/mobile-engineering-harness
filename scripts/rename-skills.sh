#!/usr/bin/env bash
# One-shot rename: normalize skill names to coding-/business-/testing- prefix.
# Idempotent: skip rename if target already present.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Mapping: old → new
declare -a MAP=(
  "android-feature:coding-feature"
  "android-mvi:coding-mvi"
  "android-compose:coding-compose"
  "android-coroutines:coding-coroutines"
  "android-network:coding-network"
  "android-database:coding-database"
  "android-refactor:coding-refactor"
  "android-diagnose:coding-diagnose"
  "android-code-review:coding-review"
  "android-orchestrator:coding-orchestrator"
  "android-testing:testing-android"
  "input-fetch:business-fetch"
  "input-analyze:business-analyze"
  "input-prepare-feature:business-prepare-feature"
  "input-validate-brief:business-validate-brief"
)

# 1. Rename folders + patch frontmatter `name:`
for pair in "${MAP[@]}"; do
  old="${pair%%:*}"
  new="${pair##*:}"
  if [ -d "skills/$old" ] && [ ! -d "skills/$new" ]; then
    git mv "skills/$old" "skills/$new" 2>/dev/null || mv "skills/$old" "skills/$new"
    # Patch `name:` in frontmatter
    sed -i.bak "s|^name: $old$|name: $new|" "skills/$new/SKILL.md" && rm "skills/$new/SKILL.md.bak"
    echo "renamed: $old → $new"
  else
    echo "skip:    $old (not found or $new exists)"
  fi
done

# 2. Bulk update cross-refs across repo
# Files: AGENTS.md, README.md, workflows/, agents/, knowledge/, skills/*/SKILL.md
# NOT CHANGELOG historical entries (we add a new v0.19.0 entry separately)
echo "---"
echo "updating cross-refs..."

FILES=$(find AGENTS.md README.md workflows agents knowledge -name "*.md" 2>/dev/null; find skills -name "SKILL.md")

for pair in "${MAP[@]}"; do
  old="${pair%%:*}"
  new="${pair##*:}"
  # Match `old` as whole-ish token: wrapped in backticks or at word boundary
  for f in $FILES; do
    if grep -q "$old" "$f" 2>/dev/null; then
      sed -i.bak "s|\`$old\`|\`$new\`|g; s|/$old/|/$new/|g; s|skills/$old|skills/$new|g" "$f"
      rm -f "$f.bak"
    fi
  done
done

echo "---"
echo "verify residual refs..."
remaining=0
for pair in "${MAP[@]}"; do
  old="${pair%%:*}"
  if grep -r "$old" AGENTS.md README.md workflows agents knowledge skills --include="*.md" --include="*.yaml" 2>/dev/null | grep -v "^$0" | head -3; then
    remaining=$((remaining+1))
  fi
done

if [ "$remaining" -eq 0 ]; then
  echo "✓ all cross-refs updated"
else
  echo "⚠ $remaining skills still have residual refs (shown above)"
fi
