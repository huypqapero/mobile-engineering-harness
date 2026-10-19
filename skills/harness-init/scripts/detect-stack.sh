#!/usr/bin/env bash
# detect-stack.sh — auto-detect UI/DI/Network/Database stack from a consumer Android/KMP project.
# Usage: detect-stack.sh <project_root>
# Output: JSON object on stdout; non-zero exit on fatal error.

set -euo pipefail

PROJECT_ROOT="${1:-$PWD}"
[ -d "$PROJECT_ROOT" ] || { echo "ERROR: project_root not a directory: $PROJECT_ROOT" >&2; exit 1; }

VERSIONS_TOML="$PROJECT_ROOT/gradle/libs.versions.toml"
SETTINGS_GRADLE_KTS="$PROJECT_ROOT/settings.gradle.kts"
SETTINGS_GRADLE="$PROJECT_ROOT/settings.gradle"

grep_safe() {
  grep -q "$1" "$2" 2>/dev/null && return 0 || return 1
}

grep_any() {
  local pattern="$1"
  shift
  for f in "$@"; do
    [ -f "$f" ] && grep -q "$pattern" "$f" 2>/dev/null && return 0
  done
  return 1
}

# Collect candidate gradle files
GRADLE_FILES=()
[ -f "$VERSIONS_TOML" ] && GRADLE_FILES+=("$VERSIONS_TOML")
while IFS= read -r f; do
  GRADLE_FILES+=("$f")
done < <(find "$PROJECT_ROOT" -maxdepth 4 -name "build.gradle.kts" -o -name "build.gradle" 2>/dev/null | head -20)

# --- UI framework
UI_FRAMEWORK="compose-android"
if grep_any "org.jetbrains.compose" "${GRADLE_FILES[@]}" 2>/dev/null; then
  UI_FRAMEWORK="compose-multiplatform"
elif grep_any "androidx.compose" "${GRADLE_FILES[@]}" 2>/dev/null; then
  UI_FRAMEWORK="compose-android"
elif grep_any "com.android.application" "${GRADLE_FILES[@]}" 2>/dev/null; then
  UI_FRAMEWORK="xml-android"
fi

# --- DI framework
DI_FRAMEWORK="manual"
if grep_any "dagger.hilt" "${GRADLE_FILES[@]}" 2>/dev/null; then
  DI_FRAMEWORK="hilt"
elif grep_any "insert-koin" "${GRADLE_FILES[@]}" 2>/dev/null; then
  DI_FRAMEWORK="koin"
fi

# --- Network framework
NETWORK_FRAMEWORK="ktor"
if grep_any "ktorfit" "${GRADLE_FILES[@]}" 2>/dev/null; then
  NETWORK_FRAMEWORK="ktorfit"
elif grep_any "retrofit2" "${GRADLE_FILES[@]}" 2>/dev/null; then
  NETWORK_FRAMEWORK="retrofit"
elif grep_any "ktor-client" "${GRADLE_FILES[@]}" 2>/dev/null; then
  NETWORK_FRAMEWORK="ktor"
fi

# --- Database framework
DATABASE_FRAMEWORK="none"
if grep_any "sqldelight" "${GRADLE_FILES[@]}" 2>/dev/null; then
  DATABASE_FRAMEWORK="sqldelight"
elif grep_any "androidx.room" "${GRADLE_FILES[@]}" 2>/dev/null; then
  DATABASE_FRAMEWORK="room"
elif grep_any "androidx.datastore" "${GRADLE_FILES[@]}" 2>/dev/null; then
  DATABASE_FRAMEWORK="datastore"
fi

# --- Package root (namespace)
PACKAGE_ROOT=""
for f in "${GRADLE_FILES[@]}"; do
  pkg=$(grep -E 'namespace\s*=' "$f" 2>/dev/null | head -1 | sed -E 's/.*namespace\s*=\s*"([^"]+)".*/\1/')
  if [ -n "$pkg" ]; then
    PACKAGE_ROOT="$pkg"
    break
  fi
done
if [ -z "$PACKAGE_ROOT" ]; then
  manifest=$(find "$PROJECT_ROOT" -maxdepth 5 -name "AndroidManifest.xml" 2>/dev/null | head -1)
  if [ -n "$manifest" ]; then
    PACKAGE_ROOT=$(grep -oE 'package="[^"]+"' "$manifest" 2>/dev/null | head -1 | sed -E 's/package="([^"]+)"/\1/')
  fi
fi
[ -z "$PACKAGE_ROOT" ] && PACKAGE_ROOT="com.example.app"

# --- Modules
MODULES_JSON="[]"
settings_file=""
[ -f "$SETTINGS_GRADLE_KTS" ] && settings_file="$SETTINGS_GRADLE_KTS"
[ -z "$settings_file" ] && [ -f "$SETTINGS_GRADLE" ] && settings_file="$SETTINGS_GRADLE"
if [ -n "$settings_file" ]; then
  mods=$(grep -oE 'include\(\s*"[^"]+"' "$settings_file" 2>/dev/null | sed -E 's/include\(\s*"([^"]+)"/\1/' | sed 's|^:||' | tr '\n' ',' | sed 's/,$//')
  if [ -n "$mods" ]; then
    MODULES_JSON="[\"${mods//,/\",\"}\"]"
  fi
fi

# --- MVI base class default
MVI_BASE_CLASS="BaseViewModel"

# --- Emit JSON
cat << EOF
{
  "ui_framework": "$UI_FRAMEWORK",
  "di_framework": "$DI_FRAMEWORK",
  "network_framework": "$NETWORK_FRAMEWORK",
  "database_framework": "$DATABASE_FRAMEWORK",
  "mvi_base_class": "$MVI_BASE_CLASS",
  "package_root": "$PACKAGE_ROOT",
  "modules": $MODULES_JSON
}
EOF
