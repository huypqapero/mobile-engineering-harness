#!/usr/bin/env python3
"""Runner contract tests using a fake CLI, not Android rendering tests."""
import copy
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).with_name('preview_test.py')
FAKE = '''#!/usr/bin/env python3
import json, os, pathlib, struct, sys, time, zlib
args = sys.argv[1:]
if args == ['--version']:
    print('FAKE Android CLI for contract testing'); sys.exit(0)
if '--help' in args:
    print('--component-tree --fqn --output --format'); sys.exit(0)
mode = os.environ.get('PREVIEW_FAKE_MODE', 'ok')
if mode == 'timeout': time.sleep(10)
out = pathlib.Path(next(a.split('=', 1)[1] for a in args if a.startswith('--output=')))
out.mkdir(parents=True, exist_ok=True)
def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
png = b'\\x89PNG\\r\\n\\x1a\\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\\x00\\xff\\x00\\x00')) + chunk(b'IEND', b'')
if mode != 'missing_png': (out / 'preview.png').write_bytes(png if mode != 'corrupt' else b'not a PNG')
if mode == 'extra': (out / 'extra.png').write_bytes(png)
if mode != 'missing_tree': (out / 'preview.json').write_text('null' if mode == 'bad_tree' else json.dumps({'component': 'Fixture'}))
print(json.dumps({'output': str(out)}))
sys.exit(7 if mode == 'exit_error' else 0)
'''


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='preview-contract-test-')
        self.base = Path(self.temp.name)
        self.project = self.base / 'project'
        self.project.mkdir()
        self.source = self.project / 'Screen.kt'
        self.source.write_text('// fixture source\n')
        self.manifest_path = self.project / 'cases.json'
        self.manifest = {
            'schema_version': 1, 'feature': 'fixture', 'target': ':app', 'references': [],
            'cases': [{'id': 'normal', 'fqn': 'demo.PreviewsKt.normal', 'expected_images': 1,
                       'review_kind': 'requirements', 'reference_ids': [],
                       'requirements': [{'id': 'visible', 'text': 'Required content is visible'}]}]}
        self.save_manifest()
        self.fake = self.base / 'android-fake'
        self.fake.write_text(FAKE)
        self.fake.chmod(0o755)
        for command in (['init', '-q'], ['add', '.'], ['-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture']):
            subprocess.run(['git', '-C', str(self.project), *command], check=True, capture_output=True)

    def tearDown(self):
        self.temp.cleanup()

    def save_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest))

    def invoke(self, *args, mode='ok'):
        env = dict(os.environ, PREVIEW_FAKE_MODE=mode)
        p = subprocess.run([sys.executable, str(RUNNER), *map(str, args)], env=env, capture_output=True, text=True, timeout=20)
        self.assertTrue(p.stdout.strip(), p.stderr)
        return p.returncode, json.loads(p.stdout)

    def render(self, mode='ok', timeout='5'):
        return self.invoke('render', '--project', self.project, '--manifest', self.manifest_path, '--android-bin', self.fake, '--runs-dir', self.base / 'runs', '--timeout', timeout, mode=mode)

    def reviewed(self):
        code, result = self.render()
        self.assertEqual(code, 0, result)
        self.assertFalse(result['ui_pass'])
        run = Path(result['run_dir'])
        review = json.loads((run / 'review-template.json').read_text())
        review['reviewer'] = 'Contract fixture; not a real visual assessment'
        review['reviewed_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
        for case in review['cases']:
            case['images_reviewed'] = case['available_images']
            case['references_reviewed'] = self.manifest['cases'][0].get('reference_ids', [])
            for check in case['checks']:
                check.update(status='PASS', evidence=case['available_images'], note='Synthetic contract check')
        return run, review

    def verify(self, run, review):
        path = run / 'review.json'
        path.write_text(json.dumps(review))
        return self.invoke('verify', '--run-dir', run, '--review', path)

    def test_render_is_not_ui_pass(self):
        code, result = self.render()
        self.assertEqual(code, 0)
        self.assertEqual(result['status'], 'RENDERED_PENDING_REVIEW')
        self.assertFalse(result['ui_pass'])

    def test_complete_review_passes_scoped_gate(self):
        run, review = self.reviewed()
        code, result = self.verify(run, review)
        self.assertEqual((code, result['status']), (0, 'PASS_PREVIEW'))
        self.assertFalse(result['runtime_tested'])

    def test_bad_render_never_passes(self):
        for mode in ('missing_png', 'missing_tree', 'bad_tree', 'corrupt', 'extra', 'exit_error'):
            with self.subTest(mode=mode):
                code, result = self.render(mode)
                self.assertEqual((code, result['status']), (1, 'FAIL_PREVIEW'))
                self.assertTrue((Path(result['run_dir']) / 'report.json').is_file())

    def test_timeout_preserves_failure(self):
        code, result = self.render('timeout', '0.2')
        self.assertEqual(code, 1, result)
        report = json.loads((Path(result['run_dir']) / 'report.json').read_text())
        self.assertTrue(report['cases'][0]['command']['timed_out'])

    def test_source_change_invalidates_review(self):
        run, review = self.reviewed()
        self.source.write_text('// changed\n')
        self.assertEqual(self.verify(run, review)[0], 2)

    def test_untracked_source_invalidates_review(self):
        run, review = self.reviewed()
        (self.project / 'NewScreen.kt').write_text('// new\n')
        self.assertEqual(self.verify(run, review)[0], 2)

    def test_artifact_change_invalidates_review(self):
        run, review = self.reviewed()
        (run / review['cases'][0]['images_reviewed'][0]).write_bytes(b'changed')
        self.assertEqual(self.verify(run, review)[0], 2)

    def test_manifest_change_invalidates_review(self):
        run, review = self.reviewed()
        self.manifest['cases'][0]['requirements'][0]['text'] = 'Weaker requirement'
        self.save_manifest()
        self.assertEqual(self.verify(run, review)[0], 2)

    def test_external_reference_change_invalidates_review(self):
        ref = self.base / 'spec.txt'
        ref.write_text('original')
        self.manifest['references'] = [{'id': 'spec', 'path': str(ref), 'kind': 'spec'}]
        self.manifest['cases'][0]['reference_ids'] = ['spec']
        self.save_manifest()
        run, review = self.reviewed()
        ref.write_text('changed')
        self.assertEqual(self.verify(run, review)[0], 2)

    def test_missing_review_fields_block(self):
        run, review = self.reviewed()
        for field, replacement in [('cases', []), ('run_id', 'another-run'), ('reviewer', ''), ('reviewed_at', '')]:
            with self.subTest(field=field):
                candidate = copy.deepcopy(review)
                candidate[field] = replacement
                self.assertEqual(self.verify(run, candidate)[0], 2)
        for field in ('checks', 'images_reviewed'):
            candidate = copy.deepcopy(review)
            candidate['cases'][0][field] = []
            self.assertEqual(self.verify(run, candidate)[0], 2)

    def test_unknown_evidence_blocks(self):
        run, review = self.reviewed()
        review['cases'][0]['checks'][0]['evidence'] = ['../../unrelated.png']
        self.assertEqual(self.verify(run, review)[0], 2)

    def test_non_object_review_blocks(self):
        run, _ = self.reviewed()
        self.assertEqual(self.verify(run, [])[0], 2)

    def test_different_run_review_blocks(self):
        _, review = self.reviewed()
        code, result = self.render()
        self.assertEqual(code, 0)
        self.assertEqual(self.verify(Path(result['run_dir']), review)[0], 2)

    def test_duplicate_manifest_case_blocks(self):
        self.manifest['cases'].append(copy.deepcopy(self.manifest['cases'][0]))
        self.save_manifest()
        self.assertEqual(self.render()[0], 2)

    def test_fail_and_uncertainty_stay_distinct(self):
        run, review = self.reviewed()
        review['cases'][0]['checks'][0]['status'] = 'FAIL'
        self.assertEqual(self.verify(run, review)[0], 1)
        review['cases'][0]['checks'][0]['status'] = 'NEEDS_REVIEW'
        self.assertEqual(self.verify(run, review)[0], 3)

    def test_unresolved_finding_prevents_pass(self):
        run, review = self.reviewed()
        review['cases'][0]['findings'] = [{'id': 'UI-001', 'description': 'Unresolved layout issue', 'evidence': review['cases'][0]['images_reviewed']}]
        self.assertEqual(self.verify(run, review)[0], 1)

    def test_missing_design_is_blocked(self):
        self.manifest['cases'][0]['review_kind'] = 'design'
        self.save_manifest()
        self.assertEqual(self.render()[0], 2)

    def test_missing_cli_is_blocked(self):
        self.fake.unlink()
        self.assertEqual(self.render()[0], 2)

    def test_runs_inside_project_are_blocked(self):
        code, _ = self.invoke('render', '--project', self.project, '--manifest', self.manifest_path, '--android-bin', self.fake, '--runs-dir', self.project / 'build')
        self.assertEqual(code, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
