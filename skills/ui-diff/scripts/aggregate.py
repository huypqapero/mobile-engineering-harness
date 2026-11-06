#!/usr/bin/env python3
"""aggregate.py — gộp kết quả compare nhiều màn thành thống kê + report fix ưu tiên.

Mode video→figma của ui-diff: sau khi mỗi màn đã compare bằng ui-diff-review (ra
findings.json + result.json), script này quét toàn bộ run, tính thống kê và sinh
report-only: tổng điểm, pass/fail, đếm diff theo severity/type, và DANH SÁCH FIX
ƯU TIÊN (gộp finding chưa khớp, sort theo severity rồi confidence).

Layout run mong đợi:
  <run>/screens/<ten-man>/findings.json   (format ui-diff-review findings)
  <run>/screens/<ten-man>/result.json     (format verdict.py)

Dùng:
  python3 aggregate.py --run <run_dir> [--pass-score 95]

Xuất: <run>/summary.json + <run>/report.md. KHÔNG sửa code (report-only).
"""
import argparse
import glob
import json
import os
import sys

SEV_ORDER = {"high": 0, "medium": 1, "med": 1, "low": 2, "info": 3}
CONF_ORDER = {"high": 0, "medium": 1, "med": 1, "low": 2}
DONE_STATUS = ("khớp", "khop", "accepted", "match", "ok")


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _is_unresolved(status):
    s = (status or "").lower()
    return not any(k in s for k in DONE_STATUS)


def main():
    ap = argparse.ArgumentParser(description="Gộp compare nhiều màn -> thống kê + report fix (ui-diff).")
    ap.add_argument("--run", required=True, help="Thư mục run (chứa screens/<man>/).")
    ap.add_argument("--pass-score", type=int, default=95)
    a = ap.parse_args()

    screen_dirs = sorted(d for d in glob.glob(os.path.join(a.run, "screens", "*")) if os.path.isdir(d))
    if not screen_dirs:
        sys.exit(f"Không thấy screens/*/ trong {a.run}")

    screens, all_fixes = [], []
    sev_count = {"high": 0, "medium": 0, "low": 0, "info": 0}
    type_count = {}
    for d in screen_dirs:
        name = os.path.basename(d)
        res = _load(os.path.join(d, "result.json")) or {}
        fnd = _load(os.path.join(d, "findings.json")) or {}
        findings = fnd.get("findings", [])
        score = res.get("match_score")
        screens.append({
            "screen": res.get("screen") or fnd.get("screen") or name,
            "dir": name,
            "match_score": score,
            "pass": res.get("pass"),
            "n_findings": len(findings),
            "summary": fnd.get("summary"),
        })
        for fx in findings:
            sev = (fx.get("severity") or "low").lower()
            sev = "medium" if sev == "med" else sev
            if sev in sev_count:
                sev_count[sev] += 1
            t = fx.get("type") or "unknown"
            type_count[t] = type_count.get(t, 0) + 1
            if _is_unresolved(fx.get("status")):
                all_fixes.append({
                    "screen": res.get("screen") or name,
                    "region": fx.get("region"),
                    "severity": sev,
                    "type": t,
                    "actual": fx.get("actual"),
                    "expected": fx.get("expected"),
                    "source_hint": fx.get("source_hint"),
                    "confidence": (fx.get("confidence") or "medium").lower(),
                })

    all_fixes.sort(key=lambda x: (SEV_ORDER.get(x["severity"], 9),
                                  CONF_ORDER.get(x["confidence"], 9)))
    scored = [s["match_score"] for s in screens if isinstance(s["match_score"], (int, float))]
    avg = round(sum(scored) / len(scored), 1) if scored else None
    n_pass = sum(1 for s in screens if s.get("pass") is True)

    summary = {
        "run": a.run,
        "pass_score": a.pass_score,
        "n_screens": len(screens),
        "avg_match_score": avg,
        "min_match_score": min(scored) if scored else None,
        "n_pass": n_pass,
        "n_fail": len(screens) - n_pass,
        "findings_by_severity": sev_count,
        "findings_by_type": type_count,
        "n_fixes": len(all_fixes),
        "screens": screens,
        "fix_priority": all_fixes,
    }
    with open(os.path.join(a.run, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # report.md
    lines = []
    lines.append(f"# ui-diff report — {os.path.basename(a.run.rstrip('/'))}\n")
    lines.append(f"- Màn so: **{len(screens)}** · PASS **{n_pass}** / FAIL **{len(screens)-n_pass}** "
                 f"(ngưỡng {a.pass_score})")
    lines.append(f"- Điểm khớp trung bình: **{avg}** · thấp nhất: **{summary['min_match_score']}**")
    lines.append(f"- Tổng diff: **{sum(sev_count.values())}** "
                 f"(high {sev_count['high']} · medium {sev_count['medium']} · low {sev_count['low']} · info {sev_count['info']})")
    lines.append(f"- Cần fix (chưa khớp): **{len(all_fixes)}**\n")

    lines.append("## Bảng màn\n")
    lines.append("| Màn | Điểm | Pass | #diff |")
    lines.append("|---|---|---|---|")
    for s in screens:
        lines.append(f"| {s['screen']} | {s['match_score']} | {'✅' if s['pass'] else '❌'} | {s['n_findings']} |")
    lines.append("")

    lines.append("## Fix ưu tiên (severity → confidence)\n")
    if not all_fixes:
        lines.append("_Không có diff cần fix._")
    for i, fx in enumerate(all_fixes, 1):
        sh = fx.get("source_hint")
        sh = f" · hint: `{sh}`" if sh else ""
        lines.append(f"{i}. **[{fx['severity']}]** {fx['screen']} — {fx['region']} ({fx['type']}, conf {fx['confidence']}){sh}")
        lines.append(f"   - actual: {fx.get('actual')}")
        lines.append(f"   - expected: {fx.get('expected')}")
    lines.append("")
    with open(os.path.join(a.run, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"OK {len(screens)} màn · avg={avg} · fix={len(all_fixes)}")
    print(f"   summary: {os.path.join(a.run, 'summary.json')}")
    print(f"   report : {os.path.join(a.run, 'report.md')}")


if __name__ == "__main__":
    main()
