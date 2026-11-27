import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import telemetry as t  # noqa: E402


class TelemetryCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {
            "MEH_TELEMETRY_DIR": str(root / "tel"),
            "CLAUDE_HOME": str(root / "claude"),
            "MEH_TELEMETRY_LOGIN": "dev-a",
            "MEH_TELEMETRY_NO_GIT": "1",
        })
        self.env.start()
        self.root = root

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def events(self):
        return list(t.load_events(t.events_dir())) if t.events_dir().exists() else []

    def run_hook(self, payload):
        with mock.patch("sys.stdin", io.StringIO(json.dumps(payload))), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            code = t.cmd_hook(None)
        return code, out.getvalue()


class ParseAndRedact(TelemetryCase):
    def test_parse_slash(self):
        self.assertEqual(t.parse_slash("/bug-fix status"), ("bug-fix", "status"))
        self.assertEqual(t.parse_slash("  /ak:debug"), ("ak:debug", ""))
        self.assertEqual(t.parse_slash("/release v1.4.0\nghi chú"), ("release", "v1.4.0\nghi chú"))
        self.assertIsNone(t.parse_slash("sửa bug màn Paywall"))
        self.assertIsNone(t.parse_slash("/"))

    def test_redact_masks_credentials_only(self):
        text = ("/bug-fix bug: login lỗi, token=abc123456789 key ghp_" + "a" * 36 +
                " Bearer eyJhbGciOiJIUzI1NiJ9xxxxxxxx và link https://jira.example.com/browse/APP-1")
        out = t.redact(text)
        self.assertNotIn("abc123456789", out)
        self.assertNotIn("ghp_" + "a" * 36, out)
        self.assertIn("[REDACTED:github-token]", out)
        self.assertIn("https://jira.example.com/browse/APP-1", out)
        self.assertIn("/bug-fix bug: login lỗi", out)

    def test_redact_keeps_plain_prompt(self):
        p = "/coding-orchestrator Build feature streak từ briefs/streak/"
        self.assertEqual(t.redact(p), p)


class Hook(TelemetryCase):
    def test_slash_prompt_writes_event_and_prints_nothing(self):
        code, out = self.run_hook({"hook_event_name": "UserPromptSubmit", "session_id": "s1",
                                   "cwd": "/x/AIP396", "prompt": "/bug-fix status"})
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        [e] = self.events()
        self.assertEqual((e["skill"], e["args"], e["source"], e["login"], e["repo"]),
                         ("bug-fix", "status", "slash", "dev-a", "AIP396"))
        self.assertEqual(e["prompt"], "/bug-fix status")

    def test_plain_prompt_writes_nothing_but_is_remembered(self):
        self.run_hook({"hook_event_name": "UserPromptSubmit", "session_id": "s1", "cwd": "/x/app",
                       "prompt": "fix giúp tôi màn Paywall"})
        self.assertEqual(self.events(), [])
        self.run_hook({"hook_event_name": "PreToolUse", "session_id": "s1", "cwd": "/x/app",
                       "tool_name": "Skill", "tool_input": {"skill": "coding-diagnose", "args": "paywall"}})
        [e] = self.events()
        self.assertEqual((e["skill"], e["source"]), ("coding-diagnose", "model"))
        self.assertEqual(e["prompt"], "fix giúp tôi màn Paywall")

    def test_other_tools_ignored(self):
        self.run_hook({"hook_event_name": "PreToolUse", "session_id": "s1", "cwd": "/x",
                       "tool_name": "Bash", "tool_input": {"command": "ls"}})
        self.assertEqual(self.events(), [])

    def test_opt_out_env_records_nothing(self):
        with mock.patch.dict(os.environ, {"MEH_TELEMETRY": "0"}):
            self.run_hook({"hook_event_name": "UserPromptSubmit", "session_id": "s1", "cwd": "/x",
                           "prompt": "/bug-fix status"})
        self.assertEqual(self.events(), [])

    def test_bad_payload_never_fails(self):
        with mock.patch("sys.stdin", io.StringIO("{not json")):
            self.assertEqual(t.cmd_hook(None), 0)
        self.assertTrue((t.data_dir() / "hook-errors.log").exists())

    def test_inventory_once_per_day(self):
        skill = self.root / "claude" / "skills" / "bug-fix" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: bug-fix\n---\n")
        for _ in range(2):
            self.run_hook({"hook_event_name": "SessionStart", "session_id": "s1", "cwd": "/x/app"})
        inv = [e for e in self.events() if e["kind"] == "inventory"]
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0]["skills"]["user"], ["bug-fix"])


class Backfill(TelemetryCase):
    def transcript(self):
        return [
            json.dumps({"type": "user", "sessionId": "old", "cwd": "/x/app", "timestamp": "2026-11-01T01:00:00Z",
                        "message": {"role": "user", "content":
                                    "<command-name>/bug-fix</command-name><command-args>status</command-args>"}}),
            json.dumps({"type": "user", "sessionId": "old", "cwd": "/x/app", "timestamp": "2026-11-01T01:01:00Z",
                        "message": {"role": "user", "content": "làm feature streak"}}),
            json.dumps({"type": "assistant", "sessionId": "old", "cwd": "/x/app", "timestamp": "2026-11-01T01:02:00Z",
                        "message": {"role": "assistant", "content": [
                            {"type": "tool_use", "name": "Skill", "input": {"skill": "coding-orchestrator"}}]}}),
        ]

    def test_parse_transcript(self):
        evs = list(t.parse_transcript(self.transcript(), {"login": "dev-a"}, repo_lookup=lambda c: "app"))
        self.assertEqual([(e["skill"], e["source"]) for e in evs],
                         [("bug-fix", "backfill-slash"), ("coding-orchestrator", "backfill-model")])
        self.assertEqual(evs[0]["prompt"], "/bug-fix status")
        self.assertEqual(evs[1]["prompt"], "làm feature streak")

    def test_rows_without_timestamp_or_meta_are_skipped(self):
        rows = self.transcript()
        no_ts = json.loads(rows[0]); no_ts.pop("timestamp")
        meta = json.loads(rows[1]); meta["isMeta"] = True
        meta["message"]["content"] = "Base directory for this skill: /x"
        evs = list(t.parse_transcript([json.dumps(no_ts), rows[1], json.dumps(meta), rows[2]],
                                      {"login": "dev-a"}, repo_lookup=lambda c: "app"))
        self.assertEqual([e["skill"] for e in evs], ["coding-orchestrator"])
        self.assertEqual(evs[0]["prompt"], "làm feature streak")

    def test_backfill_is_idempotent_and_skips_hooked_sessions(self):
        proj = self.root / "claude" / "projects" / "p"
        proj.mkdir(parents=True)
        (proj / "a.jsonl").write_text("\n".join(self.transcript()) + "\n")
        args = mock.Mock(dry_run=False)
        with mock.patch("sys.stdout", new_callable=io.StringIO):
            t.cmd_backfill(args)
            t.cmd_backfill(args)
        self.assertEqual(len(self.events()), 2)

        live = self.root / "claude" / "projects" / "p" / "b.jsonl"
        live.write_text(self.transcript()[0].replace('"old"', '"live"') + "\n")
        self.run_hook({"hook_event_name": "UserPromptSubmit", "session_id": "live", "cwd": "/x/app",
                       "prompt": "/bug-fix status"})
        with mock.patch("sys.stdout", new_callable=io.StringIO):
            t.cmd_backfill(args)
        sources = [e["source"] for e in self.events() if e["session"] == "live"]
        self.assertEqual(sources, ["slash"])


class Report(TelemetryCase):
    def sample(self):
        ident_a, ident_b = {"login": "dev-a"}, {"login": "dev-b"}
        return [
            t.make_event("inventory", ident_a, "app", "s0", ts="2026-11-20T00:00:00+00:00",
                         skills={"user": ["bug-fix", "release", "create-qa"], "plugin": [], "project": []}),
            t.make_event("skill", ident_a, "app", "s1", ts="2026-11-20T01:00:00+00:00", skill="bug-fix",
                         args="status", source="slash", prompt="/bug-fix status"),
            t.make_event("skill", ident_a, "app", "s1", ts="2026-11-20T02:00:00+00:00", skill="bug-fix",
                         args="resume", source="slash", prompt="/bug-fix resume"),
            t.make_event("skill", ident_b, "app", "s2", ts="2026-11-21T01:00:00+00:00", skill="bug-fix",
                         args="", source="model", prompt="sửa lỗi Restore"),
            t.make_event("skill", ident_b, "app", "s2", ts="2026-11-21T02:00:00+00:00", skill="clear",
                         args="", source="slash", prompt="/clear"),
        ]

    def test_aggregates(self):
        r = t.build_report(self.sample(), since_days=0)
        top = r["skills"][0]
        self.assertEqual((top["skill"], top["total"], top["slash"], top["model"]), ("bug-fix", 3, 2, 1))
        self.assertEqual(top["users"], ["dev-a", "dev-b"])
        self.assertEqual(top["prompts"][0], "sửa lỗi Restore")
        self.assertEqual(r["installed_unused"], ["create-qa", "release"])
        self.assertNotIn("clear", [s["skill"] for s in r["skills"]])
        self.assertEqual(r["commands"], [("clear", 1)])
        self.assertEqual(r["users"][0]["login"], "dev-a")
        self.assertIn("`bug-fix`", t.render_markdown(r))

    def test_duplicate_ids_counted_once(self):
        evs = self.sample()
        r = t.build_report(evs + evs, since_days=0)
        self.assertEqual(r["total_uses"], 3)

    def test_plugin_skills_get_namespaced_name(self):
        plugin = self.root / "claude" / "plugins" / "synced" / "x" / "figma"
        (plugin / ".claude-plugin").mkdir(parents=True)
        (plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "figma"}')
        skill = plugin / "skills-figquery" / "figma-use" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: figma-use\n---\n")
        self.assertEqual(t.installed_skills()["plugin"], ["figma-use", "figma:figma-use"])

    def test_model_loaded_names_count_as_skills(self):
        evs = self.sample() + [t.make_event("skill", {"login": "dev-a"}, "app", "s3",
                                            ts="2026-11-22T01:00:00+00:00", skill="artifact-design",
                                            args="", source="model", prompt="vẽ sơ đồ")]
        r = t.build_report(evs, since_days=0)
        self.assertIn("artifact-design", [s["skill"] for s in r["skills"]])

    def test_folder_and_frontmatter_names_both_installed(self):
        skill = self.root / "claude" / "skills" / "git" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: ck:git\n---\n")
        self.assertEqual(t.installed_skills()["user"], ["ck:git", "git"])


class Sync(TelemetryCase):
    def test_merge_dedups_and_redacts(self):
        e = t.make_event("skill", {"login": "dev-a"}, "app", "s1", ts="2026-11-20T01:00:00+00:00",
                         skill="bug-fix", args="", source="slash", prompt="/bug-fix x")
        e["prompt"] = "/bug-fix x password=hunter2secret"  # simulate an old, unredacted local row
        target = self.root / "remote"
        self.assertEqual(t.merge_into(target, [dict(e)], "dev-a", write=False), 1)
        self.assertFalse((target / "data").exists())
        self.assertEqual(t.merge_into(target, [dict(e)], "dev-a"), 1)
        self.assertEqual(t.merge_into(target, [dict(e)], "dev-a"), 0)
        rows = (target / "data" / "dev-a" / "2026-11.jsonl").read_text().splitlines()
        self.assertEqual(len(rows), 1)
        self.assertNotIn("hunter2secret", rows[0])


if __name__ == "__main__":
    unittest.main()
