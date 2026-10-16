#!/usr/bin/env python3
"""Consolidate stage results into final e2e report markdown.

Usage:
  report_builder.py --fixture <name> \
                    --results <path/to/results.yaml> \
                    --output <path/to/report.md>

Results YAML format:
  fixture: book-detail
  harness_version: v0.14.1
  started_at: 2026-10-16T10:30:00+07:00
  duration_seconds: 12
  stages:
    - name: brief
      status: pass | fail | skip
      exit_code: 0
      details: "..."
    - name: plan
      status: skip
      ...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


TEMPLATE = """# E2E Report — {fixture}

Date: {started_at}
Harness version: {harness_version}
Duration: {duration_seconds}s

## Summary

Status: **{overall_status}**
Stages run: {stages_run} / {stages_total}
Golden drift: {drift_count}

## Stage breakdown

{stage_table}

{details_section}

## Open issues

{open_issues}
"""


def status_from_stages(stages: list[dict]) -> str:
    if any(s["status"] == "fail" for s in stages):
        return "FAIL"
    if all(s["status"] in ("pass", "skip") for s in stages):
        if any(s["status"] == "skip" for s in stages):
            return "PARTIAL"
        return "PASS"
    return "UNKNOWN"


def build_stage_table(stages: list[dict]) -> str:
    header = "| Stage | Status | Exit code | Notes |\n|---|---|---|---|"
    rows = []
    for s in stages:
        rows.append(
            f"| {s['name']} | {s['status'].upper()} | {s.get('exit_code', '-')} | {s.get('details', '')[:100]} |"
        )
    return "\n".join([header] + rows)


def build_details(stages: list[dict]) -> str:
    sections = []
    for s in stages:
        if s["status"] == "fail" and s.get("full_output"):
            sections.append(f"### Stage {s['name']} failure\n\n```\n{s['full_output']}\n```")
    if not sections:
        return "## Details\n\n(no failure details)"
    return "## Failure details\n\n" + "\n\n".join(sections)


def build_open_issues(stages: list[dict]) -> str:
    issues = []
    for s in stages:
        if s["status"] == "fail":
            issues.append(f"- {s['name']}: {s.get('details', 'see failure details above')}")
    return "\n".join(issues) if issues else "(none)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        with args.results.open() as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR missing results: {args.results}", file=sys.stderr)
        return 3

    stages = data.get("stages", [])
    overall = status_from_stages(stages)
    drift = sum(1 for s in stages if s.get("drift_count", 0) > 0)

    report = TEMPLATE.format(
        fixture=args.fixture,
        started_at=data.get("started_at", "unknown"),
        harness_version=data.get("harness_version", "unknown"),
        duration_seconds=data.get("duration_seconds", 0),
        overall_status=overall,
        stages_run=sum(1 for s in stages if s["status"] != "skip"),
        stages_total=len(stages),
        drift_count=drift,
        stage_table=build_stage_table(stages),
        details_section=build_details(stages),
        open_issues=build_open_issues(stages),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report)

    print(f"Report written: {args.output}")
    print(f"Overall: {overall}")

    if overall == "FAIL":
        return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())
