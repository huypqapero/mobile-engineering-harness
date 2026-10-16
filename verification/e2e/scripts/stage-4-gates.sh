#!/usr/bin/env bash
# Stage 4 — Cross-reference gates: file existence, link resolution.
#
# Áp dụng cho mọi fixture, không require specific artifact.

set -uo pipefail  # no -e: để tiếp tục qua các gate dù individual check fail

FIXTURE_DIR="$1"
RESULTS="$2"

BRIEF="$FIXTURE_DIR/actual/brief.yaml"
errors=0
error_lines=()

check() {
  local desc="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    [ "${VERBOSE:-0}" -eq 1 ] && printf "    ✓ %s\n" "$desc"
  else
    printf "    ✗ %s\n" "$desc"
    error_lines+=("$desc")
    errors=$((errors + 1))
  fi
}

# Gate A — brief.yaml exists và readable
if [ -f "$BRIEF" ]; then
  check "brief.yaml readable" test -s "$BRIEF"

  # Gate B — assets referenced trong brief tồn tại
  asset_paths=$(python3 -c "
import yaml, sys
try:
    data = yaml.safe_load(open('$BRIEF'))
    sources = data.get('sources') or {}
    for cat in ('spec', 'design', 'api'):
        for s in sources.get(cat) or []:
            print(s.get('path', ''))
except Exception as e:
    print('ERROR:', e, file=sys.stderr)
    sys.exit(1)
" 2>/dev/null) || asset_paths=""

  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    asset_path="$FIXTURE_DIR/actual/$rel"
    check "asset exists: $rel" test -f "$asset_path"
  done <<< "$asset_paths"

  # Gate C — issues[].affected_requirements đều resolve về requirements[].id
  orphan_output=$(python3 -c "
import yaml
data = yaml.safe_load(open('$BRIEF'))
req_ids = {r['id'] for r in data.get('requirements') or []}
orphan = []
for issue in data.get('issues') or []:
    for ref in issue.get('affected_requirements') or []:
        if ref not in req_ids:
            orphan.append((issue.get('id'), ref))
if orphan:
    for i, r in orphan:
        print(f'{i} references missing requirement: {r}')
    exit(1)
" 2>&1)
  cross_rc=$?

  if [ "$cross_rc" -eq 0 ]; then
    check "issue.affected_requirements resolve" true
  else
    printf "%s\n" "$orphan_output" | sed 's/^/    ✗ /'
    error_lines+=("issue.affected_requirements orphan")
    errors=$((errors + 1))
  fi
else
  check "brief.yaml exists" test -f "$BRIEF"
fi

# Luôn write YAML block ở cuối
{
  echo "  - name: gates"
  if [ "$errors" -eq 0 ]; then
    echo "    status: pass"
    echo "    exit_code: 0"
    echo "    details: all cross-reference gates pass"
  else
    echo "    status: fail"
    echo "    exit_code: 4"
    echo "    details: \"$errors gate(s) failed: ${error_lines[*]}\""
  fi
} >> "$RESULTS"

if [ "$errors" -eq 0 ]; then
  printf "  stage-4 gates: PASS\n"
  exit 0
fi

printf "  stage-4 gates: FAIL (%d errors)\n" "$errors"
exit 4
