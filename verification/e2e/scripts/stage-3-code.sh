#!/usr/bin/env bash
# Stage 3 — Dry Konsist check: expected file list + forbidden/required patterns.
#
# Static check only — không spawn Gradle, không build. Verify code structure
# conformance với expected rules.

set -euo pipefail

FIXTURE_DIR="$1"
RESULTS="$2"

CODE_ROOT="$FIXTURE_DIR/actual/code"
EXPECTED="$FIXTURE_DIR/expected/code.konsist.expected.yaml"

echo "  - name: code" >> "$RESULTS"

if [ ! -d "$CODE_ROOT" ]; then
  echo "    status: skip" >> "$RESULTS"
  echo "    details: no actual/code/ directory (optional artifact)" >> "$RESULTS"
  printf "  stage-3 code: SKIP\n"
  exit 0
fi

if [ ! -f "$EXPECTED" ]; then
  echo "    status: skip" >> "$RESULTS"
  echo "    details: no expected/code.konsist.expected.yaml" >> "$RESULTS"
  printf "  stage-3 code: SKIP (no expected rules)\n"
  exit 0
fi

verbose_flag=""
[ "${VERBOSE:-0}" -eq 1 ] && verbose_flag="--verbose"

output=$(python3 "$VALIDATORS/validate_code_structure.py" \
  --code-root "$CODE_ROOT" \
  --expected "$EXPECTED" \
  $verbose_flag 2>&1) && rc=0 || rc=$?

printf "%s\n" "$output" | sed 's/^/    /'

if [ "$rc" -eq 0 ]; then
  echo "    status: pass" >> "$RESULTS"
  echo "    exit_code: 0" >> "$RESULTS"
  echo "    details: all expected files present, no violations" >> "$RESULTS"
  printf "  stage-3 code: PASS\n"
  exit 0
fi

echo "    status: fail" >> "$RESULTS"
echo "    exit_code: $rc" >> "$RESULTS"
echo "    details: code structure violations detected" >> "$RESULTS"
printf "  stage-3 code: FAIL (rc=%d)\n" "$rc"
exit "$rc"
