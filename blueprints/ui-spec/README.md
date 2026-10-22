# Blueprint: UI Spec

Per-node UI contract: Reach + Door + Elements + Tokens + Copy + Assets. Mỗi screen / popup / sheet / dialog / state có 1 markdown spec. Guard dùng `## Reach` để mở node, ui-judge compare screenshot với spec.

## Why

- **Checklist, không ảnh**: coding agent build theo checklist text, không guess từ Figma image
- **Guard navigable**: `## Reach` cho driver mở node (preset + deep link) không rely vào manual flow
- **Judge contractual**: ui-judge có checklist cụ thể để grade, không chỉ "trông giống không"
- **Door explicit**: biết SDK/library override vs app-owned draw
- **Multi-state coverage**: popup/sheet/dialog/state đều là node riêng, không ẩn trong screen

## Khác biệt với design.md trong feature-brief

| | design.md (feature-brief) | ui-spec/<node>.md |
|---|---|---|
| Scope | Toàn screen contract | 1 node (screen / popup / sheet / dialog / state) |
| Audience | Architect + Coder | Driver + ui-judge |
| Format | Table components + states | Checklist với exact copy + tokens |
| Count | 1 markdown per screen | 1 markdown per node (screen có 3 variants → 3 ui-specs) |
| Consume | Stage 2 Plan | Stage 4+ runtime E2E |

Flow: ui-spec-writer (Wave 2 agent) extract Figma frame → sinh ui-spec markdown.

## Package layout

```text
blueprints/ui-spec/
├── README.md                       # file này
├── node-spec.md.template           # per-node template
└── nodes-manifest.json.template    # _nodes.json index manifest
```

## Node types

| Kind | Example |
|---|---|
| `screen` | Full-screen route (Book List, Book Detail) |
| `popup` | Modal popup over screen (Reward popup) |
| `sheet` | Bottom sheet (Share options) |
| `dialog` | Alert dialog (Confirm logout) |
| `state` | Alt variant của screen (Loading, Error, Empty, Offline) |

## Manifest `_nodes.json`

Index all nodes của 1 fixture:

```json
[
  { "slug": "book-detail-content", "frameId": "1:234", "kind": "screen" },
  { "slug": "book-detail-loading", "frameId": "1:235", "kind": "state", "parent": "book-detail-content" },
  { "slug": "book-detail-error", "frameId": "1:236", "kind": "state", "parent": "book-detail-content" },
  { "slug": "popup-reward", "frameId": "3:9", "nodeId": "3:12", "parent": "book-detail-content", "kind": "popup" }
]
```

Rules:
- `slug` kebab-case, unique
- `frameId` Figma frame reference (nếu có Figma source)
- `nodeId` cho popup/sheet trong 1 frame
- `parent` cho state/popup — screen cha mở node này
- `kind` enum: `screen` | `popup` | `sheet` | `dialog` | `state`

## Per-node spec sections

### `## Reach`

Cách driver mở node:

```markdown
## Reach

Home → tab "Học" → tap item "Chương 1" → tap "Play preview"
```

Hoặc preset + deep link:

```markdown
## Reach

Preset: user-logged-in-with-books
Deep link: $DEEP_LINK_HOST/book/42?preview=true
```

Preset = fixture setup script khởi tạo app vào state cụ thể.

### `## Door`

Ai vẽ node — SDK/library override vs app-owned:

```markdown
## Door

sdk: learning-path — LearningPathUiConfig.verdict
```

Hoặc:

```markdown
## Door

app — presenter/feature/book-detail/BookDetailScreen.kt
```

ui-judge dùng: nếu Door là SDK override, screenshot vẫn hiện stock look → **chặn**.

### `## Elements`

Element tree theo order visual (top-down, left-right):

```markdown
## Elements

1. app-bar
   1.1. back-button (icon)
   1.2. title "Book Detail" (text, headline-small)
   1.3. share-icon (icon, action nav)
2. content-scroll
   2.1. cover-image (image, large, corner-radius-md)
   2.2. book-title (text, headline-large)
   2.3. book-author (text, body-medium)
   2.4. play-button (primary-button, label "Play preview")
3. ad-banner (visible when adsOffRemoteConfig = false)
```

Driver resolve element theo `node slug.sub-slug` (ví dụ `app-bar.share-icon`).

### `## Tokens`

Design token references (project design system):

```markdown
## Tokens

AppColors.primary — play-button background
AppColors.onPrimary — play-button text
AppTypography.headline-large — book-title
AppTypography.body-medium — book-author
AppSpacing.lg — content padding
AppRadius.md — cover-image corner
```

ui-judge compare screenshot color/typography với token definition.

### `## Copy`

Exact text content theo locale:

```markdown
## Copy

### vi

- app-bar.title: Chi tiết sách
- play-button: Nghe thử

### en

- app-bar.title: Book Detail
- play-button: Play preview
```

ui-judge enforce text exact match (ignore case nếu không có convention).

### `## Assets`

Static assets (icon, illustration):

```markdown
## Assets

- app-bar.share-icon: ic_share_24.xml
- empty-state.illustration: img_empty_books.webp
```

### `## Preset` (optional)

Fixture state preset mà `## Reach` depend:

```markdown
## Preset

user-logged-in-with-books: insert 3 books vào Room DB, auth token hợp lệ
```

### `## Door exceptions` (optional)

Nếu Door là SDK và có override cho element cụ thể:

```markdown
## Door exceptions

- play-button: app override via LearningPathUiConfig.customButton
- ad-banner: SDK vẽ, không override
```

## Rules

- **MUST** mỗi node có file ui-spec riêng
- **MUST** `## Elements` theo order visual, element con nested
- **MUST** `## Copy` exact text (không paraphrase), separate theo locale
- **MUST** `_nodes.json` list đầy đủ, slug unique
- **FORBIDDEN** trộn nhiều node vào 1 file
- **FORBIDDEN** `## Reach` dùng natural language không actionable ("từ anywhere" sai; "Home tab Học item X" đúng)
- **SHOULD** `## Tokens` reference project token name, không exact hex (judge compare semantic)

## Anti-patterns

### AP-001 — Copy image mô tả

```markdown
## Elements

(xem Figma image)
```

→ Không actionable. Phải list element với text.

### AP-002 — Reach non-deterministic

```markdown
## Reach

Mở app, sau một lúc popup sẽ hiện
```

→ Driver không reproduce. Phải exact trigger.

### AP-003 — Copy không có locale

```markdown
## Copy

- play-button: Nghe thử | Play preview
```

→ Mix locale confusing. Phải split section theo locale.

### AP-004 — Tokens exact hex

```markdown
## Tokens

- play-button-bg: #1A73E8
```

→ Fragile. Dùng semantic token name.

### AP-005 — Missing Door

Node không có Door → ui-judge không biết SDK vs app, không grade SDK override được.

### AP-006 — Overlapping variants

`book-detail-content` + `book-detail-loading` + `book-detail-error` share element nhưng mỗi file duplicate full tree.

→ Prefer parent spec + variants override:

```markdown
# book-detail-loading

## Door

Same as book-detail-content

## Elements (override)

- cover-image → skeleton-placeholder
- book-title → skeleton-text
- play-button → disabled, loading-indicator overlay
```

## Reference

- `node-spec.md.template` — per-node template
- `nodes-manifest.json.template` — _nodes.json schema
- `agents/ui-spec-writer.md` (future Wave 2) — authoring role
- `agents/ui-judge.md` — consumer role
- `knowledge/design/visual-compare/figma-vs-screenshot.md` — compare technique

## Future (Wave 2+)

- ui-spec-writer agent sinh ui-spec từ Figma qua framelink-figma MCP
- Preset library: shared presets reusable across fixtures
- Variant inheritance: base spec + overrides diff style
