#!/usr/bin/env bash
# E2E runner — orchestrate 5 stages validate fixture through harness pipeline.
#
# Usage:
#   run-e2e.sh <fixture-name> [options]
#   run-e2e.sh --all
#
# Options:
#   --stages 1,2,4           Run specific stages only (comma-separated)
#   --update-golden          Regenerate golden snapshots from current output
#   --verbose                Print detailed validator output
#   --help                   Show usage
#
# Exit codes:
#   0  all pass
#   1  stage 1 brief fail
#   2  stage 2 plan fail
#   3  stage 3 code fail
#   4  stage 4 gates fail
#   5  stage 5 report fail
#   10 setup error
#   20 golden drift

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly E2E_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
readonly REPO_ROOT="$(cd "$E2E_ROOT/../.." && pwd)"
readonly FIXTURES_DIR="$E2E_ROOT/fixtures"
readonly REPORTS_DIR="$E2E_ROOT/reports"
readonly VALIDATORS="$E2E_ROOT/validators"
readonly SCHEMA="$REPO_ROOT/verification/brief-schema/brief.schema.json"

readonly C_GREEN='\033[0;32m'
readonly C_RED='\033[0;31m'
readonly C_YELLOW='\033[1;33m'
readonly C_BLUE='\033[0;34m'
readonly C_RESET='\033[0m'

FIXTURE=""
STAGES="1,2,3,4,5"
UPDATE_GOLDEN=0
VERBOSE=0
RUN_ALL=0

log()      { printf "${C_BLUE}▶${C_RESET} %s\n" "$*"; }
success()  { printf "${C_GREEN}✓${C_RESET} %s\n" "$*"; }
warn()     { printf "${C_YELLOW}⚠${C_RESET} %s\n" "$*" >&2; }
err()      { printf "${C_RED}✗${C_RESET} %s\n" "$*" >&2; }

usage() {
  awk 'NR==1 { next } /^$/ { exit } { sub(/^# ?/, ""); print }' "$0"
  exit "${1:-0}"
}

check_deps() {
  local python_bin="${PYTHON_BIN:-python3}"
  if ! command -v "$python_bin" >/dev/null 2>&1; then
    err "python3 not found"
    exit 10
  fi
  if ! "$python_bin" -c "import yaml, jsonschema" >/dev/null 2>&1; then
    err "deps missing. Install: pip3 install pyyaml jsonschema"
    exit 10
  fi
}

parse_args() {
  if [ $# -eq 0 ]; then
    usage 0
  fi

  while [ $# -gt 0 ]; do
    case "$1" in
      --all) RUN_ALL=1; shift ;;
      --stages) STAGES="$2"; shift 2 ;;
      --update-golden) UPDATE_GOLDEN=1; shift ;;
      --verbose) VERBOSE=1; shift ;;
      -h|--help) usage 0 ;;
      --*) err "unknown option: $1"; usage 1 ;;
      *) FIXTURE="$1"; shift ;;
    esac
  done

  if [ "$RUN_ALL" -eq 0 ] && [ -z "$FIXTURE" ]; then
    err "fixture name required (or use --all)"
    usage 1
  fi
}

stage_enabled() {
  local stage="$1"
  [[ ",$STAGES," == *",$stage,"* ]]
}

harness_version() {
  (cd "$REPO_ROOT" && git describe --tags --always 2>/dev/null || echo "unknown")
}

now_iso() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Returns 0 if file exists and non-empty, 1 otherwise.
has_artifact() {
  [ -s "$1" ]
}

run_fixture() {
  local fixture="$1"
  local fixture_dir="$FIXTURES_DIR/$fixture"
  local config="$fixture_dir/config.yaml"

  if [ ! -d "$fixture_dir" ]; then
    err "fixture not found: $fixture_dir"
    return 10
  fi
  if [ ! -f "$config" ]; then
    err "config missing: $config"
    return 10
  fi

  log "Running fixture: $fixture"
  log "Harness version: $(harness_version)"

  local started_at
  started_at=$(now_iso)
  local start_sec
  start_sec=$(date +%s)

  local results_tmp
  results_tmp=$(mktemp)
  echo "fixture: $fixture" > "$results_tmp"
  echo "harness_version: $(harness_version)" >> "$results_tmp"
  echo "started_at: $started_at" >> "$results_tmp"
  echo "stages:" >> "$results_tmp"

  local overall_rc=0

  # Stage 1 — Brief
  if stage_enabled 1; then
    "$SCRIPT_DIR/stage-1-brief.sh" "$fixture_dir" "$results_tmp" || overall_rc=$?
  else
    echo "  - name: brief" >> "$results_tmp"
    echo "    status: skip" >> "$results_tmp"
  fi

  # Stage 2 — Plan
  if stage_enabled 2; then
    "$SCRIPT_DIR/stage-2-plan.sh" "$fixture_dir" "$results_tmp" || { local rc=$?; [ "$overall_rc" -eq 0 ] && overall_rc=$rc; }
  else
    echo "  - name: plan" >> "$results_tmp"
    echo "    status: skip" >> "$results_tmp"
  fi

  # Stage 3 — Code
  if stage_enabled 3; then
    "$SCRIPT_DIR/stage-3-code.sh" "$fixture_dir" "$results_tmp" || { local rc=$?; [ "$overall_rc" -eq 0 ] && overall_rc=$rc; }
  else
    echo "  - name: code" >> "$results_tmp"
    echo "    status: skip" >> "$results_tmp"
  fi

  # Stage 4 — Gates
  if stage_enabled 4; then
    "$SCRIPT_DIR/stage-4-gates.sh" "$fixture_dir" "$results_tmp" || { local rc=$?; [ "$overall_rc" -eq 0 ] && overall_rc=$rc; }
  else
    echo "  - name: gates" >> "$results_tmp"
    echo "    status: skip" >> "$results_tmp"
  fi

  # Finalize results
  local end_sec
  end_sec=$(date +%s)
  local duration=$((end_sec - start_sec))
  echo "duration_seconds: $duration" >> "$results_tmp"

  # Stage 5 — Report
  if stage_enabled 5; then
    local report_file
    report_file="$REPORTS_DIR/e2e-$(date +%y%m%d-%H%M)-$fixture.md"
    python3 "$VALIDATORS/report_builder.py" \
      --fixture "$fixture" \
      --results "$results_tmp" \
      --output "$report_file" || { local rc=$?; [ "$overall_rc" -eq 0 ] && overall_rc=$rc; }
    log "Report: $report_file"
  fi

  rm -f "$results_tmp"

  if [ "$overall_rc" -eq 0 ]; then
    success "Fixture $fixture: PASS"
  else
    err "Fixture $fixture: FAIL (rc=$overall_rc)"
  fi

  return $overall_rc
}

run_all() {
  local overall=0
  for fixture_dir in "$FIXTURES_DIR"/*/; do
    [ -d "$fixture_dir" ] || continue
    local fixture
    fixture=$(basename "$fixture_dir")
    run_fixture "$fixture" || overall=$?
  done
  return $overall
}

export VERBOSE UPDATE_GOLDEN E2E_ROOT REPO_ROOT VALIDATORS SCHEMA

main() {
  check_deps
  parse_args "$@"
  mkdir -p "$REPORTS_DIR"

  if [ "$RUN_ALL" -eq 1 ]; then
    run_all
  else
    run_fixture "$FIXTURE"
  fi
}

main "$@"
