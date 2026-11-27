#!/usr/bin/env python3
"""Add, remove or inspect one harness hook in a Claude Code settings.json (stdlib only).

Usage:
  settings_hooks.py <install|uninstall|status> --settings <path> --script <path>
                    --run "<interpreter>" --args "<script args>" --event Name[:Matcher] ... [--dry-run]

A hook is "ours" when its command runs a file whose last two path parts match --script
(e.g. skill-telemetry/telemetry.py), so copies of the harness at other paths are recognised.
install keeps an existing hook whose script still exists, repoints one whose script is gone,
and drops duplicates; the first write keeps a one-time backup <settings>.bak-<name>.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["install", "uninstall", "status"])
    p.add_argument("--settings", required=True)
    p.add_argument("--script", required=True)
    p.add_argument("--run", required=True, help="interpreter, e.g. python3 or bash")
    p.add_argument("--args", default="")
    p.add_argument("--event", action="append", required=True)
    p.add_argument("--timeout", type=int, default=5)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)

    settings_path = Path(a.settings).expanduser()
    script = Path(a.script)
    tail = "/".join(script.parts[-2:])
    command = f'{a.run} "{script}" {a.args}'.strip()
    ours_re = re.compile(rf'"?([^"\s]*{re.escape(tail)})"?(?:\s|$)')
    events = dict((e.split(":", 1) + [""])[:2] for e in a.event)

    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text() or "{}")
        except json.JSONDecodeError:
            print(f"ERROR: cannot parse {settings_path}", file=sys.stderr)
            return 2
    hooks = settings.setdefault("hooks", {})

    def ours(event):
        return [(e, h) for e in hooks.get(event, []) for h in e.get("hooks", [])
                if ours_re.search(h.get("command", ""))]

    def script_of(h):
        return ours_re.search(h.get("command", "")).group(1)

    def tidy():
        for event in events:
            if event in hooks:
                hooks[event] = [e for e in hooks[event] if e.get("hooks")]
                if not hooks[event]:
                    hooks.pop(event)
        if not hooks:
            settings.pop("hooks", None)

    def write():
        if a.dry_run:
            print(json.dumps({"hooks": {k: hooks[k] for k in events if k in hooks}}, indent=2))
            return
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        backup = settings_path.with_name(f"{settings_path.name}.bak-{script.stem}")
        if settings_path.exists() and not backup.exists():
            backup.write_text(settings_path.read_text())
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")

    if a.action == "status":
        for event in events:
            found = ours(event)
            print(f"{event}: {'present → ' + script_of(found[0][1]) if found else 'absent'}")
        return 0

    changed, kept = False, set()
    if a.action == "install":
        for event, matcher in events.items():
            found = ours(event)
            if found:
                _, h = found[0]
                if Path(script_of(h)).exists():
                    kept.add(script_of(h))
                else:
                    h["command"] = command
                    changed = True
                for entry, extra in found[1:]:  # never run the same hook twice
                    entry["hooks"].remove(extra)
                    changed = True
                continue
            entry = {"hooks": [{"type": "command", "command": command, "timeout": a.timeout}]}
            if matcher:
                entry["matcher"] = matcher
            hooks.setdefault(event, []).append(entry)
            changed = True
        tidy()
        if changed:
            write()
            print("installed" + (" (dry-run)" if a.dry_run else ""))
        else:
            print("already-present" + (f" ({', '.join(sorted(kept))})" if kept else ""))
        return 0

    for event in events:
        for entry, h in ours(event):
            entry["hooks"].remove(h)
            changed = True
    tidy()
    if changed:
        write()
        print("uninstalled")
    else:
        print("not-present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
