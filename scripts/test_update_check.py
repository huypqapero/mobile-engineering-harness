"""Tests for update-check.sh against throwaway git repos. Run: python3 -m unittest scripts/test_update_check.py"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "update-check.sh"


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


class UpdateCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.origin, self.work, self.install = root / "origin.git", root / "work", root / "install"
        git(root, "init", "--bare", "-b", "main", str(self.origin))
        git(root, "clone", "-q", str(self.origin), str(self.work))
        for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
            git(self.work, "config", k, v)
        self.commit("first", tag="v0.1.0")
        git(root, "clone", "-q", str(self.origin), str(self.install))
        self.env = {**os.environ, "MEH_UPSTREAM_DIR": str(self.install),
                    "XDG_CACHE_HOME": str(root / "cache"), "XDG_CONFIG_HOME": str(root / "config"),
                    "MEH_UPDATE_INTERVAL": "999999"}

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, name, tag=None):
        (self.work / f"{name}.txt").write_text(name)
        git(self.work, "add", ".")
        git(self.work, "commit", "-qm", name)
        if tag:
            git(self.work, "tag", tag)
        git(self.work, "push", "-q", "origin", "main", "--tags")

    def run_cmd(self, *args, **env):
        r = subprocess.run([os.environ.get("TEST_BASH", "bash"), str(SCRIPT), *args], env={**self.env, **env}, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def head(self):
        return subprocess.run(["git", "-C", str(self.install), "describe", "--tags", "--always"],
                              capture_output=True, text=True).stdout.strip()

    def test_up_to_date(self):
        self.assertIn("đã mới nhất", self.run_cmd("check"))
        self.assertEqual(self.run_cmd("notify"), "")

    def test_reports_new_version_without_moving(self):
        self.commit("second", tag="v0.2.0")
        out = self.run_cmd("check")
        self.assertIn("chậm 1 commit", out)
        self.assertIn("v0.2.0", out)
        self.assertEqual(self.head(), "v0.1.0")
        self.assertTrue(self.run_cmd("notify").startswith("HARNESS UPDATE:"))

    def test_auto_update_on_clean_main(self):
        self.assertIn("on", self.run_cmd("auto", "on"))
        self.commit("second", tag="v0.2.0")
        self.run_cmd("check", "--quiet")  # what the background refresh runs
        self.assertEqual(self.head(), "v0.2.0")
        first = self.run_cmd("notify")
        self.assertIn("đã tự cập nhật v0.1.0 → v0.2.0", first)
        self.assertEqual(self.run_cmd("notify"), "")  # shown once

    def test_auto_update_blocked_by_local_changes(self):
        self.run_cmd("auto", "on")
        (self.install / "first.txt").write_text("edited")
        self.commit("second", tag="v0.2.0")
        out = self.run_cmd("check")
        self.assertIn("Không tự cập nhật được", out)
        self.assertEqual(self.head(), "v0.1.0")

    def test_pinned_tag_is_reported_not_moved(self):
        self.run_cmd("auto", "on")
        git(self.install, "checkout", "-q", "v0.1.0")
        self.commit("second", tag="v0.2.0")
        out = self.run_cmd("check")
        self.assertIn("đang pin v0.1.0, bản mới nhất v0.2.0", out)
        self.assertEqual(self.head(), "v0.1.0")

    def test_opt_out(self):
        self.commit("second", tag="v0.2.0")
        self.run_cmd("check", "--quiet")
        self.assertEqual(self.run_cmd("notify", MEH_UPDATE_CHECK="0"), "")

    def test_stale_cache_triggers_background_refresh(self):
        self.commit("second", tag="v0.2.0")
        self.assertEqual(self.run_cmd("notify", MEH_UPDATE_INTERVAL="0"), "")  # no cache yet
        cache_dir = Path(self.env["XDG_CACHE_HOME"]) / "mobile-engineering-harness"
        for _ in range(50):
            if any(cache_dir.glob("update-*.env")) and not any(cache_dir.glob("*.lock")):
                break
            subprocess.run(["sleep", "0.1"])
        self.assertIn("HARNESS UPDATE:", self.run_cmd("notify"))


if __name__ == "__main__":
    unittest.main()
