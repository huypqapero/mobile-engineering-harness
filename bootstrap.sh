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
