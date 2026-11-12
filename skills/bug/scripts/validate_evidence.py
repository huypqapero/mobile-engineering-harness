#!/usr/bin/env python3
"""Deterministic evidence validator cho skill bug-fix (mode batch và mode note).

Hai chế độ:
  validate_evidence.py <batch_dir>                       cả batch plans/bugfix-batch-<id>/
  validate_evidence.py --evidence-dir <dir> [--base-commit <sha>]
                                                         1 thư mục evidence (mode note:
                                                         plans/reports/bugs/<BUG-ID>-<slug>/); không có
                                                         manifest nên chỉ kiểm commit khi truyền --base-commit

Kiểm CƠ HỌC (không dựa prompt) evidence:
- Batch: mỗi issue trong state.json có thư mục evidence/<ISSUE>/evidence.json.
- evidence.json đủ field bắt buộc theo schemas/evidence.schema.json.
- Mọi artifact liệt kê TỒN TẠI THẬT trên disk (và không rỗng).
- verdict set; commit khớp manifest.base_commit.
- Mỗi acceptance criterion có evidence trỏ 1 artifact có thật.

Chỉ dùng stdlib (json/os/sys/argparse) — chạy được bằng python3 hệ thống >= 3.8.

Exit code:
  0  — mọi issue PASS evidence gate.
  1  — có issue FAIL (thiếu field/artifact/commit lệch).
  2  — lỗi dùng sai (batch dir / evidence dir không hợp lệ).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

REQUIRED_TOP = ("issue", "commit", "verdict", "verification", "artifacts", "acceptance_criteria")
VALID_VERDICT = {"PASS", "FAIL", "NEEDS_VERIFICATION"}


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh), None
    except FileNotFoundError:
        return None, f"not found: {path}"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON ({exc}): {path}"


def validate_issue(issue_id, ev_dir, base_commit):
    """Trả về (ok: bool, problems: list[str])."""
    problems = []
    ev_path = os.path.join(ev_dir, "evidence.json")
    data, err = _load_json(ev_path)
    if err:
        return False, [err]

    for field in REQUIRED_TOP:
        if field not in data:
            problems.append(f"{issue_id}: thiếu field bắt buộc '{field}'")

    verdict = data.get("verdict")
    if verdict not in VALID_VERDICT:
        problems.append(f"{issue_id}: verdict không hợp lệ '{verdict}'")
    elif verdict != "PASS":
        problems.append(f"{issue_id}: verdict = {verdict} (chưa PASS → evidence gate FAIL)")

    commit = data.get("commit")
    if base_commit and commit and commit != base_commit:
        problems.append(
            f"{issue_id}: commit '{commit}' lệch manifest.base_commit '{base_commit}' (evidence stale)"
        )

    # artifact tồn tại thật
    artifacts = data.get("artifacts") or []
    if not artifacts:
        problems.append(f"{issue_id}: artifacts rỗng")
    present = set()
    for art in artifacts:
        art_path = os.path.join(ev_dir, art)
        if not os.path.isfile(art_path):
            problems.append(f"{issue_id}: artifact không tồn tại: {art}")
        elif os.path.getsize(art_path) == 0:
            problems.append(f"{issue_id}: artifact rỗng (0 byte): {art}")
        else:
            present.add(art)

    # mỗi AC có evidence trỏ artifact có thật
    acs = data.get("acceptance_criteria") or []
    if not acs:
        problems.append(f"{issue_id}: acceptance_criteria rỗng")
    for ac in acs:
        ac_id = ac.get("id", "?")
        ev_ref = ac.get("evidence")
        if not ev_ref:
            problems.append(f"{issue_id}/{ac_id}: AC thiếu evidence")
        elif ev_ref not in present:
            problems.append(f"{issue_id}/{ac_id}: evidence '{ev_ref}' không có trong artifact tồn tại")
        if ac.get("result") != "PASS":
            problems.append(f"{issue_id}/{ac_id}: AC result = {ac.get('result')} (chưa PASS)")

    return (len(problems) == 0), problems


def resolve_issue_ids(batch_dir):
    """Lấy danh sách issue từ state.json; fallback: quét evidence/ dir."""
    state, err = _load_json(os.path.join(batch_dir, "state.json"))
    if state and not err:
        issues = state.get("issues")
        if isinstance(issues, dict):
            return sorted(issues.keys())
        if isinstance(issues, list):
            return [i.get("id") if isinstance(i, dict) else i for i in issues]
    ev_root = os.path.join(batch_dir, "evidence")
    if os.path.isdir(ev_root):
        return sorted(d for d in os.listdir(ev_root) if os.path.isdir(os.path.join(ev_root, d)))
    return []


def validate_single(ev_dir, base_commit):
    if not os.path.isdir(ev_dir):
        print(f"ERROR: evidence dir không tồn tại: {ev_dir}", file=sys.stderr)
        return 2
    data, _ = _load_json(os.path.join(ev_dir, "evidence.json"))
    issue_id = (data or {}).get("issue") or os.path.basename(os.path.normpath(ev_dir))
    ok, problems = validate_issue(issue_id, ev_dir, base_commit)
    if ok:
        print(f"PASS  {issue_id}")
        return 0
    for problem in problems:
        print(f"FAIL  {problem}")
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate bugfix batch evidence (deterministic).")
    parser.add_argument("batch_dir", nargs="?", help="plans/bugfix-batch-<id> directory")
    parser.add_argument("--evidence-dir", help="validate 1 thư mục evidence (mode note) thay vì cả batch")
    parser.add_argument("--base-commit", help="với --evidence-dir: commit evidence phải khớp")
    args = parser.parse_args(argv)

    if bool(args.evidence_dir) == bool(args.batch_dir):
        parser.error("cần đúng một trong: <batch_dir> hoặc --evidence-dir <dir>")
    if args.base_commit and not args.evidence_dir:
        parser.error("--base-commit chỉ dùng với --evidence-dir (batch đọc manifest.base_commit)")
    if args.evidence_dir:
        return validate_single(args.evidence_dir, args.base_commit)

    batch_dir = args.batch_dir
    if not os.path.isdir(batch_dir):
        print(f"ERROR: batch dir không tồn tại: {batch_dir}", file=sys.stderr)
        return 2

    manifest, _ = _load_json(os.path.join(batch_dir, "manifest.json"))
    base_commit = (manifest or {}).get("base_commit")

    issue_ids = resolve_issue_ids(batch_dir)
    if not issue_ids:
        print(f"ERROR: không tìm thấy issue nào (state.json/evidence/) trong {batch_dir}", file=sys.stderr)
        return 2

    all_ok = True
    passed = 0
    for issue_id in issue_ids:
        ev_dir = os.path.join(batch_dir, "evidence", str(issue_id))
        ok, problems = validate_issue(issue_id, ev_dir, base_commit)
        if ok:
            passed += 1
            print(f"PASS  {issue_id}")
        else:
            all_ok = False
            for p in problems:
                print(f"FAIL  {p}")

    total = len(issue_ids)
    print(f"\n{passed}/{total} issue PASS evidence gate.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
