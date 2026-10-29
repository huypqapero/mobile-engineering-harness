#!/usr/bin/env python3
"""Rename KB scope from team/arch-* flat prefix to nested develop/product/testing folders.

Reads existing notes under ~/team-knowledge/notes/team/, re-pushes each with new scope
via team-kb push CLI (wrapper creates files at notes/<new-scope>/<category>/kb-<id>.md).

After all re-push success, old notes/team/ folders are removed via `git rm -r` separately.

Usage:
    scripts/rename-kb-scope.py --dry-run    # preview mapping
    scripts/rename-kb-scope.py              # execute

Idempotent via capture_id = sha256(new_scope + title). Re-run safely.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

KB_REPO = Path.home() / "team-knowledge"
NOTES_ROOT = KB_REPO / "notes"

SCOPE_MAP = {
    "team/arch":                      "develop/index",
    "team/arch-coding-sdk":           "develop/coding-sdk",
    "team/arch-coding-feature-store": "develop/coding-feature-store",
    "team/arch-coding-compose":       "develop/coding-compose",
    "team/arch-coding-coroutines":    "develop/coding-coroutines",
    "team/arch-coding-mvi":           "develop/coding-mvi",
    "team/arch-coding-clean-arch":    "develop/coding-clean-arch",
    "team/arch-coding-patterns":      "develop/coding-patterns",
    "team/arch-coding-data":          "develop/coding-data",
    "team/arch-constitution":         "develop/constitution",
    "team/arch-xcut-performance":     "develop/xcut-performance",
    "team/arch-xcut-security":        "develop/xcut-security",
    "team/arch-xcut-build-strategy":  "develop/xcut-build-strategy",
    "team/arch-meta-orchestration":   "develop/meta-orchestration",
    "team/arch-meta-governance":      "develop/meta-governance",
    "team/arch-meta-auto-fix":        "develop/meta-auto-fix",
    "team/arch-product":              "product/ba",
    "team/arch-product-input-analysis": "product/input-analysis",
    "team/arch-pm":                   "product/pm",
    "team/arch-design-system":        "product/design-system",
    "team/arch-design-compare":       "product/design-compare",
    "team/arch-design":               "product/design",
    "team/business-index":            "product/business-index",
    "team/arch-testing-e2e-runtime":  "testing/e2e-runtime",
    "team/arch-testing":              "testing/general",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def parse_note(path: Path) -> dict:
    """Extract frontmatter + body from note file."""
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path}: no YAML frontmatter")
    fm_text, body = m.group(1), m.group(2)

    meta: dict = {}
    for line in fm_text.splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        meta[k] = v

    tags = []
    tags_match = re.search(r"^tags:\n((?:- .+\n)+)", fm_text, re.MULTILINE)
    if tags_match:
        tags = [line[2:].strip() for line in tags_match.group(1).splitlines() if line.startswith("- ")]

    evidence = []
    evi_match = re.search(r"^evidence:\n((?:- .+\n)+)", fm_text, re.MULTILINE)
    if evi_match:
        evidence = [line[2:].strip() for line in evi_match.group(1).splitlines() if line.startswith("- ")]

    return {
        "title": meta.get("title", path.stem),
        "scope": meta.get("scope", ""),
        "category": meta.get("type") or meta.get("category", "runbook"),
        "verification": meta.get("verification", "unverified"),
        "tags": tags,
        "evidence": evidence,
        "body": body.strip(),
    }


def repush(note: dict, new_scope: str, dry_run: bool) -> dict:
    capture_id = hashlib.sha256(f"{new_scope}|{note['title']}".encode()).hexdigest()[:16]
    payload = {
        "title": note["title"],
        "content": note["body"],
        "scope": new_scope,
        "category": note["category"],
        "tags": note["tags"] or None,
        "verification": note["verification"] or "tested",
        "evidence": note["evidence"] or None,
        "capture_id": capture_id,
    }

    if dry_run:
        return {"status": "dry-run", "new_scope": new_scope, "title": note["title"]}

    result = subprocess.run(
        ["team-kb", "push", "--note-json", "-"],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        return {"status": "fail", "stderr": result.stderr[:300]}
    try:
        parsed = json.loads(result.stdout.strip().splitlines()[-1])
        return {"status": "ok", "new_scope": new_scope, "note_id": parsed.get("note_id"), "published": parsed.get("published")}
    except (json.JSONDecodeError, IndexError):
        return {"status": "ok", "new_scope": new_scope, "raw": result.stdout[-200:]}


def collect_notes() -> list[Path]:
    """Walk notes/team/ recursive, excluding already-renamed notes/develop/, product/, testing/."""
    files: list[Path] = []
    team_dir = NOTES_ROOT / "team"
    if team_dir.exists():
        files.extend(sorted(team_dir.rglob("*.md")))
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    paths = collect_notes()
    if args.limit:
        paths = paths[: args.limit]
    print(f"Found {len(paths)} notes under notes/team/", file=sys.stderr)

    counts = {"ok": 0, "dry-run": 0, "fail": 0, "no-mapping": 0}
    results: list[dict] = []
    for path in paths:
        try:
            note = parse_note(path)
        except Exception as e:
            print(f"[parse-fail] {path}: {e}", file=sys.stderr)
            counts["fail"] += 1
            continue

        old_scope = note["scope"]
        new_scope = SCOPE_MAP.get(old_scope)
        if not new_scope:
            print(f"[no-mapping] {path.name}: scope={old_scope}", file=sys.stderr)
            counts["no-mapping"] += 1
            continue

        r = repush(note, new_scope, dry_run=args.dry_run)
        results.append({"path": str(path.relative_to(KB_REPO)), **r})
        status = r["status"]
        counts[status] = counts.get(status, 0) + 1
        tag = f"[{status:8}]"
        print(f"{tag} {old_scope:40} → {new_scope:35} {note['title'][:50]}", file=sys.stderr)

    print("\n=== Report ===", file=sys.stderr)
    for k, v in counts.items():
        print(f"  {k}: {v}", file=sys.stderr)

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if counts.get("fail", 0) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
