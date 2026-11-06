#!/usr/bin/env python3
"""extract_frames.py — cắt frame từ video app theo interval + dedup near-duplicate.

Mode video→figma của ui-diff: video quay app chạy → cắt đều mỗi N giây → bỏ bớt
frame gần trùng (average-hash) → ra tập frame ÍT và SẠCH để đẩy vào board phân loại.

Dùng:
  python3 extract_frames.py --video app.mp4 --out frames/ [--interval 2] \
      [--dedup-dist 6] [--no-dedup]

- --interval: giây giữa 2 frame (mặc định 2).
- --dedup-dist: ngưỡng hamming aHash; frame cách frame-giữ-trước < ngưỡng bị bỏ
  (mặc định 6; 0 = chỉ bỏ trùng tuyệt đối). Đặt --no-dedup để giữ hết.

Cần: ffmpeg trong PATH, Pillow. In manifest các frame GIỮ LẠI (đường dẫn + thời điểm).
KHÔNG phán màn nào trùng về mặt NGỮ NGHĨA — việc đó để board + model làm. Script chỉ
bỏ frame gần y hệt về pixel để board gọn.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Cần Pillow: pip3 install pillow")


def _signature(path, size=8):
    """Trả (ahash layout, mean RGB). Dùng cả hai để dedup: aHash bắt khác LAYOUT,
    mean-color bắt khác MÀU (aHash grayscale không phân biệt 2 màu đặc khác nhau)."""
    rgb = Image.open(path).convert("RGB").resize((size, size))
    gray = rgb.convert("L")
    gpx = list(gray.getdata())
    avg = sum(gpx) / len(gpx)
    bits = 0
    for i, p in enumerate(gpx):
        if p >= avg:
            bits |= (1 << i)
    rpx = list(rgb.getdata())
    n = len(rpx)
    mean = (sum(p[0] for p in rpx) / n, sum(p[1] for p in rpx) / n, sum(p[2] for p in rpx) / n)
    return bits, mean


def _hamming(a, b):
    return bin(a ^ b).count("1")


def _color_dist(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1]) + abs(a[2]-b[2])


def main():
    ap = argparse.ArgumentParser(description="Cắt frame video + dedup near-duplicate (ui-diff video mode).")
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True, help="Thư mục xuất frame (sẽ tạo mới/sạch).")
    ap.add_argument("--interval", type=float, default=2.0, help="Giây giữa 2 frame (mặc định 2).")
    ap.add_argument("--dedup-dist", type=int, default=6, help="Ngưỡng hamming aHash để bỏ near-dup.")
    ap.add_argument("--dedup-color", type=int, default=24, help="Ngưỡng lệch mean-color (sum|dRGB|) coi là cùng màu.")
    ap.add_argument("--no-dedup", action="store_true")
    a = ap.parse_args()

    if not os.path.isfile(a.video):
        sys.exit(f"Không thấy video: {a.video}")
    if shutil.which("ffmpeg") is None:
        sys.exit("Cần ffmpeg trong PATH.")

    raw = os.path.join(a.out, "_raw")
    os.makedirs(raw, exist_ok=True)
    for f in os.listdir(raw):
        os.remove(os.path.join(raw, f))

    fps = 1.0 / a.interval if a.interval > 0 else 1.0
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", a.video,
           "-vf", f"fps={fps}", os.path.join(raw, "raw_%04d.png")]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit("ffmpeg lỗi khi cắt frame.")

    frames = sorted(os.path.join(raw, f) for f in os.listdir(raw) if f.endswith(".png"))
    if not frames:
        sys.exit("ffmpeg không xuất frame nào (kiểm tra video/interval).")

    kept, manifest, last_sig = [], [], None
    for idx, fp in enumerate(frames):
        t = idx * a.interval
        keep = True
        if not a.no_dedup:
            h, mean = _signature(fp)
            # Trùng chỉ khi GIỐNG cả layout (aHash) LẪN màu (mean-color).
            if last_sig is not None and _hamming(h, last_sig[0]) <= a.dedup_dist \
                    and _color_dist(mean, last_sig[1]) <= a.dedup_color:
                keep = False
            if keep:
                last_sig = (h, mean)
        if keep:
            name = f"screen_{len(kept)+1:03d}_t{t:06.1f}.png".replace(".", "_", 1)
            dst = os.path.join(a.out, name)
            shutil.copy(fp, dst)
            kept.append(dst)
            manifest.append({"index": len(kept), "t_sec": round(t, 1), "file": dst})

    with open(os.path.join(a.out, "frames.json"), "w", encoding="utf-8") as f:
        json.dump({"video": a.video, "interval": a.interval,
                   "raw_count": len(frames), "kept_count": len(kept),
                   "frames": manifest}, f, ensure_ascii=False, indent=2)
    shutil.rmtree(raw, ignore_errors=True)

    print(f"OK cắt {len(frames)} frame (mỗi {a.interval}s) -> giữ {len(kept)} sau dedup.")
    print(f"   frames/ : {a.out}")
    print(f"   manifest: {os.path.join(a.out, 'frames.json')}")
    print("   Bước tiếp: đẩy các frame giữ lại vào 1 board (create_board.py --panel ...) để model phân loại/gộp màn trùng ngữ nghĩa.")


if __name__ == "__main__":
    main()
