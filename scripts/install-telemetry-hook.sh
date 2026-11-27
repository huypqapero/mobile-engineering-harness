#!/usr/bin/env bash
# Install the skill-telemetry hooks into the user-level Claude Code settings
# (~/.claude/settings.json), so skill usage is recorded in every repo.
# Events go to ${MEH_TELEMETRY_DIR:-~/.meh-telemetry}; prompts are kept in full,
# credential-looking strings are masked. See docs/skill-telemetry.md.
#
# Usage:
#   install-telemetry-hook.sh install   [--settings <path>] [--dry-run]
#   install-telemetry-hook.sh uninstall [--settings <path>]
#   install-telemetry-hook.sh status    [--settings <path>]
#
# install is idempotent across harness copies: an existing telemetry hook whose
# script still exists is kept; one pointing at a missing script is repointed here.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TELEMETRY="$SCRIPT_DIR/skill-telemetry/telemetry.py"

SETTINGS="$HOME/.claude/settings.json"
EXTRA=()
CMD="install"

usage() {
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [ $# -gt 0 ]; do
  case "$1" in
    install|uninstall|status) CMD="$1"; shift ;;
    --settings) SETTINGS="$2"; shift 2 ;;
    --dry-run)  EXTRA+=(--dry-run); shift ;;
    -h|--help)  usage 0 ;;
    *) printf 'Unknown arg: %s\n' "$1"; usage 1 ;;
  esac
done

[ -f "$TELEMETRY" ] || { echo "ERROR: missing $TELEMETRY"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }

python3 "$SCRIPT_DIR/lib/settings_hooks.py" "$CMD" --settings "$SETTINGS" \
  --script "$TELEMETRY" --run python3 --args hook \
  --event UserPromptSubmit --event PreToolUse:Skill --event SessionStart \
  ${EXTRA[@]+"${EXTRA[@]}"}
