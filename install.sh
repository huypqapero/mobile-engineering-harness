#!/usr/bin/env bash
# Mobile Engineering Harness CLI
#
# Subcommands:
#   init      --project <path>              Scaffold .harness-overlay/ with schema template
#   install   --overlay <path>              Render templates + write manifest
#   update    --overlay <path>              Alias for install (idempotent re-render)
#   uninstall --overlay <path> [--purge]    Remove rendered files; --purge nukes entire overlay
#   help                                    Show this message
#
# Common flags (all subcommands):
#   --dry-run     Print actions without executing
#   --yes, -y     Skip confirmation prompts (for CI)
#
# Requires: bash 3.2+, python3 with PyYAML.
# macOS and Linux supported.

set -euo pipefail

readonly UPSTREAM_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly SCRIPT_NAME="$(basename "$0")"
readonly MANIFEST_VERSION=1

readonly C_GREEN='\033[0;32m'
readonly C_RED='\033[0;31m'
readonly C_YELLOW='\033[1;33m'
readonly C_BLUE='\033[0;34m'
readonly C_RESET='\033[0m'

DRY_RUN=0
SKIP_CONFIRM=0

log()      { printf "${C_BLUE}▶${C_RESET} %s\n" "$*"; }
success()  { printf "${C_GREEN}✓${C_RESET} %s\n" "$*"; }
warn()     { printf "${C_YELLOW}⚠${C_RESET} %s\n" "$*" >&2; }
err()      { printf "${C_RED}✗${C_RESET} %s\n" "$*" >&2; }
dry()      { printf "${C_YELLOW}[dry-run]${C_RESET} %s\n" "$*"; }

usage() {
  # Print leading comment block (lines 2..first blank), strip "# " prefix
  awk 'NR==1 { next } /^$/ { exit } { sub(/^# ?/, ""); print }' "$0"
  exit "${1:-0}"
}

confirm() {
  local prompt="$1"
  if [ "$SKIP_CONFIRM" -eq 1 ]; then
    return 0
  fi
  read -r -p "$prompt [y/N] " reply
  case "$reply" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

check_python() {
  local python_bin="${PYTHON_BIN:-python3}"
  if ! command -v "$python_bin" >/dev/null 2>&1; then
    err "python3 not found. Set PYTHON_BIN env var or install python3."
    exit 2
  fi
  if ! "$python_bin" -c "import yaml" >/dev/null 2>&1; then
    err "PyYAML missing. Install with: pip3 install pyyaml"
    exit 2
  fi
}

# -----------------------------------------------------------------------------
# Overlay vars resolution
# -----------------------------------------------------------------------------
read_overlay_vars() {
  local overlay_dir="$1"
  local overlay_yaml="$overlay_dir/overlay.yaml"
  if [ ! -f "$overlay_yaml" ]; then
    err "overlay.yaml not found at $overlay_yaml"
    err "Run: $SCRIPT_NAME init --project <path>"
    exit 1
  fi
  check_python
  local python_bin="${PYTHON_BIN:-python3}"

  "$python_bin" <<PYEOF
import yaml, sys
with open("$overlay_yaml") as f:
    d = yaml.safe_load(f) or {}

def g(path, default=""):
    cur = d
    for key in path.split("."):
        if cur is None or key not in cur:
            return default
        cur = cur[key]
    return cur if cur is not None else default

product_pkg = g("product.package", "com.example")
package_path = product_pkg.replace(".", "/")

targets = g("targets", ["android"])
targets_list = "[" + ", ".join(targets) + "]" if isinstance(targets, list) else "[android]"

mapping = {
    "PRODUCT_NAME": g("product.name", "YourProduct"),
    "PACKAGE_ROOT": product_pkg,
    "PACKAGE_ROOT_PATH": package_path,
    "APP_DISPLAY_NAME": g("product.app_display_name", g("product.name", "YourProduct")),
    "MODULE_APP": g("modules.app", "composeApp"),
    "MODULE_PRESENTER": g("modules.presenter", "presenter"),
    "MODULE_DOMAIN": g("modules.domain", "domain"),
    "MODULE_DATA": g("modules.data", "data"),
    "THEME_PREFIX": g("ui.theme_prefix", "App"),
    "THEME_CLASS": g("ui.theme_class", "AppTheme"),
    "UI_FRAMEWORK": g("stack.ui", "compose-multiplatform"),
    "MVI_BASE_CLASS": g("stack.mvi", "BaseViewModel"),
    "DI_FRAMEWORK": g("stack.di", "koin"),
    "NETWORK_FRAMEWORK": g("stack.network", "ktor"),
    "DATABASE_FRAMEWORK": g("stack.database", "sqldelight"),
    "IMAGE_FRAMEWORK": g("stack.image", "coil"),
    "SERIALIZATION_FRAMEWORK": g("stack.serialization", "kotlinx-serialization"),
    "FEATURES_ROOT": g("features_root", "feature"),
    "MIN_SDK": str(g("min_sdk", 24)),
    "IOS_MIN": g("ios_min", "15.0"),
    "KOTLIN_VERSION": g("kotlin_version", "2.x"),
    "COMPOSE_VERSION": g("compose_version", "1.8+"),
    "TARGETS_LIST": targets_list,
    "PROFILE": g("profile", "app"),
    "HARNESS_VERSION": g("harness_version", ">=0.1.0"),
}

platform_sdks = g("platform_sdks", [])
if isinstance(platform_sdks, list) and platform_sdks:
    mapping["PLATFORM_SDK_PREFIXES_KT"] = ", ".join(f'"{sdk}"' for sdk in platform_sdks)
else:
    mapping["PLATFORM_SDK_PREFIXES_KT"] = '"androidx.", "platform."'

forbidden = g("forbidden_imports_in_domain", ["android.", "androidx.", "platform."])
if isinstance(forbidden, list):
    mapping["DOMAIN_FORBIDDEN_PREFIXES_KT"] = ", ".join(f'"{p}"' for p in forbidden)
else:
    mapping["DOMAIN_FORBIDDEN_PREFIXES_KT"] = '"android.", "androidx."'

for k, v in mapping.items():
    v_esc = str(v).replace("'", "'\\\\''")
    print(f"export {k}='{v_esc}'")
PYEOF
}

# -----------------------------------------------------------------------------
# Template rendering
# -----------------------------------------------------------------------------
render_file() {
  local in="$1" out="$2"
  if [ "$DRY_RUN" -eq 1 ]; then
    dry "render $in → $out"
    return 0
  fi
  mkdir -p "$(dirname "$out")"
  sed \
    -e "s|{{PRODUCT_NAME}}|$PRODUCT_NAME|g" \
    -e "s|{{APP_DISPLAY_NAME}}|$APP_DISPLAY_NAME|g" \
    -e "s|{{PACKAGE_ROOT}}|$PACKAGE_ROOT|g" \
    -e "s|{{PACKAGE_ROOT_PATH}}|$PACKAGE_ROOT_PATH|g" \
    -e "s|{{MODULE_APP}}|$MODULE_APP|g" \
    -e "s|{{MODULE_PRESENTER}}|$MODULE_PRESENTER|g" \
    -e "s|{{MODULE_DOMAIN}}|$MODULE_DOMAIN|g" \
    -e "s|{{MODULE_DATA}}|$MODULE_DATA|g" \
    -e "s|{{THEME_PREFIX}}|$THEME_PREFIX|g" \
    -e "s|{{THEME_CLASS}}|$THEME_CLASS|g" \
    -e "s|{{UI_FRAMEWORK}}|$UI_FRAMEWORK|g" \
    -e "s|{{MVI_BASE_CLASS}}|$MVI_BASE_CLASS|g" \
    -e "s|{{DI_FRAMEWORK}}|$DI_FRAMEWORK|g" \
    -e "s|{{NETWORK_FRAMEWORK}}|$NETWORK_FRAMEWORK|g" \
    -e "s|{{DATABASE_FRAMEWORK}}|$DATABASE_FRAMEWORK|g" \
    -e "s|{{IMAGE_FRAMEWORK}}|$IMAGE_FRAMEWORK|g" \
    -e "s|{{SERIALIZATION_FRAMEWORK}}|$SERIALIZATION_FRAMEWORK|g" \
    -e "s|{{FEATURES_ROOT}}|$FEATURES_ROOT|g" \
    -e "s|{{MIN_SDK}}|$MIN_SDK|g" \
    -e "s|{{IOS_MIN}}|$IOS_MIN|g" \
    -e "s|{{KOTLIN_VERSION}}|$KOTLIN_VERSION|g" \
    -e "s|{{COMPOSE_VERSION}}|$COMPOSE_VERSION|g" \
    -e "s|{{TARGETS_LIST}}|$TARGETS_LIST|g" \
    -e "s|{{PLATFORM_SDK_PREFIXES_KT}}|$PLATFORM_SDK_PREFIXES_KT|g" \
    -e "s|{{DOMAIN_FORBIDDEN_PREFIXES_KT}}|$DOMAIN_FORBIDDEN_PREFIXES_KT|g" \
    -e "s|{{PROFILE}}|$PROFILE|g" \
    -e "s|{{HARNESS_VERSION}}|$HARNESS_VERSION|g" \
    "$in" > "$out"
  success "rendered $out"
}

# -----------------------------------------------------------------------------
# Manifest
# -----------------------------------------------------------------------------
list_rendered_files() {
  cat <<EOF
verification/architecture-tests/ArchitectureRulesTest.kt
verification/scripts/verify.sh
harness.yaml
README.md
EOF
}

write_manifest() {
  local overlay_dir="$1"
  local manifest="$overlay_dir/.manifest.yaml"
  local upstream_commit="unknown"
  if [ -d "$UPSTREAM_DIR/.git" ]; then
    upstream_commit=$(git -C "$UPSTREAM_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")
  fi
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  if [ "$DRY_RUN" -eq 1 ]; then
    dry "write manifest $manifest"
    return 0
  fi

  {
    echo "manifest_version: $MANIFEST_VERSION"
    echo "installed_at: $now"
    echo "upstream:"
    echo "  path: $UPSTREAM_DIR"
    echo "  commit: $upstream_commit"
    echo "product:"
    echo "  name: $PRODUCT_NAME"
    echo "  package: $PACKAGE_ROOT"
    echo "rendered:"
    list_rendered_files | sed 's/^/  - /'
  } > "$manifest"
  success "wrote $manifest"
}

read_manifest_rendered() {
  local overlay_dir="$1"
  local manifest="$overlay_dir/.manifest.yaml"
  if [ ! -f "$manifest" ]; then
    list_rendered_files
    return 0
  fi
  check_python
  local python_bin="${PYTHON_BIN:-python3}"
  "$python_bin" <<PYEOF
import yaml
with open("$manifest") as f:
    d = yaml.safe_load(f) or {}
for p in d.get("rendered", []):
    print(p)
PYEOF
}

# -----------------------------------------------------------------------------
# Overlay README
# -----------------------------------------------------------------------------
write_overlay_readme() {
  local overlay_dir="$1"
  local out="$overlay_dir/README.md"
  if [ "$DRY_RUN" -eq 1 ]; then
    dry "write overlay README $out"
    return 0
  fi
  cat > "$out" <<EOF
# $PRODUCT_NAME — Harness Overlay

Overlay cho **$PRODUCT_NAME** consume upstream mobile-engineering-harness.

- **Upstream**: \`$UPSTREAM_DIR\` (via \`upstream\` symlink or submodule)
- **Package**: \`$PACKAGE_ROOT\`
- **Profile**: \`$PROFILE\`

## Agent resolution

1. Project \`CLAUDE.md\` (nếu có)
2. \`.harness-overlay/overlay.yaml\` — vars
3. \`.harness-overlay/upstream/AGENTS.md\` — generic entry
4. \`.harness-overlay/upstream/skills/<name>/SKILL.md\`
5. Overlay delta: \`.harness-overlay/constitution/\`, \`.harness-overlay/blueprints/\`

## Rendered files (managed by install.sh)

- \`verification/architecture-tests/ArchitectureRulesTest.kt\`
- \`verification/scripts/verify.sh\`
- \`harness.yaml\`
- \`README.md\` (this file)

Track trong \`.manifest.yaml\`.

## Commands

\`\`\`bash
# Update rendered files với latest upstream + overlay.yaml
$UPSTREAM_DIR/install.sh update --overlay $overlay_dir

# Remove rendered files (giữ overlay.yaml + user content)
$UPSTREAM_DIR/install.sh uninstall --overlay $overlay_dir

# Nuke toàn bộ overlay
$UPSTREAM_DIR/install.sh uninstall --overlay $overlay_dir --purge

# Verify quality gates
./verification/scripts/verify.sh
\`\`\`
EOF
  success "wrote $out"
}

# -----------------------------------------------------------------------------
# Subcommands
# -----------------------------------------------------------------------------
cmd_init() {
  local project_dir=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --project) project_dir="$2"; shift 2 ;;
      -h|--help) usage 0 ;;
      *) err "Unknown arg for init: $1"; usage 1 ;;
    esac
  done
  if [ -z "$project_dir" ]; then
    err "init requires --project <path>"
    exit 1
  fi
  if [ ! -d "$project_dir" ]; then
    err "project directory not found: $project_dir"
    exit 1
  fi

  local overlay_dir="$project_dir/.harness-overlay"
  log "Init overlay at $overlay_dir"

  if [ -f "$overlay_dir/overlay.yaml" ]; then
    warn "$overlay_dir/overlay.yaml already exists"
    if ! confirm "Overwrite existing overlay.yaml?"; then
      log "Aborted."
      exit 0
    fi
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    dry "mkdir -p $overlay_dir"
    dry "cp $UPSTREAM_DIR/overlay.schema.yaml → $overlay_dir/overlay.yaml"
    dry "ln -s $UPSTREAM_DIR → $overlay_dir/upstream"
  else
    mkdir -p "$overlay_dir"
    cp "$UPSTREAM_DIR/overlay.schema.yaml" "$overlay_dir/overlay.yaml"
    success "copied schema → $overlay_dir/overlay.yaml"

    if [ ! -L "$overlay_dir/upstream" ]; then
      ln -s "$UPSTREAM_DIR" "$overlay_dir/upstream"
      success "symlink $overlay_dir/upstream → $UPSTREAM_DIR"
    else
      log "symlink upstream already exists"
    fi
  fi

  echo ""
  log "Next steps:"
  echo "  1. Edit $overlay_dir/overlay.yaml — fill product vars"
  echo "  2. Run: $SCRIPT_NAME install --overlay $overlay_dir"
}

cmd_install() {
  local overlay_dir=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --overlay) overlay_dir="$2"; shift 2 ;;
      -h|--help) usage 0 ;;
      *) err "Unknown arg for install: $1"; usage 1 ;;
    esac
  done
  if [ -z "$overlay_dir" ]; then
    err "install requires --overlay <path>"
    exit 1
  fi
  if [ ! -d "$overlay_dir" ]; then
    err "overlay dir not found: $overlay_dir"
    exit 1
  fi

  log "Install into $overlay_dir"

  eval "$(read_overlay_vars "$overlay_dir")"

  echo "  Product:  $PRODUCT_NAME ($PACKAGE_ROOT)"
  echo "  Profile:  $PROFILE"
  echo "  Modules:  $MODULE_APP, $MODULE_PRESENTER, $MODULE_DOMAIN, $MODULE_DATA"
  echo ""

  render_file \
    "$UPSTREAM_DIR/verification/architecture-tests/TemplateArchitectureRulesTest.kt" \
    "$overlay_dir/verification/architecture-tests/ArchitectureRulesTest.kt"

  render_file \
    "$UPSTREAM_DIR/verification/scripts/verify.sh.template" \
    "$overlay_dir/verification/scripts/verify.sh"
  [ "$DRY_RUN" -eq 1 ] || chmod +x "$overlay_dir/verification/scripts/verify.sh"

  render_file \
    "$UPSTREAM_DIR/harness.yaml.template" \
    "$overlay_dir/harness.yaml"

  write_overlay_readme "$overlay_dir"
  write_manifest "$overlay_dir"

  echo ""
  success "Install complete."
  echo ""
  log "Next steps:"
  echo "  1. Review rendered files in $overlay_dir/"
  echo "  2. Copy ArchitectureRulesTest.kt to <module>/src/jvmTest/kotlin/$PACKAGE_ROOT_PATH/harness/"
  echo "  3. Add Konsist + Detekt deps to libs.versions.toml"
  echo "  4. Run $overlay_dir/verification/scripts/verify.sh"
}

cmd_update() {
  log "Update = idempotent install"
  cmd_install "$@"
}

cmd_uninstall() {
  local overlay_dir=""
  local purge=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --overlay) overlay_dir="$2"; shift 2 ;;
      --purge) purge=1; shift ;;
      -h|--help) usage 0 ;;
      *) err "Unknown arg for uninstall: $1"; usage 1 ;;
    esac
  done
  if [ -z "$overlay_dir" ]; then
    err "uninstall requires --overlay <path>"
    exit 1
  fi
  if [ ! -d "$overlay_dir" ]; then
    err "overlay dir not found: $overlay_dir"
    exit 1
  fi

  if [ "$purge" -eq 1 ]; then
    warn "PURGE will delete the ENTIRE overlay directory: $overlay_dir"
    warn "This includes overlay.yaml, user extensions, upstream symlink."
    if ! confirm "Really purge $overlay_dir ?"; then
      log "Aborted."
      exit 0
    fi
    if ! confirm "Last chance. Confirm purge?"; then
      log "Aborted."
      exit 0
    fi
    if [ "$DRY_RUN" -eq 1 ]; then
      dry "rm -rf $overlay_dir"
    else
      rm -rf "$overlay_dir"
      success "purged $overlay_dir"
    fi
    return 0
  fi

  log "Uninstall rendered files from $overlay_dir"
  log "Preserve: overlay.yaml, constitution/, blueprints/, upstream/ symlink"
  echo ""

  local files
  files=$(read_manifest_rendered "$overlay_dir")

  local count=0
  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    local abs="$overlay_dir/$rel"
    if [ -e "$abs" ]; then
      count=$((count + 1))
      if [ "$DRY_RUN" -eq 1 ]; then
        dry "rm $abs"
      else
        rm -f "$abs"
        success "removed $rel"
      fi
    else
      warn "missing (skip): $rel"
    fi
  done <<< "$files"

  if [ "$DRY_RUN" -eq 0 ]; then
    for dir in "verification/architecture-tests" "verification/scripts" "verification"; do
      local full="$overlay_dir/$dir"
      if [ -d "$full" ] && [ -z "$(ls -A "$full")" ]; then
        rmdir "$full" 2>/dev/null && success "removed empty dir $dir" || true
      fi
    done
  fi

  if [ -f "$overlay_dir/.manifest.yaml" ]; then
    if [ "$DRY_RUN" -eq 1 ]; then
      dry "rm $overlay_dir/.manifest.yaml"
    else
      rm -f "$overlay_dir/.manifest.yaml"
      success "removed .manifest.yaml"
    fi
  fi

  echo ""
  success "Uninstall complete. ${count} rendered file(s) removed."
  log "Konsist test copied into source (if any) must be removed manually."
}

cmd_help() { usage 0; }

# -----------------------------------------------------------------------------
# Dispatcher
# -----------------------------------------------------------------------------
if [ $# -lt 1 ]; then
  usage 1
fi

SUBCMD="$1"; shift

SUB_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    -y|--yes)  SKIP_CONFIRM=1; shift ;;
    *) SUB_ARGS+=("$1"); shift ;;
  esac
done

case "$SUBCMD" in
  init)      cmd_init      "${SUB_ARGS[@]:-}" ;;
  install)   cmd_install   "${SUB_ARGS[@]:-}" ;;
  update)    cmd_update    "${SUB_ARGS[@]:-}" ;;
  uninstall) cmd_uninstall "${SUB_ARGS[@]:-}" ;;
  help|-h|--help) cmd_help ;;
  *) err "Unknown subcommand: $SUBCMD"; usage 1 ;;
esac
