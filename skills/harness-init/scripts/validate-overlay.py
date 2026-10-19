#!/usr/bin/env python3
"""Validate .harness-overlay/overlay.yaml against overlay.schema.yaml.

Usage: validate-overlay.py <overlay_yaml> <schema_yaml>
Exit codes:
  0  valid
  1  schema error (missing required keys, enum mismatch, dependency violation)
  2  file/parse error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: ~/.claude/skills/.venv/bin/pip install pyyaml", file=sys.stderr)
    sys.exit(2)


REQUIRED_KEYS = {
    "harness_version": str,
    "product": dict,
    "modules": dict,
    "ui": dict,
    "stack": dict,
    "features_root": str,
    "targets": list,
}

REQUIRED_PRODUCT_KEYS = ["name", "package"]
REQUIRED_UI_KEYS = ["theme_prefix", "theme_class"]

ENUM_VALUES = {
    "stack.ui": {"compose-multiplatform", "compose-android", "xml-android"},
    "stack.di": {"koin", "hilt", "manual"},
    "stack.network": {"ktor", "ktorfit", "retrofit"},
    "stack.database": {"sqldelight", "room", "datastore", "none"},
    "stack.image": {"coil", "glide", "kamel", "none"},
    "stack.serialization": {"kotlinx-serialization", "moshi", "gson"},
}


def load_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def validate(overlay: dict) -> list[str]:
    errors: list[str] = []

    for key, expected_type in REQUIRED_KEYS.items():
        if key not in overlay:
            errors.append(f"missing required key: {key}")
            continue
        if not isinstance(overlay[key], expected_type):
            errors.append(f"{key} wrong type: expected {expected_type.__name__}")

    product = overlay.get("product") or {}
    for pk in REQUIRED_PRODUCT_KEYS:
        if not product.get(pk):
            errors.append(f"product.{pk} is empty or missing")

    ui = overlay.get("ui") or {}
    for uk in REQUIRED_UI_KEYS:
        if not ui.get(uk):
            errors.append(f"ui.{uk} is empty or missing")

    stack = overlay.get("stack") or {}
    for enum_key, allowed in ENUM_VALUES.items():
        section, field = enum_key.split(".", 1)
        value = (overlay.get(section) or {}).get(field)
        if value is None:
            errors.append(f"{enum_key} missing")
        elif value not in allowed:
            errors.append(f"{enum_key}={value!r} not in {sorted(allowed)}")

    targets = overlay.get("targets") or []
    ui_choice = stack.get("ui")
    if "ios" in targets and ui_choice == "xml-android":
        errors.append("targets contains 'ios' but stack.ui is xml-android (not multiplatform)")

    modules = overlay.get("modules") or {}
    for mk in ("app", "presenter", "domain", "data"):
        if not modules.get(mk):
            errors.append(f"modules.{mk} is empty")

    return errors


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2

    overlay_path = Path(sys.argv[1])
    schema_path = Path(sys.argv[2])

    for p in (overlay_path, schema_path):
        if not p.exists():
            print(f"ERROR: file not found: {p}", file=sys.stderr)
            return 2

    try:
        overlay = load_yaml(overlay_path)
    except yaml.YAMLError as exc:
        print(f"ERROR: parse failed: {exc}", file=sys.stderr)
        return 2

    errors = validate(overlay)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 1

    print(json.dumps({"valid": True, "errors": []}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
