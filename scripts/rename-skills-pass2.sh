#!/usr/bin/env bash
# Second pass: substring replace for all old skill names → new names.
# Longest-first order to avoid prefix overlap (e.g. android-code-review before android-code).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

MAP=(
  "input-prepare-feature:business-prepare-feature"
  "input-validate-brief:business-validate-brief"
  "android-code-review:coding-review"
  "android-orchestrator:coding-orchestrator"
  "android-coroutines:coding-coroutines"
  "android-diagnose:coding-diagnose"
  "android-database:coding-database"
  "android-refactor:coding-refactor"
  "android-network:coding-network"
  "android-feature:coding-feature"
  "android-compose:coding-compose"
  "android-testing:testing-android"
  "android-mvi:coding-mvi"
  "input-analyze:business-analyze"
  "input-fetch:business-fetch"
)

# Gather target files
mapfile -t FILES < <(find AGENTS.md README.md workflows agents knowledge skills -name "*.md" 2>/dev/null)

for pair in "${MAP[@]}"; do
  old="${pair%%:*}"
  new="${pair##*:}"
  for f in "${FILES[@]}"; do
    if grep -q "$old" "$f" 2>/dev/null; then
      sed -i.bak "s|$old|$new|g" "$f"
      rm "$f.bak"
    fi
  done
done

echo "---verify remaining---"
remaining=0
for pair in "${MAP[@]}"; do
  old="${pair%%:*}"
  hits=$(grep -rn "$old" AGENTS.md README.md workflows agents knowledge skills --include="*.md" 2>/dev/null || true)
  if [ -n "$hits" ]; then
    echo "$hits"
    remaining=$((remaining+1))
  fi
done
if [ "$remaining" -eq 0 ]; then
  echo "✓ all names migrated"
fi
