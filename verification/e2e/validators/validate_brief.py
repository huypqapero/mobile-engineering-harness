#!/usr/bin/env python3
"""Validate brief package: JSON schema + semantic rules.

Usage:
  validate_brief.py --brief <path/to/brief.yaml> \
                    --schema <path/to/brief.schema.json> \
                    --semantics <path/to/brief.semantics.yaml>

Exit codes:
  0 — all pass
  1 — schema fail
  2 — semantic rule fail
  3 — file missing / parse error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


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


def load_json(path: Path) -> dict:
    try:
        with path.open() as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR missing schema: {path}", file=sys.stderr)
        sys.exit(3)


def validate_schema(brief: dict, schema: dict) -> list[str]:
    validator = Draft202012Validator(schema)
    errors = []
    for err in validator.iter_errors(brief):
        path = ".".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{path}: {err.message}")
    return errors


def apply_semantic_rules(brief: dict, rules: dict) -> list[tuple[str, str, str]]:
    """Returns list of (rule_name, expected, actual) for each failed rule."""
    failures = []

    reqs = brief.get("requirements", [])
    confirmed = [r for r in reqs if r.get("evidence_status") == "confirmed"]
    inferred = [r for r in reqs if r.get("evidence_status") == "inferred"]
    unresolved = [r for r in reqs if r.get("evidence_status") == "unresolved"]
    issues = brief.get("issues", [])
    blockers = [i for i in issues if i.get("severity") == "blocker" and i.get("status") == "open"]
    acs = brief.get("acceptance_criteria", [])
    screens = brief.get("screens", [])
    ambiguous = sum(len(s.get("components_ambiguous", [])) for s in screens)

    def check(name, expected, actual, ok):
        if not ok:
            failures.append((name, str(expected), str(actual)))

    if "min_confirmed_requirements" in rules:
        expected = rules["min_confirmed_requirements"]
        check("min_confirmed_requirements", f">= {expected}", len(confirmed), len(confirmed) >= expected)

    if "max_blocker_issues" in rules:
        expected = rules["max_blocker_issues"]
        check("max_blocker_issues", f"<= {expected}", len(blockers), len(blockers) <= expected)

    if "max_unresolved_requirements" in rules:
        expected = rules["max_unresolved_requirements"]
        check("max_unresolved_requirements", f"<= {expected}", len(unresolved), len(unresolved) <= expected)

    if "min_acceptance_criteria" in rules:
        expected = rules["min_acceptance_criteria"]
        check("min_acceptance_criteria", f">= {expected}", len(acs), len(acs) >= expected)

    if "required_requirement_types" in rules:
        expected = set(rules["required_requirement_types"])
        actual = {r.get("type") for r in reqs}
        missing = expected - actual
        check("required_requirement_types", list(expected), list(actual), not missing)

    if rules.get("all_ac_bind_confirmed") is True:
        confirmed_ids = {r["id"] for r in confirmed}
        for ac in acs:
            bound = set(ac.get("requirement_ids", []))
            if bound - confirmed_ids:
                failures.append(
                    (
                        "all_ac_bind_confirmed",
                        "AC bind confirmed REQ only",
                        f"{ac['id']} binds non-confirmed: {bound - confirmed_ids}",
                    )
                )
                break
        else:
            # All AC passed
            pass

    if rules.get("all_requirements_have_source") is True:
        for r in reqs:
            if r.get("evidence_status") in ("confirmed", "inferred"):
                if not r.get("source_references"):
                    failures.append(
                        (
                            "all_requirements_have_source",
                            "every confirmed/inferred has source_references",
                            f"{r['id']} missing source_references",
                        )
                    )
                    break

    if rules.get("components_ambiguous_resolved") is True:
        check(
            "components_ambiguous_resolved",
            "= 0 unresolved ambiguous",
            ambiguous,
            ambiguous == 0,
        )

    if "max_components_ambiguous" in rules:
        expected = rules["max_components_ambiguous"]
        check("max_components_ambiguous", f"<= {expected}", ambiguous, ambiguous <= expected)

    if rules.get("has_validation_pass") is True:
        validation = brief.get("validation", {})
        status = validation.get("status")
        check("has_validation_pass", "passed", status, status == "passed")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--semantics", required=True, type=Path)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    brief = load_yaml(args.brief)
    schema = load_json(args.schema)
    rules = load_yaml(args.semantics)

    schema_errors = validate_schema(brief, schema)
    semantic_failures = apply_semantic_rules(brief, rules)

    print(f"Brief: {args.brief}")
    print(f"Schema errors: {len(schema_errors)}")
    print(f"Semantic failures: {len(semantic_failures)}")

    if schema_errors:
        print("\n--- Schema errors ---")
        for err in schema_errors:
            print(f"  {err}")

    if semantic_failures:
        print("\n--- Semantic failures ---")
        for name, expected, actual in semantic_failures:
            print(f"  {name}: expected {expected}, actual {actual}")

    if args.verbose and not (schema_errors or semantic_failures):
        print("\nAll checks passed.")

    if schema_errors:
        return 1
    if semantic_failures:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
