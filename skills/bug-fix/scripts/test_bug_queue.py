#!/usr/bin/env python3
"""Unit test cho bug_queue.py (mode note). Chạy: python3 -m unittest test_bug_queue.py (từ thư mục scripts)."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
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


class QueueCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        patcher = mock.patch.dict(os.environ, {"BUG_FIX_STATE_DIR": str(self.root / "bug-fix")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def new(self, title="bug"):
        return q("new", title)[1].strip()

    def show(self, bug_id):
        return json.loads(q("show", bug_id)[1])


class BasicFlowTest(QueueCase):
    def test_new_ids_increase_and_start_queued(self):
        self.assertEqual(self.new("a"), "BUG-001")
        self.assertEqual(self.new("b"), "BUG-002")
        self.assertEqual(self.show("BUG-001")["status"], "queued")
        self.assertEqual(q("next-queued")[1].strip(), "BUG-001")
        self.assertIn("BUG-002", q("list")[1])

    def test_state_lives_in_bug_fix_dir_not_bug_note(self):
        self.new()
        self.assertTrue((self.root / "bug-fix" / "queue.json").is_file())
        self.assertFalse((self.root / "bug-note").exists())

    def test_set_and_active_count(self):
        a, b = self.new(), self.new()
        q("set", a, "status=investigating", "agent=w1")
        q("set", b, "status=fixing")
        self.assertEqual(q("active-count")[1].strip(), "2")
        self.assertEqual(self.show(a)["agent"], "w1")

    def test_unknown_bug_exits_with_message(self):
        self.assertNotEqual(q("show", "BUG-099")[0], 0)


class ClaimTest(QueueCase):
    def test_no_conflict_then_wait_then_stack(self):
        a, b, c = self.new(), self.new(), self.new()
        self.assertEqual(q("claim", a, "x.kt")[0], 0)
        self.assertEqual(self.show(a)["status"], "fixing")
        code, out = q("claim", b, "x.kt", "y.kt")
        self.assertEqual(code, 3)
        self.assertIn(f"WAIT {a}", out)
        info = self.show(b)
        self.assertEqual((info["status"], info["blocked_by"]), ("waiting", a))
        self.assertEqual(q("waiters", a)[1].split()[0], b)
        q("set", a, "status=pr_open", "pr=#1", "branch=fix/a")
        code, out = q("claim", c, "x.kt")
        self.assertEqual(code, 4)
        self.assertIn("stack_on=fix/a", out)

    def test_waiting_bug_does_not_block_others(self):
        a, b, c = self.new(), self.new(), self.new()
        q("claim", a, "x.kt")
        q("claim", b, "x.kt")  # waiting
        self.assertEqual(q("claim", c, "z.kt")[0], 0)


class DeviceLockTest(QueueCase):
    def test_lock_busy_waits_then_resumes_after_unlock(self):
        a, b = self.new(), self.new()
        self.assertEqual(q("device-lock", "s1", a), (0, "locked\n"))
        code, out = q("device-lock", "s1", b)
        self.assertEqual(code, 3)
        self.assertIn(f"busy: note:{a}", out)
        info = self.show(b)
        self.assertEqual((info["status"], info["blocked_by"]), ("waiting", a))
        self.assertEqual(q("waiters", a)[1].split()[0], b)
        q("device-unlock", "s1", a)
        self.assertEqual(q("device-lock", "s1", b)[0], 0)
        info = self.show(b)
        self.assertEqual(info["status"], "investigating")
        self.assertNotIn("blocked_by", info)

    def test_lock_goes_through_shared_devices_state(self):
        a = self.new()
        q("device-lock", "s1", a)
        self.assertEqual(devices.holder_of("s1"), f"note:{a}")
        self.assertIn("s1", q("device-list")[1])

    def test_unlock_by_non_holder_is_ignored_and_release_forces(self):
        a, b = self.new(), self.new()
        q("device-lock", "s1", a)
        q("device-unlock", "s1", b)
        self.assertEqual(devices.holder_of("s1"), f"note:{a}")
        self.assertIn(f"was note:{a}", q("device-release", "s1")[1])
        self.assertIsNone(devices.holder_of("s1"))

    def test_finishing_a_bug_releases_its_locks_so_stale_lock_never_blocks(self):
        a, b = self.new(), self.new()
        q("set", a, "status=investigating")
        q("device-lock", "s1", a)
        q("set", a, "status=failed")
        self.assertEqual(q("device-lock", "s1", b)[0], 0)

    def test_old_lock_age_never_frees_a_live_holder(self):
        a, b = self.new(), self.new()
        q("set", a, "status=investigating")
        q("device-lock", "s1", a)
        directory = self.root / "bug-fix"
        data = json.loads((directory / "devices.json").read_text())
        data["s1"]["since"] -= 10 * 3600
        (directory / "devices.json").write_text(json.dumps(data))
        self.assertEqual(q("device-lock", "s1", b)[0], 3)


class LegacyMigrationTest(QueueCase):
    def write_legacy(self):
        legacy = self.root / "bug-note"
        legacy.mkdir()
        old = {"seq": 2, "bugs": {
            "BUG-001": {"id": "BUG-001", "title": "cũ 1", "status": "investigating", "files": [],
                        "created": "t", "updated": "t"},
            "BUG-002": {"id": "BUG-002", "title": "cũ 2", "status": "pr_open", "files": [],
                        "created": "t", "updated": "t"}},
            "devices": {"s1": {"bug": "BUG-001", "since": 1.0}, "s2": {"bug": "BUG-002", "since": 1.0}}}
        (legacy / "queue.json").write_text(json.dumps(old))
        return legacy / "queue.json"

    def test_old_queue_is_read_once_and_left_untouched(self):
        legacy_file = self.write_legacy()
        before = legacy_file.read_text()
        self.assertIn("BUG-001", q("list")[1])
        self.assertEqual(self.new("mới"), "BUG-003")  # seq tiếp tục từ file cũ
        self.assertEqual(legacy_file.read_text(), before)
        new_state = json.loads((self.root / "bug-fix" / "queue.json").read_text())
        self.assertNotIn("devices", new_state)
        self.assertEqual(new_state["bugs"]["BUG-001"]["title"], "cũ 1")

    def test_old_device_lock_of_unfinished_bug_moves_to_shared_state(self):
        self.write_legacy()
        q("list")
        self.assertEqual(devices.holder_of("s1"), "note:BUG-001")
        self.assertIsNone(devices.holder_of("s2"))  # bug đã pr_open: khoá cũ là khoá treo

    def test_new_file_wins_over_legacy_once_it_exists(self):
        self.new("trước")
        self.write_legacy()
        self.assertEqual(self.new("sau"), "BUG-002")
        self.assertNotIn("cũ 1", q("list")[1])


if __name__ == "__main__":
    unittest.main()
