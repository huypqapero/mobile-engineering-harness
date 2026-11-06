#!/usr/bin/env python3
"""Collect Android CLI preview evidence and verify an explicit visual review."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
import uuid
import zlib


class Blocked(Exception):
    pass


def need(condition, message):
    if not condition:
        raise Blocked(message)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def inside(path, root):
    return path.resolve().is_relative_to(root.resolve())


def git(root, *args):
    p = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=60)
    need(p.returncode == 0, 'Git command failed: ' + p.stderr.decode(errors='replace')[:1000])
    return p.stdout


def project_state(root):
    actual = Path(os.fsdecode(git(root, 'rev-parse', '--show-toplevel')).strip()).resolve()
    need(actual == root, '--project must be the Git project root')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    names = sorted(set(git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0')) - {b''})
    h = hashlib.sha256()
    h.update(head.encode() + b'\0')
    for name in names:
        p = root / os.fsdecode(name)
        need(not p.is_dir() or p.is_symlink(), 'Submodules/directories are unsupported: ' + os.fsdecode(name))
        h.update(name + b'\0')
        if p.is_symlink():
            # Git tracks a symlink as its target path; fingerprint that committed path string
            # (deterministic, no dependency on the external target existing). This lets the runner
            # work in repos that symlink shared agent/harness files into the tree.
            h.update(b'symlink:' + os.fsencode(os.readlink(p)))
        elif p.is_file():
            h.update(str(p.stat().st_mode & 0o777).encode() + b':' + sha(p).encode())
        else:
            h.update(b'<deleted>')
        h.update(b'\0')
    return {'head': head, 'fingerprint': h.hexdigest(), 'file_count': len(names)}


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', value)


def load_manifest(path):
    m = read_json(path)
    need(isinstance(m, dict) and m.get('schema_version') == 1, 'Manifest schema_version must be 1')
    need(isinstance(m.get('feature'), str) and m['feature'].strip(), 'Missing feature')
    need(isinstance(m.get('target'), str) and re.fullmatch(r':[A-Za-z0-9_:.@-]+', m['target']), 'Use a Gradle module target such as :feature:profile')
    refs = m.get('references', [])
    need(isinstance(refs, list), 'references must be a list')
    ref_ids = set()
    for ref in refs:
        need(isinstance(ref, dict) and identifier(ref.get('id')), 'Invalid reference ID')
        need(ref['id'] not in ref_ids, 'Duplicate reference ID')
        ref_ids.add(ref['id'])
        need(ref.get('kind') in ('spec', 'design'), 'Reference kind must be spec or design')
        need(isinstance(ref.get('path'), str) and ref['path'], 'Reference needs a local path')
        need((path.parent / ref['path']).resolve().is_file(), 'Missing reference: ' + ref['path'])
    cases = m.get('cases')
    need(isinstance(cases, list) and 0 < len(cases) <= 100, 'Provide 1..100 cases')
    ids, fqns = set(), set()
    for c in cases:
        need(isinstance(c, dict) and identifier(c.get('id')), 'Invalid case ID')
        need(c['id'] not in ids, 'Duplicate case ID')
        ids.add(c['id'])
        fqn = c.get('fqn')
        need(isinstance(fqn, str) and re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$.]+', fqn), 'Invalid preview FQN')
        need(fqn not in fqns, 'Use separate FQNs for distinct cases')
        fqns.add(fqn)
        count = c.get('expected_images')
        need(type(count) is int and 0 < count <= 100, 'expected_images must be 1..100')
        need(c.get('review_kind') in ('requirements', 'design'), 'Invalid review_kind')
        cr = c.get('reference_ids', [])
        need(isinstance(cr, list) and all(isinstance(x, str) for x in cr) and len(set(cr)) == len(cr) and set(cr) <= ref_ids, 'Unknown/duplicate reference_ids')
        if c['review_kind'] == 'design':
            need(any(r['id'] in cr and r['kind'] == 'design' for r in refs), 'Design review needs a design reference')
        reqs = c.get('requirements')
        need(isinstance(reqs, list) and reqs, 'Each case needs requirements')
        req_ids = set()
        for r in reqs:
            need(isinstance(r, dict) and identifier(r.get('id')), 'Invalid requirement ID')
            need(r['id'] not in req_ids and isinstance(r.get('text'), str) and r['text'].strip(), 'Duplicate/empty requirement')
            req_ids.add(r['id'])
    return m


def command(argv, cwd, prefix, timeout):
    prefix.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    timed_out = False
    with prefix.with_suffix('.stdout.log').open('wb') as out, prefix.with_suffix('.stderr.log').open('wb') as err:
        p = subprocess.Popen(argv, cwd=cwd, stdout=out, stderr=err, start_new_session=(os.name == 'posix'))
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == 'posix':
                os.killpg(p.pid, signal.SIGKILL)
            else:
                p.kill()
            p.wait()
    return {'argv': argv, 'exit_code': p.returncode, 'timed_out': timed_out, 'seconds': round(time.monotonic() - start, 3)}


def png_size(path):
    """Check PNG framing/CRCs; visual decoding remains the reviewer's job."""
    raw = path.read_bytes()
    need(raw[:8] == b'\x89PNG\r\n\x1a\n', 'Invalid PNG signature: ' + path.name)
    at, size, saw_data, saw_end = 8, None, False, False
    while at < len(raw):
        need(at + 12 <= len(raw), 'Truncated PNG: ' + path.name)
        length = struct.unpack('>I', raw[at:at + 4])[0]
        kind = raw[at + 4:at + 8]
        end = at + 12 + length
        need(end <= len(raw), 'Truncated PNG chunk')
        data = raw[at + 8:at + 8 + length]
        crc = struct.unpack('>I', raw[at + 8 + length:end])[0]
        need(zlib.crc32(kind + data) & 0xffffffff == crc, 'Invalid PNG checksum')
        if at == 8:
            need(kind == b'IHDR' and length == 13, 'Missing PNG IHDR')
            size = list(struct.unpack('>II', data[:8]))
            need(all(x > 0 for x in size), 'Empty PNG dimensions')
        if kind == b'IDAT' and length:
            saw_data = True
        at = end
        if kind == b'IEND':
            need(length == 0 and at == len(raw), 'Invalid PNG ending')
            saw_end = True
            break
    need(size and saw_data and saw_end, 'Incomplete PNG')
    return size


def artifact(path, run, kind):
    need(not path.is_symlink() and inside(path, run), 'Artifact escaped run directory')
    result = {'path': path.relative_to(run).as_posix(), 'kind': kind, 'sha256': sha(path)}
    if kind == 'png':
        result['dimensions_px'] = png_size(path)
    else:
        value = read_json(path)
        need(isinstance(value, (dict, list)) and value, 'Empty/non-container JSON: ' + path.name)
    return result


def render(args):
    root = Path(args.project).resolve()
    manifest_path = Path(args.manifest).resolve()
    manifest = load_manifest(manifest_path)
    state = project_state(root)
    base = Path(args.runs_dir).resolve() if args.runs_dir else Path(tempfile.gettempdir()) / 'android-preview-runs'
    need(not inside(base, root), '--runs-dir must be outside the project')
    base.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='preview-', dir=base)).resolve()
    report = {
        'schema_version': 1, 'run_id': str(uuid.uuid4()), 'created_at': now(),
        'scope': 'Compose Preview only', 'feature': manifest['feature'],
        'project': str(root), 'inputs': state, 'manifest_path': str(manifest_path),
        'manifest_sha256': sha(manifest_path), 'manifest': manifest,
        'references': [], 'cases': [], 'status': 'BLOCKED', 'errors': [],
    }
    code = 2
    try:
        for ref in manifest.get('references', []):
            source = (manifest_path.parent / ref['path']).resolve()
            dest = run / 'references' / (ref['id'] + source.suffix)
            dest.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, dest)
            report['references'].append({'id': ref['id'], 'source': str(source), 'path': dest.relative_to(run).as_posix(), 'sha256': sha(dest)})
        binary = shutil.which(args.android_bin)
        need(binary, 'Android CLI executable not found: ' + args.android_bin)
        report['android_binary'] = binary
        for name, tail in [('version', ['--version']), ('capabilities', ['preview', 'render', '--help'])]:
            prefix = run / 'preflight' / name
            cmd = command([binary, *tail], root, prefix, min(args.timeout, 30))
            report[name] = cmd
            need(cmd['exit_code'] == 0 and not cmd['timed_out'], 'Android CLI preflight failed: ' + name)
            if name == 'capabilities':
                help_text = prefix.with_suffix('.stdout.log').read_text(errors='replace') + prefix.with_suffix('.stderr.log').read_text(errors='replace')
                need(all(x in help_text for x in ('--component-tree', '--fqn', '--output', '--format')), 'Installed CLI lacks required preview flags')
        for spec in manifest['cases']:
            case = {'id': spec['id'], 'status': 'RENDER_FAILED', 'artifacts': [], 'errors': []}
            report['cases'].append(case)
            output = run / 'cases' / spec['id'] / 'render'
            output.mkdir(parents=True)
            case['command'] = command([binary, 'preview', 'render', manifest['target'], '--fqn=' + spec['fqn'], '--component-tree', '--format=json', '--output=' + str(output)], root, output.parent / 'command', args.timeout)
            if case['command']['exit_code'] != 0 or case['command']['timed_out']:
                case['errors'].append('CLI command failed or timed out; see logs')
                break
            try:
                pngs = sorted(output.rglob('*.png'))
                trees = sorted(output.rglob('*.json'))
                need(len(pngs) == spec['expected_images'], 'PNG count does not match expected_images')
                need(len(trees) >= len(pngs), 'Missing companion JSON files')
                case['artifacts'] = [artifact(p, run, 'png') for p in pngs] + [artifact(p, run, 'tree') for p in trees]
                case['status'] = 'RENDERED_PENDING_REVIEW'
            except (Blocked, ValueError, OSError) as e:
                case['status'] = 'EVIDENCE_INVALID'
                case['errors'].append(str(e))
        need(project_state(root) == state, 'Project changed during rendering; rerender')
        need(sha(manifest_path) == report['manifest_sha256'], 'Manifest changed during rendering')
        for ref in report['references']:
            need(sha(ref['source']) == ref['sha256'], 'Reference changed during rendering')
        good = len(report['cases']) == len(manifest['cases']) and all(c['status'] == 'RENDERED_PENDING_REVIEW' for c in report['cases'])
        report['status'], code = ('RENDERED_PENDING_REVIEW', 0) if good else ('FAIL_PREVIEW', 1)
    except (Blocked, OSError, ValueError, subprocess.SubprocessError) as e:
        report['status'] = 'BLOCKED'
        report['errors'].append(str(e))
    report['finished_at'] = now()
    write_json(run / 'report.json', report)
    by_id = {c['id']: c for c in report['cases']}
    template = {'run_id': report['run_id'], 'report_sha256': sha(run / 'report.json'), 'reviewer': '', 'reviewed_at': '', 'cases': []}
    for spec in manifest['cases']:
        template['cases'].append({
            'id': spec['id'], 'images_reviewed': [], 'references_reviewed': [],
            'available_images': [a['path'] for a in by_id.get(spec['id'], {}).get('artifacts', []) if a['kind'] == 'png'],
            'checks': [{'id': r['id'], 'status': 'NEEDS_REVIEW', 'evidence': [], 'note': ''} for r in spec['requirements']], 'findings': []})
    write_json(run / 'review-template.json', template)
    return {'status': report['status'], 'run_dir': str(run), 'report': str(run / 'report.json'), 'ui_pass': False}, code


def local_file(run, relative):
    need(isinstance(relative, str) and relative, 'Missing evidence path')
    p = run / relative
    need(not Path(relative).is_absolute() and inside(p, run) and p.is_file() and not p.is_symlink(), 'Invalid evidence path: ' + relative)
    return p


def exact_items(values, expected, label):
    need(isinstance(values, list) and all(isinstance(x, str) for x in values), 'Invalid ' + label)
    need(len(values) == len(expected) and set(values) == set(expected), 'Incomplete/duplicate ' + label)


def verify(args):
    run = Path(args.run_dir).resolve()
    report = read_json(run / 'report.json')
    review = read_json(args.review)
    need(isinstance(report, dict) and isinstance(review, dict), 'Report and review must be JSON objects')
    need(report['status'] == 'RENDERED_PENDING_REVIEW', 'Render did not complete successfully')
    need(review.get('run_id') == report['run_id'] and review.get('report_sha256') == sha(run / 'report.json'), 'Review belongs to different/changed report')
    need(isinstance(review.get('reviewer'), str) and review['reviewer'].strip(), 'Reviewer is required')
    reviewed_at = dt.datetime.fromisoformat(review.get('reviewed_at', '').replace('Z', '+00:00'))
    need(reviewed_at.tzinfo is not None, 'reviewed_at needs timezone')
    need(project_state(Path(report['project'])) == report['inputs'], 'Project changed after rendering')
    need(sha(report['manifest_path']) == report['manifest_sha256'], 'Manifest changed after rendering')
    for ref in report['references']:
        need(sha(ref['source']) == ref['sha256'] == sha(local_file(run, ref['path'])), 'Reference changed')
    cases = review.get('cases')
    need(isinstance(cases, list) and all(isinstance(c, dict) for c in cases), 'Invalid review cases')
    expected = report['manifest']['cases']
    exact_items([c.get('id') for c in cases], [s['id'] for s in expected], 'review cases')
    rendered = {c['id']: c for c in report['cases']}
    reviewed = {c['id']: c for c in cases}
    outcomes = []
    for spec in expected:
        c = reviewed[spec['id']]
        artifacts = rendered[spec['id']]['artifacts']
        allowed = {a['path'] for a in artifacts}
        for a in artifacts:
            need(sha(local_file(run, a['path'])) == a['sha256'], 'Evidence changed: ' + a['path'])
        exact_items(c.get('images_reviewed'), [a['path'] for a in artifacts if a['kind'] == 'png'], 'images_reviewed')
        exact_items(c.get('references_reviewed'), spec.get('reference_ids', []), 'references_reviewed')
        checks = c.get('checks')
        need(isinstance(checks, list) and all(isinstance(x, dict) for x in checks), 'Invalid checks')
        exact_items([x.get('id') for x in checks], [r['id'] for r in spec['requirements']], 'requirement checks')
        for check in checks:
            need(check.get('status') in ('PASS', 'FAIL', 'NEEDS_REVIEW'), 'Invalid check status')
            evidence = check.get('evidence')
            need(isinstance(evidence, list) and evidence and all(isinstance(x, str) and x in allowed for x in evidence), 'Check needs same-case evidence')
            need(isinstance(check.get('note'), str) and check['note'].strip(), 'Check needs explanatory note')
            outcomes.append(check['status'])
        findings = c.get('findings')
        need(isinstance(findings, list), 'findings must be a list')
        for f in findings:
            need(isinstance(f, dict) and f.get('id') and f.get('description'), 'Incomplete finding')
            need(isinstance(f.get('evidence'), list) and f['evidence'] and all(isinstance(x, str) and x in allowed for x in f['evidence']), 'Finding needs same-case evidence')
        if findings:
            outcomes.append('FAIL')
    status, code = ('FAIL_PREVIEW', 1) if 'FAIL' in outcomes else (('NEEDS_REVIEW', 3) if 'NEEDS_REVIEW' in outcomes else ('PASS_PREVIEW', 0))
    verdict = {'status': status, 'scope': 'Compose Preview only', 'run_id': report['run_id'], 'verified_at': now(), 'review_sha256': sha(args.review), 'case_count': len(expected), 'runtime_tested': False}
    write_json(run / 'verdict.json', verdict)
    return verdict, code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    r = sub.add_parser('render')
    r.add_argument('--project', required=True)
    r.add_argument('--manifest', required=True)
    r.add_argument('--runs-dir')
    r.add_argument('--android-bin', default='android')
    r.add_argument('--timeout', type=float, default=600)
    v = sub.add_parser('verify')
    v.add_argument('--run-dir', required=True)
    v.add_argument('--review', required=True)
    args = parser.parse_args()
    try:
        if args.action == 'render':
            need(0 < args.timeout <= 3600, 'timeout must be >0 and <=3600 seconds')
        result, code = render(args) if args.action == 'render' else verify(args)
    except (Blocked, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as e:
        result, code = {'status': 'BLOCKED', 'error': str(e)}, 2
        if args.action == 'verify' and Path(args.run_dir).is_dir():
            write_json(Path(args.run_dir) / 'verdict.json', result)
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
