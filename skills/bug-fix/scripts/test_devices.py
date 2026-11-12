#!/usr/bin/env python3
"""Unit test cho devices.py và khoá thiết bị liên mode (note bug_queue.py <-> batch bfo_state.py).
Chạy: python3 -m unittest test_devices.py (từ thư mục scripts)."""

import io
import json
import os
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import bfo_state  # noqa: E402
import bug_queue  # noqa: E402
import devices  # noqa: E402


def q(*argv):
    out = io.StringIO()
    code = 0
    with redirect_stdout(out):
        try:
            bug_queue.COMMANDS[argv[0]](list(argv[1:]))
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue()


def bfo(*argv):
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with redirect_stdout(out), redirect_stderr(err):
        try:
            bfo_state.main(list(argv))
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 2
    return code, out.getvalue(), err.getvalue()


class SharedStateCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.dict(os.environ, {"BUG_FIX_STATE_DIR": str(Path(self.tmp.name) / "bug-fix")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)


class DevicesModuleTest(SharedStateCase):
    def test_acquire_is_exclusive_and_idempotent_for_same_holder(self):
        self.assertEqual(devices.acquire("s1", "note:BUG-001"), (True, None, 0))
        self.assertTrue(devices.acquire("s1", "note:BUG-001")[0])
        ok, holder, _ = devices.acquire("s1", "batch:b1:DJ-001")
        self.assertFalse(ok)
        self.assertEqual(holder, "note:BUG-001")

    def test_release_only_by_holder(self):
        devices.acquire("s1", "note:BUG-001")
        self.assertFalse(devices.release("s1", "note:BUG-002"))
        self.assertEqual(devices.holder_of("s1"), "note:BUG-001")
        self.assertTrue(devices.release("s1", "note:BUG-001"))
        self.assertIsNone(devices.holder_of("s1"))

    def test_force_release_and_release_holder(self):
        devices.acquire("s1", "note:BUG-001")
        devices.acquire("s2", "note:BUG-001")
        devices.acquire("s3", "batch:b1:DJ-001")
        self.assertEqual(devices.release_holder("note:BUG-001"), ["s1", "s2"])
        self.assertEqual(devices.force_release("s3"), "batch:b1:DJ-001")
        self.assertIsNone(devices.force_release("s3"))
        self.assertEqual(devices.snapshot(), {})

    def test_dead_holder_is_taken_over_only_when_is_live_says_so(self):
        devices.acquire("s1", "note:BUG-001")
        self.assertFalse(devices.acquire("s1", "note:BUG-002", is_live=lambda h: True)[0])
        self.assertTrue(devices.acquire("s1", "note:BUG-002", is_live=lambda h: False)[0])
        self.assertEqual(devices.holder_of("s1"), "note:BUG-002")

    def test_state_file_is_valid_json_written_atomically(self):
        devices.acquire("s1", "note:BUG-001")
        directory = Path(os.environ["BUG_FIX_STATE_DIR"])
        data = json.loads((directory / "devices.json").read_text())
        self.assertEqual(data["s1"]["holder"], "note:BUG-001")
        self.assertFalse((directory / "devices.tmp").exists())

    def test_concurrent_acquire_has_exactly_one_winner(self):
        winners = []

        def grab(n):
            if devices.acquire("s1", f"note:BUG-{n:03d}")[0]:
                winners.append(n)

        threads = [threading.Thread(target=grab, args=(n,)) for n in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(winners), 1)
        self.assertEqual(devices.holder_of("s1"), f"note:BUG-{winners[0]:03d}")


class CrossModeLockTest(SharedStateCase):
    """note và batch chia sẻ một khoá: không bao giờ cùng giữ 1 serial."""

    def make_batch(self, serials):
        self.batch = str(Path(self.tmp.name) / "bugfix-batch-261112-1800-proj")
        bfo("init", self.batch, "--base-commit", "abc", "--base-branch", "main", "--source", "t")
        plan = {"issues": {"A-1": {"title": "a", "kind": "code", "verify": "device", "group": "g1", "reason": "r",
                                   "spec_verdict": "confirmed", "spec_ref": "Spec 1"}},
                "groups": {"g1": {"issues": ["A-1"], "files": ["a.kt"], "cause": "x", "new_files_ok": True}},
                "lanes": {"L1": {"groups": ["g1"]}}}
        plan_file = Path(self.tmp.name) / "plan.json"
        plan_file.write_text(json.dumps(plan))
        bfo("load-plan", self.batch, str(plan_file))
        bfo("device-sync", self.batch, *serials)
        apk = Path(self.tmp.name) / "app.apk"
        apk.write_text("apk")
        bfo("device-request", self.batch, "A-1", "--lane", "L1", "--apk", str(apk))

    def test_note_holds_x_so_batch_dispatch_never_grants_x(self):
        self.make_batch(["X"])
        bug = q("new", "crash khi mở app")[1].strip()
        self.assertEqual(q("device-lock", "X", bug)[0], 0)
        code, out, err = bfo("device-dispatch", self.batch)
        self.assertEqual((code, out), (3, ""))  # job sẵn sàng nhưng hết thiết bị
        self.assertIn(f"note:{bug}", err)
        self.assertEqual(devices.holder_of("X"), f"note:{bug}")

    def test_note_holds_x_batch_gets_other_serial(self):
        self.make_batch(["X", "Y"])
        bug = q("new", "crash")[1].strip()
        q("device-lock", "X", bug)
        code, out, _ = bfo("device-dispatch", self.batch)
        self.assertEqual(code, 0)
        self.assertIn("DJ-001 Y A-1 verify", out)

    def test_batch_holds_y_so_note_device_lock_y_is_refused(self):
        self.make_batch(["Y"])
        self.assertEqual(bfo("device-dispatch", self.batch)[0], 0)
        bug = q("new", "crash")[1].strip()
        code, out = q("device-lock", "Y", bug)
        self.assertEqual(code, 3)
        self.assertIn("batch:261112-1800-proj:DJ-001", out)
        info = json.loads(q("show", bug)[1])
        self.assertEqual((info["status"], info["blocked_by"]), ("waiting", "batch:261112-1800-proj:DJ-001"))

    def test_note_can_lock_after_batch_job_done(self):
        self.make_batch(["Y"])
        bfo("device-dispatch", self.batch)
        bug = q("new", "crash")[1].strip()
        self.assertEqual(q("device-lock", "Y", bug)[0], 3)
        bfo("device-done", self.batch, "DJ-001", "--result", "pass")
        self.assertEqual(q("device-lock", "Y", bug)[0], 0)
        self.assertEqual(json.loads(q("show", bug)[1])["status"], "investigating")

    def test_batch_can_dispatch_after_note_finishes(self):
        self.make_batch(["X"])
        bug = q("new", "crash")[1].strip()
        q("device-lock", "X", bug)
        self.assertEqual(bfo("device-dispatch", self.batch)[0], 3)
        q("set", bug, "status=pr_open")  # bug xong -> nhả khoá
        self.assertEqual(bfo("device-dispatch", self.batch)[0], 0)
        self.assertEqual(devices.holder_of("X"), "batch:261112-1800-proj:DJ-001")

    def test_batch_device_release_does_not_free_a_note_lock(self):
        self.make_batch(["X"])
        bug = q("new", "crash")[1].strip()
        q("device-lock", "X", bug)
        bfo("device-release", self.batch, "X")
        self.assertEqual(devices.holder_of("X"), f"note:{bug}")


if __name__ == "__main__":
    unittest.main()
