# Screenshot Reading Rules

Rules đọc screenshot UI thành screen contract trong `design.md` + `brief.yaml`. Áp dụng cho skill `business-analyze --phase design`.

## Mục đích

Prevent agent **over-claim** từ screenshot. Vision model nhìn component ổn (70% accuracy), nhưng infer behavior/color/state **thường sai**. Rules này đặt ranh giới an toàn.

## Priority khi design source = Figma

Khi design source là Figma (có `node-tree.json` + `variables.json` + PNG snapshots), agent dùng **structured data trước**, screenshot cho visual confirm. Overrides áp dụng:

- **Color** từ Figma variable → confirmed (DESIGN-RULE-OVERRIDE-001 trong `figma-fetch-rules.md`)
- **Dimension** từ Figma fixed → confirmed (DESIGN-RULE-OVERRIDE-005)
- **Layout mode** từ Figma auto-layout → confirmed (DESIGN-RULE-OVERRIDE-007)

Khi không có Figma structured data (chỉ PNG screenshot), toàn bộ DESIGN-RULE dưới áp mặc định với confidence `inferred`.

## Hard rules

### DESIGN-RULE-001 — Không claim design token exact value

**Cấm:**
```yaml
components:
  - id: play-button
    background_color: "#1A73E8"      # ← CẤM, đây là ước lượng
```

**Đúng:**
```yaml
components:
  - id: play-button
    background_color_estimate: blue  # list ước lượng semantic
    design_token_mapping: prefer-existing-project-tokens
```

Rationale: screenshot JPEG/PNG compress, color không chính xác. Design token mapping do downstream implementer quyết dựa trên project tokens.

### DESIGN-RULE-002 — Không infer navigation từ screenshot alone

**Cấm:** "Tap play-button → nav tới AudioPlayer screen" mà không có spec quote.

**Đúng:** `components[].action_ref` chỉ gán khi có requirement confirmed; không có → `action_ref: null` + issue `MISSING_BEHAVIOR`.

### DESIGN-RULE-003 — Chỉ record states thấy được

- `states_confirmed`: states có screenshot explicit (loading.png, error.png, content.png).
- `states_missing`: states phổ biến (loading/error/empty/offline) không có screenshot.
- **Cấm** tự generate loading/error state behavior từ 1 content screenshot.

### DESIGN-RULE-004 — Ambiguous component → list candidates

Nếu component không rõ semantic (icon không nhãn, button không label):

```yaml
components_ambiguous:
  - id: top-right-icon
    position: top-right
    visual: outlined circle with heart shape
    candidates: [favorite, like, bookmark]
    resolution: human-review
```

**Cấm** đoán 1 ý nghĩa và gán confirmed.

### DESIGN-RULE-005 — Không claim exact dimension/spacing

**Cấm:**
```yaml
components:
  - id: cover-image
    width: 320dp
    height: 480dp
```

**Đúng:**
```yaml
components:
  - id: cover-image
    size_hint: large      # small | medium | large | fullwidth
    aspect_hint: portrait # portrait | landscape | square
```

### DESIGN-RULE-006 — Component type từ enum chuẩn

Dùng đúng vocabulary (map được tới Compose primitives):

- `image`, `icon`, `text`, `text-field`, `button`, `primary-button`, `secondary-button`, `text-button`
- `card`, `surface`, `divider`
- `app-bar`, `bottom-bar`, `bottom-sheet`, `dialog`, `snackbar`
- `list-item`, `grid-item`
- `checkbox`, `radio`, `switch`, `slider`
- `tab`, `chip`, `badge`

Không tạo type mới. Nếu không fit → `custom` + description.

### DESIGN-RULE-007 — Layout hint confidence

- `layout_hint: vertical-scroll` → `confidence: inferred` default
- Chỉ `confidence: confirmed` khi có spec quote mô tả scroll behavior.

### DESIGN-RULE-008 — Responsive = unresolved

Screenshot chỉ chứa 1 breakpoint (thường phone portrait). Mọi assumption về tablet/landscape/foldable:

- Add vào `unknowns` trong screen contract
- Không được render thành requirement confirmed

## Soft rules

### DESIGN-RULE-010 — Prefer semantic grouping

Group components theo region visually:

```yaml
components:
  - id: header
    type: app-bar
    children: [back-button, title, more-icon]
  - id: content-area
    children: [cover-image, metadata-block, action-row]
```

### DESIGN-RULE-011 — Asset list exhaustive

Mọi logo/icon/illustration trong screenshot phải list vào `assets_referenced`. Nếu chưa có file:

- Tạo issue `MISSING_ASSET` severity `high`
- Resolution hint: request từ designer

### DESIGN-RULE-012 — Typography hint only

```yaml
- id: book-title
  type: text
  typography_hint: headline-large
  weight_hint: bold
```

Không claim font family hoặc exact px size. Mapping tới Material Typography scale downstream.

## Reading procedure

1. **View full screenshot** (vision model) trước khi extract.
2. **Identify screen type**:
   - Full-screen? Modal? Bottom-sheet? Dialog?
   - Scroll direction? Fixed layout?
3. **Scan top-down, left-right** list visible components.
4. **For each component**:
   - Type từ enum DESIGN-RULE-006
   - Position (top/center/bottom + left/center/right)
   - Visible text content (quote exact nếu có text)
   - Action: null nếu không có spec; `action_ref: REQ-XXX` nếu có
5. **Identify states screenshot represent** → `states_confirmed`.
6. **List missing states** phổ biến chưa có.
7. **Mark ambiguous** → `components_ambiguous`.
8. **List assets** referenced.
9. **List unknowns** (responsive, animation, dark mode).
10. **Write screen section** vào `design.md`, bind YAML vào `brief.yaml`.

## Anti-patterns (CẤM)

### AP-001 — Color extraction

**Sai:** gán `background: "#FFFFFF"` từ screenshot.
**Đúng:** `background_estimate: white` + mapping downstream.

### AP-002 — Infer loading/error state

**Sai:** chỉ có content.png nhưng generate requirement "loading state show spinner".
**Đúng:** `states_missing: [loading]` + nếu spec yêu cầu loading → issue `MISSING_DESIGN`.

### AP-003 — Click-to-nav assumption

**Sai:** "tap list-item → book-detail screen" không có spec.
**Đúng:** `action_ref: null` + issue `MISSING_BEHAVIOR` nếu spec không confirm.

### AP-004 — Font family claim

**Sai:** `font_family: Roboto`.
**Đúng:** `typography_hint: body-large` + mapping project token.

### AP-005 — Over-decompose component

**Sai:** list từng icon pixel, từng divider 1dp. Noise cao, không actionable.
**Đúng:** group semantic (header block, content block), skip visual decoration không có action.

### AP-006 — Imply animation từ static image

**Sai:** "Button có ripple animation khi tap".
**Đúng:** `unknowns: [tap-feedback-animation]` → project default downstream.

## Edge cases

### Blurred / low-res screenshot

- Resolution < 720px short side → warning, giảm confidence
- Blur detected → list vào `unknowns` những region không đọc được
- Nếu > 50% components ambiguous → issue `UNSUPPORTED_INPUT` severity `high`

### Multiple variants trong 1 image (A/B)

- Treat như 2 screens riêng
- Nếu không rõ variant nào final → issue `SOURCE_CONFLICT`

### Screenshot với annotation từ designer

- Nếu có arrow/label từ Figma overlay → extract annotation thành note
- Preserve annotation vì nó là **spec implicit** (confirmed hơn screenshot alone)

### Dark mode variant

- Nếu có cả light + dark screenshot → 2 variants cùng screen
- Chỉ có 1 → unknown dark mode, không claim

## Required policies

- Reference `blueprints/feature-brief/README.md`
- Reference `requirement-extraction-rules.md` khi link action tới requirement
- Reference `reconciliation-matrix.md` khi conflict với spec
- Reference `knowledge/coding/compose/essentials.md` cho project component vocabulary (nếu có)
