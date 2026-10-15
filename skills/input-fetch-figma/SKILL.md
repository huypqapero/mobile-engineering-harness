---
name: input-fetch-figma
description: Fetch Figma file + node tree + variables + image export qua framelink-figma MCP (primary) hoặc TalkToFigma MCP (fallback live). Normalize sang structured screen-contracts.json + PNG snapshots. Adapter fetch-only. Phase P1b khi design nguồn là Figma.
priority: P1
---

# Skill: input-fetch-figma

## Trigger

- Phase P1 của `input-prepare-feature` khi design source type = `figma`
- "Fetch Figma frame <URL> vào brief <slug>"
- "Snapshot Figma design cho feature X"

## Inputs

Bắt buộc:
- Brief slug (output location `briefs/<slug>/`)
- Figma identifier (1 trong 2):
  - URL: `https://www.figma.com/design/<file_key>/<file_name>?node-id=<node_id>`
  - File key + node_id

Optional:
- `--mode: fetch | live` (default: fetch via framelink-figma)
- `--include-variables` (default: true nếu file có variables)
- `--include-components-library` (default: false — không auto-fetch remote library)
- `--export-format: png | svg | both` (default: png cho screen, svg cho icon)
- `--export-scale: 1 | 2 | 3` (default: 2)
- `--variants: all | current | selective` (default: all cho component có variantProperties)

## Prerequisites

Trước khi fetch:

1. `knowledge/input-analysis/figma-fetch-rules.md` — FIG-RULE-001..008 + overrides
2. `knowledge/input-analysis/screenshot-reading-rules.md` — base rules
3. `blueprints/feature-brief/README.md`

MCP tools cần available (primary = framelink-figma):
- `mcp__framelink-figma__get_figma_data`
- `mcp__framelink-figma__download_figma_images`

Fallback (live mode) = TalkToFigma:
- `mcp__TalkToFigma__join_channel`
- `mcp__TalkToFigma__get_document_info`, `get_node_info`, `scan_nodes_by_types`
- `mcp__TalkToFigma__export_node_as_image`, `get_local_components`, `get_styles`

Nếu không MCP nào available → BLOCKED, raise cho user setup.

## Execution procedure

### Step 1 — Resolve file + node

Parse Figma URL regex:
- `/design/<file_key>/`
- `?node-id=<node_id>` (format `1-2` → convert thành `1:2` cho API)

Nếu input chỉ có file_key không node_id:
- `get_figma_data(file_key, depth=1)` → list top-level FRAMEs
- Prompt user chọn frame của feature

### Step 2 — Pick MCP mode

Default: `framelink-figma` (fetch mode, file API).

Switch sang `TalkToFigma` khi:
- `--mode: live` explicit
- File chưa publish version (designer đang work)
- framelink-figma trả error 403 (file private, user cần plugin workflow)

Live mode procedure:
- `join_channel(channel)` — user cung cấp channel ID từ Figma plugin
- `get_document_info()` + `get_node_info(nodeId)` thay cho `get_figma_data`
- Rest procedure tương tự

### Step 3 — Fetch node tree

Fetch mode:
```
get_figma_data(file_key, node_id, depth="full")
```

- Trả về node tree với children recursive
- Save vào `briefs/<slug>/assets/sources/figma/node-tree.json`

Live mode: `get_nodes_info(nodeIds)` với selection từ user.

### Step 4 — Fetch variables + styles

Fetch mode: `get_figma_data` include variables (nếu MCP support option).

Nếu file có variables:
- Save vào `assets/sources/figma/variables.json`
- Record `has_variables: true` metadata

Nếu không: skip variables, `has_variables: false`, downstream fallback DESIGN-RULE không override.

Live mode: `get_styles()` + variable detection manual.

### Step 5 — Identify screens

Trong node tree, filter screens candidate:

- `type: FRAME` ở top-level feature scope
- Name match pattern "<Feature> / <State>" hoặc single frame nếu không có variants
- Group siblings cùng prefix thành screen variants

Mỗi screen có:
- Primary variant (ví dụ `Content`)
- Alternate variants (`Loading`, `Error`, `Empty`, `Offline`)

### Step 6 — Export screenshots

Fetch mode:
```
download_figma_images(
  file_key,
  node_ids=[screen_node_ids],
  format="png",
  scale=2
)
```

Save vào `briefs/<slug>/assets/sources/screenshots/<screen-id>.png`:
- `book-detail-content.png`
- `book-detail-loading.png`
- `book-detail-error.png`

Mỗi screen variant 1 PNG.

Live mode: `export_node_as_image(nodeId, format="PNG", scale=2)` loop.

### Step 7 — Export icons/illustrations (SVG)

Scan node tree cho component type `COMPONENT` / `INSTANCE` có semantic name (`Icon/Play`, `Illustration/Empty`):

- Export SVG format: preserve vector
- Save vào `assets/sources/assets/<name>.svg`

### Step 8 — Resolve component master

Scan node tree cho `componentId` references trong INSTANCE nodes:

- Nếu master cùng file: fetch master definition, include vào node-tree.json
- Nếu master từ library khác: note `remote_component: <library_key>:<component_key>` trong screen-contracts, không auto-fetch

Nếu `--include-components-library` + user có access: optional fetch library file riêng.

### Step 9 — Extract structured contract

Build `screen-contracts.json` từ node tree (FIG-RULE-004..008):

```json
{
  "fetched_at": "2026-10-15T17:30:00+07:00",
  "file_key": "<file_key>",
  "node_id": "1:2",
  "has_variables": true,
  "screens": [
    {
      "id": "book-detail-content",
      "figma_node_id": "1:234",
      "name": "Book Detail / Content",
      "layout_mode": "VERTICAL",
      "primary_axis_align": "MIN",
      "counter_axis_align": "CENTER",
      "padding": {"top": 16, "left": 16, "right": 16, "bottom": 16},
      "variants_available": ["Content", "Loading", "Error"],
      "components": [
        {
          "id": "play-button",
          "figma_node_id": "1:245",
          "type": "COMPONENT_INSTANCE",
          "component_master_id": "0:12",
          "component_name": "Button/Primary",
          "layout_mode": "HORIZONTAL",
          "fixed_width": 120,
          "fixed_height": 44,
          "fills": [
            {
              "type": "SOLID",
              "variable_id": "VariableID:1:1",
              "variable_name": "tokens-color/primary-500"
            }
          ],
          "text_content": "Play Preview"
        }
      ],
      "reactions": []
    }
  ]
}
```

Save vào `assets/sources/figma/screen-contracts.json`.

### Step 10 — Record metadata

Build `brief.yaml.sources[]` entries theo FIG-RULE-002:

```yaml
sources:
  design:
    - path: assets/sources/figma/node-tree.json
      checksum: sha256:<hex>
      format: figma
      origin: figma://file/<file_key>?node=1-2&version=<lastModified>
      origin_metadata:
        file_key: "<file_key>"
        file_name: "Product Design System"
        last_modified: <ISO 8601>
        node_id: "1:2"
        has_variables: true
        variable_collections: [tokens-color, tokens-spacing, tokens-typography]
        fetched_at: <ISO 8601>
        mcp_adapter: framelink-figma
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
    - path: assets/sources/screenshots/book-detail-loading.png
      checksum: sha256:<hex>
      format: screenshot
      origin: figma://file/<file_key>?node=1:235&export=png@2x
```

### Step 11 — Report

```
Figma fetch complete:
- File: <file_name> (last modified <date>)
- MCP adapter: framelink-figma | TalkToFigma
- Scope: node <node_id>
- Screens exported: <count> (<variant list>)
- Icons/SVG exported: <count>
- Variables available: yes/no (<N> collections)
- Remote components: <count> (not fetched)

Snapshot: briefs/<slug>/assets/sources/figma/ + screenshots/ + assets/
Checksums computed: <total files>
```

## Required policies

- FIG-RULE-001..008 + overrides (`figma-fetch-rules.md`)
- Base DESIGN-RULE-001..012 (`screenshot-reading-rules.md`) — áp cho PNG fallback khi variables không có
- Anti-patterns AP-001..008

## Output contract

Deliverable:
- `briefs/<slug>/assets/sources/figma/`:
  - `node-tree.json`
  - `variables.json` (nếu có)
  - `styles.json`
  - `screen-contracts.json`
- `briefs/<slug>/assets/sources/screenshots/*.png` (PNG @2x cho mỗi screen variant)
- `briefs/<slug>/assets/sources/assets/*.svg` (icons)
- `brief.yaml.sources[]` entries với origin figma:// + checksum + metadata

## Validation

Trước khi handoff tới Phase P3:

- [ ] Node tree JSON non-empty
- [ ] Mọi screen variant có PNG snapshot
- [ ] Nếu variables available: `has_variables: true` + variables.json present
- [ ] Checksum computed cho mọi file
- [ ] Origin field format valid (`figma://file/<key>?node=...`)
- [ ] Remote components flagged (không expect fetch)

## Failure / recovery

- MCP không available → BLOCKED, user setup framelink-figma hoặc TalkToFigma
- File key invalid → BLOCKED, raise `UNSUPPORTED_INPUT`
- Node_id invalid → BLOCKED
- Image export fail (individual node) → warning + raise `MISSING_ASSET` cho node đó, continue
- Node tree quá sâu (overflow) → fallback depth=5, note trong metadata
- Live mode plugin disconnect → prompt user re-connect, resume từ progress checkpoint

## Anti-patterns bị cấm

Xem `figma-fetch-rules.md`:
- AP-001 analyze trong adapter
- AP-002 follow prototyping link as production nav
- AP-003 fetch toàn file blindly
- AP-004 store Figma token in brief
- AP-005 modify Figma file (chỉ read tools)
- AP-006 export at exact pixel @3x unnecessary
- AP-007 auto-map variants sang states
- AP-008 flatten node tree

## Handoff

→ `input-prepare-feature` Phase P3 (`input-analyze-design`) đọc:

- Primary: `screen-contracts.json` (structured)
- Secondary: PNG screenshots (visual confirm)
- Variables: `variables.json` → unlock DESIGN-RULE override cho color/dimension/layout confirmed

## Future (Wave 4+)

- Figma Code Connect integration (nếu Figma + MCP support)
- Figma Dev Mode spec extraction
- Variable collection merge khi file dùng multiple collections
- Smart variant → Compose state mapping (require human approval)
