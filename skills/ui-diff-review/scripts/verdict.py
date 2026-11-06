#!/usr/bin/env python3
"""verdict.py — ghi verdict cho ui-diff-review.

Model tự suy luận match_score (0-100) bằng thị giác trên board, script này chỉ
GHI LẠI con số đó + lý do + tính pass/fail theo ngưỡng, xuất result.json để trace.
KHÔNG tự tính điểm, KHÔNG pixel-diff — điểm do model đưa vào qua --score.

Dùng:
  python3 verdict.py --score 96 --board board.png --out result.json \
      [--threshold 95] [--issue AAP079-33] [--screen "Result"] [--reason "..."]

Exit code: 0 = PASS (score >= threshold), 2 = FAIL (score < threshold).
"""
import argparse
import json
import sys
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main():
    ap = argparse.ArgumentParser(description="Ghi verdict ui-diff-review (model chấm, script chỉ record).")
    ap.add_argument("--score", type=int, required=True, help="match_score 0-100 do MODEL suy luận.")
    ap.add_argument("--board", required=True, help="Đường dẫn board đã chấm (evidence).")
    ap.add_argument("--out", required=True, help="Đường dẫn result.json xuất ra.")
    ap.add_argument("--threshold", type=int, default=95, help="Ngưỡng pass (mặc định 95).")
    ap.add_argument("--issue", default=None, help="Mã issue (tùy chọn).")
    ap.add_argument("--screen", default=None, help="Tên màn (tùy chọn).")
    ap.add_argument("--reason", default=None, help="Lý do model cho điểm này (khuyến nghị).")
    a = ap.parse_args()

    if not (0 <= a.score <= 100):
        ap.error("--score phải trong [0,100]")
    if not (0 <= a.threshold <= 100):
        ap.error("--threshold phải trong [0,100]")

    passed = a.score >= a.threshold
    verdict = {
        "issue": a.issue,
        "screen": a.screen,
        "match_score": a.score,
        "pass_score": a.threshold,
        "pass": passed,
        "reason": a.reason,
        "board": a.board,
        "scored_by": "model-visual-judgment",
        "verified_at": _now(),
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=2)
        f.write("\n")

    tag = "PASS" if passed else "FAIL"
    print(f"{tag}  match_score={a.score}  threshold={a.threshold}  -> {a.out}")
    sys.exit(0 if passed else 2)


if __name__ == "__main__":
    main()
