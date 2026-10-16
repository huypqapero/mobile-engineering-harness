#!/usr/bin/env python3
"""Validate UI visual compare: Figma reference vs app screenshot per node.

Uses perceptual hash (imagehash.phash) default. SSIM optional per node.
Pre-processes: resize, crop system UI, mask dynamic regions.

Usage:
  validate_ui_visual.py --fixture <dir> --rules <path>

Rules YAML format (expected/ui/visual.rules.yaml):
  defaults:
    target_size: [720, 1600]
    crop_top: 96        # status bar
    crop_bottom: 128    # nav bar
    max_perceptual_distance: 10
  nodes:
    - id: book-detail-content
      figma: expected/ui/figma/book-detail-content.png
      screenshot: actual/ui/screenshots/book-detail-content.png
      max_perceptual_distance: 10
      ssim_min: 0.95             # optional
      mask_regions:
        - { x: 100, y: 200, width: 300, height: 50 }

Exit codes:
  0  all pass
  1  schema / config error
  3  file missing
  25 visual drift detected
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

try:
    from PIL import Image, ImageDraw
    import imagehash
except ImportError as exc:
    print(f"ERROR missing dep: {exc}. Install: pip3 install Pillow imagehash", file=sys.stderr)
    sys.exit(1)

try:
    from skimage.metrics import structural_similarity
    import numpy as np
    HAS_SSIM = True
except ImportError:
    HAS_SSIM = False


def load_yaml(path: Path) -> dict:
    try:
        with path.open() as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"ERROR missing: {path}", file=sys.stderr)
        sys.exit(3)


def preprocess(path: Path, target_size, crop_top, crop_bottom, mask_regions):
    """Load image, crop, resize, mask dynamic regions."""
    img = Image.open(path).convert("RGB")

    # Crop system UI (only screenshot — figma không có status/nav bar)
    is_screenshot = "screenshot" in str(path) or "/actual/" in str(path)
    if is_screenshot and crop_top:
        img = img.crop((0, crop_top, img.width, img.height - (crop_bottom or 0)))

    # Resize cả 2 về cùng dimension
    if target_size:
        img = img.resize(tuple(target_size), Image.LANCZOS)

    # Mask dynamic regions (overlay solid gray)
    if mask_regions:
        draw = ImageDraw.Draw(img)
        for region in mask_regions:
            x, y, w, h = region["x"], region["y"], region["width"], region["height"]
            draw.rectangle([x, y, x + w, y + h], fill=(128, 128, 128))

    return img


def perceptual_distance(img_a, img_b) -> int:
    h_a = imagehash.phash(img_a)
    h_b = imagehash.phash(img_b)
    return h_a - h_b


def ssim_score(img_a, img_b) -> float:
    if not HAS_SSIM:
        return None
    arr_a = np.array(img_a.convert("L"))
    arr_b = np.array(img_b.convert("L"))
    return float(structural_similarity(arr_a, arr_b, data_range=255))


def classify_distance(distance: int) -> str:
    if distance <= 5:
        return "near_identical"
    if distance <= 10:
        return "minor_differences"
    if distance <= 20:
        return "significant"
    return "very_different"


def validate_node(node: dict, fixture_dir: Path, defaults: dict) -> dict:
    figma_rel = node.get("figma")
    screenshot_rel = node.get("screenshot")
    node_id = node.get("id", "<unnamed>")

    figma_path = fixture_dir / figma_rel if figma_rel else None
    screenshot_path = fixture_dir / screenshot_rel if screenshot_rel else None

    result = {
        "node": node_id,
        "figma": str(figma_rel) if figma_rel else None,
        "screenshot": str(screenshot_rel) if screenshot_rel else None,
    }

    if not figma_path or not figma_path.exists():
        result["pass"] = False
        result["classification"] = "missing_figma"
        result["note"] = f"figma reference not found: {figma_rel}"
        return result

    if not screenshot_path or not screenshot_path.exists():
        result["pass"] = False
        result["classification"] = "missing_screenshot"
        result["note"] = f"screenshot not found: {screenshot_rel}"
        return result

    target_size = node.get("target_size") or defaults.get("target_size")
    crop_top = node.get("crop_top", defaults.get("crop_top", 0))
    crop_bottom = node.get("crop_bottom", defaults.get("crop_bottom", 0))
    mask_regions = node.get("mask_regions", [])
    max_distance = node.get("max_perceptual_distance", defaults.get("max_perceptual_distance", 10))
    ssim_min = node.get("ssim_min")

    try:
        figma_img = preprocess(figma_path, target_size, crop_top, crop_bottom, mask_regions)
        screenshot_img = preprocess(screenshot_path, target_size, crop_top, crop_bottom, mask_regions)
    except Exception as exc:
        result["pass"] = False
        result["classification"] = "preprocess_error"
        result["note"] = str(exc)
        return result

    distance = perceptual_distance(figma_img, screenshot_img)
    classification = classify_distance(distance)
    pass_phash = distance <= max_distance

    result["perceptual_distance"] = distance
    result["classification"] = classification
    result["threshold"] = max_distance
    result["pass"] = pass_phash

    if ssim_min is not None and HAS_SSIM:
        ssim = ssim_score(figma_img, screenshot_img)
        result["ssim"] = round(ssim, 4)
        result["ssim_min"] = ssim_min
        if ssim < ssim_min:
            result["pass"] = False
            result["classification"] = "ssim_fail"
    elif ssim_min is not None and not HAS_SSIM:
        result["ssim_skipped"] = "scikit-image not installed"

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True, type=Path, help="fixture dir")
    parser.add_argument("--rules", required=True, type=Path, help="visual.rules.yaml path")
    parser.add_argument("--output", type=Path, help="write results YAML to path")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    rules = load_yaml(args.rules)
    defaults = rules.get("defaults", {})
    nodes = rules.get("nodes", [])

    if not nodes:
        print("no nodes in rules file; nothing to validate")
        return 0

    results = []
    fails = 0
    for node in nodes:
        res = validate_node(node, args.fixture, defaults)
        results.append(res)
        if not res.get("pass"):
            fails += 1
        if args.verbose:
            status = "PASS" if res.get("pass") else "FAIL"
            dist = res.get("perceptual_distance", "-")
            ssim = res.get("ssim", "-")
            print(f"  {status} {res['node']}  distance={dist}  ssim={ssim}  {res.get('note', '')}")

    summary = {
        "total_nodes": len(nodes),
        "pass": len(nodes) - fails,
        "fail": fails,
        "ssim_available": HAS_SSIM,
        "results": results,
    }

    print(f"Total nodes: {summary['total_nodes']}")
    print(f"Pass: {summary['pass']}, Fail: {summary['fail']}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w") as f:
            yaml.safe_dump(summary, f, sort_keys=False)
        print(f"Results written: {args.output}")

    return 25 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
