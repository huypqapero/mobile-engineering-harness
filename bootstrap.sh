#!/usr/bin/env bash
# bootstrap.sh — one-liner installer for Mobile Engineering Harness.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/huypqapero/mobile-engineering-harness/main/bootstrap.sh | bash
#
# Or install + run a subcommand in one call:
#   curl -fsSL .../bootstrap.sh | bash -s init --project .
#
# Env vars (optional):
#   MEH_INSTALL_DIR   Target dir (default: $HOME/.mobile-engineering-harness)
#   MEH_BIN_DIR       Target symlink dir (default: $HOME/.local/bin)
#   MEH_REF           Git ref to checkout (default: main)
#   MEH_TELEMETRY     Set to 0 to skip installing the skill-telemetry hook (default: install)
#   MEH_UPDATE_CHECK  Set to 0 to skip the daily "new harness version" notice (default: install)
#   MEH_AUTO_UPDATE   Set to 1 to let that daily check also `git pull --ff-only` on main

set -euo pipefail

readonly REPO_URL="https://github.com/huypqapero/mobile-engineering-harness.git"
readonly CLI_NAME="mehcli"
INSTALL_DIR="${MEH_INSTALL_DIR:-$HOME/.mobile-engineering-harness}"
BIN_DIR="${MEH_BIN_DIR:-$HOME/.local/bin}"
REF="${MEH_REF:-main}"

readonly C_GREEN='\033[0;32m'
readonly C_YELLOW='\033[1;33m'
readonly C_RED='\033[0;31m'
readonly C_BLUE='\033[0;34m'
readonly C_RESET='\033[0m'

log()     { printf "${C_BLUE}▶${C_RESET} %s\n" "$*"; }
success() { printf "${C_GREEN}✓${C_RESET} %s\n" "$*"; }
warn()    { printf "${C_YELLOW}⚠${C_RESET} %s\n" "$*" >&2; }
err()     { printf "${C_RED}✗${C_RESET} %s\n" "$*" >&2; }

# Prerequisites
for bin in git python3; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    err "$bin is required but not found."
    exit 2
  fi
done

if ! python3 -c "import yaml" >/dev/null 2>&1; then
  warn "Python PyYAML not installed. Install with: pip3 install pyyaml"
  warn "You can continue; mehcli will error on install/uninstall until PyYAML is available."
fi

if ! command -v graphify >/dev/null 2>&1; then
  warn "graphify not installed (optional code graph for scout/bug-fix). Install with: uv tool install graphifyy"
  warn "Without it, skills fall back to grep."
fi

# Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
  log "Updating existing install at $INSTALL_DIR"
  git -C "$INSTALL_DIR" fetch --tags --quiet
  git -C "$INSTALL_DIR" checkout --quiet "$REF"
  git -C "$INSTALL_DIR" pull --ff-only --quiet
  success "Updated to $(git -C "$INSTALL_DIR" describe --tags --always)"
else
  log "Cloning $REPO_URL → $INSTALL_DIR"
  git clone --quiet "$REPO_URL" "$INSTALL_DIR"
  git -C "$INSTALL_DIR" checkout --quiet "$REF"
  success "Cloned at $(git -C "$INSTALL_DIR" describe --tags --always)"
fi

chmod +x "$INSTALL_DIR/install.sh"

# Create bin dir + symlink
mkdir -p "$BIN_DIR"
ln -sf "$INSTALL_DIR/install.sh" "$BIN_DIR/$CLI_NAME"
success "Linked $BIN_DIR/$CLI_NAME → $INSTALL_DIR/install.sh"

# Skill telemetry: user-level Claude Code hook, one per machine (docs/skill-telemetry.md)
if [ "${MEH_TELEMETRY:-1}" = "0" ]; then
  warn "Skipped skill telemetry (MEH_TELEMETRY=0). Enable later: $CLI_NAME telemetry install"
elif "$INSTALL_DIR/scripts/install-telemetry-hook.sh" install >/dev/null; then
  python3 "$INSTALL_DIR/scripts/skill-telemetry/telemetry.py" backfill >/dev/null 2>&1 || true
  success "Skill telemetry hook installed in ~/.claude/settings.json"
  echo "   Records skill name + full prompt of each skill call (credentials masked) to ~/.meh-telemetry."
  echo "   Opt out: $CLI_NAME telemetry uninstall  ·  details: $INSTALL_DIR/docs/skill-telemetry.md"
else
  warn "Could not install skill telemetry hook. Retry: $CLI_NAME telemetry install"
fi

# Update notice: user-level SessionStart hook, checks upstream once a day in the background
if [ "${MEH_UPDATE_CHECK:-1}" = "0" ]; then
  warn "Skipped update notice (MEH_UPDATE_CHECK=0). Enable later: $CLI_NAME update-hook install"
elif "$INSTALL_DIR/scripts/install-update-hook.sh" install >/dev/null; then
  success "Update notice installed: new Claude Code sessions mention a newer harness (checked daily)"
  if [ "${MEH_AUTO_UPDATE:-0}" = "1" ]; then
    MEH_UPSTREAM_DIR="$INSTALL_DIR" "$INSTALL_DIR/scripts/update-check.sh" auto on >/dev/null
    success "Auto-update on: the daily check fast-forwards $INSTALL_DIR on main"
  else
    echo "   Auto-update is off. Turn on: $CLI_NAME auto-update on"
  fi
else
  warn "Could not install update notice. Retry: $CLI_NAME update-hook install"
fi

# PATH check
case ":$PATH:" in
  *":$BIN_DIR:"*)
    ;;
  *)
    echo ""
    warn "$BIN_DIR is NOT in your PATH."
    echo "   Add this to your shell rc (~/.zshrc, ~/.bashrc, ~/.profile):"
    echo ""
    echo "       export PATH=\"$BIN_DIR:\$PATH\""
    echo ""
    echo "   Then reload: source ~/.zshrc (or restart terminal)"
    ;;
esac

echo ""
success "Mobile Engineering Harness installed."
echo "   Try: $CLI_NAME help"
echo ""

# Run subcommand if any args were passed through bash -s
if [ "$#" -gt 0 ]; then
  log "Running: $CLI_NAME $*"
  exec "$BIN_DIR/$CLI_NAME" "$@"
fi
