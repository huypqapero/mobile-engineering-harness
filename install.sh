#!/usr/bin/env bash
# install.sh — render upstream harness templates into a product overlay.
# Usage:
#   ./install.sh --overlay /path/to/project/.harness-overlay
#
# Reads `.harness-overlay/overlay.yaml`, renders:
#   - verification/architecture-tests/ArchitectureRulesTest.kt
#   - verification/scripts/verify.sh
#   - harness.yaml
# into the overlay folder (not into upstream).
#
# Requires: bash, python3, yaml module (pyyaml).

set -euo pipefail

UPSTREAM_DIR="$(cd "$(dirname "$0")" && pwd)"
OVERLAY_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --overlay) OVERLAY_DIR="$2"; shift 2;;
    -h|--help)
      echo "Usage: $0 --overlay <path-to-overlay>"
      exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

if [[ -z "$OVERLAY_DIR" ]]; then
  echo "Error: --overlay <path> required"
  exit 1
fi

if [[ ! -f "$OVERLAY_DIR/overlay.yaml" ]]; then
  echo "Error: $OVERLAY_DIR/overlay.yaml not found."
  echo "Create it from $UPSTREAM_DIR/overlay.schema.yaml first."
  exit 1
fi

# -- Read overlay.yaml via python3 --
python_bin="${PYTHON_BIN:-python3}"
if ! command -v "$python_bin" >/dev/null 2>&1; then
  echo "Error: $python_bin not found. Set PYTHON_BIN env var."
  exit 1
fi

# Export vars from overlay.yaml as env vars for sed substitution
eval "$(
  "$python_bin" <<PYEOF
import yaml, sys
with open("$OVERLAY_DIR/overlay.yaml") as f:
    d = yaml.safe_load(f)

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
if isinstance(targets, list):
    targets_list = "[" + ", ".join(targets) + "]"
else:
    targets_list = "[android]"

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
}

platform_sdks = g("platform_sdks", [])
# For the Konsist test we need a Kotlin-syntax list of prefixes
if isinstance(platform_sdks, list) and platform_sdks:
    kt_list = ", ".join(f'"{sdk}"' for sdk in platform_sdks)
else:
    kt_list = '"androidx.", "platform."'
mapping["PLATFORM_SDK_PREFIXES_KT"] = kt_list

forbidden_imports = g("forbidden_imports_in_domain", ["android.", "androidx.", "platform."])
if isinstance(forbidden_imports, list):
    kt_list2 = ", ".join(f'"{p}"' for p in forbidden_imports)
else:
    kt_list2 = '"android.", "androidx."'
mapping["DOMAIN_FORBIDDEN_PREFIXES_KT"] = kt_list2

mapping["PROFILE"] = g("profile", "app")
mapping["HARNESS_VERSION"] = g("harness_version", ">=0.1.0")

for k, v in mapping.items():
    # Escape for shell
    v_esc = str(v).replace("'", "'\\''")
    print(f"export {k}='{v_esc}'")
PYEOF
)"

echo "═══════════════════════════════════════"
echo " Harness install"
echo "  Upstream: $UPSTREAM_DIR"
echo "  Overlay:  $OVERLAY_DIR"
echo "  Product:  $PRODUCT_NAME ($PACKAGE_ROOT)"
echo "═══════════════════════════════════════"

render_sed() {
  local in="$1" out="$2"
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
  echo "  ✓ rendered $out"
}

# 1. Konsist test
render_sed \
  "$UPSTREAM_DIR/verification/architecture-tests/TemplateArchitectureRulesTest.kt" \
  "$OVERLAY_DIR/verification/architecture-tests/ArchitectureRulesTest.kt"

# 2. verify.sh
render_sed \
  "$UPSTREAM_DIR/verification/scripts/verify.sh.template" \
  "$OVERLAY_DIR/verification/scripts/verify.sh"
chmod +x "$OVERLAY_DIR/verification/scripts/verify.sh"

# 3. harness.yaml
render_sed \
  "$UPSTREAM_DIR/harness.yaml.template" \
  "$OVERLAY_DIR/harness.yaml"

# 4. Overlay README index
cat > "$OVERLAY_DIR/README.md" <<EOF
# $PRODUCT_NAME — Harness Overlay

Overlay cho **$PRODUCT_NAME** consume upstream harness.

**Upstream**: \`$UPSTREAM_DIR\` (resolved qua \`upstream\` symlink hoặc submodule)
**Package**: \`$PACKAGE_ROOT\`
**Profile**: \`$PROFILE\`

## Agent resolution

1. Project \`CLAUDE.md\` (nếu có)
2. \`.harness-overlay/overlay.yaml\` — vars
3. \`.harness-overlay/upstream/AGENTS.md\` — generic entry
4. \`.harness-overlay/upstream/skills/<name>/SKILL.md\`
5. Overlay delta: \`.harness-overlay/constitution/\`, \`.harness-overlay/blueprints/\`

## Rendered files (do install.sh sinh ra)

- \`verification/architecture-tests/ArchitectureRulesTest.kt\`
- \`verification/scripts/verify.sh\`
- \`harness.yaml\`

## Rerun install

\`\`\`bash
$UPSTREAM_DIR/install.sh --overlay $OVERLAY_DIR
\`\`\`

## Verify

\`\`\`bash
./verification/scripts/verify.sh
\`\`\`
EOF
echo "  ✓ wrote $OVERLAY_DIR/README.md"

echo ""
echo "✅ Install complete."
echo "Next steps:"
echo "  1. Review rendered files in $OVERLAY_DIR/"
echo "  2. Copy ArchitectureRulesTest.kt to <module>/src/jvmTest/kotlin/$PACKAGE_ROOT_PATH/harness/"
echo "  3. Add Konsist + Detekt deps to libs.versions.toml"
echo "  4. Run $OVERLAY_DIR/verification/scripts/verify.sh"
