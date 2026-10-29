#!/usr/bin/env python3
"""Migrate harness knowledge/ + constitution/ + briefs/ to team-knowledge KB.

Uses team-kb push CLI (stdin JSON). Idempotent via capture_id = sha256(path)[:16].
Multi-tag strategy: 5-enum category + rich tags for free-text search.

Usage:
    scripts/migrate-knowledge-to-kb.py             # push all (idempotent)
    scripts/migrate-knowledge-to-kb.py --dry-run   # preview mapping only
    scripts/migrate-knowledge-to-kb.py --filter knowledge/coding-sdk  # subset
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent

CATEGORY_RUNBOOK = "runbook"
CATEGORY_DECISION = "decision"
CATEGORY_PATTERN = "pattern"
CATEGORY_PITFALL = "pitfall"
CATEGORY_LESSON = "lesson"

# Scope slug rule: wrapper enforces `team/<area>` or `projects/<project>`.
# → Flatten 2-tier arch/<domain>/<sub> into single slug `team/arch-<domain>-<sub>`.
# → Preserve hierarchy via tags for discovery.
#
# (regex, scope_template, category, extra_tags)
MAP: list[tuple[str, str, str, list[str]]] = [
    # knowledge/coding-sdk — SDK framework
    (r"knowledge/coding-sdk/sdk-mindset\.md",          "team/arch-coding-sdk", CATEGORY_DECISION, ["mindset", "adr", "framework", "sdk", "arch"]),
    (r"knowledge/coding-sdk/essentials\.md",           "team/arch-coding-sdk", CATEGORY_RUNBOOK,  ["rule", "checklist", "framework", "sdk", "arch"]),
    (r"knowledge/coding-sdk/pattern-catalog\.md",      "team/arch-coding-sdk", CATEGORY_PATTERN,  ["canonical", "framework", "sdk", "arch"]),
    (r"knowledge/coding-sdk/brainstorm-process\.md",   "team/arch-coding-sdk", CATEGORY_RUNBOOK,  ["process", "phase-0", "framework", "sdk", "arch"]),
    (r"knowledge/coding-sdk/testing-kit-rules\.md",    "team/arch-coding-sdk", CATEGORY_RUNBOOK,  ["testing", "framework", "sdk", "arch"]),
    (r"knowledge/coding-sdk/layered-architecture\.md", "team/arch-coding-sdk", CATEGORY_DECISION, ["architecture", "layered", "framework", "sdk", "arch"]),

    # knowledge/coding-feature-store — FS framework
    (r"knowledge/coding-feature-store/mindset\.md",                   "team/arch-coding-feature-store", CATEGORY_DECISION, ["mindset", "adr", "framework", "feature-store", "arch"]),
    (r"knowledge/coding-feature-store/capability-contract\.md",       "team/arch-coding-feature-store", CATEGORY_PATTERN,  ["contract", "yaml", "framework", "feature-store", "arch"]),
    (r"knowledge/coding-feature-store/module-topology\.md",           "team/arch-coding-feature-store", CATEGORY_PATTERN,  ["module", "gradle", "konsist", "framework", "feature-store", "arch"]),
    (r"knowledge/coding-feature-store/data-port-runtime-config\.md",  "team/arch-coding-feature-store", CATEGORY_PATTERN,  ["port", "adapter", "runtime", "framework", "feature-store", "arch"]),
    (r"knowledge/coding-feature-store/theme-adapter\.md",             "team/arch-coding-feature-store", CATEGORY_PATTERN,  ["theme", "ui", "compose", "framework", "feature-store", "arch"]),
    (r"knowledge/coding-feature-store/testing-kit\.md",               "team/arch-coding-feature-store", CATEGORY_RUNBOOK,  ["testing", "testfixtures", "framework", "feature-store", "arch"]),
    (r"knowledge/coding-feature-store/essentials\.md",                "team/arch-coding-feature-store", CATEGORY_RUNBOOK,  ["rule", "checklist", "framework", "feature-store", "arch"]),

    # knowledge/coding/* — language/framework patterns
    (r"knowledge/coding/compose/.*\.md",     "team/arch-coding-compose",     CATEGORY_PATTERN, ["ui", "compose", "framework", "arch"]),
    (r"knowledge/coding/coroutines/.*\.md",  "team/arch-coding-coroutines",  CATEGORY_PATTERN, ["async", "flow", "framework", "arch"]),
    (r"knowledge/coding/mvi/.*\.md",         "team/arch-coding-mvi",         CATEGORY_PATTERN, ["state", "intent", "effect", "framework", "arch"]),
    (r"knowledge/coding/clean-arch/.*\.md",  "team/arch-coding-clean-arch",  CATEGORY_PATTERN, ["architecture", "clean", "framework", "arch"]),
    (r"knowledge/coding/patterns/.*\.md",    "team/arch-coding-patterns",    CATEGORY_PATTERN, ["kotlin", "framework", "arch"]),
    (r"knowledge/coding/data/.*\.md",        "team/arch-coding-data",        CATEGORY_PATTERN, ["persistence", "cache", "framework", "arch"]),

    # knowledge/product/*
    (r"knowledge/product/input-analysis/.*\.md", "team/arch-product-input-analysis", CATEGORY_RUNBOOK, ["spec", "ba", "framework", "arch"]),
    (r"knowledge/product/.*\.md",                "team/arch-product",                CATEGORY_RUNBOOK, ["product", "ba", "framework", "arch"]),

    # knowledge/design/*
    (r"knowledge/design/design-system/.*\.md",  "team/arch-design-system",   CATEGORY_RUNBOOK, ["design-system", "ui", "framework", "arch"]),
    (r"knowledge/design/visual-compare/.*\.md", "team/arch-design-compare",  CATEGORY_RUNBOOK, ["visual", "compare", "framework", "arch"]),
    (r"knowledge/design/.*\.md",                "team/arch-design",          CATEGORY_RUNBOOK, ["design", "framework", "arch"]),

    # knowledge/pm/*
    (r"knowledge/pm/.*\.md", "team/arch-pm", CATEGORY_RUNBOOK, ["pm", "deadline", "scope", "framework", "arch"]),

    # knowledge/testing/*
    (r"knowledge/testing/e2e-runtime/.*\.md", "team/arch-testing-e2e-runtime", CATEGORY_RUNBOOK, ["e2e", "testing", "framework", "arch"]),
    (r"knowledge/testing/.*\.md",             "team/arch-testing",             CATEGORY_RUNBOOK, ["testing", "framework", "arch"]),

    # knowledge/meta/*
    (r"knowledge/meta/agent-orchestration/.*\.md", "team/arch-meta-orchestration", CATEGORY_RUNBOOK, ["orchestration", "agent", "framework", "arch"]),
    (r"knowledge/meta/harness-governance/.*\.md",  "team/arch-meta-governance",    CATEGORY_RUNBOOK, ["governance", "framework", "arch"]),
    (r"knowledge/meta/auto-fix/.*\.md",            "team/arch-meta-auto-fix",      CATEGORY_RUNBOOK, ["debug", "auto-fix", "framework", "arch"]),
    (r"knowledge/meta/.*\.md",                     "team/arch-meta",               CATEGORY_RUNBOOK, ["meta", "framework", "arch"]),

    # knowledge/cross-cutting/*
    (r"knowledge/cross-cutting/performance/.*\.md",    "team/arch-xcut-performance",    CATEGORY_RUNBOOK, ["performance", "framework", "arch"]),
    (r"knowledge/cross-cutting/security/.*\.md",       "team/arch-xcut-security",       CATEGORY_RUNBOOK, ["security", "owasp", "framework", "arch"]),
    (r"knowledge/cross-cutting/build-strategy/.*\.md", "team/arch-xcut-build-strategy", CATEGORY_RUNBOOK, ["gradle", "build", "framework", "arch"]),

    # knowledge/README.md — top-level index
    (r"knowledge/README\.md", "team/arch", CATEGORY_RUNBOOK, ["index", "framework", "arch"]),

    # constitution/*
    (r"constitution/README\.md",             "team/arch-constitution", CATEGORY_RUNBOOK,  ["index", "adr", "framework", "arch"]),
    (r"constitution/definition-of-done\.md", "team/arch-constitution", CATEGORY_RUNBOOK,  ["dod", "quality-gate", "framework", "arch"]),
    (r"constitution/adr-(.+)\.md",           "team/arch-constitution", CATEGORY_DECISION, ["adr", "framework", "arch"]),
    (r"constitution/coro-(.+)\.md",          "team/arch-constitution", CATEGORY_DECISION, ["coro", "coroutines", "framework", "arch"]),
    (r"constitution/kot-(.+)\.md",           "team/arch-constitution", CATEGORY_DECISION, ["kot", "kotlin", "framework", "arch"]),
    (r"constitution/.*\.md",                 "team/arch-constitution", CATEGORY_DECISION, ["constitution", "framework", "arch"]),

    # briefs/* — product spec runtime (projects/<slug>)
    (r"briefs/([^/]+)/req\.md",     r"projects/\1", CATEGORY_DECISION, ["spec", "requirement", "business"]),
    (r"briefs/([^/]+)/.*\.md",      r"projects/\1", CATEGORY_RUNBOOK,  ["spec", "business"]),
    (r"briefs/README\.md",          "team/business-index", CATEGORY_RUNBOOK, ["index", "business"]),

    # fallback
    (r"knowledge/.*\.md",     "team/arch", CATEGORY_RUNBOOK, ["framework", "arch"]),
    (r"constitution/.*\.md",  "team/arch-constitution", CATEGORY_DECISION, ["constitution", "framework", "arch"]),
    (r"briefs/.*\.md",        "team/business-index", CATEGORY_RUNBOOK, ["spec", "business"]),
]


def infer(rel_path: str) -> tuple[str, str, list[str]] | None:
    for pattern, scope_tmpl, category, tags in MAP:
        m = re.fullmatch(pattern, rel_path)
        if m:
            scope = m.expand(scope_tmpl) if "\\" in scope_tmpl else scope_tmpl
            return scope, category, tags
    return None


def extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return fallback.replace("-", " ").replace("_", " ").title()


def push_note(path: Path, dry_run: bool) -> dict:
    rel = path.relative_to(HARNESS).as_posix()
    inferred = infer(rel)
    if not inferred:
        return {"path": rel, "status": "skip", "reason": "no mapping"}

    scope, category, tags = inferred
    content = path.read_text(encoding="utf-8")
    title = extract_title(content, path.stem)
    capture_id = hashlib.sha256(rel.encode()).hexdigest()[:16]

    note = {
        "title": title,
        "content": content,
        "scope": scope,
        "category": category,
        "tags": tags,
        "verification": "tested",
        "evidence": [f"source: {rel}"],
        "capture_id": capture_id,
    }

    if dry_run:
        return {"path": rel, "status": "dry-run", "scope": scope, "category": category, "tags": tags, "title": title}

    result = subprocess.run(
        ["team-kb", "push", "--note-json", "-"],
        input=json.dumps(note, ensure_ascii=False),
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        return {"path": rel, "status": "fail", "stderr": result.stderr[:400], "returncode": result.returncode}
    try:
        parsed = json.loads(result.stdout.strip().splitlines()[-1])
        return {"path": rel, "status": "ok", "scope": scope, "category": category, "note_id": parsed.get("note_id"), "published": parsed.get("published")}
    except (json.JSONDecodeError, IndexError):
        return {"path": rel, "status": "ok", "scope": scope, "category": category, "raw": result.stdout[-200:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--filter", help="regex to filter rel path (e.g. knowledge/coding-sdk)")
    ap.add_argument("--limit", type=int, help="process first N files only")
    args = ap.parse_args()

    paths: list[Path] = []
    for base in ["knowledge", "constitution", "briefs"]:
        root = HARNESS / base
        if root.exists():
            paths.extend(root.rglob("*.md"))

    paths.sort()
    if args.filter:
        paths = [p for p in paths if re.search(args.filter, p.relative_to(HARNESS).as_posix())]
    if args.limit:
        paths = paths[: args.limit]

    print(f"Found {len(paths)} markdown files to process", file=sys.stderr)

    results: list[dict] = []
    counts = {"ok": 0, "dry-run": 0, "fail": 0, "skip": 0}
    for p in paths:
        r = push_note(p, dry_run=args.dry_run)
        results.append(r)
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        status = r["status"]
        tag = f"[{status:7}]"
        extra = ""
        if status == "fail":
            extra = f"  !! {r.get('stderr', '')[:120]}"
        elif status in ("ok", "dry-run"):
            extra = f"  scope={r.get('scope')} category={r.get('category')}"
        print(f"{tag} {r['path']}{extra}", file=sys.stderr)

    print("\n=== Report ===", file=sys.stderr)
    for k, v in counts.items():
        print(f"  {k}: {v}", file=sys.stderr)

    print(json.dumps(results, ensure_ascii=False, indent=2))

    return 1 if counts.get("fail", 0) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
