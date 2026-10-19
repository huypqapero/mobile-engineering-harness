#!/usr/bin/env bash
# render-overlay.sh — build .harness-overlay/overlay.yaml from detect-stack.sh JSON + branding env.
# Usage:
#   render-overlay.sh <project_root> <stack_json_file> <output_yaml>
# Env (required):
#   PRODUCT_NAME, THEME_PREFIX, THEME_CLASS
# Env (optional):
#   APP_DISPLAY_NAME (default = PRODUCT_NAME)
#   TARGETS (default = "android ios"), IMAGE_LIB (default = coil)

set -euo pipefail

PROJECT_ROOT="${1:?project_root required}"
STACK_JSON="${2:?stack_json required}"
OUT="${3:?output_yaml required}"

: "${PRODUCT_NAME:?env PRODUCT_NAME required}"
: "${THEME_PREFIX:?env THEME_PREFIX required}"
: "${THEME_CLASS:?env THEME_CLASS required}"
APP_DISPLAY_NAME="${APP_DISPLAY_NAME:-$PRODUCT_NAME}"
TARGETS_RAW="${TARGETS:-android ios}"
IMAGE_LIB="${IMAGE_LIB:-coil}"

[ -f "$STACK_JSON" ] || { echo "ERROR: stack_json not found: $STACK_JSON" >&2; exit 1; }

PY="${CLAUDE_PY:-$HOME/.claude/skills/.venv/bin/python3}"
command -v "$PY" >/dev/null 2>&1 || PY="python3"

read_json_key() {
  "$PY" -c "import json,sys; print(json.load(open('$STACK_JSON')).get('$1',''))"
}

UI=$(read_json_key ui_framework)
DI=$(read_json_key di_framework)
NET=$(read_json_key network_framework)
DB=$(read_json_key database_framework)
MVI=$(read_json_key mvi_base_class)
PKG=$(read_json_key package_root)

APP_MODULE=$("$PY" -c "import json; mods=json.load(open('$STACK_JSON')).get('modules',[]); print(mods[0] if mods else 'composeApp')")

mkdir -p "$(dirname "$OUT")"
{
  echo "harness_version: \">=0.1.0\""
  echo ""
  echo "product:"
  echo "  name: $PRODUCT_NAME"
  echo "  package: $PKG"
  echo "  app_display_name: $APP_DISPLAY_NAME"
  echo ""
  echo "modules:"
  echo "  app: $APP_MODULE"
  echo "  presenter: presenter"
  echo "  domain: domain"
  echo "  data: data"
  echo ""
  echo "ui:"
  echo "  theme_prefix: $THEME_PREFIX"
  echo "  theme_class: $THEME_CLASS"
  echo ""
  echo "stack:"
  echo "  ui: $UI"
  echo "  mvi: $MVI"
  echo "  di: $DI"
  echo "  network: $NET"
  echo "  database: $DB"
  echo "  image: $IMAGE_LIB"
  echo "  serialization: kotlinx-serialization"
  echo ""
  echo "features_root: feature"
  echo ""
  echo "targets:"
  for t in $TARGETS_RAW; do
    echo "  - $t"
  done
} > "$OUT"

echo "WROTE: $OUT"
