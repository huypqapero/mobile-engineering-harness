#!/usr/bin/env python3
"""Validate plan artifact against task-contract schema + expected structure.

Usage:
  validate_plan.py --plan <path/to/plan.yaml> \
                   --structure <path/to/plan.structure.yaml>

Exit codes:
  0 — pass
  2 — structural mismatch
  3 — file missing / parse error
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REQUIRED_FIELDS = ["id", "type", "goal", "acceptance_criteria"]
VALID_TYPES = {"feature", "bugfix", "refactor", "release", "spike"}


def load_yaml(path: Path) -> dict:
    try:
        with path.open() as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR missing file: {path}", file=sys.stderr)
        sys.exit(3)
    except yaml.YAMLError as exc:
        print(f"ERROR yaml parse {path}: {exc}", file=sys.stderr)
        sys.exit(3)


def validate_plan(plan: dict, expected: dict) -> list[str]:
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in plan:
            errors.append(f"missing required field: {field}")

    if plan.get("type") not in VALID_TYPES:
        errors.append(f"invalid type: {plan.get('type')} (expected one of {VALID_TYPES})")

    if "expected_files" in expected:
        actual_files = set(plan.get("files", []) or [])
        expected_files = set(expected["expected_files"])
        missing = expected_files - actual_files
        if missing:
            errors.append(f"expected files missing: {sorted(missing)}")

    if "min_acceptance_criteria" in expected:
        acs = plan.get("acceptance_criteria", [])
        if len(acs) < expected["min_acceptance_criteria"]:
            errors.append(
                f"too few AC: {len(acs)} < {expected['min_acceptance_criteria']}"
            )

    if "required_scope_modules" in expected:
        expected_mods = set(expected["required_scope_modules"])
        actual_mods = set((plan.get("scope") or {}).get("modules") or [])
        missing = expected_mods - actual_mods
        if missing:
            errors.append(f"missing scope modules: {sorted(missing)}")

    if "brief_id_required" in expected and expected["brief_id_required"]:
        if not plan.get("brief_id"):
            errors.append("plan missing brief_id (traceability to Feature Brief)")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--structure", required=True, type=Path)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    plan = load_yaml(args.plan)
    expected = load_yaml(args.structure)

    errors = validate_plan(plan, expected)

    print(f"Plan: {args.plan}")
    print(f"Structural errors: {len(errors)}")

    if errors:
        print("\n--- Errors ---")
        for e in errors:
            print(f"  {e}")
        return 2

    if args.verbose:
        print("Plan validates against expected structure.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
