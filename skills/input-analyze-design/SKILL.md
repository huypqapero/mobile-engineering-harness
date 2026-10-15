---
name: input-analyze-design
description: Extract screen contract từ screenshots thành design.md + partial brief.yaml. Nhận diện components, states, ambiguity, assets; không claim design token exact. Thực hiện Phase P3 của prepare-feature pipeline hoặc gọi độc lập.
priority: P1
---

# Skill: input-analyze-design

## Trigger

- Phase P3 của `input-prepare-feature`
- "Phân tích screenshots của <feature>"
- "Refresh design section của brief <slug>"
- Figma export → screen contract (Wave 3)

## Inputs

Bắt buộc:
- Design source trong `briefs/<slug>/assets/sources/`:
  - Local: thư mục `screenshots/` (PNG files)
  - Figma: `figma/node-tree.json` + `figma/variables.json` + `figma/screen-contracts.json` + `screenshots/*.png`
- Brief slug

Optional:
- Spec analysis output từ `input-analyze-spec` (để link `action_ref`)
- Project `knowledge/compose/essentials.md` cho component vocabulary

## Source priority

Nếu `figma/screen-contracts.json` present:
- **Primary input**: structured contract (component hierarchy, layout mode, variables bind)
- **Secondary input**: PNG snapshots (visual confirm)
- **Override rules áp dụng**: color/dimension/layout confirmed khi có variable bind

Nếu chỉ PNG screenshots:
- Vision model đọc PNG
- Toàn bộ DESIGN-RULE mặc định với confidence `inferred`

## Prerequisites

Trước khi analyze:

1. `agents/design-analyst.md` — role boundaries + anti-patterns
2. `knowledge/input-analysis/screenshot-reading-rules.md` — DESIGN-RULE-001..012
3. `knowledge/input-analysis/figma-fetch-rules.md` — override rules khi có variables
4. `blueprints/feature-brief/design.md.template`
5. `blueprints/feature-brief/brief.yaml.template`

## Execution procedure

### Step 1 — Inventory input

- List screenshots trong thư mục
- Record filename convention: `<screen-id>.png` hoặc `<screen-id>-<state>.png`
- Compute checksum nếu chưa có trong brief

### Step 2 — Per-screenshot analysis

Lặp qua từng screenshot:

#### Step 2.1 — View full image

- Vision model load full resolution
- Check quality:
  - Resolution < 720px short side → warning, giảm confidence
  - Blur detected → list region vào `unknowns`

#### Step 2.2 — Screen identification

- Type: full-screen / dialog / bottom-sheet / modal / overlay
- Scroll direction: vertical / horizontal / none / grid
- Variant: single hoặc multiple A/B

#### Step 2.3 — Component scan

Top-down, left-right:

- Type từ enum DESIGN-RULE-006 (nếu không fit → `custom` + description)
- Position (top/center/bottom + left/center/right)
- Visible text: quote exact nếu có label
- Group semantic (header/content/footer block)
- Skip decoration (divider 1dp, spacer, background pattern)

#### Step 2.4 — Classify confidence

Mỗi component:

- Confirmed (có label text visible) → `components_inferred` (visual confirmed, action chưa confirm)
- Ambiguous (icon không nhãn, button không label) → `components_ambiguous` với candidates list

**DESIGN-RULE-004:** không claim single meaning cho ambiguous.

#### Step 2.5 — State detection

- `states_confirmed`: states có screenshot explicit
- `states_missing`: states phổ biến không có screenshot (loading, error, empty, offline)

**DESIGN-RULE-003:** không generate behavior cho state missing.

#### Step 2.6 — Asset tracking

- List mọi logo/icon/illustration → `assets_referenced`
- Match với file có sẵn trong `assets/sources/`
- Missing file → issue `MISSING_ASSET` severity high

#### Step 2.7 — Unknowns

- Responsive layout (chỉ 1 breakpoint)
- Animation (static image)
- Dark mode (nếu chỉ có 1 variant)
- Behavior khi tap (nếu spec không confirm)

### Step 3 — Cross-reference với spec (nếu có)

Nếu spec analysis đã complete:

- Match component có action semantic với REQ confirmed → gán `action_ref: REQ-XXX`
- Component không có REQ match → `action_ref: null`, issue `MISSING_BEHAVIOR`
- REQ UI không có component screenshot → issue `MISSING_DESIGN`

**Nếu spec analysis chưa complete:** để `action_ref: null`, phase P4 reconcile sẽ link.

### Step 4 — Write prose

Vào `briefs/<slug>/design.md` theo template:

- Design system scope (strategy: prefer-existing-project-tokens)
- Mỗi screen 1 section:
  - Source + layout hint
  - Visible components table
  - Ambiguous components list
  - States confirmed + missing
  - Assets referenced
- Navigation section (confirmed + inferred)
- Open design questions

### Step 5 — Bind YAML

Update `briefs/<slug>/brief.yaml`:

- `screens[]` entries với:
  - `id`, `name`, `source`, `layout_hint`
  - `states_confirmed`, `states_missing`
  - `components_inferred[]`, `components_ambiguous[]`
- `issues[]` cho MISSING_DESIGN, MISSING_BEHAVIOR, MISSING_ASSET, AMBIGUOUS_COMPONENT

### Step 6 — Edge case handling

- Blurred/low-res → warning + continue
- > 50% component ambiguous trên 1 screen → issue `UNSUPPORTED_INPUT` severity high
- Multiple variants trong 1 image → tách thành 2 screens
- Annotation designer trên screenshot → extract note, confidence cao hơn visual alone
- No screenshot provided → skip skill, flag `screens: []`

## Required policies

- DESIGN-RULE-001..012 (`screenshot-reading-rules.md`)
- `agents/design-analyst.md` anti-patterns AP-001..010

## Output contract

Deliverable gồm:

- `briefs/<slug>/design.md` (prose complete)
- `briefs/<slug>/brief.yaml` partial update (screens + design issues)

## Validation

Trước khi handoff:

- [ ] Mọi screenshot có screen entry
- [ ] Mọi screen entry có source path + checksum match
- [ ] Mọi component có type từ enum (hoặc `custom` với description)
- [ ] Mọi ambiguous component có candidates ≥ 2
- [ ] Mọi state missing listed
- [ ] Mọi asset referenced match file hoặc issue MISSING_ASSET
- [ ] Không claim exact color/dimension/font (DESIGN-RULE-001, -005)
- [ ] Không infer navigation (DESIGN-RULE-002)

## Failure / recovery

- Screenshot path không tồn tại → BLOCKED gate DESIGN-001
- Screenshot corrupted → report + skip, không fail toàn phase
- Vision model confidence quá thấp → warning + output partial, flag `UNSUPPORTED_INPUT`

## Anti-patterns bị cấm

Xem `agents/design-analyst.md`:
- AP-001 color extraction exact
- AP-002 infer navigation
- AP-003 generate missing state
- AP-004 exact dimensions
- AP-005 font family claim
- AP-006 icon semantic single meaning
- AP-007 over-decompose
- AP-008 imply animation
- AP-009 design new UI
- AP-010 skip ambiguity

## Handoff

→ `input-reconcile` (Phase P4) với design analysis output

## Figma mode procedure (khi có screen-contracts.json)

### Step F1 — Load structured contract

- Parse `figma/screen-contracts.json`
- Parse `figma/variables.json` nếu present
- Verify checksum match với brief.yaml.sources[]

### Step F2 — Map screens

Mỗi screen trong contract → entry trong brief:
- `figma_node_id` → metadata reference
- `layout_mode` → `layout_hint` confirmed (override DESIGN-RULE-007)
- `variants_available` → `states_confirmed` nếu match semantic (Content, Loading, Error)

### Step F3 — Map components

Mỗi component trong contract:
- `type` convert sang component enum (COMPONENT_INSTANCE với name "Button/Primary" → `primary-button`)
- `fills[].variable_name` → `background_color_token` confirmed (override DESIGN-RULE-001)
- `fixed_width/height` → size info confirmed
- `text_content` → text visible confirmed
- Vẫn flag ambiguous nếu component name không semantic rõ

### Step F4 — Visual confirm bằng PNG

Load tương ứng PNG screenshot:
- Verify component layout từ contract match visual
- Mismatch → raise issue `SOURCE_CONFLICT` giữa Figma contract và render
- (Rare, nhưng xảy ra khi designer chưa refresh)

### Step F5 — Preserve DESIGN-RULE không override

Vẫn áp:
- DESIGN-RULE-002 không infer navigation (prototyping link ≠ production nav)
- DESIGN-RULE-003 chỉ record states có variant hoặc frame
- DESIGN-RULE-004 ambiguous component (icon không semantic name)

## Future (Wave 4+)

- Figma Dev Mode spec extraction (nếu MCP support)
- Smart variant → Compose state mapping với human approval
- Figma Code Connect integration
