#!/usr/bin/env bash
# Stage 2 — Validate plan artifact against task-contract + expected structure.

set -euo pipefail

FIXTURE_DIR="$1"
RESULTS="$2"

PLAN_ACTUAL="$FIXTURE_DIR/actual/plan.yaml"
PLAN_STRUCTURE="$FIXTURE_DIR/expected/plan.structure.yaml"

echo "  - name: plan" >> "$RESULTS"

if [ ! -f "$PLAN_ACTUAL" ]; then
  echo "    status: skip" >> "$RESULTS"
  echo "    details: no actual plan.yaml (optional artifact)" >> "$RESULTS"
  printf "  stage-2 plan: SKIP\n"
  exit 0
fi

if [ ! -f "$PLAN_STRUCTURE" ]; then
  echo "    status: skip" >> "$RESULTS"
  echo "    details: no expected/plan.structure.yaml (fixture không require plan check)" >> "$RESULTS"
  printf "  stage-2 plan: SKIP (no expected structure)\n"
  exit 0
fi

verbose_flag=""
[ "${VERBOSE:-0}" -eq 1 ] && verbose_flag="--verbose"

output=$(python3 "$VALIDATORS/validate_plan.py" \
  --plan "$PLAN_ACTUAL" \
  --structure "$PLAN_STRUCTURE" \
  $verbose_flag 2>&1) && rc=0 || rc=$?

printf "%s\n" "$output" | sed 's/^/    /'

if [ "$rc" -eq 0 ]; then
  echo "    status: pass" >> "$RESULTS"
  echo "    exit_code: 0" >> "$RESULTS"
  echo "    details: plan structure matches expected" >> "$RESULTS"
  printf "  stage-2 plan: PASS\n"
  exit 0
fi

echo "    status: fail" >> "$RESULTS"
echo "    exit_code: $rc" >> "$RESULTS"
echo "    details: structural mismatch" >> "$RESULTS"
printf "  stage-2 plan: FAIL (rc=%d)\n" "$rc"
exit "$rc"
