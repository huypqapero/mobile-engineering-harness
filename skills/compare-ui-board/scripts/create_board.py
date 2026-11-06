#!/usr/bin/env python3
"""create_board.py — ghép nhiều ảnh UI vào MỘT canvas có nhãn để vision model
so sánh trực tiếp trong một lần nhìn (giảm miss-context so với đọc rời từng ảnh).

Nguồn ảnh mỗi panel: đường dẫn local, hoặc URL (http/https). URL prnt.sc / lightshot
được tự resolve sang ảnh gốc.

Ví dụ:
  # 2 ảnh: actual vs expected
  python3 create_board.py --mode pair \
      --actual https://prnt.sc/xxxx --expected design.png \
      --title "AI Tutor" --output board.png

  # 2x2: runtime/expected + compose preview/figma node
  python3 create_board.py --mode quad \
      --actual a.png --expected e.png --preview p.png --figma f.png \
      --title "AI Tutor — Runtime+Preview+Design" --output board.png

  # before/after (evidence sau fix)
  python3 create_board.py --mode before-after \
      --before b.png --expected e.png --after af.png --note "Fixed hero + mascot" \
      --title "AI Tutor — Evidence" --output board.png

  # tự do: mỗi --panel "Nhãn=nguồn" là một ô (xếp 2 ô/hàng)
  python3 create_board.py --panel "ACTUAL=a.png" --panel "EXPECTED=e.png" \
      --panel "FIGMA NODE=f.png" --output board.png
"""
import argparse
import io
import re
import sys
import urllib.request
from PIL import Image, ImageDraw, ImageFont

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

COL_W = 540          # chiều rộng nội dung mỗi panel (px)
MAX_H = 1180         # cao tối đa ảnh trong 1 ô (ảnh dài sẽ fit theo chiều cao)
PAD = 28             # lề ngoài canvas
GAP = 22             # khoảng cách giữa cột / hàng
LABEL_H = 44         # cao dải nhãn mỗi ô
TITLE_H = 72         # cao dải tiêu đề
BG = (31, 36, 46)    # nền board (slate đậm)
PANEL_BG = (255, 255, 255)
BORDER = (60, 68, 82)
TITLE_BG = (16, 20, 31)
WHITE = (255, 255, 255)

# màu dải nhãn theo vai trò (gợi ý cho model: xanh lá = nguồn chuẩn)
ROLE_COLORS = [
    (("expected", "design", "figma", "reference"), (22, 179, 100)),   # source of truth — green
    (("preview", "compose"), (47, 107, 255)),                         # implementation preview — blue
    (("after",), (245, 158, 11)),                                     # current (after fix) — amber
    (("before",), (138, 148, 168)),                                   # previous — gray
    (("actual", "runtime", "current"), (245, 158, 11)),               # current — amber
    (("note", "summary", "diff"), (99, 102, 120)),                    # note — slate
]


def label_color(label: str):
    low = label.lower()
    for keys, color in ROLE_COLORS:
        if any(k in low for k in keys):
            return color
    return (99, 102, 120)


def _font(size: int, bold: bool = True):
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _resolve_url(url: str) -> str:
    """prnt.sc / lightshot: lấy URL ảnh thật từ og:image."""
    if "prnt.sc" in url or "prntscr.com" in url or "lightshot" in url:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if not m:
            m = re.search(r'https://img\.lightshot\.app/[A-Za-z0-9_-]+\.png', html)
            if m:
                return m.group(0)
            raise RuntimeError(f"Không tìm được ảnh thật từ {url}")
        return m.group(1)
    return url


def load_image(src: str) -> Image.Image:
    if src.startswith("http://") or src.startswith("https://"):
        real = _resolve_url(src)
        req = urllib.request.Request(real, headers={"User-Agent": UA})
        data = urllib.request.urlopen(req, timeout=60).read()
        img = Image.open(io.BytesIO(data))
    else:
        img = Image.open(src)
    return img.convert("RGBA")


def make_note_image(text: str) -> Image.Image:
    """Ô NOTE: render text thành ảnh (dùng cho mode before-after)."""
    img = Image.new("RGBA", (COL_W, 320), (241, 244, 250, 255))
    d = ImageDraw.Draw(img)
    font = _font(26, bold=False)
    y = 24
    for line in text.split("\n"):
        d.text((24, y), line, fill=(16, 20, 31), font=font)
        y += 38
    return img


def scale_panel(img: Image.Image):
    w, h = img.size
    new_w = COL_W
    new_h = round(h * COL_W / w)
    if new_h > MAX_H:
        new_h = MAX_H
        new_w = round(w * MAX_H / h)
    return img.resize((new_w, new_h), Image.LANCZOS), new_w, new_h


def draw_cell(canvas, draw, x, y, row_h, label, pimg, pw, ph):
    # dải nhãn
    color = label_color(label)
    draw.rectangle([x, y, x + COL_W, y + LABEL_H], fill=color)
    draw.text((x + 14, y + 11), label, fill=WHITE, font=_font(22))
    # vùng ảnh (nền trắng, viền), ảnh căn giữa ngang + trên
    img_top = y + LABEL_H
    draw.rectangle([x, img_top, x + COL_W, y + row_h], fill=PANEL_BG, outline=BORDER, width=1)
    off_x = x + (COL_W - pw) // 2
    canvas.alpha_composite(pimg, (off_x, img_top + 8))


def build(cells, title, subtitle, output):
    # cells: list of (label, PIL.Image)
    prepared = []
    for label, img in cells:
        pimg, pw, ph = scale_panel(img)
        prepared.append((label, pimg, pw, ph))

    rows = [prepared[i:i + 2] for i in range(0, len(prepared), 2)]
    row_heights = [LABEL_H + 16 + max(c[3] for c in row) for row in rows]

    top = PAD + (TITLE_H if title else 0)
    total_h = top + sum(row_heights) + GAP * (len(rows) - 1) + PAD
    ncols = 2 if len(prepared) > 1 else 1
    total_w = PAD + COL_W * ncols + GAP * (ncols - 1) + PAD

    canvas = Image.new("RGBA", (total_w, total_h), BG + (255,))
    draw = ImageDraw.Draw(canvas)

    if title:
        draw.rectangle([PAD, PAD, total_w - PAD, PAD + TITLE_H], fill=TITLE_BG)
        draw.text((PAD + 18, PAD + 12), title, fill=WHITE, font=_font(30))
        if subtitle:
            draw.text((PAD + 18, PAD + 44), subtitle, fill=(170, 182, 200), font=_font(20, bold=False))

    y = top
    for row, row_h in zip(rows, row_heights):
        x = PAD
        for (label, pimg, pw, ph) in row:
            draw_cell(canvas, draw, x, y, row_h, label, pimg, pw, ph)
            x += COL_W + GAP
        y += row_h + GAP

    canvas.convert("RGB").save(output, "PNG")
    print(f"OK board -> {output}  ({total_w}x{total_h}, {len(prepared)} panels)")


def cells_from_mode(a):
    def need(*names):
        for n in names:
            if getattr(a, n) is None:
                sys.exit(f"mode '{a.mode}' cần --{n}")
    if a.mode == "pair":
        need("actual", "expected")
        return [("1. ACTUAL (Runtime)", load_image(a.actual)),
                ("2. EXPECTED (Design)", load_image(a.expected))]
    if a.mode == "quad":
        need("actual", "expected", "preview", "figma")
        return [("1. ACTUAL (Runtime)", load_image(a.actual)),
                ("2. EXPECTED (Design)", load_image(a.expected)),
                ("3. COMPOSE PREVIEW", load_image(a.preview)),
                ("4. FIGMA NODE", load_image(a.figma))]
    if a.mode == "before-after":
        need("before", "expected", "after")
        fourth = make_note_image(a.note) if a.note else (load_image(a.preview) if a.preview else make_note_image("(no note)"))
        fourth_label = "4. NOTE" if a.note or not a.preview else "4. COMPOSE PREVIEW"
        return [("1. BEFORE (Actual)", load_image(a.before)),
                ("2. EXPECTED (Design)", load_image(a.expected)),
                ("3. AFTER (Actual)", load_image(a.after)),
                (fourth_label, fourth)]
    sys.exit(f"mode không hợp lệ: {a.mode}")


def main():
    p = argparse.ArgumentParser(description="Ghép ảnh UI vào 1 board có nhãn để so sánh.")
    p.add_argument("--mode", choices=["pair", "quad", "before-after"], default="pair")
    p.add_argument("--actual")
    p.add_argument("--expected")
    p.add_argument("--preview")
    p.add_argument("--figma")
    p.add_argument("--before")
    p.add_argument("--after")
    p.add_argument("--note")
    p.add_argument("--panel", action="append", default=[], help='Tự do: "Nhãn=nguồn", xếp 2 ô/hàng')
    p.add_argument("--title", default="")
    p.add_argument("--subtitle", default="")
    p.add_argument("--output", required=True)
    a = p.parse_args()

    if a.panel:
        cells = []
        for spec in a.panel:
            if "=" not in spec:
                sys.exit(f'--panel sai định dạng (cần "Nhãn=nguồn"): {spec}')
            label, src = spec.split("=", 1)
            cells.append((label.strip(), load_image(src.strip())))
    else:
        cells = cells_from_mode(a)

    build(cells, a.title, a.subtitle, a.output)


if __name__ == "__main__":
    main()
