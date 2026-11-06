#!/usr/bin/env python3
"""sample_region.py — đo màu trung bình + độ sáng của một vùng ảnh (tier-2).

Dùng để CHỐT những khác biệt màu/nền/nút mà mắt dễ miss (vd nền "xanh đặc" vs
"xanh mint nhạt", nút "trắng chữ xanh" vs "xanh chữ trắng"). Chạy trên cả ảnh
actual-crop lẫn design-crop ở cùng vùng tương ứng rồi SO HEX, không tin mắt.

Dùng:
  # 1 vùng (toạ độ pixel)
  python3 sample_region.py --image card.png --rect 20,260,400,330 --label "card-bg"

  # toạ độ theo tỉ lệ 0-1 (bền với khác resolution giữa actual/design)
  python3 sample_region.py --image design.png --rect 0.05,0.55,0.95,0.72 --frac --label "card-bg"

  # nhiều vùng 1 lần
  python3 sample_region.py --image popup.png \
      --region "title=0.1,0.2,0.9,0.35" --region "button=0.1,0.75,0.9,0.95" --frac

In ra mỗi vùng: mean #RRGGBB, độ sáng 0-255, nhãn light/dark, và độ lệch màu nội
vùng (std) để biết vùng đồng màu hay nhiều màu (text trên nền).
"""
import argparse
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Cần Pillow: pip3 install pillow")


def _parse_rect(s, frac, w, h):
    parts = [float(x) for x in s.split(",")]
    if len(parts) != 4:
        raise ValueError("rect phải là x0,y0,x1,y1")
    x0, y0, x1, y1 = parts
    if frac:
        x0, x1 = x0 * w, x1 * w
        y0, y1 = y0 * h, y1 * h
    x0, x1 = sorted((int(round(x0)), int(round(x1))))
    y0, y1 = sorted((int(round(y0)), int(round(y1))))
    x0 = max(0, min(x0, w - 1)); x1 = max(x0 + 1, min(x1, w))
    y0 = max(0, min(y0, h - 1)); y1 = max(y0 + 1, min(y1, h))
    return x0, y0, x1, y1


def _stats(img, rect):
    crop = img.crop(rect)
    px = list(crop.getdata())
    n = len(px)
    r = sum(p[0] for p in px) / n
    g = sum(p[1] for p in px) / n
    b = sum(p[2] for p in px) / n
    bright = 0.299 * r + 0.587 * g + 0.114 * b
    # std tổng (độ đồng nhất màu trong vùng)
    var = sum((p[0]-r)**2 + (p[1]-g)**2 + (p[2]-b)**2 for p in px) / n
    std = var ** 0.5
    return (r, g, b, bright, std)


def _fmt(label, rect, s):
    r, g, b, bright, std = s
    hexc = "#%02X%02X%02X" % (round(r), round(g), round(b))
    tone = "light" if bright >= 140 else ("dark" if bright <= 90 else "mid")
    uni = "đồng-màu" if std < 35 else "nhiều-màu(text/nền)"
    return f"{label:16s} rect={rect} mean={hexc} bright={bright:5.1f} ({tone}) std={std:5.1f} [{uni}]"


def main():
    ap = argparse.ArgumentParser(description="Đo màu trung bình vùng ảnh (tier-2 cho ui-diff-review).")
    ap.add_argument("--image", required=True)
    ap.add_argument("--rect", help="x0,y0,x1,y1 (1 vùng)")
    ap.add_argument("--label", default="region")
    ap.add_argument("--region", action="append", default=[], help='"label=x0,y0,x1,y1" (lặp nhiều lần)')
    ap.add_argument("--frac", action="store_true", help="toạ độ theo tỉ lệ 0-1")
    a = ap.parse_args()

    img = Image.open(a.image).convert("RGB")
    w, h = img.size
    print(f"# image={a.image} size={w}x{h} frac={a.frac}")

    jobs = []
    if a.rect:
        jobs.append((a.label, a.rect))
    for r in a.region:
        if "=" not in r:
            ap.error("--region phải dạng label=x0,y0,x1,y1")
        lbl, coords = r.split("=", 1)
        jobs.append((lbl.strip(), coords.strip()))
    if not jobs:
        ap.error("cần --rect hoặc --region")

    for label, coords in jobs:
        rect = _parse_rect(coords, a.frac, w, h)
        print(_fmt(label, rect, _stats(img, rect)))


if __name__ == "__main__":
    main()
