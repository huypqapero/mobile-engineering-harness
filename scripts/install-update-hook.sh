#!/usr/bin/env bash
# Install the harness update notice as a user-level SessionStart hook
# (~/.claude/settings.json). Each new Claude Code session prints one line when a newer
# harness is known and refreshes the check in the background once a day.
# Automatic updating is a separate opt-in: `mehcli auto-update on`.
#
# Usage:
#   install-update-hook.sh install   [--settings <path>] [--dry-run]
#   install-update-hook.sh uninstall [--settings <path>]
#   install-update-hook.sh status    [--settings <path>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="$SCRIPT_DIR/update-check.sh"

SETTINGS="$HOME/.claude/settings.json"
EXTRA=()
CMD="install"

usage() {
  sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
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

[ -f "$CHECKER" ] || { echo "ERROR: missing $CHECKER"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }

python3 "$SCRIPT_DIR/lib/settings_hooks.py" "$CMD" --settings "$SETTINGS" \
  --script "$CHECKER" --run bash --args notify --event SessionStart \
  ${EXTRA[@]+"${EXTRA[@]}"}
