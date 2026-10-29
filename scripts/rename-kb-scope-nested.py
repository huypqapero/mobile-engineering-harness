#!/usr/bin/env python3
"""Re-structure develop/* scope into nested 2-level: app/sdk/feature-store/mindset|structure + 8 flat.

Reads existing notes under ~/team-knowledge/notes/{develop,product,testing}/, re-pushes with
new nested scope via team-kb push CLI (wrapper fork v0.3.0 allows 2-level scope).

Mapping per note (title-aware for coding-sdk/, coding-feature-store/, coding-data/).
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

# Default scope mapping (by current scope only)
SCOPE_MAP = {
    # develop/* restructure
    "develop/coding-clean-arch":   "develop/clean-arch",
    "develop/coding-patterns":     "develop/design-pattern",
    "develop/coding-mvi":          "develop/structure-code",
    "develop/coding-compose":      "develop/compose-ui",
    "develop/coding-coroutines":   "develop/kotlin-coroutine",
    # develop/coding-data → split per title (xem TITLE_MAP)
    # develop/coding-sdk → split per title → develop/sdk/mindset|structure
    # develop/coding-feature-store → split per title → develop/feature-store/mindset|structure
    "develop/constitution":        "develop/constitution",
    "develop/meta-orchestration":  "develop/meta-orchestration",
    "develop/meta-governance":     "develop/meta-governance",
    "develop/meta-auto-fix":       "develop/meta-auto-fix",
    "develop/xcut-performance":    "develop/xcut-performance",
    "develop/xcut-security":       "develop/xcut-security",
    "develop/xcut-build-strategy": "develop/xcut-build-strategy",
    "develop/index":               None,  # drop

    # product/*, testing/* keep as-is
    "product/ba":                "product/ba",
    "product/business-index":    "product/business-index",
    "product/design-compare":    "product/design-compare",
    "product/design-system":     "product/design-system",
    "product/input-analysis":    "product/input-analysis",
    "product/pm":                "product/pm",
    "testing/e2e-runtime":       "testing/e2e-runtime",
}

# Title-aware override for scopes needing split
TITLE_MAP = {
    # SDK → sdk/mindset vs sdk/structure
    ("develop/coding-sdk", "SDK Mindset — ADR Set"):               "develop/sdk/mindset",
    ("develop/coding-sdk", "SDK Brainstorm Process — 10-Step Top-Down"): "develop/sdk/mindset",
    ("develop/coding-sdk", "Layered Kernel-Plugin Architecture"):   "develop/sdk/structure",
    ("develop/coding-sdk", "SDK Pattern Catalog"):                   "develop/sdk/structure",
    ("develop/coding-sdk", "TestingKit Rules"):                      "develop/sdk/structure",
    ("develop/coding-sdk", "Shared Library — Essentials"):           "develop/sdk/structure",

    # Feature Store → feature-store/mindset vs feature-store/structure
    ("develop/coding-feature-store", "Feature Store Mindset — ADR Set"):  "develop/feature-store/mindset",
    ("develop/coding-feature-store", "Capability Contract — 6-trục YAML"): "develop/feature-store/structure",
    ("develop/coding-feature-store", "Module Topology — 2-Module Template"): "develop/feature-store/structure",
    ("develop/coding-feature-store", "Data Port + Runtime Config Pattern"): "develop/feature-store/structure",
    ("develop/coding-feature-store", "Theme Adapter Contract"):              "develop/feature-store/structure",
    ("develop/coding-feature-store", "TestingKit via testFixtures"):         "develop/feature-store/structure",
    ("develop/coding-feature-store", "Feature Store — Essentials"):          "develop/feature-store/structure",

    # coding-data → split database vs networking vs design-pattern
    ("develop/coding-data", "Persistence — Essentials"):   "develop/database",
    ("develop/coding-data", "Caching — Essentials"):       "develop/database",
    ("develop/coding-data", "Network — Essentials"):       "develop/networking",
    ("develop/coding-data", "DTO Serialization — Always @SerialName Rule"): "develop/networking",
    # JSON Deserialize note has long title; match prefix
    ("develop/coding-data", "JSON Deserialize — Fallback Default on Wrong Type / Missing / Null"): "develop/networking",
    ("develop/coding-data", "Repository Pattern — Essentials"): "develop/design-pattern",
}


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def parse_note(path: Path) -> dict:
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
        meta[k.strip()] = v.strip().strip('"').strip("'")

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


def resolve_new_scope(old_scope: str, title: str) -> str | None:
    # Try title-aware first
    tk = (old_scope, title)
    if tk in TITLE_MAP:
        return TITLE_MAP[tk]
    # Fallback to scope-only
    return SCOPE_MAP.get(old_scope)


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
        capture_output=True, text=True, timeout=90,
    )
    if result.returncode != 0:
        return {"status": "fail", "stderr": result.stderr[:300]}
    try:
        parsed = json.loads(result.stdout.strip().splitlines()[-1])
        return {"status": "ok", "new_scope": new_scope, "note_id": parsed.get("note_id")}
    except (json.JSONDecodeError, IndexError):
        return {"status": "ok", "new_scope": new_scope, "raw": result.stdout[-200:]}


def collect_notes() -> list[Path]:
    files: list[Path] = []
    for d in ["develop", "product", "testing"]:
        root = NOTES_ROOT / d
        if root.exists():
            files.extend(sorted(root.rglob("*.md")))
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    paths = collect_notes()
    if args.limit:
        paths = paths[: args.limit]
    print(f"Found {len(paths)} notes under notes/{{develop,product,testing}}/", file=sys.stderr)

    counts = {"ok": 0, "dry-run": 0, "fail": 0, "no-mapping": 0, "drop": 0}
    results: list[dict] = []
    for path in paths:
        try:
            note = parse_note(path)
        except Exception as e:
            print(f"[parse-fail] {path}: {e}", file=sys.stderr)
            counts["fail"] += 1
            continue

        old_scope = note["scope"]
        new_scope = resolve_new_scope(old_scope, note["title"])
        if new_scope is None:
            print(f"[drop     ] {path.name}: scope={old_scope}  title={note['title'][:40]}", file=sys.stderr)
            counts["drop"] += 1
            continue
        if new_scope == old_scope:
            # Already correctly scoped — skip to avoid duplicate push
            counts["no-mapping"] += 1
            continue

        r = repush(note, new_scope, dry_run=args.dry_run)
        results.append({"path": str(path.relative_to(KB_REPO)), **r})
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        tag = f"[{r['status']:8}]"
        print(f"{tag} {old_scope:40} → {new_scope:40} {note['title'][:50]}", file=sys.stderr)

    print("\n=== Report ===", file=sys.stderr)
    for k, v in counts.items():
        print(f"  {k}: {v}", file=sys.stderr)

    return 1 if counts.get("fail", 0) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
