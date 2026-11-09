#!/usr/bin/env python3
"""Unit test cho bfo_state.py. Chạy: python3 -m unittest test_bfo_state.py (từ thư mục scripts)."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bfo_state  # noqa: E402


def plan(**over):
    base = {
        "issues": {
            "A-1": {"title": "a", "kind": "ui", "verify": "preview", "group": "g1", "reason": "r",
                    "spec_verdict": "confirmed", "spec_ref": "Figma 1:2"},
            "A-2": {"title": "b", "kind": "code", "verify": "device", "group": "g2", "reason": "r",
                    "spec_verdict": "confirmed", "spec_ref": "Spec 3.5"},
            "A-3": {"title": "c", "kind": "spec-gap", "reason": "PO chưa chốt"},
        },
        "groups": {
            "g1": {"issues": ["A-1"], "files": ["ui/Home.kt"], "cause": "x"},
            "g2": {"issues": ["A-2"], "files": ["player/Vm.kt"], "cause": "y"},
        },
        "lanes": {"L1": {"groups": ["g1"]}, "L2": {"groups": ["g2"]}},
    }
    base.update(over)
    return base


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with redirect_stdout(out), redirect_stderr(err):
        try:
            bfo_state.main(list(argv))
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 2
    return code, out.getvalue(), err.getvalue()


class DispatchJobFilterTest(unittest.TestCase):
    def test_dispatch_only_selected_job(self):
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "batch"
            run("init", str(b), "--base-commit", "abc", "--base-branch", "main", "--source", "t")
            f = Path(d) / "plan.json"; f.write_text(json.dumps(plan()))
            run("load-plan", str(b), str(f))
            run("device-sync", str(b), "emu-1")
            run("device-request", str(b), "A-1", "--lane", "L1")
            run("device-request", str(b), "A-2", "--lane", "L2")
            code, out, _ = run("device-dispatch", str(b), "--job", "DJ-002")
            self.assertEqual(code, 0)
            self.assertIn("DJ-002", out)
            self.assertNotIn("DJ-001", out)


class ReloadPlanTest(unittest.TestCase):
    def test_reload_drops_stale_after(self):
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "batch"
            run("init", str(b), "--base-commit", "abc", "--base-branch", "main", "--source", "t")
            p1 = plan(); p1["lanes"]["L2"]["after"] = ["L1"]
            f = Path(d) / "plan.json"; f.write_text(json.dumps(p1))
            self.assertEqual(run("load-plan", str(b), str(f))[0], 0)
            p2 = plan(); f.write_text(json.dumps(p2))
            self.assertEqual(run("load-plan", str(b), str(f))[0], 0)
            state = json.loads((b / "state.json").read_text())
            self.assertNotIn("after", state["lanes"]["L2"])


class ValidatePlanTest(unittest.TestCase):
    def test_fixable_requires_confirmed_spec_verdict(self):
        p = plan()
        del p["issues"]["A-1"]["spec_verdict"]
        errors, _ = bfo_state.validate_plan(p)
        self.assertTrue(any("A-1" in e and "spec_verdict" in e for e in errors))

    def test_needs_confirm_requires_question_and_no_group(self):
        p = plan()
        p["issues"]["A-3"] = {"title": "c", "kind": "needs-confirm", "reason": "tester hiểu nhầm?"}
        errors, _ = bfo_state.validate_plan(p)
        self.assertTrue(any("A-3" in e and "question" in e for e in errors))
        p["issues"]["A-3"]["question"] = "Spec 3.2 không nói X — có cần fix?"
        errors, _ = bfo_state.validate_plan(p)
        self.assertEqual(errors, [])

    def test_valid_plan(self):
        errors, _ = bfo_state.validate_plan(plan())
        self.assertEqual(errors, [])

    def test_fixable_issue_needs_group_and_tier(self):
        p = plan()
        p["issues"]["A-1"].update(group=None, verify="maybe")
        errors, _ = bfo_state.validate_plan(p)
        self.assertTrue(any("verify" in e for e in errors))
        self.assertTrue(any("chưa thuộc group" in e for e in errors))

    def test_excluded_issue_needs_reason_and_no_group(self):
        p = plan()
        p["issues"]["A-3"] = {"title": "c", "kind": "needs-info", "group": "g1"}
        errors, _ = bfo_state.validate_plan(p)
        self.assertTrue(any("không được vào group" in e for e in errors))
        self.assertTrue(any("reason" in e for e in errors))

    def test_overlapping_lanes_need_order(self):
        p = plan()
        p["groups"]["g2"]["files"] = ["ui/Home.kt"]
        errors, _ = bfo_state.validate_plan(p)
        self.assertTrue(any("cùng sửa ui/Home.kt" in e for e in errors))
        p["lanes"]["L2"]["after"] = ["L1"]
        errors, _ = bfo_state.validate_plan(p)
        self.assertEqual(errors, [])

    def test_cycle_detected(self):
        p = plan()
        p["lanes"]["L1"]["after"] = ["L2"]
        p["lanes"]["L2"]["after"] = ["L1"]
        errors, _ = bfo_state.validate_plan(p)
        self.assertTrue(any("vòng lặp" in e for e in errors))

    def test_group_in_two_lanes(self):
        p = plan()
        p["lanes"]["L2"]["groups"] = ["g2", "g1"]
        errors, _ = bfo_state.validate_plan(p)
        self.assertTrue(any("nằm ở 2 lane" in e for e in errors))


class PlanCoverageTest(unittest.TestCase):
    def test_every_bug_must_be_classified(self):
        errors, _ = bfo_state.validate_plan(plan(), bugs={"A-1": {}, "A-2": {}, "A-3": {}, "A-9": {}})
        self.assertTrue(any("A-9" in e for e in errors))

    def test_files_must_exist_in_repo(self):
        with tempfile.TemporaryDirectory() as repo:
            (Path(repo) / "ui").mkdir()
            (Path(repo) / "ui/Home.kt").write_text("x")
            errors, _ = bfo_state.validate_plan(plan(), repo=Path(repo))
            self.assertTrue(any("player/Vm.kt" in e for e in errors))
            p = plan()
            p["groups"]["g2"]["new_files_ok"] = True
            errors, _ = bfo_state.validate_plan(p, repo=Path(repo))
            self.assertEqual(errors, [])

    def test_shared_files_count_as_overlap(self):
        p = plan()
        p["groups"]["g1"]["shared_files"] = ["res/values/strings.xml"]
        p["groups"]["g2"]["shared_files"] = ["res/values/strings.xml"]
        errors, _ = bfo_state.validate_plan(p)
        self.assertTrue(any("strings.xml" in e for e in errors))

    def test_new_excluded_kinds(self):
        p = plan()
        p["issues"]["A-3"] = {"title": "c", "kind": "already-fixed", "reason": "PR #36"}
        errors, _ = bfo_state.validate_plan(p)
        self.assertEqual(errors, [])

    def test_natural_sort(self):
        self.assertEqual(sorted(["L10", "L2", "L1"], key=bfo_state.natural_key), ["L1", "L2", "L10"])


class StateFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = str(Path(self.tmp.name) / "bugfix-batch-t1")
        run("init", self.dir, "--base-commit", "abc", "--base-branch", "main", "--source", "jql", "--max-lanes", "1")
        p = plan()
        p["lanes"]["L2"]["after"] = []
        plan_path = Path(self.tmp.name) / "plan.json"
        plan_path.write_text(json.dumps(p), encoding="utf-8")
        code, out, _ = run("load-plan", self.dir, str(plan_path))
        self.assertEqual(code, 0, out)

    def tearDown(self):
        self.tmp.cleanup()

    def state(self):
        return json.loads((Path(self.dir) / "state.json").read_text(encoding="utf-8"))

    def test_load_sets_lane_and_status(self):
        st = self.state()
        self.assertEqual(st["issues"]["A-1"]["lane"], "L1")
        self.assertEqual(st["issues"]["A-3"]["status"], "excluded")
        self.assertEqual(st["lanes"]["L1"]["files"], ["ui/Home.kt"])

    def test_next_lanes_respects_capacity(self):
        _, out, _ = run("next-lanes", self.dir)
        self.assertEqual(out.split(), ["L1"])
        run("lane", self.dir, "L1", "status=running")
        _, out, _ = run("next-lanes", self.dir)
        self.assertEqual(out.strip(), "")

    def test_next_lanes_respects_after(self):
        st_path = Path(self.dir) / "state.json"
        st = self.state()
        st["max_lanes"] = 5
        st["lanes"]["L2"]["after"] = ["L1"]
        st_path.write_text(json.dumps(st), encoding="utf-8")
        _, out, _ = run("next-lanes", self.dir)
        self.assertEqual(out.split(), ["L1"])
        run("lane", self.dir, "L1", "status=pr_open")
        _, out, _ = run("next-lanes", self.dir)
        self.assertEqual(out.split(), ["L2"])

    def test_invalid_status_rejected(self):
        code, _, err = run("issue", self.dir, "A-1", "status=whatever")
        self.assertEqual(code, 2)
        self.assertIn("không hợp lệ", err)

    def test_device_queue_waits_then_dispatches(self):
        code, _, _ = run("device-dispatch", self.dir)
        self.assertEqual(code, 0)  # không job
        _, job, _ = run("device-request", self.dir, "A-2", "--lane", "L2")
        job = job.strip()
        _, again, _ = run("device-request", self.dir, "A-2", "--lane", "L2")
        self.assertEqual(again.strip(), job)  # idempotent
        code, _, _ = run("device-dispatch", self.dir)
        self.assertEqual(code, 3)  # chưa có thiết bị
        run("device-sync", self.dir, "emulator-5554")
        code, _, _ = run("device-dispatch", self.dir, "--exclude", "emulator-5554")
        self.assertEqual(code, 3)  # thiết bị đang bị task ngoài batch dùng
        code, out, _ = run("device-dispatch", self.dir)
        self.assertEqual(code, 0)
        self.assertIn("emulator-5554", out)
        self.assertEqual(self.state()["issues"]["A-2"]["status"], "verifying_device")
        run("device-done", self.dir, job, "--result", "pass")
        st = self.state()
        self.assertIsNone(st["devices"]["emulator-5554"]["holder"])
        self.assertEqual(st["issues"]["A-2"]["status"], "verified")

    def test_release_returns_job_to_queue(self):
        run("device-sync", self.dir, "s1")
        _, job, _ = run("device-request", self.dir, "A-2", "--lane", "L2")
        run("device-dispatch", self.dir)
        run("device-release", self.dir, "s1")
        st = self.state()
        self.assertEqual(st["device_jobs"][job.strip()]["status"], "pending")
        self.assertEqual(st["issues"]["A-2"]["status"], "pending_device")

    def test_repro_job_does_not_touch_issue_status(self):
        run("device-sync", self.dir, "s1")
        _, job, _ = run("device-request", self.dir, "A-2", "--lane", "L2", "--purpose", "repro")
        self.assertEqual(self.state()["issues"]["A-2"]["status"], "planned")
        _, out, _ = run("device-dispatch", self.dir)
        self.assertIn("repro", out)
        run("device-done", self.dir, job.strip(), "--result", "pass")
        self.assertEqual(self.state()["issues"]["A-2"]["status"], "planned")

    def test_reload_prunes_removed_lane(self):
        p = plan()
        del p["lanes"]["L2"]
        p["lanes"]["L1"]["groups"] = ["g1", "g2"]
        path = Path(self.tmp.name) / "plan2.json"
        path.write_text(json.dumps(p), encoding="utf-8")
        code, out, _ = run("load-plan", self.dir, str(path))
        self.assertEqual(code, 0, out)
        self.assertNotIn("L2", self.state()["lanes"])
        self.assertEqual(self.state()["issues"]["A-2"]["lane"], "L1")

    def test_reload_refuses_to_drop_running_lane(self):
        run("lane", self.dir, "L2", "status=running")
        p = plan()
        del p["lanes"]["L2"]
        p["lanes"]["L1"]["groups"] = ["g1", "g2"]
        path = Path(self.tmp.name) / "plan3.json"
        path.write_text(json.dumps(p), encoding="utf-8")
        code, _, err = run("load-plan", self.dir, str(path))
        self.assertEqual(code, 1)
        self.assertIn("L2", err)

    def test_board_renders(self):
        code, out, _ = run("board", self.dir)
        self.assertEqual(code, 0)
        self.assertIn("| L1 | planned | A-1 |", out)


if __name__ == "__main__":
    unittest.main()
