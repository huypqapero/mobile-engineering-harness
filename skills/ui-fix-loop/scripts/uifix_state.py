#!/usr/bin/env python3
"""uifix_state.py — registry Figma reference + bo dem vong fix cho ui-fix-loop.

Chi LUU / DEM / ENFORCE tran 3 vong; KHONG cham diem (model cham qua ui-diff-review).

Lenh:
  ref-add  --refs F.json --screen S --url FIGMA_URL [--spec P] [--source P ...]
           [--module :app] [--preview-fqn FQN] [--note T]
  ref-get  --refs F.json --screen S
  bug-new  --state-dir D --id BUG --screen S [--desc T] [--max-rounds 3] [--threshold 95]
  bug-record --state-dir D --id BUG --kind baseline|fix --score N [--board P] [--note T]
  bug-status --state-dir D [--id BUG]

Exit bug-record: 0 = PASS (score>=threshold), 2 = con vong de fix, 3 = STUCK (het 3 vong fix).
"""
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load(p, default):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def save(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def parse_figma(url):
    u = urlparse(url)
    m = re.search(r"/(?:file|design|proto)/([A-Za-z0-9]+)", u.path)
    if not m:
        sys.exit(f"khong tach duoc fileKey tu URL: {url}")
    node = parse_qs(u.query).get("node-id", [None])[0]
    if not node:
        sys.exit("URL thieu node-id (copy link cua frame/node, khong phai file)")
    return m.group(1), node.replace("-", ":")


def cmd_ref_add(a):
    file_key, node_id = parse_figma(a.url)
    refs = load(a.refs, {"screens": {}})
    cur = refs["screens"].get(a.screen, {})
    cur.update({"figma_url": a.url, "file_key": file_key, "node_id": node_id, "updated": now()})
    for k, v in (("spec", a.spec), ("module", a.module), ("preview_fqn", a.preview_fqn), ("note", a.note)):
        if v:
            cur[k] = v
    if a.source:
        cur["source_files"] = sorted(set(cur.get("source_files", []) + a.source))
    refs["screens"][a.screen] = cur
    save(a.refs, refs)
    print(json.dumps({a.screen: cur}, ensure_ascii=False, indent=2))


def cmd_ref_get(a):
    cur = load(a.refs, {"screens": {}})["screens"].get(a.screen)
    if not cur:
        sys.exit(f"chua co ref cho man '{a.screen}' trong {a.refs}")
    print(json.dumps(cur, ensure_ascii=False, indent=2))


def bug_path(a):
    return Path(a.state_dir) / f"{a.id}.json"


def cmd_bug_new(a):
    p = bug_path(a)
    if p.exists():
        sys.exit(f"bug {a.id} da ton tai: {p}")
    save(p, {"id": a.id, "screen": a.screen, "desc": a.desc, "max_rounds": a.max_rounds,
             "threshold": a.threshold, "status": "open", "history": [], "created": now()})
    print(f"created {p}")


def fix_rounds(b):
    return sum(1 for h in b["history"] if h["kind"] == "fix")


def cmd_bug_record(a):
    p = bug_path(a)
    b = load(p, None)
    if b is None:
        sys.exit(f"chua co bug {a.id}; chay bug-new truoc")
    if b["status"] in ("pass", "stuck"):
        sys.exit(f"bug {a.id} da dong ({b['status']}); khong ghi them")
    if a.kind == "fix" and fix_rounds(b) >= b["max_rounds"]:
        sys.exit(f"bug {a.id} da het {b['max_rounds']} vong fix")
    b["history"].append({"kind": a.kind, "round": fix_rounds(b) + (1 if a.kind == "fix" else 0),
                         "score": a.score, "board": a.board, "note": a.note, "at": now()})
    if a.score >= b["threshold"]:
        b["status"], code = "pass", 0
    elif fix_rounds(b) >= b["max_rounds"]:
        b["status"], code = "stuck", 3
    else:
        b["status"], code = "open", 2
    save(p, b)
    print(f"{b['status'].upper()} bug={a.id} kind={a.kind} score={a.score} fix_rounds={fix_rounds(b)}/{b['max_rounds']}")
    sys.exit(code)


def cmd_bug_status(a):
    d = Path(a.state_dir)
    files = [d / f"{a.id}.json"] if a.id else sorted(d.glob("*.json"))
    for f in files:
        b = load(f, None)
        if b:
            last = b["history"][-1]["score"] if b["history"] else None
            print(f"{b['id']:<20} {b['screen']:<18} {b['status']:<6} fix={fix_rounds(b)}/{b['max_rounds']} last={last}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("ref-add"); s.add_argument("--refs", required=True); s.add_argument("--screen", required=True)
    s.add_argument("--url", required=True); s.add_argument("--spec"); s.add_argument("--source", action="append")
    s.add_argument("--module"); s.add_argument("--preview-fqn"); s.add_argument("--note"); s.set_defaults(f=cmd_ref_add)
    s = sp.add_parser("ref-get"); s.add_argument("--refs", required=True); s.add_argument("--screen", required=True); s.set_defaults(f=cmd_ref_get)
    s = sp.add_parser("bug-new"); s.add_argument("--state-dir", required=True); s.add_argument("--id", required=True)
    s.add_argument("--screen", required=True); s.add_argument("--desc", default="")
    s.add_argument("--max-rounds", type=int, default=3); s.add_argument("--threshold", type=int, default=95); s.set_defaults(f=cmd_bug_new)
    s = sp.add_parser("bug-record"); s.add_argument("--state-dir", required=True); s.add_argument("--id", required=True)
    s.add_argument("--kind", choices=["baseline", "fix"], required=True); s.add_argument("--score", type=int, required=True)
    s.add_argument("--board"); s.add_argument("--note"); s.set_defaults(f=cmd_bug_record)
    s = sp.add_parser("bug-status"); s.add_argument("--state-dir", required=True); s.add_argument("--id"); s.set_defaults(f=cmd_bug_status)
    a = ap.parse_args(); a.f(a)


if __name__ == "__main__":
    main()
