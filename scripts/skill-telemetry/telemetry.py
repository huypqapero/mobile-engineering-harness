#!/usr/bin/env python3
"""Skill usage telemetry for mobile-engineering-harness (stdlib only, Python >= 3.9).

Subcommands:
  hook        read one Claude Code hook payload on stdin and append an event; never fails the session
  backfill    import past skill usage from ~/.claude/projects/*/*.jsonl transcripts
  inventory   print the skills installed on this machine (and in --cwd)
  report      aggregate events into Markdown (default) or JSON
  sync        merge local events into a private telemetry git repo, commit and push

Events live in ${MEH_TELEMETRY_DIR:-~/.meh-telemetry}/events/<yyyy-mm>.jsonl.
Prompts are stored in full; only credential-looking strings are masked before writing.
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import datetime as dt
import fcntl
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA_VERSION = 1
IDENTITY_TTL_SECONDS = 24 * 3600
MAX_SESSIONS_IN_STATE = 50

# --------------------------------------------------------------------------- paths


def data_dir() -> Path:
    return Path(os.environ.get("MEH_TELEMETRY_DIR", "~/.meh-telemetry")).expanduser()


def events_dir() -> Path:
    return data_dir() / "events"


def state_path() -> Path:
    return data_dir() / "state.json"


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_HOME", "~/.claude")).expanduser()


# --------------------------------------------------------------------------- redaction

_REDACTIONS = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}")),
    ("aws-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("google-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("slack-token", re.compile(r"\bxox[abposr]-[A-Za-z0-9\-]{10,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}")),
]
_ASSIGNMENT = re.compile(
    r"(?i)\b([A-Za-z0-9_\-]*(?:api[_-]?key|token|secret|passw(?:or)?d|access[_-]?key))(\s*[:=]\s*)(['\"]?)([^\s'\"]{6,})\3"
)


def redact(text: str) -> str:
    """Mask credential-looking substrings; leave everything else untouched."""
    if not text:
        return text
    for kind, pattern in _REDACTIONS:
        text = pattern.sub(f"[REDACTED:{kind}]", text)
    return _ASSIGNMENT.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED:secret]", text)


# --------------------------------------------------------------------------- small helpers

_SLASH = re.compile(r"^\s*/([A-Za-z0-9][\w:.\-]*)(?:\s+(.*))?$", re.S)


def parse_slash(prompt: str):
    """Return (name, args) when the prompt starts with a slash command, else None."""
    m = _SLASH.match(prompt or "")
    if not m:
        return None
    return m.group(1), (m.group(2) or "").strip()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def event_id(*parts: str) -> str:
    return hashlib.sha1("\x1f".join(p or "" for p in parts).encode("utf-8")).hexdigest()[:16]


def _run(cmd, cwd=None, timeout=3.0) -> str:
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


@contextlib.contextmanager
def locked(path: Path, mode: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield fh
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def load_state() -> dict:
    try:
        return json.loads(state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# --------------------------------------------------------------------------- identity + repo


def identity(state: dict) -> dict:
    """GitHub login and git email, cached in state for a day."""
    override = os.environ.get("MEH_TELEMETRY_LOGIN")
    if override:
        return {"login": override, "git_email": os.environ.get("MEH_TELEMETRY_EMAIL", "")}
    cached = state.get("identity") or {}
    if cached.get("login") and cached.get("at", 0) + IDENTITY_TTL_SECONDS > dt.datetime.now().timestamp():
        return {"login": cached["login"], "git_email": cached.get("git_email", "")}
    login = _run(["gh", "api", "user", "-q", ".login"])
    email = _run(["git", "config", "--global", "user.email"])
    ident = {"login": login or cached.get("login", ""), "git_email": email or cached.get("git_email", "")}
    state["identity"] = {**ident, "at": dt.datetime.now().timestamp()}
    return ident


_REMOTE = re.compile(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$")


def repo_of(cwd: str) -> str:
    """owner/repo from the origin remote, else the top-level folder name."""
    if not cwd:
        return ""
    if os.environ.get("MEH_TELEMETRY_NO_GIT"):
        return Path(cwd).name
    url = _run(["git", "-C", cwd, "remote", "get-url", "origin"])
    m = _REMOTE.search(url) if url else None
    if m:
        return m.group(1)
    top = _run(["git", "-C", cwd, "rev-parse", "--show-toplevel"])
    return Path(top or cwd).name


# --------------------------------------------------------------------------- inventory


def _skill_names(skill_md: Path) -> set:
    """Folder name plus frontmatter name: `/git` and `ck:git` both refer to skills/git."""
    names = {skill_md.parent.name}
    try:
        head = skill_md.read_text(encoding="utf-8", errors="ignore")[:2000]
    except OSError:
        return names
    m = re.search(r"^name:\s*['\"]?([^'\"\n]+)", head, re.M)
    if m and m.group(1).strip():
        names.add(m.group(1).strip())
    return names


def _plugin_name(skill_md: Path, stop: Path) -> str:
    """Name from the nearest .claude-plugin/plugin.json above a plugin skill."""
    d = skill_md.parent
    while d != stop and d != d.parent:
        manifest = d / ".claude-plugin" / "plugin.json"
        if manifest.exists():
            try:
                return json.loads(manifest.read_text(encoding="utf-8")).get("name") or d.name
            except (OSError, ValueError):
                return d.name
        d = d.parent
    return ""


def installed_skills(cwd: str = "") -> dict:
    """{'user': [...], 'plugin': [...], 'project': [...]} of installed skill names."""
    home = claude_home()
    found = {"user": set(), "plugin": set(), "project": set()}
    for p in glob.glob(str(home / "skills" / "*" / "SKILL.md")):
        found["user"] |= _skill_names(Path(p))
    plugins = home / "plugins"
    for p in glob.glob(str(plugins / "**" / "SKILL.md"), recursive=True):
        names = _skill_names(Path(p))
        plugin = _plugin_name(Path(p), plugins)
        found["plugin"] |= names | {f"{plugin}:{n}" for n in names if plugin}
    if cwd:
        for p in glob.glob(str(Path(cwd) / ".claude" / "skills" / "*" / "SKILL.md")):
            found["project"] |= _skill_names(Path(p))
    return {k: sorted(v) for k, v in found.items()}


# --------------------------------------------------------------------------- writing events


def month_file(ts: str) -> Path:
    return events_dir() / f"{ts[:7]}.jsonl"


def append_events(events) -> int:
    by_file = collections.defaultdict(list)
    for e in events:
        by_file[month_file(e["ts"])].append(e)
    n = 0
    for path, items in by_file.items():
        with locked(path, "a") as fh:
            for e in items:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
                n += 1
    return n


def make_event(kind: str, ident: dict, repo: str, session: str, ts: str = "", **fields) -> dict:
    ts = ts or now_iso()
    e = {"v": SCHEMA_VERSION, "ts": ts, "kind": kind, "login": ident.get("login", ""),
         "git_email": ident.get("git_email", ""), "repo": repo, "session": session or ""}
    for key in ("prompt", "args"):
        if key in fields:
            fields[key] = redact(fields[key] or "")
    e.update(fields)
    e["id"] = event_id(kind, e["session"], ts, fields.get("skill", ""), fields.get("source", ""), repo)
    return e


def _remember_prompt(state: dict, session: str, prompt: str) -> None:
    prompts = state.setdefault("last_prompt", {})
    prompts.pop(session, None)
    prompts[session] = prompt
    while len(prompts) > MAX_SESSIONS_IN_STATE:
        prompts.pop(next(iter(prompts)))


def handle_hook(payload: dict) -> list:
    """Turn one hook payload into zero or more events. Pure apart from state and git lookups."""
    name = payload.get("hook_event_name", "")
    session = payload.get("session_id", "")
    cwd = payload.get("cwd", "")
    state = load_state()
    out = []

    if name == "UserPromptSubmit":
        prompt = payload.get("prompt", "") or ""
        _remember_prompt(state, session, prompt)
        slash = parse_slash(prompt)
        if slash:
            ident = identity(state)
            out.append(make_event("skill", ident, repo_of(cwd), session, skill=slash[0], args=slash[1],
                                  source="slash", prompt=prompt))
    elif name == "PreToolUse" and payload.get("tool_name") == "Skill":
        tool_input = payload.get("tool_input") or {}
        ident = identity(state)
        out.append(make_event("skill", ident, repo_of(cwd), session, skill=tool_input.get("skill", ""),
                              args=str(tool_input.get("args", "") or ""), source="model",
                              prompt=(state.get("last_prompt") or {}).get(session, "")))
    elif name == "SessionStart":
        today = now_iso()[:10]
        repo = repo_of(cwd)
        seen = state.setdefault("inventory_seen", {})
        key_user, key_repo = f"user:{today}", f"repo:{repo}:{today}"
        if key_user not in seen or (repo and key_repo not in seen):
            ident = identity(state)
            inv = installed_skills(cwd)
            out.append(make_event("inventory", ident, repo, session, skills=inv))
            seen[key_user] = seen[key_repo] = True
            for k in [k for k in seen if not k.endswith(today)]:
                seen.pop(k)
    save_state(state)
    return out


def cmd_hook(_args) -> int:
    if os.environ.get("MEH_TELEMETRY") == "0":  # per-shell opt-out without uninstalling
        return 0
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        events = handle_hook(payload)
        if events:
            append_events(events)
    except Exception as exc:  # the hook must never break a session
        with contextlib.suppress(Exception):
            data_dir().mkdir(parents=True, exist_ok=True)
            with open(data_dir() / "hook-errors.log", "a", encoding="utf-8") as fh:
                fh.write(f"{now_iso()} {type(exc).__name__}: {exc}\n")
    return 0


# --------------------------------------------------------------------------- backfill

_CMD_NAME = re.compile(r"<command-name>/?([^<]+)</command-name>")
_CMD_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)
_INJECTED_PREFIXES = ("<", "Base directory for this skill", "Caveat:", "[Request interrupted")


def _texts(content):
    if isinstance(content, str):
        yield content
    elif isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                yield c.get("text", "")


def parse_transcript(lines, ident: dict, repo_lookup=repo_of):
    """Yield backfill events from transcript JSONL lines."""
    last_prompt = ""
    repo_cache = {}
    for line in lines:
        try:
            o = json.loads(line)
        except ValueError:
            continue
        ts = o.get("timestamp")
        if not ts or o.get("isMeta"):
            continue  # no stable timestamp means no stable id; meta rows are injected, not typed
        msg = o.get("message") or {}
        role = msg.get("role") or o.get("type")
        content = msg.get("content")
        session = o.get("sessionId", "")
        cwd = o.get("cwd", "")
        if cwd not in repo_cache:
            repo_cache[cwd] = repo_lookup(cwd)
        repo = repo_cache[cwd]
        if role == "user":
            for text in _texts(content):
                m = _CMD_NAME.search(text)
                if m:
                    a = _CMD_ARGS.search(text)
                    args = (a.group(1).strip() if a else "")
                    name = m.group(1).strip()
                    prompt = f"/{name} {args}".strip()
                    last_prompt = prompt
                    yield make_event("skill", ident, repo, session, ts=ts, skill=name, args=args,
                                     source="backfill-slash", prompt=prompt)
                elif text.strip() and not text.lstrip().startswith(_INJECTED_PREFIXES):
                    last_prompt = text
        elif role == "assistant" and isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                    inp = c.get("input") or {}
                    yield make_event("skill", ident, repo, session, ts=ts, skill=inp.get("skill", ""),
                                     args=str(inp.get("args", "") or ""), source="backfill-model",
                                     prompt=last_prompt)


def existing_ids(paths) -> set:
    ids = set()
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    with contextlib.suppress(ValueError, KeyError):
                        ids.add(json.loads(line)["id"])
        except OSError:
            continue
    return ids


def live_sessions(root: Path) -> set:
    """Sessions already recorded by the hook; backfill skips them to avoid double counting."""
    return {e.get("session") for e in load_events(root)
            if e.get("kind") == "skill" and e.get("source") in ("slash", "model")}


def cmd_backfill(args) -> int:
    state = load_state()
    ident = identity(state)
    save_state(state)
    known = existing_ids(glob.glob(str(events_dir() / "*.jsonl")))
    hooked = live_sessions(events_dir()) if events_dir().exists() else set()
    files = sorted(glob.glob(str(claude_home() / "projects" / "*" / "*.jsonl")))
    fresh = []
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                for e in parse_transcript(fh, ident):
                    if e["id"] not in known and e["session"] not in hooked:
                        known.add(e["id"])
                        fresh.append(e)
        except OSError:
            continue
    n = 0 if args.dry_run else append_events(fresh)
    print(f"transcripts={len(files)} new_events={len(fresh)} written={n}")
    return 0


# --------------------------------------------------------------------------- report


def load_events(root: Path):
    for p in sorted(root.rglob("*.jsonl")):
        with open(p, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                with contextlib.suppress(ValueError):
                    yield json.loads(line)


def build_report(events, since_days: int = 0, login: str = "", prompts: int = 3) -> dict:
    cutoff = ""
    if since_days:
        cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=since_days)).isoformat()
    seen, uses, inventories = set(), [], {}
    for e in events:
        if e.get("id") in seen:
            continue
        seen.add(e.get("id"))
        if login and e.get("login") != login:
            continue
        if e.get("kind") == "inventory":
            who = e.get("login", "")
            if e["ts"] >= inventories.get(who, {}).get("ts", ""):
                inventories[who] = e
        elif e.get("kind") == "skill" and (not cutoff or e.get("ts", "") >= cutoff):
            uses.append(e)

    installed = set()
    for inv in inventories.values():
        for names in (inv.get("skills") or {}).values():
            installed.update(names)
    # Without an inventory every slash name counts. With one, built-ins like /clear are split out;
    # names the Skill tool loaded or namespaced names (plugin:skill) are skills even when not on disk.
    known = installed | {e.get("skill", "") for e in uses
                         if "model" in e.get("source", "") or ":" in e.get("skill", "")}
    commands = [e for e in uses if installed and e.get("skill", "") not in known]
    uses = [e for e in uses if not installed or e.get("skill", "") in known]

    per_skill = {}
    for e in sorted(uses, key=lambda x: x.get("ts", "")):
        s = per_skill.setdefault(e.get("skill", ""), {"skill": e.get("skill", ""), "total": 0, "slash": 0,
                                                       "model": 0, "users": set(), "last": "", "prompts": []})
        s["total"] += 1
        s["model" if "model" in e.get("source", "") else "slash"] += 1
        s["users"].add(e.get("login", ""))
        s["last"] = e.get("ts", "")
        p = (e.get("prompt") or "").strip()
        if p and p not in s["prompts"]:
            s["prompts"].append(p)
    skills = []
    for s in per_skill.values():
        skills.append({**s, "users": sorted(u for u in s["users"] if u),
                       "prompts": list(reversed(s["prompts"]))[:prompts]})
    skills.sort(key=lambda s: (-s["total"], s["skill"]))

    per_user = {}
    for e in uses:
        u = per_user.setdefault(e.get("login", ""), collections.Counter())
        u[e.get("skill", "")] += 1
    users = [{"login": k, "total": sum(c.values()), "top": c.most_common(5)} for k, c in per_user.items()]
    users.sort(key=lambda u: -u["total"])

    used = {s["skill"] for s in skills}
    return {
        "generated_at": now_iso(),
        "since_days": since_days,
        "total_uses": len(uses),
        "commands": collections.Counter(e.get("skill", "") for e in commands).most_common(),
        "skills": skills,
        "users": users,
        "installed_count": len(installed),
        "installed_unused": sorted(installed - used),
    }


def render_markdown(r: dict) -> str:
    window = f"{r['since_days']} ngày gần nhất" if r["since_days"] else "toàn bộ dữ liệu"
    out = [f"# Skill telemetry ({window})", "",
           f"Tổng lượt gọi: {r['total_uses']} · Skill đã cài: {r['installed_count']}", "",
           "## Skill dùng nhiều nhất", "", "| Skill | Tổng | Slash | Model | Người dùng | Lần cuối |",
           "|---|---|---|---|---|---|"]
    for s in r["skills"][:25]:
        out.append(f"| `{s['skill']}` | {s['total']} | {s['slash']} | {s['model']} | "
                   f"{', '.join(s['users'])} | {s['last'][:10]} |")
    out += ["", "## Theo người", "", "| Login | Tổng | Top skill |", "|---|---|---|"]
    for u in r["users"]:
        out.append(f"| {u['login'] or '(không rõ)'} | {u['total']} | "
                   f"{', '.join(f'{k} ({n})' for k, n in u['top'])} |")
    out += ["", "## Mẫu prompt", ""]
    for s in [s for s in r["skills"] if s["prompts"]][:15]:
        out.append(f"### `{s['skill']}`")
        out += [f"- {p[:300].replace(chr(10), ' ')}" for p in s["prompts"]]
        out.append("")
    if r["commands"]:
        out += ["## Lệnh có sẵn của Claude Code (không tính là skill)", "",
                ", ".join(f"`/{k}` ({n})" for k, n in r["commands"]), ""]
    if r["installed_unused"]:
        out += ["## Đã cài nhưng chưa dùng", "", ", ".join(f"`{n}`" for n in r["installed_unused"]), ""]
    return "\n".join(out)


def cmd_report(args) -> int:
    root = Path(args.data).expanduser() if args.data else events_dir()
    r = build_report(load_events(root), args.since, args.login or "", args.prompts)
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.json else render_markdown(r))
    return 0


# --------------------------------------------------------------------------- sync


def merge_into(target_root: Path, events, default_login: str, write: bool = True) -> int:
    """Append events missing from target_root/data/<login>/<yyyy-mm>.jsonl. Returns rows added (or to add)."""
    grouped = collections.defaultdict(list)
    for e in events:
        who = e.get("login") or default_login or "unknown"
        grouped[target_root / "data" / who / f"{e['ts'][:7]}.jsonl"].append(e)
    added = 0
    for path, items in grouped.items():
        known = existing_ids([path])
        new = []
        for e in items:
            if e["id"] in known:
                continue
            known.add(e["id"])
            for key in ("prompt", "args"):
                if key in e:
                    e[key] = redact(e[key])
            new.append(e)
        if new and write:
            with locked(path, "a") as fh:
                for e in new:
                    fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        added += len(new)
    return added


def _git(cwd: Path, *args, check=True):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=check)


def cmd_sync(args) -> int:
    state = load_state()
    ident = identity(state)
    save_state(state)
    if not ident.get("login"):
        print("ERROR: không xác định được GitHub login (chạy `gh auth login` hoặc đặt MEH_TELEMETRY_LOGIN)",
              file=sys.stderr)
        return 2
    clone = Path(args.dir).expanduser() if args.dir else data_dir() / "remote"
    if not (clone / ".git").exists():
        clone.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["gh", "repo", "clone", args.repo, str(clone)], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"ERROR: không clone được {args.repo}: {r.stderr.strip()}", file=sys.stderr)
            return 2
    else:
        _git(clone, "pull", "--rebase", "--quiet", check=False)
    events = list(load_events(events_dir()))
    if args.dry_run:
        added = merge_into(clone, events, ident["login"], write=False)
        print(f"dry-run: {added} event mới sẽ được đẩy lên {args.repo}")
        return 0
    added = merge_into(clone, events, ident["login"])
    if not added:
        print("không có event mới")
        return 0
    _git(clone, "add", "data")
    _git(clone, "commit", "--quiet", "-m", f"chore(telemetry): sync {ident['login']} ({added} events)")
    push = _git(clone, "push", "--quiet", check=False)
    if push.returncode != 0:
        print(f"ERROR: push thất bại: {push.stderr.strip()}", file=sys.stderr)
        return 1
    print(f"đã đẩy {added} event lên {args.repo}")
    return 0


# --------------------------------------------------------------------------- CLI


def cmd_inventory(args) -> int:
    print(json.dumps(installed_skills(args.cwd or ""), ensure_ascii=False, indent=2))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hook").set_defaults(fn=cmd_hook)
    b = sub.add_parser("backfill")
    b.add_argument("--dry-run", action="store_true")
    b.set_defaults(fn=cmd_backfill)
    i = sub.add_parser("inventory")
    i.add_argument("--cwd", default=os.getcwd())
    i.set_defaults(fn=cmd_inventory)
    r = sub.add_parser("report")
    r.add_argument("--data", help="thư mục chứa *.jsonl (mặc định: event cục bộ)")
    r.add_argument("--since", type=int, default=30, help="số ngày gần nhất, 0 = tất cả")
    r.add_argument("--login")
    r.add_argument("--prompts", type=int, default=3, help="số mẫu prompt mỗi skill")
    r.add_argument("--json", action="store_true")
    r.set_defaults(fn=cmd_report)
    s = sub.add_parser("sync")
    s.add_argument("--repo", required=True, help="owner/repo private chứa telemetry")
    s.add_argument("--dir", help="thư mục clone (mặc định ~/.meh-telemetry/remote)")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_sync)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
