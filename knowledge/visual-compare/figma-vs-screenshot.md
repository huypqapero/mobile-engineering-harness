# Visual Compare: Figma vs Screenshot

Technique + threshold cho visual comparison giữa Figma reference image và app screenshot runtime. Pre-check layer trước khi call LLM-based ui-judge (giảm cost + nhanh hơn).

## Mục đích

Hai layer verify UI:

1. **Visual compare** (fast, deterministic): perceptual hash + pixel diff — catch large layout drift
2. **ui-judge agent** (slow, semantic): LLM compare element tree + copy + tokens — catch missing element, wrong text

Flow:
```
Figma image + App screenshot
      ↓
  Visual compare (ms)
      ↓
  Distance < threshold? → likely similar, let LLM confirm
  Distance >= threshold? → clearly different, flag immediate, LLM confirm cause
```

Visual compare **không replace** ui-judge, chỉ pre-filter + evidence quantitative.

## Technique: Perceptual hash (phash/dhash)

### Nguyên lý

Perceptual hash = fingerprint 64-bit từ image. Images **visually similar** có hash distance (Hamming) nhỏ. Robust với:
- Resize (keep aspect)
- Compression artifacts (JPEG quality)
- Slight color shift
- Small text content change

Fragile với:
- Layout drift (element move)
- Major content change
- Different color scheme

### Perceptual hash variants

| Variant | Pros | Cons | Use case |
|---|---|---|---|
| **aHash** (average) | Simplest, fast | Noise-sensitive | Quick first pass |
| **pHash** (perceptual) | DCT-based, robust | Moderate speed | **Default, khuyên** |
| **dHash** (difference) | Fast, orientation-sensitive | Weak with rotations | Low-latency check |
| **wHash** (wavelet) | Best quality | Slow, dep lớn | Last resort |

Default: `pHash` cho balance.

### Library

Python `imagehash` + Pillow:

```python
import imagehash
from PIL import Image

figma = Image.open("figma/book-detail-content.png")
screenshot = Image.open("screenshots/book-detail-content.png")

h_figma = imagehash.phash(figma)
h_screenshot = imagehash.phash(screenshot)

distance = h_figma - h_screenshot  # Hamming distance
```

Range: 0 (identical) — 64 (completely different).

## Thresholds

### Default rules

| Distance | Classification | Action |
|---|---|---|
| 0 — 5 | Near-identical | ✅ Pass visual, skip ui-judge nếu config |
| 6 — 10 | Minor differences | ⚠️ Likely acceptable, call ui-judge confirm |
| 11 — 20 | Significant | 🚨 Flag ngay, call ui-judge diagnose |
| 21+ | Very different | ❌ Fail visual, call ui-judge chỉ cho root cause |

### Per-node threshold override

```yaml
# briefs/<slug>/expected/ui/visual.rules.yaml
nodes:
  - id: book-detail-content
    max_perceptual_distance: 10
  - id: popup-reward
    max_perceptual_distance: 15        # popup có dynamic data (user name), looser
  - id: ad-banner
    max_perceptual_distance: 30        # ad content thay đổi, very loose
```

### Logo / brand nodes stricter

```yaml
  - id: splash-logo
    max_perceptual_distance: 3           # logo phải pixel-perfect
```

## SSIM (Structural Similarity Index)

### Khi nào dùng SSIM

Perceptual hash catch "overall similar", nhưng không catch "wrong color" nếu structure giống. SSIM:

- Measure **luminance + contrast + structure** similarity
- Range: -1 (opposite) đến 1 (identical)
- Threshold: SSIM >= 0.95 typical acceptable

### Trade-off

| | pHash | SSIM |
|---|---|---|
| Speed | ~5ms | ~50-100ms |
| Dep size | ~1 MB imagehash | ~50 MB scikit-image + numpy |
| Catch color shift | Weak | Strong |
| Catch element move | Strong | Weak (shift breaks) |

Khuyên:
- Default: pHash (KISS)
- Add SSIM optional cho nodes stricter (logo, brand colors)

### Library

```python
from skimage.metrics import structural_similarity
import numpy as np
from PIL import Image

figma_arr = np.array(Image.open("figma/x.png").convert("L"))      # grayscale
screenshot_arr = np.array(Image.open("screenshots/x.png").convert("L"))

ssim = structural_similarity(figma_arr, screenshot_arr, data_range=255)
```

## Pre-processing

### Normalize image size

Figma export @2x, emulator screenshot DPI 420 → different absolute pixel size.

Resize cả 2 về cùng dimension trước compare:

```python
TARGET_SIZE = (720, 1600)  # typical mobile portrait
figma_norm = figma.resize(TARGET_SIZE, Image.LANCZOS)
screenshot_norm = screenshot.resize(TARGET_SIZE, Image.LANCZOS)
```

### Crop system UI

Screenshot bao gồm status bar + nav bar system — không trong Figma. Crop:

```python
# Pixel 6 emulator: status bar ~96px top, nav bar ~128px bottom (gesture nav off)
screenshot_cropped = screenshot.crop((0, 96, screenshot.width, screenshot.height - 128))
```

Status bar height configurable per device (xem `device.config.yaml` nếu có).

### Mask dynamic content

Nếu screen có user data (name, count, timestamp) — mask trước compare:

```yaml
nodes:
  - id: user-greeting
    mask_regions:
      - { x: 100, y: 200, width: 300, height: 50 }  # user name area
      - { x: 100, y: 400, width: 100, height: 30 }  # xu/token count
```

Validator overlay mask (solid color) trước hash. Both figma + screenshot masked.

## Report format

Mỗi node 1 result:

```yaml
# briefs/<slug>/actual/ui/visual-compare-results.yaml
results:
  - node: book-detail-content
    figma: expected/ui/figma/book-detail-content.png
    screenshot: actual/ui/screenshots/book-detail-content.png
    perceptual_distance: 7
    ssim: 0.96
    classification: minor_differences
    threshold: 10
    pass: true
    duration_ms: 12
  - node: play-button-popup
    perceptual_distance: 25
    classification: significant
    threshold: 10
    pass: false
    note: "Button color significantly different"
    duration_ms: 15
```

## When to re-generate Figma reference

Figma design update → re-export reference images:

```bash
# Export from Figma qua MCP (nếu có token):
# ... fetch via framelink-figma MCP → save vào expected/ui/figma/

# Hoặc manual:
# Figma → Export → PNG @2x → save vào briefs/<slug>/expected/ui/figma/<node>.png
```

Rules:
- Re-export khi designer thay đổi frame
- Commit new reference với clear changelog note
- Run visual compare với new reference để refresh baseline

## Rules

- **MUST** 2 images same dimension sau pre-processing
- **MUST** phash default; SSIM optional cho stricter nodes
- **MUST** threshold per-node overridable
- **MUST** mask dynamic content explicit, không auto-detect
- **SHOULD** crop system UI (status + nav bar) default
- **SHOULD** call ui-judge khi distance >= 6 (manual confirm)
- **FORBIDDEN** fail node dựa chỉ vào visual compare (phải có ui-judge cross-check)

## Anti-patterns

### AP-001 — Over-strict threshold

Set threshold = 3 cho mọi node → false-positive flood (dynamic data, time, counter).

### AP-002 — Compare without pre-process

Figma export 1080x2340, screenshot 720x1600 → distance luôn cao vì resize artifact, không meaningful.

### AP-003 — Skip mask dynamic data

Screen có user name → compare mỗi user khác → luôn fail.

### AP-004 — Rely only on visual compare

Visual pass không có nghĩa UI đúng. Element thiếu trong app nhưng Figma có → visual có thể pass nếu còn khoảng trắng. ui-judge semantic cần cross-check.

### AP-005 — Hash before crop

Status bar + nav bar không trong Figma → noise.

### AP-006 — SSIM mọi node

SSIM slow (50-100ms/node). Fixture 20 nodes = 1-2s overhead. Chỉ dùng cho strict nodes.

## Reference

- `imagehash` library: https://pypi.org/project/ImageHash/
- `scikit-image` SSIM: https://scikit-image.org/docs/stable/api/skimage.metrics.html
- `agents/ui-judge.md` — downstream LLM semantic check
- `verification/e2e/validators/validate_ui_visual.py` (next Wave 1 commit)

## Future (Wave 2+)

- Element-level mask: auto detect text region, mask dynamic chars
- Learn threshold: adjust per node based on historical variance
- Delta visualization: generate overlay image showing diff regions
- Multi-reference: compare với 2-3 valid states (light/dark mode)
