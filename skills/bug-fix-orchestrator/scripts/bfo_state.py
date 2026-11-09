#!/usr/bin/env python3
"""Batch state cho skill bug-fix-orchestrator.

Một batch = thư mục plans/bugfix-batch-<id>/ trong repo app. File:
  manifest.json  batch_id, base_commit, base_branch, source, created
  state.json     issues / groups / lanes / devices / device_jobs (leader + lane cùng đọc)
Mọi lệnh ghi đều lấy file lock riêng của batch, nên leader và nhiều lane gọi song song an toàn.
Định dạng state.json["issues"] (dict theo issue key) tương thích skills/bug/scripts/validate_evidence.py.

Lệnh (batch_dir luôn là tham số đầu, đường dẫn tuyệt đối):
  init <dir> --base-commit SHA --base-branch BR --source TEXT [--max-lanes 3]
  check-plan <plan.json> [--bugs bugs.json] [--repo WORKTREE]
                                    chỉ kiểm, không ghi (--bugs: mọi bug phải có mặt; --repo: file phải tồn tại)
  load-plan <dir> <plan.json> [--bugs …] [--repo …]
                                    kiểm rồi nạp vào state (sau khi user duyệt); lane/issue không còn trong plan bị gỡ
  next-lanes <dir>                  in lane được phép chạy ngay (tôn trọng after + max_lanes)
  lane <dir> <LANE> k=v ...         cập nhật lane (status, branch, worktree, agent, pr, note)
  issue <dir> <KEY> k=v ...         cập nhật issue (status, pr, note, fix_commit)
  device-sync <dir> <serial> ...    khai báo pool thiết bị (từ `adb devices`)
  device-request <dir> <KEY> --lane L [--purpose verify|repro]
                                    xếp hàng 1 job thiết bị (idempotent theo issue + purpose).
                                    repro = tái hiện + lấy logcat TRƯỚC khi fix (crash chưa có stack)
  device-dispatch <dir> [--exclude SERIAL ...] [--job JOB ...]
                                    gán job pending cho thiết bị rảnh; in "JOB SERIAL" mỗi dòng.
                                    exit 0 đã gán ≥1 · exit 3 còn job nhưng hết thiết bị · exit 0 không in gì = hết job
  device-done <dir> <JOB> --result pass|fail   trả thiết bị, ghi kết quả
  device-release <dir> <SERIAL>     nhả thiết bị bị giữ quá lâu (job quay về pending)
  board <dir>                       bảng trạng thái Markdown

Exit code chung: 0 ok · 1 plan/state không hợp lệ · 2 dùng sai · 3 phải chờ.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path

KINDS_FIXABLE = {"code", "ui", "content"}
KINDS_EXCLUDED = {"spec-gap", "needs-info", "needs-confirm", "duplicate", "not-a-bug", "external",
                  "already-fixed", "conflict"}
# Bug chỉ được fix khi đã so 1-1 với spec/Figma và chắc chắn lệch (spec_verdict=confirmed + spec_ref).
# Nghi ngờ (tester hiểu nhầm, spec im lặng, spec mâu thuẫn) → needs-confirm + câu hỏi, không chặn bug khác.
SPEC_VERDICTS = {"confirmed"}
VERIFY_TIERS = {"none", "unit", "preview", "device"}
ISSUE_STATUSES = {"planned", "fixing", "fixed", "pending_device", "verifying_device", "verified",
                  "pr_open", "done", "blocked", "failed", "excluded"}
LANE_STATUSES = {"planned", "running", "waiting", "pr_open", "done", "failed", "cancelled"}
LANE_UNBLOCKS = {"pr_open", "done"}
LANE_RUNNING = {"running"}
MAX_ISSUES_PER_LANE = 8
DEVICE_STALE_SECONDS = 45 * 60


def natural_key(text: str):
    """L2 < L10, AAP884-2 < AAP884-10."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(text))]


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def die(msg: str, code: int = 2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"không tìm thấy: {path}")
    except json.JSONDecodeError as exc:
        die(f"JSON lỗi ({exc}): {path}", 1)


def write_json(path: Path, data) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


@contextmanager
def locked(batch_dir: Path, write: bool = True):
    if not batch_dir.is_dir():
        die(f"batch dir không tồn tại: {batch_dir}")
    with open(batch_dir / ".state.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state_file = batch_dir / "state.json"
        state = read_json(state_file)
        yield state
        if write:
            write_json(state_file, state)


# ---------------------------------------------------------------- plan validation

def _lane_order_ok(lanes: dict, a: str, b: str) -> bool:
    """True nếu a chạy sau b hoặc b chạy sau a (theo chuỗi after)."""
    def reaches(src, dst, seen=None):
        seen = seen or set()
        for dep in lanes[src].get("after", []):
            if dep == dst or (dep not in seen and dep in lanes and reaches(dep, dst, seen | {dep})):
                return True
        return False
    return reaches(a, b) or reaches(b, a)


def group_files(group: dict) -> set:
    return set(group.get("files", [])) | set(group.get("shared_files", []))


def validate_plan(plan: dict, bugs: dict = None, repo: Path = None) -> tuple:
    errors, warnings = [], []
    issues = plan.get("issues") or {}
    if bugs is not None:
        missing = sorted(set(bugs) - set(issues), key=natural_key)
        extra = sorted(set(issues) - set(bugs), key=natural_key)
        if missing:
            errors.append(f"bug chưa được phân loại: {', '.join(missing)}")
        if extra:
            warnings.append(f"issue không có trong bugs.json: {', '.join(extra)}")
    groups = plan.get("groups") or {}
    lanes = plan.get("lanes") or {}
    if not issues:
        errors.append("plan không có issue nào")

    for key, issue in issues.items():
        kind, verify, group = issue.get("kind"), issue.get("verify"), issue.get("group")
        if kind not in KINDS_FIXABLE | KINDS_EXCLUDED:
            errors.append(f"{key}: kind '{kind}' không hợp lệ")
        if kind in KINDS_FIXABLE:
            if verify not in VERIFY_TIERS:
                errors.append(f"{key}: verify '{verify}' không hợp lệ ({'/'.join(sorted(VERIFY_TIERS))})")
            if not group:
                errors.append(f"{key}: bug sửa được ({kind}) nhưng chưa thuộc group")
            elif group not in groups:
                errors.append(f"{key}: group '{group}' không tồn tại")
            if not issue.get("reason"):
                warnings.append(f"{key}: thiếu reason cho phân loại")
            if issue.get("spec_verdict") not in SPEC_VERDICTS or not issue.get("spec_ref"):
                errors.append(f"{key}: chỉ fix khi đã so spec 1-1 — cần spec_verdict=confirmed + spec_ref "
                              f"(trích spec/Figma/decision); còn nghi ngờ → kind needs-confirm")
        elif kind in KINDS_EXCLUDED:
            if group:
                errors.append(f"{key}: kind '{kind}' không được vào group (loại khỏi batch)")
            if not issue.get("reason"):
                errors.append(f"{key}: bị loại ({kind}) phải ghi reason / câu hỏi cho PO")
            if kind == "needs-confirm" and not issue.get("question"):
                errors.append(f"{key}: needs-confirm phải có question (câu hỏi cụ thể cho user/BA/tester)")

    lane_of_group: dict[str, str] = {}
    for lane_id, lane in lanes.items():
        for gid in lane.get("groups", []):
            if gid not in groups:
                errors.append(f"lane {lane_id}: group '{gid}' không tồn tại")
            elif gid in lane_of_group:
                errors.append(f"group {gid} nằm ở 2 lane: {lane_of_group[gid]}, {lane_id}")
            else:
                lane_of_group[gid] = lane_id
        for dep in lane.get("after", []):
            if dep not in lanes:
                errors.append(f"lane {lane_id}: after '{dep}' không tồn tại")
            if dep == lane_id:
                errors.append(f"lane {lane_id}: after chính nó")

    for gid, group in groups.items():
        if gid not in lane_of_group:
            errors.append(f"group {gid} chưa thuộc lane nào")
        if not group.get("files"):
            errors.append(f"group {gid}: thiếu files dự kiến sửa (lấy từ scout)")
        if repo is not None:
            for path in sorted(group_files(group)):
                if not (repo / path).exists() and not group.get("new_files_ok"):
                    errors.append(f"group {gid}: file không tồn tại ở base: {path} "
                                  f"(file mới → đặt new_files_ok: true)")
        members = group.get("issues", [])
        if not members:
            errors.append(f"group {gid}: rỗng")
        for key in members:
            if key not in issues:
                errors.append(f"group {gid}: issue '{key}' không có trong issues")
            elif issues[key].get("group") != gid:
                errors.append(f"group {gid}: issue {key} lại trỏ group '{issues[key].get('group')}'")

    # cycle check on after
    def has_cycle(node, stack):
        if node in stack:
            return True
        return any(has_cycle(d, stack | {node}) for d in lanes.get(node, {}).get("after", []) if d in lanes)
    for lane_id in lanes:
        if has_cycle(lane_id, set()):
            errors.append(f"lane {lane_id}: after tạo vòng lặp")
            break

    lane_files = {lid: set().union(*[group_files(groups.get(g, {})) for g in lane.get("groups", [])] or [set()])
                  for lid, lane in lanes.items()}
    lane_ids = sorted(lanes, key=natural_key)
    if not any("vòng lặp" in e for e in errors):
        for i, a in enumerate(lane_ids):
            for b in lane_ids[i + 1:]:
                overlap = sorted(lane_files[a] & lane_files[b])
                if overlap and not _lane_order_ok(lanes, a, b):
                    errors.append(f"lane {a} và {b} cùng sửa {', '.join(overlap)} nhưng không có after → "
                                  f"gộp chung lane hoặc thêm after")

    for lane_id, lane in lanes.items():
        count = sum(len(groups.get(g, {}).get("issues", [])) for g in lane.get("groups", []))
        if count > MAX_ISSUES_PER_LANE:
            warnings.append(f"lane {lane_id}: {count} issue > {MAX_ISSUES_PER_LANE}, PR khó review — cân nhắc tách")
    return errors, warnings


def print_findings(errors, warnings) -> None:
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print("plan OK" if not errors else f"plan FAIL ({len(errors)} lỗi)")


# ---------------------------------------------------------------- commands

def cmd_init(a):
    batch_dir = Path(a.batch_dir)
    batch_dir.mkdir(parents=True, exist_ok=True)
    manifest = batch_dir / "manifest.json"
    if not manifest.exists():
        write_json(manifest, {"batch_id": batch_dir.name.removeprefix("bugfix-batch-"),
                              "base_commit": a.base_commit, "base_branch": a.base_branch,
                              "source": a.source, "created": now(), "status": "open"})
    state = batch_dir / "state.json"
    if not state.exists():
        write_json(state, {"max_lanes": a.max_lanes, "issues": {}, "groups": {}, "lanes": {},
                           "devices": {}, "device_jobs": {}})
    print(f"batch ready: {batch_dir}")


def _validate_args(a, plan):
    bugs = read_json(Path(a.bugs)) if a.bugs else None
    repo = Path(a.repo) if a.repo else None
    errors, warnings = validate_plan(plan, bugs, repo)
    print_findings(errors, warnings)
    return errors


def cmd_check_plan(a):
    sys.exit(1 if _validate_args(a, read_json(Path(a.plan))) else 0)


def cmd_load_plan(a):
    plan = read_json(Path(a.plan))
    if _validate_args(a, plan):
        sys.exit(1)
    with locked(Path(a.batch_dir)) as state:
        busy = [l for l, v in state["lanes"].items() if l not in plan["lanes"] and v.get("status") != "planned"]
        if busy:
            die(f"lane đã chạy nhưng bị bỏ khỏi plan: {', '.join(busy)} — dừng/huỷ lane trước", 1)
        for lane_id in [l for l in state["lanes"] if l not in plan["lanes"]]:
            del state["lanes"][lane_id]
        for key in [k for k in state["issues"] if k not in plan["issues"]]:
            del state["issues"][key]
        for key, issue in plan["issues"].items():
            old = state["issues"].get(key, {})
            merged = {**issue, **{k: old[k] for k in ("status", "pr", "note", "fix_commit") if k in old}}
            merged.setdefault("status", "excluded" if issue["kind"] in KINDS_EXCLUDED else "planned")
            if issue.get("group"):
                merged["lane"] = next(l for l, v in plan["lanes"].items() if issue["group"] in v["groups"])
            state["issues"][key] = merged
        state["groups"] = plan["groups"]
        for lane_id, lane in plan["lanes"].items():
            old = state["lanes"].get(lane_id, {})
            files = sorted(set().union(*[group_files(plan["groups"][g]) for g in lane["groups"]]))
            # Chỉ giữ field runtime của lane cũ; field plan (after, groups, slug) lấy từ plan mới.
            runtime = {k: old[k] for k in ("status", "branch", "worktree", "agent", "pr", "note", "updated") if k in old}
            state["lanes"][lane_id] = {**runtime, **lane, "files": files, "status": old.get("status", "planned")}
    print("plan loaded")


def cmd_next_lanes(a):
    with locked(Path(a.batch_dir), write=False) as state:
        lanes = state["lanes"]
        running = sum(1 for l in lanes.values() if l.get("status") in LANE_RUNNING)
        free = max(0, int(state.get("max_lanes", 3)) - running)
        ready = [lid for lid, l in sorted(lanes.items(), key=lambda kv: natural_key(kv[0]))
                 if l.get("status") == "planned"
                 and all(lanes.get(d, {}).get("status") in LANE_UNBLOCKS for d in l.get("after", []))]
        for lid in ready[:free]:
            print(lid)
        if ready and not free:
            print(f"# {len(ready)} lane sẵn sàng nhưng đang chạy đủ {running}/{state.get('max_lanes', 3)}",
                  file=sys.stderr)


def _apply(target: dict, pairs, allowed_status, label):
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            die(f"{label}: '{pair}' phải có dạng key=value")
        if key == "status" and value not in allowed_status:
            die(f"{label}: status '{value}' không hợp lệ ({', '.join(sorted(allowed_status))})")
        target[key] = value
    target["updated"] = now()


def cmd_lane(a):
    with locked(Path(a.batch_dir)) as state:
        lane = state["lanes"].get(a.lane) or die(f"không có lane {a.lane}")
        _apply(lane, a.pairs, LANE_STATUSES, f"lane {a.lane}")
    print("ok")


def cmd_issue(a):
    with locked(Path(a.batch_dir)) as state:
        issue = state["issues"].get(a.key) or die(f"không có issue {a.key}")
        _apply(issue, a.pairs, ISSUE_STATUSES, f"issue {a.key}")
    print("ok")


def cmd_device_sync(a):
    with locked(Path(a.batch_dir)) as state:
        devices = state["devices"]
        for serial in a.serials:
            devices.setdefault(serial, {"holder": None, "since": None})
        for serial in list(devices):
            if serial not in a.serials and not devices[serial]["holder"]:
                del devices[serial]
    print(f"devices: {', '.join(a.serials) or '-'}")


def cmd_device_request(a):
    with locked(Path(a.batch_dir)) as state:
        if a.key not in state["issues"]:
            die(f"không có issue {a.key}")
        for job_id, job in state["device_jobs"].items():
            if (job["issue"] == a.key and job.get("purpose", "verify") == a.purpose
                    and job["status"] in {"pending", "running"}):
                print(job_id)
                return
        job_id = f"DJ-{len(state['device_jobs']) + 1:03d}"
        state["device_jobs"][job_id] = {"issue": a.key, "lane": a.lane, "purpose": a.purpose,
                                        "status": "pending", "serial": None, "created": now()}
        if a.purpose == "verify":
            state["issues"][a.key]["status"] = "pending_device"
    print(job_id)


def cmd_device_dispatch(a):
    with locked(Path(a.batch_dir)) as state:
        devices, jobs = state["devices"], state["device_jobs"]
        for serial, dev in devices.items():
            if dev["holder"] and time.time() - (dev["since"] or 0) > DEVICE_STALE_SECONDS:
                print(f"# {serial} giữ bởi {dev['holder']} quá {DEVICE_STALE_SECONDS // 60} phút "
                      f"— kiểm tra agent rồi dùng device-release nếu treo", file=sys.stderr)
        free = [s for s, d in sorted(devices.items()) if not d["holder"] and s not in (a.exclude or [])]
        pending = sorted((j for j in jobs.items() if j[1]["status"] == "pending"
                          and (not a.job or j[0] in a.job)), key=lambda j: j[1]["created"])
        dispatched = 0
        for job_id, job in pending:
            if not free:
                break
            serial = free.pop(0)
            devices[serial] = {"holder": job_id, "since": time.time()}
            job.update(status="running", serial=serial, started=now())
            purpose = job.get("purpose", "verify")
            if purpose == "verify":
                state["issues"][job["issue"]]["status"] = "verifying_device"
            print(f"{job_id} {serial} {job['issue']} {purpose}")
            dispatched += 1
        waiting = sum(1 for j in jobs.values() if j["status"] == "pending")
    if waiting and not dispatched:
        print(f"# {waiting} job chờ thiết bị", file=sys.stderr)
        sys.exit(3)


def cmd_device_done(a):
    with locked(Path(a.batch_dir)) as state:
        job = state["device_jobs"].get(a.job) or die(f"không có job {a.job}")
        if job.get("serial") and state["devices"].get(job["serial"], {}).get("holder") == a.job:
            state["devices"][job["serial"]] = {"holder": None, "since": None}
        job.update(status="done" if a.result == "pass" else "failed", finished=now(), result=a.result)
        if job.get("purpose", "verify") == "verify":
            state["issues"][job["issue"]]["status"] = "verified" if a.result == "pass" else "failed"
    print("ok")


def cmd_device_release(a):
    with locked(Path(a.batch_dir)) as state:
        dev = state["devices"].get(a.serial) or die(f"không có device {a.serial}")
        holder = dev["holder"]
        state["devices"][a.serial] = {"holder": None, "since": None}
        if holder and holder in state["device_jobs"]:
            job = state["device_jobs"][holder]
            job.update(status="pending", serial=None)
            if job.get("purpose", "verify") == "verify":
                state["issues"][job["issue"]]["status"] = "pending_device"
    print(f"released {a.serial}")


def cmd_board(a):
    batch_dir = Path(a.batch_dir)
    manifest = read_json(batch_dir / "manifest.json")
    with locked(batch_dir, write=False) as state:
        print(f"## Batch {manifest.get('batch_id')} — base `{manifest.get('base_branch')}` @ "
              f"`{str(manifest.get('base_commit'))[:9]}`\n")
        print("| Lane | Status | Issues | PR | After |\n|---|---|---|---|---|")
        for lid, lane in sorted(state["lanes"].items(), key=lambda kv: natural_key(kv[0])):
            keys = [k for g in lane.get("groups", []) for k in state["groups"].get(g, {}).get("issues", [])]
            print(f"| {lid} | {lane.get('status')} | {', '.join(keys)} | {lane.get('pr', '-')} | "
                  f"{', '.join(lane.get('after', [])) or '-'} |")
        print("\n| Issue | Kind | Verify | Lane | Status |\n|---|---|---|---|---|")
        for key, issue in sorted(state["issues"].items(), key=lambda kv: natural_key(kv[0])):
            print(f"| {key} | {issue.get('kind')} | {issue.get('verify', '-')} | {issue.get('lane', '-')} | "
                  f"{issue.get('status')} |")
        pending = [k for k, i in sorted(state["issues"].items(), key=lambda kv: natural_key(kv[0]))
                   if i.get("kind") == "needs-confirm"]
        if pending:
            print(f"\nChờ xác nhận (không chặn lane): {', '.join(pending)} — xem confirm-checklist.md")
        jobs = state["device_jobs"]
        if jobs or state["devices"]:
            print("\n| Device job | Issue | Purpose | Status | Serial |\n|---|---|---|---|---|")
            for jid, job in sorted(jobs.items()):
                print(f"| {jid} | {job['issue']} | {job.get('purpose', 'verify')} | {job['status']} | "
                      f"{job.get('serial') or '-'} |")
            busy = ", ".join("%s=%s" % (s, d["holder"] or "rảnh") for s, d in state["devices"].items())
            print("\nThiết bị: " + (busy or "không có"))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init"); s.add_argument("batch_dir"); s.add_argument("--base-commit", required=True)
    s.add_argument("--base-branch", required=True); s.add_argument("--source", required=True)
    s.add_argument("--max-lanes", type=int, default=3); s.set_defaults(fn=cmd_init)
    s = sub.add_parser("check-plan"); s.add_argument("plan")
    s.add_argument("--bugs"); s.add_argument("--repo"); s.set_defaults(fn=cmd_check_plan)
    s = sub.add_parser("load-plan"); s.add_argument("batch_dir"); s.add_argument("plan")
    s.add_argument("--bugs"); s.add_argument("--repo"); s.set_defaults(fn=cmd_load_plan)
    s = sub.add_parser("next-lanes"); s.add_argument("batch_dir"); s.set_defaults(fn=cmd_next_lanes)
    s = sub.add_parser("lane"); s.add_argument("batch_dir"); s.add_argument("lane"); s.add_argument("pairs", nargs="+")
    s.set_defaults(fn=cmd_lane)
    s = sub.add_parser("issue"); s.add_argument("batch_dir"); s.add_argument("key"); s.add_argument("pairs", nargs="+")
    s.set_defaults(fn=cmd_issue)
    s = sub.add_parser("device-sync"); s.add_argument("batch_dir"); s.add_argument("serials", nargs="*")
    s.set_defaults(fn=cmd_device_sync)
    s = sub.add_parser("device-request"); s.add_argument("batch_dir"); s.add_argument("key")
    s.add_argument("--lane", required=True); s.add_argument("--purpose", choices=["verify", "repro"], default="verify")
    s.set_defaults(fn=cmd_device_request)
    s = sub.add_parser("device-dispatch"); s.add_argument("batch_dir"); s.add_argument("--exclude", nargs="*")
    s.add_argument("--job", nargs="*", help="chỉ dispatch các job này (vd job verify của lane đã review xong)")
    s.set_defaults(fn=cmd_device_dispatch)
    s = sub.add_parser("device-done"); s.add_argument("batch_dir"); s.add_argument("job")
    s.add_argument("--result", choices=["pass", "fail"], required=True); s.set_defaults(fn=cmd_device_done)
    s = sub.add_parser("device-release"); s.add_argument("batch_dir"); s.add_argument("serial")
    s.set_defaults(fn=cmd_device_release)
    s = sub.add_parser("board"); s.add_argument("batch_dir"); s.set_defaults(fn=cmd_board)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
