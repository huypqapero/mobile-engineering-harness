# Figma Fetch Rules

Rules fetch Figma file + node tree + image export qua `framelink-figma` MCP (primary) hoặc `TalkToFigma` MCP (fallback live canvas), normalize sang screen contract để feed vào `business-analyze --phase design`. Áp dụng cho skill `business-fetch --source figma`.

## Mục đích

Figma là design source authoritative. Khác screenshot, Figma có **node tree structured**: component hierarchy, variants, variables (design tokens), auto-layout, constraints. Adapter trích xuất structured data + export image để downstream analyzer có cả visual lẫn metadata.

**Nguyên tắc adapter:** fetch-only. Không thiết kế UI mới, không map tới Compose components, không infer business behavior.

## Available MCP tools

### Primary: `framelink-figma` (REST API, file key based)

| Tool | Dùng cho |
|---|---|
| `get_figma_data` | Fetch file content theo file_key + optional node_id (node tree + styles + variables) |
| `download_figma_images` | Export node thành PNG/SVG/JPG theo node_id list |

**Ưu điểm:** không cần Figma plugin, chỉ cần API token. Deterministic, re-fetch stable.

### Fallback: `TalkToFigma` (plugin, live canvas)

| Tool | Dùng cho |
|---|---|
| `join_channel` | Connect tới Figma plugin instance |
| `get_document_info` | Document metadata |
| `get_node_info` / `get_nodes_info` | Node details |
| `read_my_design` / `get_selection` | Current selection |
| `scan_text_nodes` | Text content tree |
| `scan_nodes_by_types` | Filter theo type (COMPONENT, INSTANCE, FRAME, ...) |
| `export_node_as_image` | Export image |
| `get_local_components` | Component library |
| `get_styles` | Styles palette |

**Dùng khi:** designer đang work live, cần capture current state ngay (chưa publish file version), hoặc interact với plugin workflow.

**Default:** prefer `framelink-figma` cho fetch pipeline deterministic.

## Hard rules

### FIG-RULE-001 — Snapshot immutable

- Node tree JSON → `briefs/<slug>/assets/sources/figma/node-tree.json`
- Variables (design tokens) → `assets/sources/figma/variables.json`
- Styles → `assets/sources/figma/styles.json`
- Image exports → `assets/sources/screenshots/<node-name>.png` (PNG @2x default)
- Compute checksum sha256 cho mọi file

### FIG-RULE-002 — Record file version

- Figma file có version/branch; `get_figma_data` trả về `lastModified`
- Record vào `brief.yaml.sources[].origin`:
  ```yaml
  origin: figma://file/<file_key>?node=<node_id>&version=<lastModified>
  ```
- Re-fetch khác version → brief version bump

### FIG-RULE-003 — Node selection explicit

- MUST không fetch toàn file nếu user chỉ cần 1 feature
- User chỉ định `node_id` của frame feature (từ Figma URL `?node-id=1-2`)
- Fallback: fetch root → list top-level frames → user chọn

### FIG-RULE-004 — Variables = authoritative design token

Figma variables (color/number/string) là design token source truth. Khi có variables:

- Record đầy đủ `variables.json` snapshot
- Trong `brief.yaml.sources[].origin_metadata`:
  ```yaml
  origin_metadata:
    has_variables: true
    variable_collections: [tokens-color, tokens-spacing, tokens-typography]
  ```
- Downstream `business-analyze --phase design` có variables → được phép `confirmed` thay vì `inferred` cho color/spacing (xem override rule DESIGN-RULE-OVERRIDE-FIGMA bên dưới)

### FIG-RULE-005 — Component instance resolution

Figma components: `COMPONENT` (master) vs `INSTANCE` (reuse).

- Khi export INSTANCE: record `componentId` reference về master
- Nếu master trong cùng file: fetch cả master definition
- Nếu master từ library khác: note `remote_component: true`, không auto-fetch library

### FIG-RULE-006 — Image export quality

- Format: PNG @2x cho screenshot analysis (DESIGN-RULE-001 vẫn áp: không claim exact color từ PNG)
- Format: SVG cho icon export (preserve vector cho asset)
- Scale: 2x default (balance quality vs size); user override được

### FIG-RULE-007 — Variants export riêng

Component có `variantProperties` (ví dụ `state: default/hover/pressed`):

- Export mỗi variant riêng: `<component>-<variant>.png`
- Record trong node-tree.json với variant metadata
- Downstream map variants sang Compose state (hover khó trên mobile → agent decide)

### FIG-RULE-008 — Preserve constraints + auto-layout

- Node có `layoutMode: VERTICAL | HORIZONTAL | NONE` → record làm layout hint confirmed
- Node có `primaryAxisAlignItems`, `counterAxisAlignItems` → record alignment
- Rationale: Figma auto-layout = Compose Row/Column mapping deterministic; không cần "infer vertical-scroll"

## Design rule overrides khi có Figma

Khi design source là Figma (có variables + node tree), các DESIGN-RULE bị override:

### DESIGN-RULE-OVERRIDE-001 — Color từ variable confirmed

Nếu node color bind tới variable:

```yaml
components:
  - id: play-button
    background_color_token: tokens-color/primary-500   # ← confirmed, không estimate
    source: figma-variable
```

Không áp `background_color_estimate: blue` nữa.

### DESIGN-RULE-OVERRIDE-005 — Dimension confirmed khi fixed

Node có `constraints.horizontal: SCALE` + fixed width:

- Width/height confirmed trong Figma context
- Downstream `business-analyze --phase design` vẫn note: implementation có thể dùng flexible modifier thay vì hardcoded dp

### DESIGN-RULE-OVERRIDE-007 — Layout confirmed

Figma auto-layout `layoutMode` → `layout_hint` confirmed, không inferred.

### DESIGN-RULE không override

Vẫn áp:
- DESIGN-RULE-002 (không infer navigation): Figma có prototyping links nhưng link ≠ production nav; vẫn cần spec confirm
- DESIGN-RULE-003 (chỉ record states thấy được): Figma có variants nhưng không mapping 1-1 với Compose runtime state
- DESIGN-RULE-004 (ambiguous → candidates): icon trong Figma không có semantic label vẫn ambiguous

## Fetch procedure

### Step 1 — Resolve file + node

Input có thể là:
- Figma URL: `https://www.figma.com/design/<file_key>/<file_name>?node-id=1-2`
- File key: `<file_key>` + optional node_id

Agent:
1. Parse URL → extract `file_key` + `node_id`
2. Nếu không có `node_id`: `get_figma_data(file_key)` → list top-level frames → user chọn

### Step 2 — Fetch node tree

`get_figma_data(file_key, node_id, depth=full)`:

- Trả về node tree với component hierarchy
- Lưu vào `assets/sources/figma/node-tree.json`

### Step 3 — Fetch variables + styles

- `get_figma_data` với query includeVariables=true → variables collection
- Lưu vào `assets/sources/figma/variables.json` + `styles.json`
- Nếu file không có variables (older design): note `has_variables: false`

### Step 4 — Identify screens

Trong node tree, filter nodes có `type: FRAME` ở top-level feature → candidate screens.

Mỗi screen:
- Name: Figma frame name (ví dụ "Book Detail / Content")
- ID: slug từ name (`book-detail-content`)
- Variants: list sibling frames cùng prefix (`Book Detail / Loading`, `Book Detail / Error`)

### Step 5 — Export images

`download_figma_images(node_ids, format=PNG, scale=2)`:

- Mỗi screen → 1 PNG
- Save vào `assets/sources/screenshots/<screen-id>.png`
- Icons/illustrations (type: COMPONENT, INSTANCE với semantic name) → SVG export vào `assets/sources/assets/`

### Step 6 — Resolve component references

Scan node tree cho `componentId` references:

- Nếu master trong file: fetch master definition, include trong node-tree.json
- Remote components: note `remote_component: <library_key>:<component_key>`, không fetch

### Step 7 — Extract design metadata

Build structured contract vào `assets/sources/figma/screen-contracts.json`:

```json
{
  "screens": [
    {
      "id": "book-detail-content",
      "figma_node_id": "1:234",
      "name": "Book Detail / Content",
      "layout_mode": "VERTICAL",
      "variants_available": ["Content", "Loading", "Error"],
      "components": [
        {
          "id": "play-button",
          "figma_node_id": "1:245",
          "type": "COMPONENT_INSTANCE",
          "component_master_id": "0:12",
          "layout_hint": "horizontal-auto",
          "fixed_width": 120,
          "fixed_height": 44,
          "fills": [
            {
              "type": "SOLID",
              "variable_id": "VariableID:1:1",
              "variable_name": "tokens-color/primary-500"
            }
          ]
        }
      ]
    }
  ]
}
```

### Step 8 — Checksum + record

Build `brief.yaml.sources[]` entries:

```yaml
sources:
  design:
    - path: assets/sources/figma/node-tree.json
      checksum: sha256:<hex>
      format: figma
      origin: figma://file/<file_key>?node=1-2&version=1697...
      origin_metadata:
        file_key: "<file_key>"
        file_name: "Product Design System"
        last_modified: 2026-10-14T10:30:00+07:00
        node_id: "1:2"
        has_variables: true
        variable_collections: [tokens-color, tokens-spacing]
        fetched_at: 2026-10-15T17:30:00+07:00
    - path: assets/sources/figma/variables.json
      checksum: sha256:<hex>
      format: figma
      origin: figma://file/<file_key>/variables
    - path: assets/sources/figma/screen-contracts.json
      checksum: sha256:<hex>
      format: figma
      origin: figma://file/<file_key>?node=1-2
    - path: assets/sources/screenshots/book-detail-content.png
      checksum: sha256:<hex>
      format: screenshot
      origin: figma://file/<file_key>?node=1:234&export=png@2x
```

## Anti-patterns (CẤM)

### AP-001 — Analyze trong adapter

Fetch skill map Figma components sang Compose. CẤM. `business-analyze --phase design` làm việc này.

### AP-002 — Follow prototyping link as nav

Figma có `prototypeStartNodeID`, `transitionNodeID`. CẤM treat là production navigation. Nav vẫn cần spec confirm (DESIGN-RULE-002).

### AP-003 — Fetch toàn file blindly

File lớn > 1000 nodes. Fetch toàn bộ waste. Phải user chỉ định node_id scope.

### AP-004 — Store Figma token in brief

API token Figma vào metadata. CẤM. Credential ở MCP config.

### AP-005 — Modify Figma file

TalkToFigma có tools write (`create_frame`, `set_fill_color`, `delete_node`). Fetch adapter CẤM dùng write tools. Chỉ read.

### AP-006 — Export at exact pixel

Export @3x vì "chất lượng cao hơn". KHÔNG cần cho analysis. @2x đủ, giảm disk + MCP latency.

### AP-007 — Treat variants as states automatic

Figma variant `state: hover` → Compose `isHovered`. CẤM auto-map. Mobile không có hover; agent downstream decide.

### AP-008 — Flatten node tree

Lose hierarchy khi serialize. Preserve full tree để downstream phân tích component containment.

## Edge cases

### File không có variables (older design)

- `has_variables: false` → design token vẫn `_estimate`, không override
- Downstream fallback về screenshot reading rules

### File dùng component library external

- Component master ở library khác → `remote_component: true`
- Không auto-fetch library (phần lớn case user không có permission library)
- Downstream biết: component contract từ library, có thể hỏi designer snapshot

### Prototyping với conditional interactions

- Figma có `reaction` với condition logic → complex nav graph
- Adapter record raw reactions vào node-tree.json
- Phân tích flow vẫn thuộc Product Analyst + spec reconcile, không adapter

### Frame quá sâu (nested > 10 levels)

- Fetch với `depth: full` có thể overflow MCP response
- Fallback: fetch root → selective expand theo node_id user quan tâm

### Image export fail

- Node bị hidden hoặc permission issue → export fail
- Raise issue `MISSING_ASSET` severity high, continue với các node khác

### TalkToFigma plugin disconnect

- Live canvas workflow có risk plugin disconnect
- Fallback: user re-connect + resume từ checkpoint (adapter track progress)
- Hoặc switch sang framelink-figma nếu file key available

## Required policies

- `blueprints/feature-brief/README.md`
- `screenshot-reading-rules.md` — base rules, apply với overrides khi có variables
- `reconciliation-matrix.md` — Figma source level trust rules
- Project `constitution/engineering-principles.md`

## Downstream handoff

Figma output → `business-analyze --phase design`:

- Primary input: `screen-contracts.json` (structured) + PNG screenshots (visual fallback)
- Design analyst dùng structured data trước, screenshot cho visual confirm
- Variables available → mark design token confirmed trong brief

Nếu user chỉ cung cấp Figma URL (không spec text) → feature headless. Spec vẫn cần source riêng (brief gate SPEC-001 require ≥1 spec source).
