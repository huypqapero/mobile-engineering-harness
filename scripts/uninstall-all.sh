#!/usr/bin/env bash
# Uninstall harness consumer artifacts: project-local skills, agents, SessionStart hook.
# Optional: purge .harness-overlay/ (overlay.yaml + upstream symlink).
#
# Usage:
#   uninstall-all.sh [--target <project_root>] [--purge] [--dry-run]
#
# Flags:
#   --target <dir>   consumer project root (default: $PWD)
#   --purge          also remove .harness-overlay/ (overlay.yaml + upstream link)
#   --dry-run        show actions without touching the filesystem

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET_ROOT="$PWD"
PURGE=0
DRY_RUN=0

usage() {
  sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

log() { printf '%s\n' "$*"; }
run() { if [ "$DRY_RUN" = 1 ]; then log "DRY: $*"; else eval "$@"; fi; }

while [ $# -gt 0 ]; do
  case "$1" in
    --target)  TARGET_ROOT="$2"; shift 2 ;;
    --purge)   PURGE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage 0 ;;
    *) log "Unknown arg: $1"; usage 1 ;;
  esac
done

[ -d "$TARGET_ROOT" ] || { log "ERROR: target not a directory: $TARGET_ROOT"; exit 1; }

SKILLS_SCRIPT="$SCRIPT_DIR/activate-claude-skills.sh"
AGENTS_SCRIPT="$SCRIPT_DIR/activate-claude-agents.sh"
HOOK_SCRIPT="$SCRIPT_DIR/install-session-hook.sh"

dry_arg=""
[ "$DRY_RUN" = 1 ] && dry_arg="--dry-run"

cd "$TARGET_ROOT"

log "=== Uninstall skills (project-local) ==="
run "\"$SKILLS_SCRIPT\" uninstall --target .claude/skills $dry_arg"

echo
log "=== Uninstall agents (project-local) ==="
run "\"$AGENTS_SCRIPT\" uninstall --target .claude/agents $dry_arg"

echo
log "=== Uninstall SessionStart hook ==="
run "\"$HOOK_SCRIPT\" uninstall --target . $dry_arg"

if [ "$PURGE" = 1 ]; then
  echo
  log "=== Purge .harness-overlay/ ==="
  if [ -d .harness-overlay ]; then
    if [ -L .harness-overlay/upstream ]; then
      run "rm \".harness-overlay/upstream\""
      log "unlink .harness-overlay/upstream"
    fi
    run "rm -rf \".harness-overlay\""
    log "removed .harness-overlay/"
  else
    log "SKIP: .harness-overlay/ not present"
  fi
fi

echo
log "Done. Restart Claude Code để runtime re-scan."
