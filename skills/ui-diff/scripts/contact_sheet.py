#!/usr/bin/env python3
"""contact_sheet.py — xếp N ảnh thành board lưới có LABEL để model phân loại/dedup.

Bước "đưa frame lên 1 board rồi đánh label, bỏ trùng" của ui-diff — dùng CHUNG cho
cả frame video LẪN frame Figma. Khác create_board (2 cột full-height, cao khó đọc
khi nhiều ảnh), script này xếp thumbnail NHỎ nhiều cột, gắn nhãn #index + tên file,
chia nhiều sheet nếu đông, xuất JPEG gọn (đọc được, không vỡ context).

Dùng:
  python3 contact_sheet.py --dir frames/ --out sheets/ [--cols 6] [--per 24] \
      [--thumb 175] [--prefix grid] [--glob "*.png"]
  python3 contact_sheet.py --images a.png b.png c.png --out sheets/

Mỗi sheet: <out>/<prefix>_NN.jpg. Nhãn = #thứ-tự toàn cục + tên file (rút gọn).
Model đọc sheet → gom ảnh cùng màn (dedup ngữ nghĩa), chọn 1 đại diện mỗi màn.
"""
import argparse
import glob
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Cần Pillow: pip3 install pillow")


def _font(sz=13):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser(description="Board lưới có label cho phân loại/dedup (ui-diff).")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--dir", help="Thư mục ảnh.")
    src.add_argument("--images", nargs="+", help="Danh sách ảnh.")
    ap.add_argument("--glob", default="*.png", help="Mẫu khi dùng --dir (mặc định *.png).")
    ap.add_argument("--out", required=True, help="Thư mục xuất sheet.")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--per", type=int, default=24, help="Số thumbnail mỗi sheet.")
    ap.add_argument("--thumb", type=int, default=175, help="Bề rộng thumbnail (px).")
    ap.add_argument("--prefix", default="grid")
    a = ap.parse_args()

    if a.dir:
        files = sorted(glob.glob(os.path.join(a.dir, a.glob)))
    else:
        files = a.images
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        sys.exit("Không có ảnh nào.")
    os.makedirs(a.out, exist_ok=True)

    font = _font(13)
    TW, cols, per, pad, lab = a.thumb, a.cols, a.per, 6, 16

    def thumb(fp):
        im = Image.open(fp).convert("RGB")
        w, h = im.size
        return im.resize((TW, max(1, int(TW * h / w))))

    sheets = []
    for s, i in enumerate(range(0, len(files), per), 1):
        grp = files[i:i + per]
        ims = [(i + k + 1, os.path.basename(f), thumb(f)) for k, f in enumerate(grp)]
        maxth = max(im.size[1] for _, _, im in ims)
        rows = (len(ims) + cols - 1) // cols
        cellw, cellh = TW + pad, maxth + lab + pad
        W, H = cols * cellw + pad, rows * cellh + pad
        sheet = Image.new("RGB", (W, H), "#101420")
        d = ImageDraw.Draw(sheet)
        for k, (num, name, im) in enumerate(ims):
            r, c = divmod(k, cols)
            x, y = pad + c * cellw, pad + r * cellh
            tag = f"#{num} {name[:14]}"
            d.text((x + 2, y), tag, fill="#FFD24A", font=font)
            sheet.paste(im, (x, y + lab))
        out = os.path.join(a.out, f"{a.prefix}_{s:02d}.jpg")
        sheet.save(out, "JPEG", quality=78)
        sheets.append(out)
        print(f"{os.path.basename(out)}  {os.path.getsize(out)//1024}KB  {sheet.size}  (#{i+1}-{i+len(grp)})")

    print(f"OK {len(files)} ảnh -> {len(sheets)} sheet trong {a.out}")


if __name__ == "__main__":
    main()
