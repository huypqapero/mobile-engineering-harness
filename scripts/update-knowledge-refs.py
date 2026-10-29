#!/usr/bin/env python3
"""Batch replace knowledge/, constitution/, briefs/ path references in agent/skill/workflow files.

Replaces path pattern with inline KB locator so agent knows where to kb_search.

Before:
    - `knowledge/coding-sdk/sdk-mindset.md` — ADR SDK-001..006

After:
    - `knowledge/coding-sdk/sdk-mindset.md` [KB → team/arch-coding-sdk, kb_search "sdk mindset"] — ADR SDK-001..006

Usage:
    scripts/update-knowledge-refs.py --dry-run
    scripts/update-knowledge-refs.py          # apply
    scripts/update-knowledge-refs.py --filter agents/feature-store
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent

# Target files to update (exclude migrated sources)
TARGET_DIRS = ["agents", "skills", "workflows", "verification"]
TARGET_FILES = ["AGENTS.md", "CLAUDE.md", "README.md"]
EXCLUDE = {"knowledge", "constitution", "briefs", "plans", "node_modules", ".git", "dist"}

# Mirrors migrate script MAP (path → scope). Keep in sync.
PATH_TO_SCOPE: list[tuple[str, str]] = [
    (r"knowledge/coding-sdk/sdk-mindset", "team/arch-coding-sdk"),
    (r"knowledge/coding-sdk/", "team/arch-coding-sdk"),
    (r"knowledge/coding-feature-store/", "team/arch-coding-feature-store"),
    (r"knowledge/coding/compose/", "team/arch-coding-compose"),
    (r"knowledge/coding/coroutines/", "team/arch-coding-coroutines"),
    (r"knowledge/coding/mvi/", "team/arch-coding-mvi"),
    (r"knowledge/coding/clean-arch/", "team/arch-coding-clean-arch"),
    (r"knowledge/coding/patterns/", "team/arch-coding-patterns"),
    (r"knowledge/coding/data/", "team/arch-coding-data"),
    (r"knowledge/product/input-analysis/", "team/arch-product-input-analysis"),
    (r"knowledge/product/", "team/arch-product"),
    (r"knowledge/design/design-system/", "team/arch-design-system"),
    (r"knowledge/design/visual-compare/", "team/arch-design-compare"),
    (r"knowledge/design/", "team/arch-design"),
    (r"knowledge/pm/", "team/arch-pm"),
    (r"knowledge/testing/e2e-runtime/", "team/arch-testing-e2e-runtime"),
    (r"knowledge/testing/", "team/arch-testing"),
    (r"knowledge/meta/agent-orchestration/", "team/arch-meta-orchestration"),
    (r"knowledge/meta/harness-governance/", "team/arch-meta-governance"),
    (r"knowledge/meta/auto-fix/", "team/arch-meta-auto-fix"),
    (r"knowledge/meta/", "team/arch-meta"),
    (r"knowledge/cross-cutting/performance/", "team/arch-xcut-performance"),
    (r"knowledge/cross-cutting/security/", "team/arch-xcut-security"),
    (r"knowledge/cross-cutting/build-strategy/", "team/arch-xcut-build-strategy"),
    (r"knowledge/", "team/arch"),
    (r"constitution/", "team/arch-constitution"),
    (r"briefs/([^/]+)/", r"projects/\1"),
    (r"briefs/", "team/business-index"),
]

# Match: `path/to/file.md`, path/to/file.md (bare), or in markdown link syntax
# Capture full path for query hint derivation
PATH_PATTERN = re.compile(
    r"(?P<prefix>knowledge/|constitution/|briefs/)(?P<rest>[\w\-./]+?\.md)",
    re.MULTILINE,
)


def derive_scope(full_path: str) -> str:
    for pattern, scope in PATH_TO_SCOPE:
        m = re.match(pattern, full_path)
        if m:
            return m.expand(scope) if "\\" in scope else scope
    return "team/arch"


def derive_query(full_path: str) -> str:
    stem = Path(full_path).stem  # e.g. "sdk-mindset"
    # Also include parent dir hint
    parts = Path(full_path).parts
    # Take last 2-3 segments, excluding "knowledge" prefix
    hint_parts = [p for p in parts if p not in {"knowledge", "constitution", "briefs"}]
    hint_parts = [p.replace(".md", "").replace("-", " ") for p in hint_parts[-2:]]
    query = " ".join(hint_parts)
    return query.strip()


def is_already_marked(match_start: int, text: str) -> bool:
    # Avoid double-rewrite: check if "[KB →" appears within next 80 chars
    window = text[match_start : match_start + 300]
    return "[KB →" in window[:200]


def transform_file(path: Path, dry_run: bool) -> dict:
    text = path.read_text(encoding="utf-8")
    original = text
    replacements = 0

    def repl(m: re.Match) -> str:
        nonlocal replacements
        full = m.group(0)
        start = m.start()
        if is_already_marked(start, text):
            return full
        scope = derive_scope(full)
        query = derive_query(full)
        replacements += 1
        return f"{full} [KB → {scope}, kb_search \"{query}\"]"

    new_text = PATH_PATTERN.sub(repl, text)

    if replacements == 0:
        return {"path": str(path.relative_to(HARNESS)), "status": "no-match", "count": 0}

    if dry_run:
        return {"path": str(path.relative_to(HARNESS)), "status": "dry-run", "count": replacements}

    path.write_text(new_text, encoding="utf-8")
    return {"path": str(path.relative_to(HARNESS)), "status": "updated", "count": replacements}


def collect_files(filter_regex: str | None) -> list[Path]:
    files: set[Path] = set()
    for d in TARGET_DIRS:
        root = HARNESS / d
        if root.exists():
            files.update(root.rglob("*.md"))
    for f in TARGET_FILES:
        p = HARNESS / f
        if p.exists():
            files.add(p)
    out = sorted(files)
    if filter_regex:
        out = [p for p in out if re.search(filter_regex, str(p.relative_to(HARNESS)))]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--filter", help="regex to filter rel path")
    args = ap.parse_args()

    files = collect_files(args.filter)
    print(f"Scanning {len(files)} files", file=sys.stderr)

    totals = {"updated": 0, "dry-run": 0, "no-match": 0, "total-replacements": 0}
    for p in files:
        r = transform_file(p, dry_run=args.dry_run)
        totals[r["status"]] += 1
        totals["total-replacements"] += r["count"]
        if r["count"] > 0:
            tag = "[dry-run]" if args.dry_run else "[updated]"
            print(f"{tag} {r['path']}  ({r['count']} ref)", file=sys.stderr)

    print(f"\n=== Report ===\n  updated: {totals['updated']}\n  dry-run: {totals['dry-run']}\n  no-match: {totals['no-match']}\n  total replacements: {totals['total-replacements']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
