#!/usr/bin/env python3
"""Kiểm tra tự động spec Screen + Description.

Usage: python3 check_spec.py <spec.md> [--json]
Exit code 1 khi có ERROR.
"""

import json
import re
import sys
from pathlib import Path

SECTIONS = {
    "overview": ("tổng quan", "thông tin chung"),
    "detail": ("mô tả chi tiết",),
    "remote": ("remote config",),
    "event": ("event tracking",),
}
BLOCK_ORDER = ["**Mô tả:**", "**Flow:**", "**Logic:**", "**Logic click button:**", "**Remote config:**"]
IDENT_RE = re.compile(r"`([a-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)`")
SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
PO_RE = re.compile(r"PO confirm", re.IGNORECASE)
MODULE_RE = re.compile(r"^###\s+(~~)?\d+\.")
JSON_FIELD_RE = re.compile(r'"([A-Za-z][A-Za-z0-9_]*)"\s*:')

def split_row(line):
    """Tách 1 dòng bảng markdown thành các ô, bỏ qua `\\|` đã escape."""
    body = line.strip().strip("|")
    cells = re.split(r"(?<!\\)\|", body)
    return [c.strip() for c in cells]


def is_separator(cells):
    return all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c)


def is_h2(lines, i):
    """Heading cấp 2 dạng `## X` hoặc setext (X + dòng `---`, kiểu Confluence export)."""
    if lines[i].startswith("## "):
        return True
    return (
        bool(lines[i].strip())
        and not lines[i].lstrip().startswith(("|", "#", "*", "-"))
        and i + 1 < len(lines)
        and re.fullmatch(r"-{3,}", lines[i + 1].strip()) is not None
    )


def parse_sections(lines):
    """Trả về {key: (start, end)} theo heading cấp 2."""
    heads = [(i, lines[i]) for i in range(len(lines)) if is_h2(lines, i)]
    found = {}
    for idx, (i, ln) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        title = ln.lower()
        for key, kws in SECTIONS.items():
            if any(kw in title for kw in kws) and key not in found:
                found[key] = (i, end)
    return found


def parse_tables(lines, start, end):
    """Yield (line_no, header_cells, [(line_no, cells)]) cho mỗi bảng trong khoảng."""
    i = start
    while i < end:
        if lines[i].lstrip().startswith("|") and i + 1 < end and is_separator(split_row(lines[i + 1])):
            header = split_row(lines[i])
            rows = []
            j = i + 2
            while j < end and lines[j].lstrip().startswith("|"):
                rows.append((j + 1, split_row(lines[j])))
                j += 1
            yield i + 1, header, rows
            i = j
        else:
            i += 1


def check(text):
    lines = text.splitlines()
    findings = []

    def add(sev, line, msg):
        findings.append({"severity": sev, "line": line, "message": msg})

    sections = parse_sections(lines)
    for key, kws in SECTIONS.items():
        if key not in sections:
            add("ERROR", 0, f"Thiếu mục '{kws[0]}'")

    remote_keys, event_names = {}, {}
    if "remote" in sections:
        for _, header, rows in parse_tables(lines, *sections["remote"]):
            for ln, cells in rows:
                m = re.fullmatch(r"`([^`]+)`", cells[0]) if cells else None
                if not m:
                    continue
                if m.group(1) in remote_keys:
                    add("ERROR", ln, f"Key `{m.group(1)}` trùng (đã có ở dòng {remote_keys[m.group(1)]})")
                    continue
                remote_keys[m.group(1)] = ln
                if len(cells) < 2 or not cells[1]:
                    add("ERROR", ln, f"Key `{m.group(1)}` thiếu default")
    if "event" in sections:
        for _, header, rows in parse_tables(lines, *sections["event"]):
            for ln, cells in rows:
                m = re.fullmatch(r"`([^`]+)`", cells[-1]) if cells else None
                if not m:
                    continue
                name = m.group(1)
                if name in event_names:
                    add("ERROR", ln, f"Event `{name}` trùng (đã có ở dòng {event_names[name]})")
                else:
                    event_names[name] = ln
                if not SNAKE_RE.match(name):
                    add("ERROR", ln, f"Event `{name}` không phải snake_case")

    # Field trong JSON (vd "watch_1_ad": 10) không phải key remote / event.
    json_fields = set(JSON_FIELD_RE.findall(text))
    # Tên khai báo ở cột đầu bảng trong phần Tổng quan (vd asset `anim_confetti`) là hợp lệ.
    declared = set()
    if "overview" in sections:
        for _, _, rows in parse_tables(lines, *sections["overview"]):
            for _, cells in rows:
                m = re.fullmatch(r"`([^`]+)`", cells[0]) if cells else None
                if m:
                    declared.add(m.group(1))
    if "detail" in sections:
        d_start, d_end = sections["detail"]
        # Chỉ heading đánh số mới là module; "### FIRST OPEN" kiểu đoạn giới thiệu thì bỏ qua.
        modules = [i for i in range(d_start, d_end) if MODULE_RE.match(lines[i])]
        for idx, m_start in enumerate(modules):
            m_end = modules[idx + 1] if idx + 1 < len(modules) else d_end
            title = lines[m_start][4:].strip()
            if title.startswith("~~"):
                continue
            screen_tables = [
                t for t in parse_tables(lines, m_start, m_end)
                if [c.lower() for c in t[1][:3]] == ["screen", "description", "ui"]
            ]
            if not screen_tables:
                add("WARN", m_start + 1, f"Module '{title}' không có bảng Screen | Description | UI")
            for _, _, rows in screen_tables:
                for ln, cells in rows:
                    if cells[0].startswith("~~") or len(cells) < 2:
                        continue
                    name = cells[0].strip("* ")
                    # `|` trần hoặc bảng con trong ô làm tách thừa cột: gộp mọi ô giữa
                    # cột đầu (Screen) và cột cuối (UI) thành Description.
                    if len(cells) >= 3:
                        desc, ui = "|".join(cells[1:-1]), cells[-1]
                    else:
                        desc, ui = cells[1], ""
                    if "**Mô tả:**" not in desc and "**Logic:**" not in desc:
                        # Hàng logic (không có ảnh UI) như "Bảng coin" chỉ cần nội dung rõ ràng.
                        sev = "ERROR" if ui else "WARN"
                        add(sev, ln, f"'{name}': thiếu khối Mô tả và Logic")
                    positions = [desc.find(b) for b in BLOCK_ORDER if b in desc]
                    if positions != sorted(positions):
                        add("WARN", ln, f"'{name}': thứ tự khối sai (chuẩn: Mô tả → Flow → Logic → Logic click button → Remote config)")
                    if not ui and "**Mô tả:**" in desc:
                        add("INFO", ln, f"'{name}': cột UI trống, ghi [design pending] nếu chưa có ảnh")
        for i in range(d_start, d_end):
            for ident in IDENT_RE.findall(lines[i]):
                if ident not in remote_keys and ident not in event_names and ident not in json_fields and ident not in declared:
                    add("WARN", i + 1, f"`{ident}` không có trong bảng Remote config hay Event tracking")

    # Key được coi là "có dùng" khi nhắc ở bất kỳ đâu ngoài chính bảng Remote config.
    r_start, r_end = sections.get("remote", (0, 0))
    used = {
        ident
        for i, line in enumerate(lines)
        if not r_start <= i < r_end
        for ident in IDENT_RE.findall(line)
    }
    for key, ln in remote_keys.items():
        if key not in used:
            add("INFO", ln, f"Key `{key}` không được nhắc ngoài bảng Remote config")

    for i, line in enumerate(lines):
        if line.startswith("*Quy ước"):
            continue
        row_name = split_row(line)[0].strip("*~ ") if line.lstrip().startswith("|") else ""
        for m in PO_RE.finditer(line):
            if line[: m.start()].count("~~") % 2 == 1:
                continue  # còn `~~` chưa đóng phía trước → nằm trong đoạn gạch ngang (backlog)
            ctx = re.sub(r"<br>|\s+", " ", line[max(0, m.start() - 80): m.end() + 40]).strip()
            prefix = f"[{row_name}] " if row_name else ""
            add("INFO", i + 1, f"PO confirm: {prefix}…{ctx}…")

    seen, unique = set(), []
    for f in findings:
        k = (f["severity"], f["line"], f["message"])
        if k not in seen:
            seen.add(k)
            unique.append(f)
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    return sorted(unique, key=lambda f: (order[f["severity"]], f["line"]))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    findings = check(Path(argv[1]).read_text(encoding="utf-8"))
    if "--json" in argv:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print(f"{f['severity']:5} L{f['line']:<5} {f['message']}")
        errors = sum(f["severity"] == "ERROR" for f in findings)
        warns = sum(f["severity"] == "WARN" for f in findings)
        print(f"\n{'READY' if errors == 0 else 'NEEDS WORK'} — {errors} ERROR, {warns} WARN")
    return 1 if any(f["severity"] == "ERROR" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
