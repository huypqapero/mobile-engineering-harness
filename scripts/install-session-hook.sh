#!/usr/bin/env bash
# Install the SessionStart hook into consumer project's .claude/settings.json.
# The hook invokes `scripts/check-overlay.sh` (symlinked into .claude/hooks/) to
# remind the agent to trigger harness-init when overlay is missing.
#
# Usage:
#   install-session-hook.sh install [--target <project_root>] [--dry-run]
#   install-session-hook.sh uninstall [--target <project_root>]
#   install-session-hook.sh status [--target <project_root>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET_ROOT="$PWD"
DRY_RUN=0
CMD="install"

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

log() { printf '%s\n' "$*"; }
run() { if [ "$DRY_RUN" = 1 ]; then log "DRY: $*"; else eval "$@"; fi; }

while [ $# -gt 0 ]; do
  case "$1" in
    install|uninstall|status) CMD="$1"; shift ;;
    --target)  TARGET_ROOT="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage 0 ;;
    *) log "Unknown arg: $1"; usage 1 ;;
  esac
done

HOOK_SRC="$REPO_ROOT/scripts/check-overlay.sh"
[ -x "$HOOK_SRC" ] || { log "ERROR: hook script not executable: $HOOK_SRC"; exit 1; }

CLAUDE_DIR="$TARGET_ROOT/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"
HOOK_DEST="$HOOKS_DIR/check-overlay.sh"
SETTINGS="$CLAUDE_DIR/settings.json"

PY="${CLAUDE_PY:-$HOME/.claude/skills/.venv/bin/python3}"
command -v "$PY" >/dev/null 2>&1 || PY="python3"

patch_settings() {
  local action="$1"
  "$PY" - "$SETTINGS" "$HOOK_DEST" "$action" <<'PYEOF'
import json
import os
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
hook_path = sys.argv[2]
action = sys.argv[3]

settings = {}
if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text() or "{}")
    except json.JSONDecodeError:
        print(f"ERROR: cannot parse {settings_path}", file=sys.stderr)
        sys.exit(2)

hooks = settings.setdefault("hooks", {})
session_start = hooks.setdefault("SessionStart", [])

entry = {
    "matcher": "",
    "hooks": [
        {"type": "command", "command": hook_path}
    ],
}

def already_present():
    for existing in session_start:
        for h in existing.get("hooks", []):
            if h.get("command") == hook_path:
                return True
    return False

if action == "install":
    if already_present():
        print("already-present")
    else:
        session_start.append(entry)
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        print("installed")
elif action == "uninstall":
    changed = False
    for existing in list(session_start):
        existing_hooks = existing.get("hooks", [])
        kept = [h for h in existing_hooks if h.get("command") != hook_path]
        if len(kept) != len(existing_hooks):
            changed = True
            if kept:
                existing["hooks"] = kept
            else:
                session_start.remove(existing)
    if not session_start:
        hooks.pop("SessionStart", None)
    if not hooks:
        settings.pop("hooks", None)
    if changed:
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        print("uninstalled")
    else:
        print("not-present")
elif action == "status":
    print("present" if already_present() else "absent")
else:
    print(f"ERROR: unknown action {action}", file=sys.stderr)
    sys.exit(2)
PYEOF
}

case "$CMD" in
  install)
    run "mkdir -p \"$HOOKS_DIR\""
    if [ -L "$HOOK_DEST" ]; then
      current=$(readlink "$HOOK_DEST")
      if [ "$current" != "$HOOK_SRC" ]; then
        log "relink $HOOK_DEST -> $HOOK_SRC (was: $current)"
        run "rm \"$HOOK_DEST\""
        run "ln -s \"$HOOK_SRC\" \"$HOOK_DEST\""
      else
        log "ok    $HOOK_DEST (already linked)"
      fi
    elif [ -e "$HOOK_DEST" ]; then
      log "ERROR: $HOOK_DEST exists as non-symlink; refuse to overwrite"
      exit 1
    else
      run "ln -s \"$HOOK_SRC\" \"$HOOK_DEST\""
      log "link   $HOOK_DEST -> $HOOK_SRC"
    fi
    if [ "$DRY_RUN" = 1 ]; then
      log "DRY: patch_settings install"
    else
      result=$(patch_settings install)
      log "settings: $result"
    fi
    log "Done. SessionStart hook ready at $SETTINGS"
    ;;

  uninstall)
    if [ -L "$HOOK_DEST" ]; then
      run "rm \"$HOOK_DEST\""
      log "unlink $HOOK_DEST"
    fi
    if [ -f "$SETTINGS" ]; then
      result=$(patch_settings uninstall 2>/dev/null || echo "settings-missing")
      log "settings: $result"
    fi
    ;;

  status)
    if [ -L "$HOOK_DEST" ] || [ -f "$HOOK_DEST" ]; then
      log "hook file: present at $HOOK_DEST"
    else
      log "hook file: missing"
    fi
    if [ -f "$SETTINGS" ]; then
      result=$(patch_settings status 2>/dev/null || echo "unreadable")
      log "settings: $result"
    else
      log "settings: no $SETTINGS"
    fi
    ;;
esac
