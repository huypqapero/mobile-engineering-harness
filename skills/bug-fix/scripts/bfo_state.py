#!/usr/bin/env python3
"""Batch state cho skill bug-fix (mode batch).

Một batch = thư mục plans/bugfix-batch-<id>/ trong repo app. File:
  manifest.json  batch_id, base_commit, base_branch, source, created, wave, issue_wave
  state.json     issues / groups / lanes / devices / device_jobs (leader + lane cùng đọc)
Mọi lệnh ghi đều lấy file lock riêng của batch, nên leader và nhiều lane gọi song song an toàn.
Khoá thiết bị đi qua devices.py (<git-common-dir>/bug-fix/devices.json), dùng chung với mode note
(bug_queue.py): `state.devices` chỉ là bản sao để hiển thị, nguồn sự thật là khoá chung, holder
`batch:<batch-id>:<JOB>`.
Định dạng state.json["issues"] (dict theo issue key) tương thích skills/bug/scripts/validate_evidence.py.

Lệnh (batch_dir luôn là tham số đầu, đường dẫn tuyệt đối):
  init <dir> --base-commit SHA --base-branch BR --source TEXT [--max-lanes 3]
  check-plan <plan.json> [--bugs bugs.json] [--repo WORKTREE] [--batch DIR]
                                    chỉ kiểm, không ghi (--bugs: mọi bug phải có mặt; --repo: file phải tồn tại;
                                    --batch: lane đã merge (status=done hoặc merged=base) không tính chồng file)
  load-plan <dir> <plan.json> [--bugs …] [--repo …]
                                    kiểm rồi nạp vào state (sau khi user duyệt); lane/issue không còn trong plan bị gỡ
  next-lanes <dir>                  in lane được phép chạy ngay (tôn trọng after + max_lanes)
  lane <dir> <LANE> k=v ...         cập nhật lane: status (planned|running|waiting|blocked|pr_open|done|failed|
                                    cancelled), branch, worktree, agent, pr, note, ready=yes|no (PR đã ready),
                                    merged=no|base|other (base = đã merge và head là tổ tiên base)
  lane-remove <dir> <LANE> [--plan plan.json] [--force]
                                    gỡ lane khỏi state (và khỏi plan.json nếu có --plan), dọn after trỏ vào nó;
                                    từ chối khi lane đang chạy / có device job running trừ khi --force
  issue <dir> <KEY> k=v ...         cập nhật issue (status, pr, note, fix_commit, jira=<trạng thái Jira hiện tại>)
  jira-sync <dir> [--all]           IN kế hoạch chuyển trạng thái Jira (hiện tại -> đích + lý do) từ state; không gọi Jira.
                                    Leader tự jira_get_transitions + jira_transition_issue rồi ghi lại `issue … jira=`
  device-sync <dir> <serial> ...    khai báo pool thiết bị (từ `adb devices`)
  device-request <dir> <KEY> --lane L [--purpose verify|repro] [--apk PATH] [--head SHA] [--priority N]
                                    xếp hàng 1 job thiết bị (idempotent theo issue + purpose; gọi lại để cập nhật
                                    apk/head/priority). repro = tái hiện + lấy logcat TRƯỚC khi fix (crash chưa có stack).
                                    apk/head = APK vừa build + commit head lúc build; priority lớn chạy trước
  device-dispatch <dir> [--exclude SERIAL ...] [--job JOB ...]
                                    gán job pending SẴN SÀNG (APK tồn tại, head khớp worktree lane) cho thiết bị rảnh
                                    (rảnh = cả trong batch lẫn khoá chung: máy note đang giữ không bao giờ được cấp);
                                    in "JOB SERIAL KEY PURPOSE" mỗi dòng, ưu tiên priority rồi thứ tự xếp hàng.
                                    exit 0 đã gán ≥1 · exit 3 còn job sẵn sàng nhưng hết thiết bị ·
                                    exit 4 chỉ còn job chưa sẵn sàng (thiếu APK / head lệch) · exit 0 không in gì = hết job
  device-done <dir> <JOB> --result pass|fail   trả thiết bị, ghi kết quả
  device-release <dir> <SERIAL>     nhả thiết bị bị giữ quá lâu (job quay về pending)
  import-ui-diff <dir> <summary.json | run dir> [--bugs bugs.json]
                                    mỗi mục fix_priority[] của report ui-diff -> 1 bug kind=ui verify=preview key
                                    `UI-<screen-slug>-<n>` (không Jira) ghi vào bugs.json (gộp với file có sẵn, chạy lại
                                    không đổi key), chép ảnh actual/design của màn vào <dir>/context/ui-diff/<screen-slug>/
  next-wave <dir> [--start]         liệt kê ticket cần đợt (wave) tiếp theo: chưa có evidence.json verdict PASS
                                    (thiếu / FAIL / NEEDS_VERIFICATION) và ticket needs-confirm đã có `answer`.
                                    --start: tăng manifest.wave và ghi wave mới cho các ticket đó
  board <dir>                       bảng trạng thái Markdown (kèm cột wave + verdict)

Exit code chung: 0 ok · 1 plan/state không hợp lệ · 2 dùng sai · 3 phải chờ · 4 job chưa sẵn sàng.

Issue key: Jira (`PROJ-123`), việc không có Jira `TASK-<slug>` (slug chữ thường, có ít nhất 1 chữ cái), hoặc
finding ui-diff `UI-<screen-slug>-<n>`; key TASK-/UI- vào state với tracker=none và bị `jira-sync` bỏ qua.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from contextlib import contextmanager
from pathlib import Path

import devices as device_locks

KINDS_FIXABLE = {"code", "ui", "content"}
KINDS_EXCLUDED = {"spec-gap", "needs-info", "needs-confirm", "duplicate", "not-a-bug", "external",
                  "already-fixed", "conflict"}
# Bug chỉ được fix khi đã so 1-1 với spec/Figma và chắc chắn lệch (spec_verdict=confirmed + spec_ref).
# Nghi ngờ (tester hiểu nhầm, spec im lặng, spec mâu thuẫn) → needs-confirm + câu hỏi, không chặn bug khác.
SPEC_VERDICTS = {"confirmed"}
VERIFY_TIERS = {"none", "unit", "preview", "device"}
ISSUE_STATUSES = {"planned", "fixing", "fixed", "pending_device", "verifying_device", "verified",
                  "pr_open", "done", "blocked", "failed", "excluded"}
LANE_STATUSES = {"planned", "running", "waiting", "blocked", "pr_open", "done", "failed", "cancelled"}
LANE_FIELD_VALUES = {"ready": {"yes", "no"}, "merged": {"no", "base", "other"}}
LANE_RUNTIME_FIELDS = ("status", "branch", "worktree", "agent", "pr", "note", "updated", "ready", "merged")
ISSUE_RUNTIME_FIELDS = ("status", "pr", "note", "fix_commit", "jira", "answer")
JIRA_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*-\d+$")
TASK_KEY_RE = re.compile(r"^TASK-(?=[a-z0-9-]*[a-z])[a-z0-9]+(?:-[a-z0-9]+)*$")
UI_KEY_RE = re.compile(r"^UI-[a-z0-9]+(?:-[a-z0-9]+)*-\d+$")
LANE_UNBLOCKS = {"pr_open", "done"}
LANE_RUNNING = {"running"}
MAX_ISSUES_PER_LANE = 8
DEVICE_STALE_SECONDS = 45 * 60


def natural_key(text: str):
    """L2 < L10, PROJ-2 < PROJ-10."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(text))]


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def is_task_key(key: str) -> bool:
    """Việc không có Jira: TASK-<slug>."""
    return bool(TASK_KEY_RE.match(str(key)))


def is_ui_key(key: str) -> bool:
    """Finding từ report ui-diff: UI-<screen-slug>-<n>."""
    return bool(UI_KEY_RE.match(str(key)))


def is_untracked_key(key: str) -> bool:
    """Key không có Jira: bị bỏ qua khi jira-sync, không bao giờ transition."""
    return is_task_key(key) or is_ui_key(key)


def lane_is_merged(lane: dict) -> bool:
    """Lane đã xong hẳn trong base: status=done hoặc PR merged vào base."""
    return lane.get("status") == "done" or lane.get("merged") == "base"


def git_head(worktree: str):
    try:
        out = subprocess.run(["git", "-C", worktree, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def batch_id_of(batch_dir: Path) -> str:
    return batch_dir.name.removeprefix("bugfix-batch-")


def device_holder(batch_dir: Path, job_id: str) -> str:
    """Holder trong khoá thiết bị chung (devices.py)."""
    return f"batch:{batch_id_of(batch_dir)}:{job_id}"


def evidence_verdict(batch_dir: Path, key: str):
    """verdict trong evidence/<KEY>/evidence.json: PASS|FAIL|NEEDS_VERIFICATION, None nếu thiếu, 'INVALID' nếu hỏng."""
    path = batch_dir / "evidence" / key / "evidence.json"
    if not path.is_file():
        return None
    try:
        verdict = json.loads(path.read_text(encoding="utf-8")).get("verdict")
    except (OSError, ValueError, AttributeError):
        return "INVALID"
    return verdict if isinstance(verdict, str) and verdict else "INVALID"


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


def validate_plan(plan: dict, bugs: dict = None, repo: Path = None, merged_lanes=frozenset()) -> tuple:
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
        if not (JIRA_KEY_RE.match(key) or is_untracked_key(key)):
            errors.append(f"{key}: key không hợp lệ (Jira PROJ-123, việc không Jira TASK-<slug> "
                          f"(slug chữ thường có ≥1 chữ cái) hoặc finding ui-diff UI-<screen-slug>-<n>)")
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
                if a in merged_lanes or b in merged_lanes:
                    continue  # lane đã merge vào base: lane sau tách từ base đã chứa thay đổi đó
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
                              "source": a.source, "created": now(), "status": "open",
                              "wave": 1, "issue_wave": {}})
    state = batch_dir / "state.json"
    if not state.exists():
        write_json(state, {"max_lanes": a.max_lanes, "issues": {}, "groups": {}, "lanes": {},
                           "devices": {}, "device_jobs": {}})
    print(f"batch ready: {batch_dir}")


def _merged_lanes(batch_dir) -> set:
    state_file = Path(batch_dir) / "state.json"
    if not state_file.exists():
        return set()
    return {lid for lid, lane in read_json(state_file).get("lanes", {}).items() if lane_is_merged(lane)}


def _validate_args(a, plan):
    bugs = read_json(Path(a.bugs)) if a.bugs else None
    repo = Path(a.repo) if a.repo else None
    batch_dir = getattr(a, "batch", None) or getattr(a, "batch_dir", None)
    errors, warnings = validate_plan(plan, bugs, repo, _merged_lanes(batch_dir) if batch_dir else frozenset())
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
            merged = {**issue, **{k: old[k] for k in ISSUE_RUNTIME_FIELDS if k in old}}
            merged.setdefault("status", "excluded" if issue["kind"] in KINDS_EXCLUDED else "planned")
            if is_untracked_key(key):
                merged["tracker"] = "none"
            if issue.get("group"):
                merged["lane"] = next(l for l, v in plan["lanes"].items() if issue["group"] in v["groups"])
            state["issues"][key] = merged
        state["groups"] = plan["groups"]
        for lane_id, lane in plan["lanes"].items():
            old = state["lanes"].get(lane_id, {})
            files = sorted(set().union(*[group_files(plan["groups"][g]) for g in lane["groups"]]))
            # Chỉ giữ field runtime của lane cũ; field plan (after, groups, slug) lấy từ plan mới.
            runtime = {k: old[k] for k in LANE_RUNTIME_FIELDS if k in old}
            state["lanes"][lane_id] = {**runtime, **lane, "files": files, "status": old.get("status", "planned")}
    stamp_wave(Path(a.batch_dir), plan["issues"])
    print("plan loaded")


def stamp_wave(batch_dir: Path, keys, restamp: bool = False, wave=None) -> int:
    """Ghi manifest.issue_wave[KEY] = wave hiện tại cho ticket chưa có wave (restamp=True: ghi đè)."""
    manifest_file = batch_dir / "manifest.json"
    manifest = read_json(manifest_file)
    wave = wave or int(manifest.get("wave", 1))
    issue_wave = manifest.setdefault("issue_wave", {})
    for key in keys:
        if restamp or key not in issue_wave:
            issue_wave[key] = wave
    manifest["wave"] = wave
    write_json(manifest_file, manifest)
    return wave


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


def _apply(target: dict, pairs, allowed_status, label, field_values=None):
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            die(f"{label}: '{pair}' phải có dạng key=value")
        if key == "status" and value not in allowed_status:
            die(f"{label}: status '{value}' không hợp lệ ({', '.join(sorted(allowed_status))})")
        if field_values and key in field_values and value not in field_values[key]:
            die(f"{label}: {key} '{value}' không hợp lệ ({', '.join(sorted(field_values[key]))})")
        target[key] = value
    target["updated"] = now()


def cmd_lane(a):
    with locked(Path(a.batch_dir)) as state:
        lane = state["lanes"].get(a.lane) or die(f"không có lane {a.lane}")
        _apply(lane, a.pairs, LANE_STATUSES, f"lane {a.lane}", LANE_FIELD_VALUES)
    print("ok")


def cmd_lane_remove(a):
    with locked(Path(a.batch_dir)) as state:
        lane = state["lanes"].get(a.lane) or die(f"không có lane {a.lane}")
        running_jobs = [j for j, job in state["device_jobs"].items()
                        if job.get("lane") == a.lane and job["status"] == "running"]
        if not a.force and (lane.get("status") in LANE_RUNNING or running_jobs):
            die(f"lane {a.lane} đang chạy" + (f" / device job {', '.join(running_jobs)} đang chạy" if running_jobs else "")
                + " — dừng agent/job trước hoặc dùng --force", 1)
        dropped = [j for j, job in state["device_jobs"].items() if job.get("lane") == a.lane and job["status"] == "pending"]
        for job_id in dropped:
            del state["device_jobs"][job_id]
        del state["lanes"][a.lane]
        for other in state["lanes"].values():
            if a.lane in other.get("after", []):
                other["after"] = [d for d in other["after"] if d != a.lane]
                if not other["after"]:
                    del other["after"]
        orphan_groups = [g for g in lane.get("groups", []) if g in state["groups"]]
        orphan_issues = sorted((k for k, i in state["issues"].items() if i.get("lane") == a.lane), key=natural_key)
        for key in orphan_issues:
            del state["issues"][key]["lane"]
    if a.plan:
        plan_path = Path(a.plan)
        plan = read_json(plan_path)
        plan.get("lanes", {}).pop(a.lane, None)
        for other in plan.get("lanes", {}).values():
            if a.lane in other.get("after", []):
                other["after"] = [d for d in other["after"] if d != a.lane]
                if not other["after"]:
                    del other["after"]
        write_json(plan_path, plan)
    print(f"removed lane {a.lane}")
    if dropped:
        print(f"# bỏ device job pending: {', '.join(dropped)}")
    if orphan_groups:
        print(f"# group chưa thuộc lane nào: {', '.join(orphan_groups)} (issue: {', '.join(orphan_issues) or '-'}) "
              f"— gán vào lane khác trong plan.json rồi load-plan, hoặc loại issue", file=sys.stderr)


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
        extra = {k: v for k, v in (("apk", a.apk), ("head", a.head), ("priority", a.priority)) if v is not None}
        for job_id, job in state["device_jobs"].items():
            if (job["issue"] == a.key and job.get("purpose", "verify") == a.purpose
                    and job["status"] in {"pending", "running"}):
                job.update(extra)  # gọi lại để cập nhật apk/head/priority (vd sau khi build lại)
                print(job_id)
                return
        job_id = f"DJ-{len(state['device_jobs']) + 1:03d}"
        state["device_jobs"][job_id] = {"issue": a.key, "lane": a.lane, "purpose": a.purpose,
                                        "status": "pending", "serial": None, "created": now(), "priority": 0, **extra}
        if a.purpose == "verify":
            state["issues"][a.key]["status"] = "pending_device"
    print(job_id)


def job_not_ready(state: dict, job: dict):
    """Lý do job chưa giao được (None = sẵn sàng): phải có APK tồn tại và, với verify, APK build đúng head lane."""
    apk = job.get("apk")
    if not apk:
        return "chưa có APK (build rồi device-request --apk … --head …)"
    if not Path(apk).is_file():
        return f"APK không tồn tại: {apk}"
    worktree = state["lanes"].get(job.get("lane"), {}).get("worktree")
    if job.get("purpose", "verify") == "verify" and job.get("head") and worktree and Path(worktree).is_dir():
        current = git_head(worktree)
        head = job["head"]
        if current and not (current.startswith(head) or head.startswith(current)):
            return f"APK build ở {head[:9]} nhưng lane đã ở {current[:9]} — build lại + device-request --apk --head"
    return None


def cmd_device_dispatch(a):
    with locked(Path(a.batch_dir)) as state:
        devices, jobs = state["devices"], state["device_jobs"]
        batch_dir = Path(a.batch_dir)
        for serial, dev in devices.items():
            if dev["holder"] and time.time() - (dev["since"] or 0) > DEVICE_STALE_SECONDS:
                print(f"# {serial} giữ bởi {dev['holder']} quá {DEVICE_STALE_SECONDS // 60} phút "
                      f"— kiểm tra agent rồi dùng device-release nếu treo", file=sys.stderr)
        free = [s for s, d in sorted(devices.items()) if not d["holder"] and s not in (a.exclude or [])]
        pending = sorted((j for j in jobs.items() if j[1]["status"] == "pending"
                          and (not a.job or j[0] in a.job)),
                         key=lambda j: (-int(j[1].get("priority", 0)), j[1]["created"], natural_key(j[0])))
        dispatched, not_ready, ready_waiting = 0, 0, 0
        for job_id, job in pending:
            reason = job_not_ready(state, job)
            if reason:
                not_ready += 1
                print(f"# {job_id} ({job['issue']}) chưa sẵn sàng: {reason}", file=sys.stderr)
                continue
            serial = None
            while free and serial is None:
                candidate = free.pop(0)
                ok, other, _ = device_locks.acquire(candidate, device_holder(batch_dir, job_id), start=batch_dir)
                if ok:
                    serial = candidate
                else:
                    print(f"# {candidate} đang bị {other} giữ (ngoài batch) — bỏ qua", file=sys.stderr)
            if serial is None:
                ready_waiting += 1
                continue
            devices[serial] = {"holder": job_id, "since": time.time()}
            job.update(status="running", serial=serial, started=now())
            purpose = job.get("purpose", "verify")
            if purpose == "verify":
                state["issues"][job["issue"]]["status"] = "verifying_device"
            print(f"{job_id} {serial} {job['issue']} {purpose}")
            dispatched += 1
    if dispatched:
        return
    if ready_waiting:
        print(f"# {ready_waiting} job chờ thiết bị", file=sys.stderr)
        sys.exit(3)
    if not_ready:
        print(f"# {not_ready} job chưa sẵn sàng (xem lý do ở trên)", file=sys.stderr)
        sys.exit(4)


def cmd_device_done(a):
    with locked(Path(a.batch_dir)) as state:
        job = state["device_jobs"].get(a.job) or die(f"không có job {a.job}")
        if job.get("serial") and state["devices"].get(job["serial"], {}).get("holder") == a.job:
            state["devices"][job["serial"]] = {"holder": None, "since": None}
            device_locks.release(job["serial"], device_holder(Path(a.batch_dir), a.job), start=a.batch_dir)
        job.update(status="done" if a.result == "pass" else "failed", finished=now(), result=a.result)
        if job.get("purpose", "verify") == "verify":
            state["issues"][job["issue"]]["status"] = "verified" if a.result == "pass" else "failed"
    print("ok")


def cmd_device_release(a):
    with locked(Path(a.batch_dir)) as state:
        dev = state["devices"].get(a.serial) or die(f"không có device {a.serial}")
        holder = dev["holder"]
        state["devices"][a.serial] = {"holder": None, "since": None}
        if holder:
            device_locks.release(a.serial, device_holder(Path(a.batch_dir), holder), start=a.batch_dir)
        if holder and holder in state["device_jobs"]:
            job = state["device_jobs"][holder]
            job.update(status="pending", serial=None)
            if job.get("purpose", "verify") == "verify":
                state["issues"][job["issue"]]["status"] = "pending_device"
    print(f"released {a.serial}")


def slugify(text: str) -> str:
    """Screen -> slug chữ thường ASCII (bỏ dấu, đ->d); rỗng -> 'screen'."""
    folded = unicodedata.normalize("NFKD", str(text).replace("đ", "d").replace("Đ", "D"))
    ascii_text = "".join(c for c in folded if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-") or "screen"


def finding_fingerprint(fx: dict) -> str:
    return "|".join(str(fx.get(k) or "").strip() for k in ("screen", "region", "type", "actual", "expected"))


def cmd_import_ui_diff(a):
    source = Path(a.summary)
    summary_file = source / "summary.json" if source.is_dir() else source
    summary = read_json(summary_file)
    run_dir = summary_file.parent
    findings = summary.get("fix_priority")
    if not isinstance(findings, list):
        die(f"{summary_file}: thiếu mảng fix_priority", 1)
    batch_dir = Path(a.batch_dir)
    if not batch_dir.is_dir():
        die(f"batch dir không tồn tại: {batch_dir}")
    bugs_file = Path(a.bugs) if a.bugs else batch_dir / "bugs.json"
    bugs = read_json(bugs_file) if bugs_file.exists() else {}
    known = {b.get("fingerprint"): k for k, b in bugs.items() if b.get("fingerprint")}
    next_n: dict[str, int] = {}
    for key in bugs:
        match = re.match(r"^(UI-.+)-(\d+)$", key)
        if match:
            next_n[match.group(1)] = max(next_n.get(match.group(1), 0), int(match.group(2)))
    dir_of = {s.get("screen"): s.get("dir") for s in summary.get("screens", []) if s.get("screen")}
    imported, copied = [], set()
    for fx in findings:
        screen = fx.get("screen") or "screen"
        slug = slugify(screen)
        fingerprint = finding_fingerprint(fx)
        key = known.pop(fingerprint, None)  # pop: 2 finding y hệt nhau trong 1 run vẫn ra 2 key
        if key is None:
            next_n[f"UI-{slug}"] = next_n.get(f"UI-{slug}", 0) + 1
            key = f"UI-{slug}-{next_n[f'UI-{slug}']}"
        attachments = []
        src_dir = run_dir / "screens" / (dir_of.get(screen) or screen)
        for kind in ("actual", "design"):
            image = src_dir / f"{kind}.png"
            if not image.is_file():
                print(f"WARN  {key}: không có ảnh {image}", file=sys.stderr)
                continue
            target = batch_dir / "context" / "ui-diff" / slug / f"{kind}.png"
            if (slug, kind) not in copied:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(image, target)
                copied.add((slug, kind))
            attachments.append(f"context/ui-diff/{slug}/{kind}.png")
        severity = str(fx.get("severity") or "low")
        bugs[key] = {
            "title": f"[{screen}] {fx.get('region') or '?'} — {fx.get('type') or 'lệch UI'}",
            "priority": severity.capitalize(), "screen_hint": screen,
            "actual": fx.get("actual") or "", "expected": fx.get("expected") or "", "repro": "",
            "frequency": "Always", "attachments": attachments, "comments": [], "url": None,
            "source": "ui-diff", "source_run": str(run_dir), "region": fx.get("region"), "type": fx.get("type"),
            "source_hint": fx.get("source_hint"), "confidence": fx.get("confidence"),
            "kind_hint": "ui", "verify_hint": "preview", "spec_verdict_hint": "confirmed",
            "spec_ref_hint": f"ui-diff {run_dir.name}: {screen} / {fx.get('region') or '?'} (design.png của màn)",
            "fingerprint": fingerprint,
        }
        imported.append((key, severity, screen, fx.get("region")))
    write_json(bugs_file, bugs)
    for key, severity, screen, region in imported:
        print(f"{key}  {severity}  {screen} / {region}")
    print(f"# imported {len(imported)} finding vào {bugs_file}", file=sys.stderr)


def wave_candidates(batch_dir: Path, state: dict) -> list:
    """[(KEY, lý do)] ticket cần đợt kế tiếp: bug sửa được chưa có evidence verdict PASS, và needs-confirm đã
    được trả lời (issue có `answer`). Ticket bị loại khác (spec-gap, needs-info, duplicate…) không vào."""
    rows = []
    for key, issue in sorted(state["issues"].items(), key=lambda kv: natural_key(kv[0])):
        kind = issue.get("kind")
        if kind == "needs-confirm":
            if issue.get("answer"):
                rows.append((key, f"needs-confirm đã trả lời: {issue['answer']}"))
            continue
        if kind not in KINDS_FIXABLE:
            continue
        verdict = evidence_verdict(batch_dir, key)
        lane = state["lanes"].get(issue.get("lane"), {})
        where = f" (lane {issue.get('lane')} {lane.get('status')}, issue {issue.get('status')})" if lane else ""
        if verdict == "PASS":
            continue
        if verdict is None:
            rows.append((key, "thiếu evidence.json" + where))
        elif verdict == "INVALID":
            rows.append((key, "evidence.json hỏng hoặc không có verdict" + where))
        else:
            rows.append((key, f"evidence verdict {verdict}" + where))
    return rows


def cmd_next_wave(a):
    batch_dir = Path(a.batch_dir)
    manifest = read_json(batch_dir / "manifest.json")
    with locked(batch_dir, write=False) as state:
        rows = wave_candidates(batch_dir, state)
    current = int(manifest.get("wave", 1))
    if not rows:
        print(f"# không còn ticket nào cần đợt mới (wave hiện tại {current})")
        return
    for key, reason in rows:
        print(f"{key}: {reason}")
    if a.start:
        stamp_wave(batch_dir, [k for k, _ in rows], restamp=True, wave=current + 1)
        print(f"# wave {current + 1} bắt đầu: {len(rows)} ticket", file=sys.stderr)
    else:
        print(f"# {len(rows)} ticket cho wave {current + 1} (thêm --start để ghi wave vào manifest)", file=sys.stderr)


JIRA_DONE_STATES = {"reviewing", "done", "closed"}


def jira_target(issue: dict, lane: dict):
    """(trạng thái đích | None, lý do, luôn in?) cho 1 issue, theo bảng Jira status của SKILL.md."""
    status, lane_status = issue.get("status"), lane.get("status")
    merged = lane.get("merged", "no")
    if status in {"blocked", "excluded"}:
        return None, "giữ nguyên (bug blocked/bị loại)", False
    if merged == "base":
        if status == "failed":
            return "In Progress", "device job FAIL sau khi PR đã merge: mở lane/PR mới từ base (Reopened nếu workflow có)", False
        return "Reviewing", "PR đã merge và head là tổ tiên base", False
    if merged == "other":
        return None, "PR merge vào branch ngoài base, code chưa vào base — đưa branch đó vào base trước", True
    if lane_status in {"failed", "cancelled", "planned", None}:
        return None, "giữ nguyên (lane chưa chạy/FAILED/huỷ)", False
    if lane.get("ready") == "yes" and status in {"verified", "pr_open", "done"}:
        return "Resolved", "reviewer APPROVE, PR ready, device job (nếu có) đã pass", False
    return "In Progress", f"lane {lane_status}, issue {status}", False


def cmd_jira_sync(a):
    with locked(Path(a.batch_dir), write=False) as state:
        rows = []
        for key, issue in sorted(state["issues"].items(), key=lambda kv: natural_key(kv[0])):
            if issue.get("tracker") == "none" or is_untracked_key(key) or issue.get("kind") in KINDS_EXCLUDED:
                continue
            lane_id = issue.get("lane")
            target, reason, always = jira_target(issue, state["lanes"].get(lane_id, {}))
            current = issue.get("jira", "?")
            if target is None:
                if a.all or always:
                    rows.append(f"{key}: giữ nguyên {current} ({reason})")
                continue
            if current.lower() == target.lower():
                if a.all:
                    rows.append(f"{key}: {current} (đã đúng — {reason})")
                continue
            if target == "Resolved" and current.lower() in JIRA_DONE_STATES:
                continue  # không lùi Reviewing/Done về Resolved
            via = " [qua Resolved trước, 2 bước]" if target == "Reviewing" and current.lower() == "in progress" else ""
            rows.append(f"{key}: {current} -> {target}{via} ({reason}; lane {lane_id})")
    print("# KẾ HOẠCH jira-sync — script không gọi Jira. Với mỗi dòng: jira_get_transitions -> jira_transition_issue ->\n"
          "# gán assignee -> `bfo issue <dir> <KEY> jira=<trạng thái mới>`. Hiện tại `?` = chưa ghi, đọc từ Jira trước.")
    print("\n".join(rows) if rows else "# không có chuyển trạng thái nào cần làm")


def cmd_board(a):
    batch_dir = Path(a.batch_dir)
    manifest = read_json(batch_dir / "manifest.json")
    with locked(batch_dir, write=False) as state:
        print(f"## Batch {manifest.get('batch_id')} — base `{manifest.get('base_branch')}` @ "
              f"`{str(manifest.get('base_commit'))[:9]}` — wave {manifest.get('wave', 1)}\n")
        print("| Lane | Status | Issues | PR | After |\n|---|---|---|---|---|")
        for lid, lane in sorted(state["lanes"].items(), key=lambda kv: natural_key(kv[0])):
            keys = [k for g in lane.get("groups", []) for k in state["groups"].get(g, {}).get("issues", [])]
            print(f"| {lid} | {lane.get('status')} | {', '.join(keys)} | {lane.get('pr', '-')} | "
                  f"{', '.join(lane.get('after', [])) or '-'} |")
        waves = manifest.get("issue_wave", {})
        print("\n| Issue | Kind | Verify | Lane | Status | Wave | Verdict |\n|---|---|---|---|---|---|---|")
        for key, issue in sorted(state["issues"].items(), key=lambda kv: natural_key(kv[0])):
            print(f"| {key} | {issue.get('kind')} | {issue.get('verify', '-')} | {issue.get('lane', '-')} | "
                  f"{issue.get('status')} | {waves.get(key, '-')} | {evidence_verdict(batch_dir, key) or '-'} |")
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
    s.add_argument("--bugs"); s.add_argument("--repo")
    s.add_argument("--batch", help="batch dir: lane đã merge trong state không tính chồng file")
    s.set_defaults(fn=cmd_check_plan)
    s = sub.add_parser("load-plan"); s.add_argument("batch_dir"); s.add_argument("plan")
    s.add_argument("--bugs"); s.add_argument("--repo"); s.set_defaults(fn=cmd_load_plan)
    s = sub.add_parser("next-lanes"); s.add_argument("batch_dir"); s.set_defaults(fn=cmd_next_lanes)
    s = sub.add_parser("lane"); s.add_argument("batch_dir"); s.add_argument("lane"); s.add_argument("pairs", nargs="+")
    s.set_defaults(fn=cmd_lane)
    s = sub.add_parser("lane-remove"); s.add_argument("batch_dir"); s.add_argument("lane")
    s.add_argument("--plan", help="plan.json: gỡ lane khỏi file này luôn"); s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_lane_remove)
    s = sub.add_parser("jira-sync"); s.add_argument("batch_dir")
    s.add_argument("--all", action="store_true", help="in cả issue đã đúng / giữ nguyên"); s.set_defaults(fn=cmd_jira_sync)
    s = sub.add_parser("issue"); s.add_argument("batch_dir"); s.add_argument("key"); s.add_argument("pairs", nargs="+")
    s.set_defaults(fn=cmd_issue)
    s = sub.add_parser("device-sync"); s.add_argument("batch_dir"); s.add_argument("serials", nargs="*")
    s.set_defaults(fn=cmd_device_sync)
    s = sub.add_parser("device-request"); s.add_argument("batch_dir"); s.add_argument("key")
    s.add_argument("--lane", required=True); s.add_argument("--purpose", choices=["verify", "repro"], default="verify")
    s.add_argument("--apk", help="đường dẫn APK vừa build"); s.add_argument("--head", help="commit head lúc build APK")
    s.add_argument("--priority", type=int, help="số lớn chạy trước (mặc định 0)")
    s.set_defaults(fn=cmd_device_request)
    s = sub.add_parser("device-dispatch"); s.add_argument("batch_dir"); s.add_argument("--exclude", nargs="*")
    s.add_argument("--job", nargs="*", help="chỉ dispatch các job này (vd job verify của lane đã review xong)")
    s.set_defaults(fn=cmd_device_dispatch)
    s = sub.add_parser("device-done"); s.add_argument("batch_dir"); s.add_argument("job")
    s.add_argument("--result", choices=["pass", "fail"], required=True); s.set_defaults(fn=cmd_device_done)
    s = sub.add_parser("device-release"); s.add_argument("batch_dir"); s.add_argument("serial")
    s.set_defaults(fn=cmd_device_release)
    s = sub.add_parser("import-ui-diff"); s.add_argument("batch_dir"); s.add_argument("summary")
    s.add_argument("--bugs", help="bugs.json đích (mặc định <batch>/bugs.json)"); s.set_defaults(fn=cmd_import_ui_diff)
    s = sub.add_parser("next-wave"); s.add_argument("batch_dir")
    s.add_argument("--start", action="store_true", help="tăng manifest.wave và ghi wave mới cho các ticket liệt kê")
    s.set_defaults(fn=cmd_next_wave)
    s = sub.add_parser("board"); s.add_argument("batch_dir"); s.set_defaults(fn=cmd_board)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
