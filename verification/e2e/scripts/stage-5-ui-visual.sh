#!/usr/bin/env bash
# Stage 5 — Visual UI compare: Figma reference vs app screenshot per node.
#
# Áp dụng khi fixture có expected/ui/figma/ + actual/ui/screenshots/ + visual.rules.yaml.

set -uo pipefail

FIXTURE_DIR="$1"
RESULTS="$2"

RULES="$FIXTURE_DIR/expected/ui/visual.rules.yaml"
SCREENSHOTS_DIR="$FIXTURE_DIR/actual/ui/screenshots"
OUTPUT="$FIXTURE_DIR/actual/ui/visual-compare-results.yaml"

echo "  - name: ui-visual" >> "$RESULTS"

if [ ! -f "$RULES" ]; then
  echo "    status: skip" >> "$RESULTS"
  echo "    details: no expected/ui/visual.rules.yaml (fixture không require visual compare)" >> "$RESULTS"
  printf "  stage-5 ui-visual: SKIP (no rules)\n"
  exit 0
fi

if [ ! -d "$SCREENSHOTS_DIR" ]; then
  echo "    status: skip" >> "$RESULTS"
  echo "    details: no actual/ui/screenshots/ (run agent to capture first)" >> "$RESULTS"
  printf "  stage-5 ui-visual: SKIP (no screenshots)\n"
  exit 0
fi

if ! python3 -c "import PIL, imagehash" >/dev/null 2>&1; then
  echo "    status: skip" >> "$RESULTS"
  echo "    details: Pillow + imagehash missing (pip3 install Pillow imagehash)" >> "$RESULTS"
  printf "  stage-5 ui-visual: SKIP (deps missing)\n"
  exit 0
fi

verbose_flag=""
[ "${VERBOSE:-0}" -eq 1 ] && verbose_flag="--verbose"

output=$(python3 "$VALIDATORS/validate_ui_visual.py" \
  --fixture "$FIXTURE_DIR" \
  --rules "$RULES" \
  --output "$OUTPUT" \
  $verbose_flag 2>&1)
rc=$?

printf "%s\n" "$output" | sed 's/^/    /'

if [ "$rc" -eq 0 ]; then
  echo "    status: pass" >> "$RESULTS"
  echo "    exit_code: 0" >> "$RESULTS"
  echo "    details: visual compare passed (all nodes within threshold)" >> "$RESULTS"
  echo "    results_file: actual/ui/visual-compare-results.yaml" >> "$RESULTS"
  printf "  stage-5 ui-visual: PASS\n"
  exit 0
fi

if [ "$rc" -eq 25 ]; then
  echo "    status: fail" >> "$RESULTS"
  echo "    exit_code: 25" >> "$RESULTS"
  echo "    details: visual drift detected (exceed threshold on ≥1 node)" >> "$RESULTS"
  echo "    results_file: actual/ui/visual-compare-results.yaml" >> "$RESULTS"
  printf "  stage-5 ui-visual: FAIL (drift)\n"
  exit 5
fi

echo "    status: fail" >> "$RESULTS"
echo "    exit_code: $rc" >> "$RESULTS"
echo "    details: validator error (rc=$rc)" >> "$RESULTS"
printf "  stage-5 ui-visual: FAIL (rc=%d)\n" "$rc"
exit "$rc"
