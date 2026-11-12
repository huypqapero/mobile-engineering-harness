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


def make_apk(directory, name="app.apk"):
    path = Path(directory) / name
    path.write_text("apk")
    return str(path)


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
            apk = make_apk(d)
            run("device-request", str(b), "A-1", "--lane", "L1", "--apk", apk)
            run("device-request", str(b), "A-2", "--lane", "L2", "--apk", apk)
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
        self.apk = make_apk(self.tmp.name)
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
        _, job, _ = run("device-request", self.dir, "A-2", "--lane", "L2", "--apk", self.apk)
        job = job.strip()
        _, again, _ = run("device-request", self.dir, "A-2", "--lane", "L2", "--apk", self.apk)
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
        _, job, _ = run("device-request", self.dir, "A-2", "--lane", "L2", "--apk", self.apk)
        run("device-dispatch", self.dir)
        run("device-release", self.dir, "s1")
        st = self.state()
        self.assertEqual(st["device_jobs"][job.strip()]["status"], "pending")
        self.assertEqual(st["issues"]["A-2"]["status"], "pending_device")

    def test_repro_job_does_not_touch_issue_status(self):
        run("device-sync", self.dir, "s1")
        _, job, _ = run("device-request", self.dir, "A-2", "--lane", "L2", "--purpose", "repro", "--apk", self.apk)
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


class IssueKeyTest(unittest.TestCase):
    def test_task_key_rules(self):
        self.assertTrue(bfo_state.is_task_key("TASK-fix-login"))
        self.assertFalse(bfo_state.is_task_key("TASK-12"))  # trùng key Jira của project TASK
        self.assertFalse(bfo_state.is_task_key("TASK-Fix"))
        self.assertFalse(bfo_state.is_task_key("PROJ-1"))

    def test_plan_accepts_task_key_and_rejects_malformed(self):
        p = plan()
        p["issues"]["TASK-fix-login"] = dict(p["issues"].pop("A-1"))
        p["groups"]["g1"]["issues"] = ["TASK-fix-login"]
        errors, _ = bfo_state.validate_plan(p)
        self.assertEqual(errors, [])
        p["issues"]["bad key"] = {"title": "x", "kind": "needs-info", "reason": "r"}
        errors, _ = bfo_state.validate_plan(p)
        self.assertTrue(any("bad key" in e and "không hợp lệ" in e for e in errors))

    def test_task_key_skips_jira_and_joins_device_queue(self):
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "batch"
            run("init", str(b), "--base-commit", "abc", "--base-branch", "main", "--source", "t")
            p = plan()
            p["issues"]["TASK-fix-login"] = p["issues"].pop("A-2")
            p["groups"]["g2"]["issues"] = ["TASK-fix-login"]
            f = Path(d) / "plan.json"; f.write_text(json.dumps(p))
            self.assertEqual(run("load-plan", str(b), str(f))[0], 0)
            st = json.loads((b / "state.json").read_text())
            self.assertEqual(st["issues"]["TASK-fix-login"]["tracker"], "none")
            run("lane", str(b), "L2", "status=running")
            _, out, _ = run("jira-sync", str(b))
            self.assertNotIn("TASK-fix-login", out)
            run("device-sync", str(b), "emu-1")
            run("device-request", str(b), "TASK-fix-login", "--lane", "L2", "--apk", make_apk(d))
            _, out, _ = run("device-dispatch", str(b))
            self.assertIn("TASK-fix-login", out)


class CheckPlanMergedLaneTest(unittest.TestCase):
    def overlapping(self):
        p = plan()
        p["groups"]["g2"]["files"] = ["ui/Home.kt"]
        return p

    def test_overlap_ignored_for_merged_lane(self):
        errors, _ = bfo_state.validate_plan(self.overlapping())
        self.assertTrue(any("cùng sửa ui/Home.kt" in e for e in errors))
        errors, _ = bfo_state.validate_plan(self.overlapping(), merged_lanes={"L1"})
        self.assertEqual(errors, [])

    def test_check_plan_batch_reads_done_and_merged_lanes(self):
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "batch"
            run("init", str(b), "--base-commit", "abc", "--base-branch", "main", "--source", "t")
            f = Path(d) / "plan.json"; f.write_text(json.dumps(plan()))
            run("load-plan", str(b), str(f))
            f.write_text(json.dumps(self.overlapping()))
            self.assertEqual(run("check-plan", str(f))[0], 1)
            self.assertEqual(run("check-plan", str(f), "--batch", str(b))[0], 1)  # L1 chưa merge
            run("lane", str(b), "L1", "status=pr_open", "merged=other")
            self.assertEqual(run("check-plan", str(f), "--batch", str(b))[0], 1)  # merge vào branch khác base
            run("lane", str(b), "L1", "merged=base")
            self.assertEqual(run("check-plan", str(f), "--batch", str(b))[0], 0)
            run("lane", str(b), "L1", "merged=no", "status=done")
            self.assertEqual(run("check-plan", str(f), "--batch", str(b))[0], 0)
            self.assertEqual(run("load-plan", str(b), str(f))[0], 0)  # load-plan tự đọc lane merged từ state


class LaneBlockedAndRemoveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = str(Path(self.tmp.name) / "batch")
        run("init", self.dir, "--base-commit", "abc", "--base-branch", "main", "--source", "t", "--max-lanes", "5")
        self.plan_path = Path(self.tmp.name) / "plan.json"
        p = plan(); p["lanes"]["L2"]["after"] = ["L1"]
        self.plan_path.write_text(json.dumps(p))
        self.assertEqual(run("load-plan", self.dir, str(self.plan_path))[0], 0)

    def tearDown(self):
        self.tmp.cleanup()

    def state(self):
        return json.loads((Path(self.dir) / "state.json").read_text())

    def test_blocked_lane_is_not_scheduled_and_does_not_unblock_after(self):
        run("lane", self.dir, "L1", "status=blocked")
        _, out, _ = run("next-lanes", self.dir)
        self.assertEqual(out.split(), [])  # L1 blocked, L2 vẫn chờ after

    def test_lane_field_values_validated(self):
        self.assertEqual(run("lane", self.dir, "L1", "merged=maybe")[0], 2)
        self.assertEqual(run("lane", self.dir, "L1", "ready=yes", "merged=base")[0], 0)

    def test_remove_cleans_state_and_after_and_plan(self):
        code, out, err = run("lane-remove", self.dir, "L1", "--plan", str(self.plan_path))
        self.assertEqual(code, 0, err)
        st = self.state()
        self.assertNotIn("L1", st["lanes"])
        self.assertNotIn("after", st["lanes"]["L2"])
        self.assertNotIn("lane", st["issues"]["A-1"])
        self.assertIn("g1", err)  # group mồ côi được báo
        plan_after = json.loads(self.plan_path.read_text())
        self.assertNotIn("L1", plan_after["lanes"])
        self.assertNotIn("after", plan_after["lanes"]["L2"])

    def test_remove_refuses_running_lane_without_force(self):
        run("lane", self.dir, "L1", "status=running")
        code, _, err = run("lane-remove", self.dir, "L1")
        self.assertEqual(code, 1)
        self.assertIn("--force", err)
        self.assertEqual(run("lane-remove", self.dir, "L1", "--force")[0], 0)

    def test_remove_drops_pending_device_jobs_but_refuses_running_ones(self):
        apk = make_apk(self.tmp.name)
        run("device-sync", self.dir, "s1")
        run("device-request", self.dir, "A-1", "--lane", "L1", "--apk", apk)
        code, out, _ = run("lane-remove", self.dir, "L1")
        self.assertEqual(code, 0)
        self.assertIn("DJ-001", out)
        self.assertEqual(self.state()["device_jobs"], {})
        run("device-request", self.dir, "A-2", "--lane", "L2", "--apk", apk)
        run("device-dispatch", self.dir)
        code, _, err = run("lane-remove", self.dir, "L2")
        self.assertEqual(code, 1)
        self.assertIn("DJ-", err)


class DeviceReadinessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = str(Path(self.tmp.name) / "batch")
        run("init", self.dir, "--base-commit", "abc", "--base-branch", "main", "--source", "t")
        f = Path(self.tmp.name) / "plan.json"; f.write_text(json.dumps(plan()))
        run("load-plan", self.dir, str(f))
        run("device-sync", self.dir, "s1")

    def tearDown(self):
        self.tmp.cleanup()

    def state(self):
        return json.loads((Path(self.dir) / "state.json").read_text())

    def test_job_without_apk_is_not_dispatched(self):
        run("device-request", self.dir, "A-1", "--lane", "L1")
        code, out, err = run("device-dispatch", self.dir)
        self.assertEqual(code, 4)
        self.assertEqual(out, "")
        self.assertIn("chưa có APK", err)
        self.assertEqual(self.state()["device_jobs"]["DJ-001"]["status"], "pending")

    def test_missing_apk_file_is_not_ready(self):
        run("device-request", self.dir, "A-1", "--lane", "L1", "--apk", "/nonexistent/app.apk")
        code, _, err = run("device-dispatch", self.dir)
        self.assertEqual(code, 4)
        self.assertIn("không tồn tại", err)

    def test_ready_job_skips_not_ready_ahead_of_it(self):
        apk = make_apk(self.tmp.name)
        run("device-request", self.dir, "A-1", "--lane", "L1")  # DJ-001 chưa có APK
        run("device-request", self.dir, "A-2", "--lane", "L2", "--apk", apk)  # DJ-002 sẵn sàng
        code, out, _ = run("device-dispatch", self.dir)
        self.assertEqual(code, 0)
        self.assertIn("DJ-002", out)
        self.assertNotIn("DJ-001", out)

    def test_request_again_updates_apk_and_makes_job_ready(self):
        run("device-request", self.dir, "A-1", "--lane", "L1")
        self.assertEqual(run("device-dispatch", self.dir)[0], 4)
        run("device-request", self.dir, "A-1", "--lane", "L1", "--apk", make_apk(self.tmp.name))
        code, out, _ = run("device-dispatch", self.dir)
        self.assertEqual((code, out.split()[0]), (0, "DJ-001"))

    def test_priority_beats_queue_order(self):
        apk = make_apk(self.tmp.name)
        run("device-request", self.dir, "A-1", "--lane", "L1", "--apk", apk)
        run("device-request", self.dir, "A-2", "--lane", "L2", "--apk", apk, "--priority", "5")
        _, out, _ = run("device-dispatch", self.dir)
        self.assertEqual(out.split()[0], "DJ-002")

    def test_all_ready_jobs_waiting_exits_3(self):
        apk = make_apk(self.tmp.name)
        run("device-request", self.dir, "A-1", "--lane", "L1", "--apk", apk)
        self.assertEqual(run("device-dispatch", self.dir, "--exclude", "s1")[0], 3)

    def test_verify_job_with_stale_head_is_not_ready(self):
        import subprocess
        wt = Path(self.tmp.name) / "wt"
        wt.mkdir()
        git = lambda *a: subprocess.run(["git", "-C", str(wt), *a], check=True, capture_output=True)
        git("init", "-q"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "one")
        old = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "two")
        new = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        run("lane", self.dir, "L1", f"worktree={wt}")
        apk = make_apk(self.tmp.name)
        run("device-request", self.dir, "A-1", "--lane", "L1", "--apk", apk, "--head", old)
        code, _, err = run("device-dispatch", self.dir)
        self.assertEqual(code, 4)
        self.assertIn("build lại", err)
        run("device-request", self.dir, "A-1", "--lane", "L1", "--apk", apk, "--head", new[:12])
        self.assertEqual(run("device-dispatch", self.dir)[0], 0)


class JiraSyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = str(Path(self.tmp.name) / "batch")
        run("init", self.dir, "--base-commit", "abc", "--base-branch", "main", "--source", "t")
        f = Path(self.tmp.name) / "plan.json"; f.write_text(json.dumps(plan()))
        run("load-plan", self.dir, str(f))

    def tearDown(self):
        self.tmp.cleanup()

    def sync(self, *extra):
        code, out, _ = run("jira-sync", self.dir, *extra)
        self.assertEqual(code, 0)
        return [line for line in out.splitlines() if not line.startswith("#")]

    def test_planned_lane_needs_nothing_and_excluded_never_appears(self):
        self.assertEqual(self.sync(), [])
        self.assertNotIn("A-3", "\n".join(self.sync("--all")))

    def test_running_lane_means_in_progress(self):
        run("lane", self.dir, "L1", "status=running")
        run("issue", self.dir, "A-1", "jira=Request")
        rows = self.sync()
        self.assertEqual(len(rows), 1)
        self.assertIn("A-1: Request -> In Progress", rows[0])
        run("issue", self.dir, "A-1", "jira=In Progress")
        self.assertEqual(self.sync(), [])

    def test_unknown_current_status_is_flagged(self):
        run("lane", self.dir, "L1", "status=running")
        self.assertIn("A-1: ? -> In Progress", self.sync()[0])

    def test_ready_and_verified_means_resolved(self):
        run("lane", self.dir, "L1", "status=pr_open", "ready=yes")
        run("issue", self.dir, "A-1", "status=pr_open", "jira=In Progress")
        self.assertIn("A-1: In Progress -> Resolved", self.sync()[0])

    def test_device_bug_pending_stays_in_progress_even_if_lane_open(self):
        run("lane", self.dir, "L2", "status=pr_open")
        run("issue", self.dir, "A-2", "status=pending_device", "jira=In Progress")
        self.assertEqual(self.sync(), [])

    def test_merged_into_base_means_reviewing_via_resolved_when_in_progress(self):
        run("lane", self.dir, "L1", "status=done", "merged=base", "ready=yes")
        run("issue", self.dir, "A-1", "status=pr_open", "jira=In Progress")
        row = self.sync()[0]
        self.assertIn("A-1: In Progress -> Reviewing", row)
        self.assertIn("qua Resolved", row)
        run("issue", self.dir, "A-1", "jira=Resolved")
        self.assertNotIn("qua Resolved", self.sync()[0])
        run("issue", self.dir, "A-1", "jira=Reviewing")
        self.assertEqual(self.sync(), [])

    def test_merged_before_device_pass_is_reviewing_and_fail_reopens(self):
        run("lane", self.dir, "L2", "status=done", "merged=base")
        run("issue", self.dir, "A-2", "status=verifying_device", "jira=Resolved")
        self.assertIn("A-2: Resolved -> Reviewing", self.sync()[0])
        run("issue", self.dir, "A-2", "status=failed", "jira=Reviewing")
        self.assertIn("A-2: Reviewing -> In Progress", self.sync()[0])

    def test_merged_into_other_branch_is_not_reviewing(self):
        run("lane", self.dir, "L1", "status=pr_open", "merged=other")
        run("issue", self.dir, "A-1", "jira=In Progress")
        row = self.sync()[0]
        self.assertIn("giữ nguyên", row)
        self.assertNotIn("Reviewing", row.split("(")[0])

    def test_blocked_issue_untouched_and_no_regress_from_reviewing(self):
        run("lane", self.dir, "L1", "status=running")
        run("issue", self.dir, "A-1", "status=blocked", "jira=Request")
        self.assertEqual(self.sync(), [])
        run("lane", self.dir, "L2", "status=pr_open", "ready=yes")
        run("issue", self.dir, "A-2", "status=verified", "jira=Reviewing")
        self.assertEqual(self.sync(), [])

    def test_decision_change_after_ready_returns_to_in_progress(self):
        run("lane", self.dir, "L1", "status=pr_open", "ready=yes")
        run("issue", self.dir, "A-1", "status=pr_open", "jira=Resolved")
        self.assertEqual(self.sync(), [])  # đã Resolved, không có gì phải làm
        run("lane", self.dir, "L1", "status=running", "ready=no")
        self.assertIn("A-1: Resolved -> In Progress", self.sync()[0])

    def test_jira_and_lane_flags_survive_reload(self):
        run("issue", self.dir, "A-1", "jira=In Progress")
        run("lane", self.dir, "L1", "ready=yes", "merged=base")
        f = Path(self.tmp.name) / "plan.json"
        run("load-plan", self.dir, str(f))
        st = json.loads((Path(self.dir) / "state.json").read_text())
        self.assertEqual(st["issues"]["A-1"]["jira"], "In Progress")
        self.assertEqual((st["lanes"]["L1"]["ready"], st["lanes"]["L1"]["merged"]), ("yes", "base"))


if __name__ == "__main__":
    unittest.main()
