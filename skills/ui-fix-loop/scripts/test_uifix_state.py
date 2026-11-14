import json, subprocess, sys, tempfile, unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("uifix_state.py")
URL = "https://www.figma.com/design/AbC123/App?node-id=646-5489"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


class ScreenRegistryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.refs = str(Path(self.tmp.name) / "screens")

    def tearDown(self):
        self.tmp.cleanup()

    def entry(self, screen):
        return json.loads((Path(self.refs) / f"{screen}.json").read_text())

    def test_add_writes_one_file_per_screen_and_unions_lists(self):
        r = run("ref-add", "--refs", self.refs, "--screen", "home", "--url", URL,
                "--spec", "docs/spec.md#Home", "--source", "a/HomeScreen.kt", "--preview-fqn", "a.HomePreview")
        self.assertEqual(r.returncode, 0, r.stderr)
        run("ref-add", "--refs", self.refs, "--screen", "home", "--spec", "docs/spec.md#Home-empty",
            "--preview-fqn", "a.HomeEmptyPreview")
        e = self.entry("home")
        self.assertEqual(e["node_id"], "646:5489")
        self.assertEqual(e["file_key"], "AbC123")
        self.assertEqual(e["spec"], ["docs/spec.md#Home", "docs/spec.md#Home-empty"])
        self.assertEqual([p["fqn"] for p in e["previews"]], ["a.HomeEmptyPreview", "a.HomePreview"])
        self.assertFalse((Path(self.refs) / "library.json").exists())

    def test_merge_accepts_legacy_figma_refs_file(self):
        legacy = Path(self.tmp.name) / "figma-refs.json"
        legacy.write_text(json.dumps({"screens": {"level": {
            "figma_url": URL, "node_id": "21:171", "spec": "docs/level.md",
            "preview_fqn": "a.LevelPreview", "source_files": ["a/Level.kt"]}}}))
        r = run("ref-merge", "--refs", self.refs, "--delta", str(legacy))
        self.assertEqual(r.returncode, 0, r.stderr)
        e = self.entry("level")
        self.assertEqual(e["spec"], ["docs/level.md"])
        self.assertEqual(e["previews"], [{"fqn": "a.LevelPreview"}])
        self.assertNotIn("preview_fqn", e)

    def test_merge_keeps_existing_scalar_when_delta_empty(self):
        run("ref-add", "--refs", self.refs, "--screen", "home", "--url", URL, "--name", "Home")
        delta = Path(self.tmp.name) / "delta.json"
        delta.write_text(json.dumps({"home": {"name": "", "source_files": ["b/Home.kt"]}}))
        run("ref-merge", "--refs", self.refs, "--delta", str(delta))
        e = self.entry("home")
        self.assertEqual(e["name"], "Home")
        self.assertEqual(e["source_files"], ["b/Home.kt"])

    def test_get_and_list(self):
        run("ref-add", "--refs", self.refs, "--screen", "home", "--url", URL, "--preview-fqn", "a.HomePreview")
        self.assertIn("646:5489", run("ref-get", "--refs", self.refs, "--screen", "home").stdout)
        self.assertIn("HomePreview", run("ref-list", "--refs", self.refs).stdout)
        self.assertNotEqual(run("ref-get", "--refs", self.refs, "--screen", "nope").returncode, 0)

    def test_rejects_path_like_screen_id(self):
        self.assertNotEqual(run("ref-add", "--refs", self.refs, "--screen", "../x", "--url", URL).returncode, 0)


if __name__ == "__main__":
    unittest.main()
