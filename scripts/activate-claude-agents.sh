#!/usr/bin/env bash
# Symlink mobile-engineering-harness agents into target .claude/agents/
# so Claude Code can discover them via the Agent tool.
#
# Commands:
#   install    create symlinks (default)
#   uninstall  remove previously created symlinks
#   status     list which harness agents are currently active
#
# Flags:
#   --from <dir>     source agents dir (default: <repo>/agents)
#   --target <dir>   target dir      (default: ~/.claude/agents)
#   --prefix <str>   prepend to each agent name (default: empty)
#   --force          overwrite existing non-symlink entries at target
#   --dry-run        show actions without touching the filesystem

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SOURCE_DIR="$REPO_ROOT/agents"
TARGET_DIR="$HOME/.claude/agents"
PREFIX=""
FORCE=0
DRY_RUN=0
CMD="install"

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

log()  { printf '%s\n' "$*"; }
run()  { if [ "$DRY_RUN" = 1 ]; then log "DRY: $*"; else eval "$@"; fi; }

while [ $# -gt 0 ]; do
  case "$1" in
    install|uninstall|status) CMD="$1"; shift ;;
    --from)    SOURCE_DIR="$2"; shift 2 ;;
    --target)  TARGET_DIR="$2"; shift 2 ;;
    --prefix)  PREFIX="$2"; shift 2 ;;
    --force)   FORCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage 0 ;;
    *) log "Unknown arg: $1"; usage 1 ;;
  esac
done

[ -d "$SOURCE_DIR" ] || { log "ERROR: source not found: $SOURCE_DIR"; exit 1; }
mkdir -p "$TARGET_DIR"

mapfile -t AGENTS < <(find "$SOURCE_DIR" -mindepth 1 -maxdepth 1 -name "*.md" -print0 \
  | xargs -0 -n1 echo | sort)

if [ "${#AGENTS[@]}" -eq 0 ]; then
  log "No agent *.md found under $SOURCE_DIR"
  exit 1
fi

installed=0
skipped=0
removed=0

for src in "${AGENTS[@]}"; do
  name="$(basename "$src")"
  dest="$TARGET_DIR/${PREFIX}${name}"

  case "$CMD" in
    install)
      if [ -L "$dest" ]; then
        current="$(readlink "$dest")"
        if [ "$current" = "$src" ]; then
          log "ok    $dest  (already linked)"
          skipped=$((skipped+1))
          continue
        fi
        log "relink $dest  ->  $src (was: $current)"
        run "rm \"$dest\""
      elif [ -e "$dest" ]; then
        if [ "$FORCE" = 1 ]; then
          log "force  $dest  (replacing existing file)"
          run "rm -f \"$dest\""
        else
          log "SKIP  $dest exists and is not a symlink (use --force to replace)"
          skipped=$((skipped+1))
          continue
        fi
      fi
      run "ln -s \"$src\" \"$dest\""
      log "link   $dest  ->  $src"
      installed=$((installed+1))
      ;;

    uninstall)
      if [ -L "$dest" ]; then
        current="$(readlink "$dest")"
        case "$current" in
          "$SOURCE_DIR"/*)
            run "rm \"$dest\""
            log "unlink $dest"
            removed=$((removed+1))
            ;;
          *)
            log "SKIP  $dest links elsewhere ($current)"
            skipped=$((skipped+1))
            ;;
        esac
      else
        skipped=$((skipped+1))
      fi
      ;;

    status)
      if [ -L "$dest" ]; then
        current="$(readlink "$dest")"
        if [ "$current" = "$src" ]; then
          log "active   ${PREFIX}${name}"
        else
          log "diverged ${PREFIX}${name}  ->  $current"
        fi
      elif [ -e "$dest" ]; then
        log "shadowed ${PREFIX}${name}  (non-symlink at target)"
      else
        log "missing  ${PREFIX}${name}"
      fi
      ;;
  esac
done

echo
case "$CMD" in
  install)   log "Done. linked=$installed  skipped=$skipped  target=$TARGET_DIR" ;;
  uninstall) log "Done. removed=$removed  skipped=$skipped" ;;
  status)    log "Source: $SOURCE_DIR"; log "Target: $TARGET_DIR" ;;
esac

if [ "$CMD" = "install" ] && [ "$DRY_RUN" = 0 ] && [ "$installed" -gt 0 ]; then
  cat <<EOF

Next:
  1. Restart Claude Code (or /reload) để runtime scan lại $TARGET_DIR
  2. Thử spawn agent: /agent ${PREFIX}$(basename "${AGENTS[0]}" .md)
EOF
fi
