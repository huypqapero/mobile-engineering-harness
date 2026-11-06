#!/usr/bin/env python3
"""pair_board.py — ghép NHIỀU cặp [ACTUAL | EXPECTED] vào MỘT board để compare 1 lượt.

Bước "ra output board gồm nhiều cặp actual-expect" của ui-diff: sau khi đã trải phẳng
frame video + chọn frame tốt nhất mỗi màn (APP SẠCH) và có screenshot Figma, script
này xếp mỗi màn thành 1 HÀNG = [actual | expected] cạnh nhau, có nhãn màn, stack
nhiều hàng. Model đọc board này rồi compare + chấm từng cặp trong một lượt.

Dùng:
  python3 pair_board.py \
    --pair "lesson-result" app/77.png figma/34-212.png \
    --pair "speaking-result" app/64.png figma/speaking.png \
    --out pairs.png [--per 4] [--width 380] [--max-h 560]

- --pair LABEL ACTUAL EXPECTED (lặp nhiều lần). EXPECTED có thể để "NONE" nếu no-match.
- --per: số cặp mỗi board (mặc định 4); đông hơn thì chia pairs_01, pairs_02...
- Xuất <out> (hoặc <out_prefix>_NN.png nếu >1 board).
"""
import argparse
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Cần Pillow: pip3 install pillow")


def _font(sz):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def _thumb(fp, TW, MAXH):
    im = Image.open(fp).convert("RGB")
    w, h = im.size
    th = int(TW * h / w)
    if th > MAXH:
        TW2 = int(TW * MAXH / th); th = MAXH
        return im.resize((TW2, th))
    return im.resize((TW, th))


def _placeholder(TW, h, text):
    im = Image.new("RGB", (TW, h), "#2A2F3A")
    d = ImageDraw.Draw(im)
    d.text((10, h // 2 - 8), text, fill="#8A94A8", font=_font(14))
    return im


def _render(pairs, out, TW, MAXH, bg="#101420"):
    lab = _font(16); hdr = _font(15)
    labH, hdrH, pad, gap = 24, 22, 10, 14
    rows = []
    for label, a, e in pairs:
        ia = _thumb(a, TW, MAXH)
        ie = _thumb(e, TW, MAXH) if (e and e.upper() != "NONE" and os.path.isfile(e)) \
            else _placeholder(TW, ia.size[1], "NO-MATCH / no design")
        rows.append((label, ia, ie))
    rowH = [labH + max(a.size[1], e.size[1]) + pad for _, a, e in rows]
    W = pad + TW + gap + TW + pad
    H = hdrH + sum(rowH) + pad
    board = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(board)
    d.text((pad, 4), "ACTUAL (app)", fill="#F2A33C", font=hdr)
    d.text((pad + TW + gap, 4), "EXPECTED (design)", fill="#36B37E", font=hdr)
    y = hdrH
    for (label, ia, ie), rh in zip(rows, rowH):
        d.text((pad, y), label, fill="#FFD24A", font=lab)
        board.paste(ia, (pad, y + labH))
        board.paste(ie, (pad + TW + gap, y + labH))
        y += rh
    board.save(out, quality=85) if out.lower().endswith((".jpg", ".jpeg")) else board.save(out)
    return board.size


def main():
    ap = argparse.ArgumentParser(description="Board nhiều cặp [actual|expected] (ui-diff).")
    ap.add_argument("--pair", nargs=3, action="append", metavar=("LABEL", "ACTUAL", "EXPECTED"),
                    required=True, help="Lặp nhiều lần. EXPECTED=NONE nếu no-match.")
    ap.add_argument("--out", required=True, help="File board (png/jpg). Nếu >1 board: <stem>_NN.<ext>.")
    ap.add_argument("--per", type=int, default=4, help="Số cặp mỗi board.")
    ap.add_argument("--width", type=int, default=380, help="Bề rộng mỗi panel.")
    ap.add_argument("--max-h", type=int, default=560, help="Cap chiều cao mỗi panel.")
    a = ap.parse_args()

    for label, act, exp in a.pair:
        if not os.path.isfile(act):
            sys.exit(f"Không thấy ACTUAL: {act}")

    stem, ext = os.path.splitext(a.out)
    chunks = [a.pair[i:i + a.per] for i in range(0, len(a.pair), a.per)]
    outs = []
    for idx, ch in enumerate(chunks, 1):
        out = a.out if len(chunks) == 1 else f"{stem}_{idx:02d}{ext}"
        size = _render(ch, out, a.width, a.max_h)
        outs.append((out, size, len(ch)))
        print(f"OK {os.path.basename(out)}  {size}  ({len(ch)} cặp)")
    print(f"Tổng {len(a.pair)} cặp -> {len(outs)} board.")


if __name__ == "__main__":
    main()
