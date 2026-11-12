#!/usr/bin/env python3
"""Khoá thiết bị dùng chung cho mode note (bug_queue.py) và mode batch (bfo_state.py).

State: <git-common-dir>/bug-fix/devices.json = {serial: {"holder": "...", "since": <epoch>}}, dùng chung
mọi worktree của repo, không bao giờ commit. Mọi thao tác lấy `fcntl` lock, ghi tạm rồi `os.replace`,
nên một serial không bao giờ có 2 holder dù note và batch chạy song song.

Holder: `note:<BUG-ID>` hoặc `batch:<batch-id>:<JOB>`.
Thư mục state: biến môi trường BUG_FIX_STATE_DIR (dùng cho test) hoặc `git rev-parse --git-common-dir` chạy ở
thư mục `start` (mặc định CWD) rồi nối `bug-fix`.

CLI (chỉ để xem / gỡ tay):
  devices.py list                 in serial -> holder + thời gian giữ
  devices.py release <serial>     gỡ khoá treo (sau khi đã kiểm tra holder)
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path


def state_dir(start=None) -> Path:
    override = os.environ.get("BUG_FIX_STATE_DIR")
    if override:
        path = Path(override)
    else:
        result = subprocess.run(
            ["git", "-C", str(start or "."), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            sys.exit(f"devices: không tìm thấy git repo từ {start or os.getcwd()}: {result.stderr.strip()}")
        path = Path(result.stdout.strip()) / "bug-fix"
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def _locked(start=None):
    directory = state_dir(start)
    with open(directory / "devices.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        device_file = directory / "devices.json"
        data = json.loads(device_file.read_text()) if device_file.exists() else {}
        before = json.dumps(data, sort_keys=True)
        yield data
        if json.dumps(data, sort_keys=True) != before:
            tmp = device_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            os.replace(tmp, device_file)


def acquire(serial: str, holder: str, is_live=None, start=None):
    """Giữ `serial` cho `holder`. Trả (True, None, 0) hoặc (False, holder_đang_giữ, giây_đã_giữ).

    Đã là holder → idempotent. `is_live(holder_khác)` trả False → khoá treo, lấy luôn. Tuổi của khoá không
    bao giờ tự giải phóng nó: repro dài không được bị worker khác ngắt."""
    with _locked(start) as data:
        current = data.get(serial)
        if current and current["holder"] != holder:
            if is_live is None or is_live(current["holder"]):
                return False, current["holder"], int(time.time() - current["since"])
        if not current or current["holder"] != holder:
            data[serial] = {"holder": holder, "since": time.time()}
    return True, None, 0


def release(serial: str, holder: str, start=None) -> bool:
    """Nhả `serial` nếu `holder` đang giữ. True nếu đã nhả."""
    with _locked(start) as data:
        if data.get(serial, {}).get("holder") == holder:
            del data[serial]
            return True
    return False


def force_release(serial: str, start=None):
    """Gỡ khoá bất kể holder. Trả holder cũ (None nếu đang rảnh)."""
    with _locked(start) as data:
        old = data.pop(serial, None)
    return old["holder"] if old else None


def release_holder(holder: str, start=None) -> list:
    """Nhả mọi serial `holder` đang giữ (vd bug note xong). Trả danh sách serial."""
    with _locked(start) as data:
        serials = sorted(s for s, d in data.items() if d["holder"] == holder)
        for serial in serials:
            del data[serial]
    return serials


def holder_of(serial: str, start=None):
    with _locked(start) as data:
        return data.get(serial, {}).get("holder")


def snapshot(start=None) -> dict:
    with _locked(start) as data:
        return {serial: dict(entry) for serial, entry in data.items()}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["list"] and len(argv) == 1:
        entries = snapshot()
        for serial, entry in sorted(entries.items()):
            print(f"{serial}  {entry['holder']}  {int(time.time() - entry['since'])}s")
        if not entries:
            print("không có khoá thiết bị nào")
    elif argv[:1] == ["release"] and len(argv) == 2:
        old = force_release(argv[1])
        print(f"released {argv[1]}" + (f" (was {old})" if old else " (was free)"))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
