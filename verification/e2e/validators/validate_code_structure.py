#!/usr/bin/env python3
"""Dry Konsist check — compare expected file list + rule compliance với actual.

Chạy static (grep + file list), không spawn Gradle. Chỉ verify presence + convention,
không verify behavior.

Usage:
  validate_code_structure.py --code-root <path> \
                             --expected <path/to/code.konsist.expected.yaml>

Expected YAML format:
  expected_files:
    - domain/.../BookDetail.kt
    - presenter/.../BookDetailViewModel.kt
  forbidden_patterns:
    - path_glob: "domain/**/*.kt"
      regex: "import android\\."
      message: "domain module không import Android"
  required_patterns:
    - path: presenter/.../BookDetailViewModel.kt
      regex: "class BookDetailViewModel.*: BaseViewModel"
      message: "ViewModel extends BaseViewModel"
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    try:
        with path.open() as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR missing file: {path}", file=sys.stderr)
        sys.exit(3)


def check_expected_files(code_root: Path, expected: list[str]) -> list[str]:
    missing = []
    for rel in expected:
        if not (code_root / rel).exists():
            missing.append(rel)
    return [f"missing file: {m}" for m in missing]


def check_forbidden_patterns(code_root: Path, patterns: list[dict]) -> list[str]:
    errors = []
    for rule in patterns:
        path_glob = rule.get("path_glob", "**/*")
        regex = re.compile(rule["regex"])
        message = rule.get("message", "forbidden pattern")

        for path in code_root.glob(path_glob):
            if not path.is_file():
                continue
            try:
                content = path.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(content.splitlines(), 1):
                if regex.search(line):
                    errors.append(f"{path.relative_to(code_root)}:{i} violates [{message}]: {line.strip()[:80]}")
    return errors


def check_required_patterns(code_root: Path, patterns: list[dict]) -> list[str]:
    errors = []
    for rule in patterns:
        rel = rule["path"]
        regex = re.compile(rule["regex"])
        message = rule.get("message", "required pattern missing")

        file_path = code_root / rel
        if not file_path.exists():
            errors.append(f"required-pattern target missing: {rel}")
            continue

        content = file_path.read_text()
        if not regex.search(content):
            errors.append(f"{rel} missing [{message}]")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", required=True, type=Path)
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not args.code_root.exists():
        print(f"SKIP code-root not found: {args.code_root}")
        return 0

    expected = load_yaml(args.expected)

    all_errors = []
    all_errors += check_expected_files(args.code_root, expected.get("expected_files", []))
    all_errors += check_forbidden_patterns(args.code_root, expected.get("forbidden_patterns", []))
    all_errors += check_required_patterns(args.code_root, expected.get("required_patterns", []))

    print(f"Code root: {args.code_root}")
    print(f"Violations: {len(all_errors)}")

    if all_errors:
        print("\n--- Violations ---")
        for e in all_errors:
            print(f"  {e}")
        return 3

    if args.verbose:
        print("Code structure matches expected.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
