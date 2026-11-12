#!/usr/bin/env python3
"""Unit test cho validate_evidence.py. Chạy: python3 -m unittest test_validate_evidence.py (từ thư mục scripts)."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import validate_evidence  # noqa: E402


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = validate_evidence.main(list(argv))
        except SystemExit as exc:  # argparse error
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def write_evidence(directory, verdict="PASS", commit="abc123", artifacts=("report.md",), **over):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in artifacts:
        (directory / name).write_text("nội dung")
    data = {"issue": "BUG-001", "commit": commit, "verdict": verdict, "verification": {"unit": "PASS"},
            "artifacts": list(artifacts),
            "acceptance_criteria": [{"id": "AC1", "result": verdict, "evidence": artifacts[0]}]}
    data.update(over)
    (directory / "evidence.json").write_text(json.dumps(data))


class EvidenceDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "BUG-001-crash-home"

    def tearDown(self):
        self.tmp.cleanup()

    def test_pass(self):
        write_evidence(self.dir)
        code, out, _ = run("--evidence-dir", str(self.dir))
        self.assertEqual(code, 0)
        self.assertIn("PASS  BUG-001", out)

    def test_base_commit_checked_only_when_given(self):
        write_evidence(self.dir, commit="abc123")
        self.assertEqual(run("--evidence-dir", str(self.dir))[0], 0)
        self.assertEqual(run("--evidence-dir", str(self.dir), "--base-commit", "abc123")[0], 0)
        code, out, _ = run("--evidence-dir", str(self.dir), "--base-commit", "def456")
        self.assertEqual(code, 1)
        self.assertIn("lệch manifest.base_commit", out)

    def test_not_pass_verdict_fails(self):
        write_evidence(self.dir, verdict="NEEDS_VERIFICATION")
        code, out, _ = run("--evidence-dir", str(self.dir))
        self.assertEqual(code, 1)
        self.assertIn("NEEDS_VERIFICATION", out)

    def test_missing_artifact_fails(self):
        write_evidence(self.dir)
        (self.dir / "report.md").unlink()
        code, out, _ = run("--evidence-dir", str(self.dir))
        self.assertEqual(code, 1)
        self.assertIn("artifact không tồn tại: report.md", out)

    def test_empty_artifact_fails(self):
        write_evidence(self.dir)
        (self.dir / "report.md").write_text("")
        self.assertIn("artifact rỗng", run("--evidence-dir", str(self.dir))[1])

    def test_missing_required_field_and_missing_file(self):
        write_evidence(self.dir)
        data = json.loads((self.dir / "evidence.json").read_text())
        del data["verification"]
        (self.dir / "evidence.json").write_text(json.dumps(data))
        self.assertIn("thiếu field bắt buộc 'verification'", run("--evidence-dir", str(self.dir))[1])
        (self.dir / "evidence.json").unlink()
        code, out, _ = run("--evidence-dir", str(self.dir))
        self.assertEqual(code, 1)
        self.assertIn("not found", out)

    def test_ac_evidence_must_be_a_real_artifact(self):
        write_evidence(self.dir, acceptance_criteria=[{"id": "AC1", "result": "PASS", "evidence": "ghost.png"}])
        self.assertIn("AC1: evidence 'ghost.png' không có", run("--evidence-dir", str(self.dir))[1])

    def test_nonexistent_dir_is_usage_error(self):
        code, _, err = run("--evidence-dir", str(self.dir / "nope"))
        self.assertEqual(code, 2)
        self.assertIn("không tồn tại", err)

    def test_arguments_must_pick_exactly_one_mode(self):
        self.assertEqual(run()[0], 2)
        self.assertEqual(run("batch", "--evidence-dir", "x")[0], 2)
        self.assertEqual(run("batch", "--base-commit", "x")[0], 2)


class BatchModeStillWorksTest(unittest.TestCase):
    def test_batch_dir_mode_uses_manifest_base_commit(self):
        with tempfile.TemporaryDirectory() as d:
            batch = Path(d) / "bugfix-batch-1"
            batch.mkdir()
            (batch / "manifest.json").write_text(json.dumps({"base_commit": "abc123"}))
            (batch / "state.json").write_text(json.dumps({"issues": {"A-1": {}, "A-2": {}}}))
            write_evidence(batch / "evidence" / "A-1", issue="A-1")
            write_evidence(batch / "evidence" / "A-2", issue="A-2", commit="other")
            code, out, _ = run(str(batch))
            self.assertEqual(code, 1)
            self.assertIn("PASS  A-1", out)
            self.assertIn("A-2: commit 'other' lệch", out)
            self.assertIn("1/2 issue PASS", out)


if __name__ == "__main__":
    unittest.main()
