#!/usr/bin/env python3
"""Compare actual brief/plan output với golden snapshot. Ignore noise (timestamps, checksums).

Usage:
  diff_golden.py --actual <path> --golden <path> [--ignore-fields a,b,c]

Exit codes:
  0 — no drift
  20 — drift detected (expected khi intentional harness change)
  3 — file missing
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# Default fields to ignore khi diff (noise fields không reliable để pin)
DEFAULT_IGNORE = {
    "generated_at",
    "fetched_at",
    "validated_at",
    "last_modified",
    "checksum",
    "origin_metadata.fetched_at",
    "origin_metadata.last_modified",
    "validation.validated_at",
    "validation.validated_by",
}


def load_yaml(path: Path) -> dict:
    try:
        with path.open() as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"ERROR missing file: {path}", file=sys.stderr)
        sys.exit(3)


def strip_ignored(obj, ignore: set[str], prefix: str = ""):
    """Recursively remove ignored field paths. Mutates object."""
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            full = f"{prefix}.{key}" if prefix else key
            if key in ignore or full in ignore:
                del obj[key]
            else:
                strip_ignored(obj[key], ignore, full)
    elif isinstance(obj, list):
        for item in obj:
            strip_ignored(item, ignore, prefix)


def diff_recursive(actual, golden, path: str = "") -> list[str]:
    """Return list of drift descriptions."""
    drifts = []

    if type(actual) is not type(golden):
        drifts.append(f"{path}: type mismatch (actual {type(actual).__name__} vs golden {type(golden).__name__})")
        return drifts

    if isinstance(actual, dict):
        for key in sorted(set(actual.keys()) | set(golden.keys())):
            sub_path = f"{path}.{key}" if path else key
            if key not in actual:
                drifts.append(f"{sub_path}: missing in actual (golden has: {golden[key]!r:.80s})")
            elif key not in golden:
                drifts.append(f"{sub_path}: new in actual (not in golden): {actual[key]!r:.80s}")
            else:
                drifts += diff_recursive(actual[key], golden[key], sub_path)
    elif isinstance(actual, list):
        if len(actual) != len(golden):
            drifts.append(f"{path}: length mismatch (actual {len(actual)} vs golden {len(golden)})")
        else:
            for i, (a, g) in enumerate(zip(actual, golden)):
                drifts += diff_recursive(a, g, f"{path}[{i}]")
    else:
        if actual != golden:
            drifts.append(f"{path}: actual={actual!r:.60s} golden={golden!r:.60s}")

    return drifts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actual", required=True, type=Path)
    parser.add_argument("--golden", required=True, type=Path)
    parser.add_argument("--ignore-fields", default="", help="comma-separated field paths to ignore")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    extra_ignore = {f.strip() for f in args.ignore_fields.split(",") if f.strip()}
    ignore = DEFAULT_IGNORE | extra_ignore

    actual = load_yaml(args.actual)
    golden = load_yaml(args.golden)

    strip_ignored(actual, ignore)
    strip_ignored(golden, ignore)

    drifts = diff_recursive(actual, golden)

    print(f"Actual: {args.actual}")
    print(f"Golden: {args.golden}")
    print(f"Ignored fields: {sorted(ignore)}")
    print(f"Drift count: {len(drifts)}")

    if drifts:
        print("\n--- Drift ---")
        for d in drifts:
            print(f"  {d}")
        return 20

    if args.verbose:
        print("No drift from golden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
