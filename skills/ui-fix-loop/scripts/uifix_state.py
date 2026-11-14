#!/usr/bin/env python3
"""uifix_state.py — screen registry (spec <-> Figma <-> code) + bo dem vong fix cho ui-fix-loop.

Chi LUU / DEM / ENFORCE tran 3 vong; KHONG cham diem (model cham qua ui-diff-review).

Registry = THU MUC, moi man 1 file `<screen>.json` (mac dinh docs/references/screens),
de nhieu lane song song sua man khac nhau khong conflict. Schema: ui-fix-loop/references/screen-registry.md.

Lenh:
  ref-add   [--refs DIR] --screen S [--url FIGMA_URL] [--name T] [--section T] [--screenshot P]
            [--spec P#muc ...] [--source P ...] [--module :app] [--preview-fqn FQN ...] [--note T]
  ref-get   [--refs DIR] --screen S
  ref-list  [--refs DIR]                       (bang screen | node | preview | spec)
  ref-merge [--refs DIR] --delta F.json        (gop delta {"screens": {...}} hoac {screen: {...}};
                                                nhan ca file figma-refs.json cu de chuyen doi)
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


DEFAULT_REFS = "docs/references/screens"
SCALARS = ("name", "section", "figma_url", "file_key", "node_id", "screenshot", "module", "note")


def screen_file(refs, screen):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", screen):
        sys.exit(f"screen id khong hop le (chi chu, so, . _ -): {screen}")
    return Path(refs) / f"{screen}.json"


def normalize(screen, e):
    """Doc entry ca format cu (spec/preview_fqn la chuoi) lan moi (list)."""
    e = dict(e)
    e["screen"] = screen
    spec = e.get("spec") or []
    e["spec"] = [spec] if isinstance(spec, str) else list(spec)
    previews = e.get("previews") or []
    old_fqn = e.pop("preview_fqn", None)
    if old_fqn:
        previews = previews + [{"fqn": old_fqn}]
    e["previews"] = previews
    e["source_files"] = list(e.get("source_files") or [])
    if e.get("figma_url") and not (e.get("file_key") and e.get("node_id")):
        e["file_key"], e["node_id"] = parse_figma(e["figma_url"])
    return e


def merge_entry(cur, new):
    """Scalar: gia tri moi khac rong thang. List: hop, preview gop theo fqn."""
    for k in SCALARS:
        if new.get(k):
            cur[k] = new[k]
    cur["spec"] = sorted(set(cur.get("spec", []) + new.get("spec", [])))
    cur["source_files"] = sorted(set(cur.get("source_files", []) + new.get("source_files", [])))
    by_fqn = {p["fqn"]: p for p in cur.get("previews", []) if p.get("fqn")}
    for p in new.get("previews", []):
        if p.get("fqn"):
            by_fqn[p["fqn"]] = {**by_fqn.get(p["fqn"], {}), **{k: v for k, v in p.items() if v}}
    cur["previews"] = [by_fqn[k] for k in sorted(by_fqn)]
    cur["updated"] = now()
    return cur


def upsert(refs, screen, new):
    p = screen_file(refs, screen)
    cur = normalize(screen, load(p, {}))
    save(p, merge_entry(cur, normalize(screen, new)))
    return p


def cmd_ref_add(a):
    new = {"name": a.name, "section": a.section, "screenshot": a.screenshot, "module": a.module,
           "note": a.note, "spec": a.spec or [], "source_files": a.source or [],
           "previews": [{"fqn": f, "source": (a.source or [None])[0]} for f in (a.preview_fqn or [])]}
    if a.url:
        new["file_key"], new["node_id"] = parse_figma(a.url)
        new["figma_url"] = a.url
    p = upsert(a.refs, a.screen, new)
    print(p.read_text(), end="")


def cmd_ref_get(a):
    p = screen_file(a.refs, a.screen)
    if not p.exists():
        sys.exit(f"chua co ref cho man '{a.screen}' trong {a.refs}")
    print(json.dumps(normalize(a.screen, load(p, {})), ensure_ascii=False, indent=2))


def cmd_ref_list(a):
    for f in sorted(Path(a.refs).glob("*.json")):
        e = normalize(f.stem, load(f, {}))
        fqn = ",".join(p["fqn"].rsplit(".", 1)[-1] for p in e["previews"]) or "-"
        print(f"{f.stem:<36} {e.get('node_id') or '-':<10} {fqn:<40} {len(e['spec'])} spec")


def cmd_ref_merge(a):
    delta = load(a.delta, None)
    if delta is None:
        sys.exit(f"khong doc duoc {a.delta}")
    screens = delta.get("screens", delta)
    for screen, e in screens.items():
        upsert(a.refs, screen, e)
    print(f"merged {len(screens)} man vao {a.refs}")


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
    s = sp.add_parser("ref-add"); s.add_argument("--refs", default=DEFAULT_REFS); s.add_argument("--screen", required=True)
    s.add_argument("--url"); s.add_argument("--name"); s.add_argument("--section"); s.add_argument("--screenshot")
    s.add_argument("--spec", action="append"); s.add_argument("--source", action="append")
    s.add_argument("--module"); s.add_argument("--preview-fqn", action="append"); s.add_argument("--note"); s.set_defaults(f=cmd_ref_add)
    s = sp.add_parser("ref-get"); s.add_argument("--refs", default=DEFAULT_REFS); s.add_argument("--screen", required=True); s.set_defaults(f=cmd_ref_get)
    s = sp.add_parser("ref-list"); s.add_argument("--refs", default=DEFAULT_REFS); s.set_defaults(f=cmd_ref_list)
    s = sp.add_parser("ref-merge"); s.add_argument("--refs", default=DEFAULT_REFS); s.add_argument("--delta", required=True)
    s.set_defaults(f=cmd_ref_merge)
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
