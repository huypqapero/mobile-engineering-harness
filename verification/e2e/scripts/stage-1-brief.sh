#!/usr/bin/env bash
# Stage 1 — Validate brief package: schema + semantic + golden diff.
#
# Usage (called from run-e2e.sh):
#   stage-1-brief.sh <fixture-dir> <results-file>

set -euo pipefail

FIXTURE_DIR="$1"
RESULTS="$2"

BRIEF_ACTUAL="$FIXTURE_DIR/actual/brief.yaml"
BRIEF_GOLDEN="$FIXTURE_DIR/expected/brief.golden.yaml"
SEMANTICS="$FIXTURE_DIR/expected/brief.semantics.yaml"

echo "  - name: brief" >> "$RESULTS"

if [ ! -f "$BRIEF_ACTUAL" ]; then
  echo "    status: skip" >> "$RESULTS"
  echo "    details: no actual brief.yaml (fixture/actual/brief.yaml missing — run agent first)" >> "$RESULTS"
  printf "  stage-1 brief: SKIP (no actual output)\n"
  exit 0
fi

if [ ! -f "$SEMANTICS" ]; then
  echo "    status: fail" >> "$RESULTS"
  echo "    exit_code: 10" >> "$RESULTS"
  echo "    details: expected/brief.semantics.yaml missing" >> "$RESULTS"
  printf "  stage-1 brief: FAIL (semantics file missing)\n"
  exit 1
fi

verbose_flag=""
[ "${VERBOSE:-0}" -eq 1 ] && verbose_flag="--verbose"

output=$(python3 "$VALIDATORS/validate_brief.py" \
  --brief "$BRIEF_ACTUAL" \
  --schema "$SCHEMA" \
  --semantics "$SEMANTICS" \
  $verbose_flag 2>&1) && rc=0 || rc=$?

printf "%s\n" "$output" | sed 's/^/    /'

drift_count=0
if [ -f "$BRIEF_GOLDEN" ]; then
  diff_output=$(python3 "$VALIDATORS/diff_golden.py" \
    --actual "$BRIEF_ACTUAL" \
    --golden "$BRIEF_GOLDEN" \
    $verbose_flag 2>&1) && diff_rc=0 || diff_rc=$?
  drift_count=$(printf "%s\n" "$diff_output" | grep -c "^  " || true)
  printf "%s\n" "$diff_output" | sed 's/^/    /'
  if [ "$diff_rc" -eq 20 ] && [ "$rc" -eq 0 ]; then
    rc=20
  fi
fi

if [ "$rc" -eq 0 ]; then
  echo "    status: pass" >> "$RESULTS"
  echo "    exit_code: 0" >> "$RESULTS"
  echo "    drift_count: $drift_count" >> "$RESULTS"
  echo "    details: schema + semantics pass" >> "$RESULTS"
  printf "  stage-1 brief: PASS\n"
  exit 0
fi

echo "    status: fail" >> "$RESULTS"
echo "    exit_code: $rc" >> "$RESULTS"
echo "    drift_count: $drift_count" >> "$RESULTS"
echo "    details: rc=$rc (1=schema, 2=semantic, 20=golden drift)" >> "$RESULTS"
printf "  stage-1 brief: FAIL (rc=%d)\n" "$rc"
exit "$rc"
