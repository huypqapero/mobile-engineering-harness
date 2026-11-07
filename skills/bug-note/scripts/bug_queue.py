#!/usr/bin/env python3
"""Bug queue shared by the bug-note orchestrator and its worker agents.

State lives in <git-common-dir>/bug-note/queue.json, so every worktree of the repo sees the
same queue and nothing is ever committed. Every command takes an exclusive file lock.

Commands (run from anywhere inside the repo or one of its worktrees):
  new "<title>"                      -> prints new id (BUG-001), status queued
  set <id> key=value [...]           -> update fields (status, branch, pr, base, worktree, note, blocked_by)
  claim <id> <file> [<file> ...]     -> record files the fix will touch; reports overlaps
  waiters <id>                       -> bugs waiting on <id>
  next-queued                        -> oldest queued bug id (empty if none)
  active-count                       -> number of bugs being worked on
  list | show <id>                   -> print state (json for show)
  device-lock <serial> <id>          -> take the device lock. Exit 3 if another unfinished bug holds it;
                                        the caller is then marked waiting with blocked_by = holder
  device-unlock <serial> <id>        -> release it (holder only)
  device-release <serial>            -> force-release a stuck lock (orchestrator, after checking the holder)
  sync-merged                        -> ask gh for every bug with a PR; MERGED -> status merged and
                                        its worktree removed (kept if it holds tracked changes)

Statuses: queued, investigating, waiting, fixing, pr_open, merged, failed, cancelled.
claim sets status fixing, or waiting + blocked_by. Exit codes: 0 no conflict, 3 must wait (overlap
with a bug still fixing), 4 stack (overlap only with bugs whose PR is open; prints stack_on=<branch>).
Waiting bugs never block, so two bugs cannot wait on each other.
"""

import fcntl
import json
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

UNFINISHED = {"queued", "investigating", "waiting", "fixing"}


def state_dir() -> Path:
    common = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    path = Path(common) / "bug-note"
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def locked_state():
    directory = state_dir()
    with open(directory / "queue.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        queue_file = directory / "queue.json"
        data = json.loads(queue_file.read_text()) if queue_file.exists() else {"seq": 0, "bugs": {}, "devices": {}}
        yield data
        tmp = queue_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        tmp.replace(queue_file)


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def require(data, bug_id):
    bug = data["bugs"].get(bug_id)
    if bug is None:
        sys.exit(f"unknown bug {bug_id}")
    return bug


def cmd_new(args):
    title = " ".join(args).strip() or sys.exit("title required")
    with locked_state() as data:
        data["seq"] += 1
        bug_id = f"BUG-{data['seq']:03d}"
        data["bugs"][bug_id] = {"id": bug_id, "title": title, "status": "queued", "files": [],
                                "created": now(), "updated": now()}
    print(bug_id)


def cmd_set(args):
    if len(args) < 2:
        sys.exit("usage: set <id> key=value ...")
    with locked_state() as data:
        bug = require(data, args[0])
        for pair in args[1:]:
            key, _, value = pair.partition("=")
            bug[key] = value
        bug["updated"] = now()
    print("ok")


def cmd_claim(args):
    if len(args) < 2:
        sys.exit("usage: claim <id> <file> ...")
    bug_id, files = args[0], sorted(set(args[1:]))
    with locked_state() as data:
        bug = require(data, bug_id)
        bug["files"] = files
        bug["updated"] = now()
        # First claim wins: only a bug already editing (fixing) blocks. Waiting bugs have not
        # edited anything, so they never block, which rules out two bugs waiting on each other.
        must_wait, stack = [], []
        for other in data["bugs"].values():
            if other["id"] == bug_id:
                continue
            overlap = sorted(set(files) & set(other.get("files", [])))
            if not overlap:
                continue
            if other["status"] == "fixing":
                must_wait.append((other, overlap))
            elif other["status"] == "pr_open":
                stack.append((other, overlap))
        if must_wait:
            bug["status"], bug["blocked_by"] = "waiting", must_wait[0][0]["id"]
            for other, overlap in must_wait:
                print(f"WAIT {other['id']} ({other['status']}) overlap: {', '.join(overlap)}")
            code = 3
        else:
            bug["status"] = "fixing"
            bug.pop("blocked_by", None)
            if stack:
                latest = max(stack, key=lambda item: item[0]["updated"])[0]
                for other, overlap in stack:
                    print(f"STACK {other['id']} pr={other.get('pr', '')} branch={other.get('branch', '')} "
                          f"overlap: {', '.join(overlap)}")
                print(f"stack_on={latest.get('branch', '')}")
                code = 4
            else:
                print("no conflict")
                code = 0
    sys.exit(code)


def cmd_waiters(args):
    with locked_state() as data:
        for bug in data["bugs"].values():
            if bug["status"] == "waiting" and bug.get("blocked_by") == args[0]:
                print(bug["id"], bug.get("agent", ""))


def cmd_next_queued(_):
    with locked_state() as data:
        queued = [b for b in data["bugs"].values() if b["status"] == "queued"]
        if queued:
            print(min(queued, key=lambda b: b["id"])["id"])


def cmd_active_count(_):
    with locked_state() as data:
        print(sum(1 for b in data["bugs"].values() if b["status"] in {"investigating", "fixing"}))


def cmd_list(_):
    with locked_state() as data:
        for bug in sorted(data["bugs"].values(), key=lambda b: b["id"]):
            extra = bug.get("pr") or bug.get("blocked_by") or ""
            print(f"{bug['id']}  {bug['status']:<13} {bug['title'][:60]}  {extra}")


def cmd_show(args):
    with locked_state() as data:
        print(json.dumps(require(data, args[0]), indent=2, ensure_ascii=False))


def cmd_device_lock(args):
    serial, bug_id = args
    busy = False
    with locked_state() as data:
        bug = require(data, bug_id)
        holder = data["devices"].get(serial)
        if holder and holder["bug"] != bug_id:
            holder_bug = data["bugs"].get(holder["bug"], {})
            # A lock is released only by its holder, by the holder finishing, or by device-release.
            # Age alone never frees it: a long repro must not be interrupted by a second worker.
            if holder_bug.get("status") in UNFINISHED:
                age = int(time.time() - holder["since"])
                bug["status"], bug["blocked_by"] = "waiting", holder["bug"]
                bug["updated"] = now()
                print(f"busy: {holder['bug']} for {age}s")
                busy = True  # exit after the with block so the waiting state is saved
        if not busy:
            data["devices"][serial] = {"bug": bug_id, "since": time.time()}
            # Device locks are taken before file claims (worker step 2 < step 4), so a waiting bug
            # that gets the lock was waiting for the device and is active again.
            if bug["status"] == "waiting":
                bug["status"] = "investigating"
                bug.pop("blocked_by", None)
                bug["updated"] = now()
    if busy:
        sys.exit(3)
    print("locked")


def cmd_device_unlock(args):
    serial, bug_id = args
    with locked_state() as data:
        if data["devices"].get(serial, {}).get("bug") == bug_id:
            del data["devices"][serial]
    print("unlocked")


def cmd_device_release(args):
    serial = args[0]
    with locked_state() as data:
        holder = data["devices"].pop(serial, None)
    print(f"released {serial}" + (f" (was {holder['bug']})" if holder else " (was free)"))


def remove_worktree(path: str) -> str:
    """Remove a finished bug's worktree. Untracked leftovers (build outputs) are discarded; tracked
    edits are never thrown away: the worktree is kept and reported instead."""
    if not path or not Path(path).exists():
        return "no worktree"
    dirty = subprocess.run(["git", "-C", path, "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        return f"kept {path} (tracked changes)"
    result = subprocess.run(["git", "worktree", "remove", "--force", path], capture_output=True, text=True)
    return f"removed {path}" if result.returncode == 0 else f"remove failed: {result.stderr.strip()}"


def cmd_sync_merged(_):
    # gh is slow: read under the lock, query outside it, write back under the lock.
    with locked_state() as data:
        candidates = [(b["id"], b.get("pr", ""), b.get("worktree", "")) for b in data["bugs"].values()
                      if b.get("pr") and b["status"] != "merged"]
    merged = []
    for bug_id, pr, worktree in candidates:
        view = subprocess.run(["gh", "pr", "view", pr, "--json", "state", "-q", ".state"],
                              capture_output=True, text=True)
        if view.returncode != 0:
            print(f"{bug_id}: gh failed: {view.stderr.strip()}")
            continue
        state = view.stdout.strip()
        if state == "MERGED":
            merged.append(bug_id)
            print(f"{bug_id}: MERGED, {remove_worktree(worktree)}")
        else:
            print(f"{bug_id}: {state}")
    with locked_state() as data:
        for bug_id in merged:
            data["bugs"][bug_id]["status"] = "merged"
            data["bugs"][bug_id]["updated"] = now()
    # Leftover worktrees of merged bugs from earlier runs (e.g. marked merged by hand).
    with locked_state() as data:
        leftovers = [(b["id"], b.get("worktree", "")) for b in data["bugs"].values()
                     if b["status"] == "merged" and b["id"] not in merged and b.get("worktree")
                     and Path(b["worktree"]).exists()]
    for bug_id, worktree in leftovers:
        print(f"{bug_id}: merged earlier, {remove_worktree(worktree)}")
    subprocess.run(["git", "worktree", "prune"], capture_output=True)


COMMANDS = {
    "new": cmd_new, "set": cmd_set, "claim": cmd_claim, "waiters": cmd_waiters,
    "next-queued": cmd_next_queued, "active-count": cmd_active_count, "list": cmd_list,
    "show": cmd_show, "device-lock": cmd_device_lock, "device-unlock": cmd_device_unlock,
    "device-release": cmd_device_release,
    "sync-merged": cmd_sync_merged,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
