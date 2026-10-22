# Blueprint: E2E Step Contract

Runner-neutral JSON step file schema cho E2E test execution. Driver (ARTEMIS/Appium/custom) consume cùng format, swap runner mà không rewrite test case.

## Why

- **Portability**: 1 step file chạy được qua nhiều driver (ARTEMIS MCP, Appium, Espresso, Maestro)
- **Enforcement**: schema reject forbidden ops (force-stop, pm clear, hardcode packageId) ở validation level, không rely vào runner catch
- **Composability**: step file = unit atomic; multiple files chain thành journey
- **Replay-safe**: deterministic steps, không hidden state giữa runs

## Khác biệt với test case PO-readable

| | Test case (PO-readable) | Step file (runner-neutral) |
|---|---|---|
| Format | Markdown Given-When-Then | JSON actions array |
| Audience | PO + stakeholder review | Driver execute |
| Content | Business behavior + expected | Precise taps/types/assertions |
| Ownership | test-writer agent | e2e-author agent |
| Count | 1 case = 1 markdown | 1 case = 1 JSON file |

Flow: test-writer produce markdown → e2e-author convert → JSON step file → driver execute.

## Package layout

```text
blueprints/e2e-step-contract/
├── README.md                      # file này
├── step-file.json.template        # schema template
├── step-file.schema.json          # JSON schema validation
├── forbidden-ops.md               # FORBID-001..004 detailed
└── examples/
    ├── simple-tap.json            # 1-screen flow
    ├── journey-multi-screen.json  # chain nhiều screens
    └── with-hook.json             # debug receiver hook
```

## Usage

### Author step file

```bash
# e2e-author agent:
# 1. Load test case markdown
# 2. Load UI spec để resolve node slug → element
# 3. Draft step file JSON
# 4. Validate against step-file.schema.json
# 5. Write briefs/<slug>/actual/e2e/<case-id>.json
```

### Validate

```bash
check-jsonschema \
  --schemafile blueprints/e2e-step-contract/step-file.schema.json \
  briefs/<slug>/actual/e2e/*.json
```

### Execute

```bash
# Downstream driver (not in harness):
# Example ARTEMIS adapter:
node runner/artemis-adapter.js \
  --step-file briefs/<slug>/actual/e2e/TC-001.json \
  --device emulator-5554 \
  --app-id com.company.product
```

Harness không build runner — downstream chọn adapter.

## Schema overview

### Top-level

```json
{
  "case": "TC-001-view-book-detail",
  "description": "User mở Book Detail verify metadata",
  "preconditions": ["App installed", "Debug build"],
  "steps": [ ... ],
  "cleanup": [ ... ],
  "metadata": {
    "ad_aware": true,
    "timeout_seconds": 60,
    "require_remote_config": {}
  }
}
```

### Action types

| Action | Purpose | Example |
|---|---|---|
| `launch` | Start app, optional clearState + deepLink | `{ "launch": { "clearState": true } }` |
| `tap` | Tap element qua node slug hoặc coords | `{ "tap": { "node": "play-button" } }` |
| `long_press` | Long press element | `{ "long_press": { "node": "item-42", "ms": 1000 } }` |
| `type` | Type text, hỗ trợ unicode (dấu tiếng Việt) | `{ "type": { "node": "email", "text": "a@b.vn" } }` |
| `swipe` | Swipe gesture direction + distance | `{ "swipe": { "direction": "up", "distance": 500 } }` |
| `scroll_to` | Scroll until element visible | `{ "scroll_to": { "node": "footer" } }` |
| `wait` | Delay ms hoặc wait node visible | `{ "wait": { "node": "cover-image", "timeout": 5000 } }` |
| `assert` | Verify element state | `{ "assert": { "node": "title", "text": "Book" } }` |
| `screenshot` | Capture screen → `actual/ui/screenshots/<name>.png` | `{ "screenshot": { "name": "book-detail-content" } }` |
| `shell` | Raw adb shell (scanned forbidden ops) | `{ "shell": "input keyevent KEYCODE_HOME" }` |
| `hook` | Broadcast tới debug receiver | `{ "hook": { "action": "...", "receiver": "$APP_ID/.debug" } }` |
| `speak` | TTS vào mic (Windows với VB-Cable) | `{ "speak": { "text": "Hello" } }` |
| `press_key` | Press keycode | `{ "press_key": "BACK" }` |

### Placeholders

- `$APP_ID` — resolve bởi runner từ `product.properties → app.applicationId`
- `$DEEP_LINK_HOST` — deep link host (nếu config)
- `$FIXTURE_PATH` — path tới fixture data file

### Assertion types

```json
{ "assert": { "node": "title", "text": "Book Detail" } }
{ "assert": { "node": "play-button", "exists": true } }
{ "assert": { "node": "error-message", "visible": false } }
{ "assert": { "node": "count", "text_regex": "^\\d+$" } }
{ "assert": { "shell": "dumpsys ...", "contains": "running" } }
```

### Metadata flags

- `ad_aware: true` — runner tự dismiss ads popup
- `timeout_seconds: 60` — overall case timeout
- `require_remote_config: { "key": "value" }` — set Remote Config trước launch (require debug hook)
- `require_locale: "vi"` — set locale qua broadcast
- `audio_input: "cable-virtual"` — route mic cho speak action

## Rules

- **MUST** mỗi case = 1 file độc lập (không chia sẻ state giữa files, trừ khi journey explicit)
- **MUST** validate schema trước khi driver execute
- **MUST** screenshot ≥1 critical state cho ui-judge evidence
- **MUST** assertion ≥1 về data/state, không chỉ UI visible
- **FORBIDDEN** operations xem `forbidden-ops.md`
- **FORBIDDEN** modify step file sau khi driver start (immutable per run)
- **SHOULD** cleanup section press Home để leave app background clean

## Anti-patterns

### AP-001 — Visible-only test

```json
// Sai: chỉ assert UI exists
{ "assert": { "node": "greeting", "visible": true } }

// Đúng: assert cả content
{ "assert": { "node": "greeting", "text": "Hello, user" } }
```

### AP-002 — Fixed sleep thay cho wait

```json
// Sai: brittle, chậm
{ "shell": "sleep 5" }

// Đúng: poll element
{ "wait": { "node": "cover-image", "timeout": 5000 } }
```

### AP-003 — Multi-case trong 1 file

Mỗi case 1 file. Shared setup → `preconditions`, không chain cases.

### AP-004 — Hardcode coords

```json
// Sai: brittle resolution
{ "tap": { "coords": [540, 1200] } }

// Đúng: node slug
{ "tap": { "node": "primary-cta" } }
```

Exception: khi node slug không expose được (SDK UI closed) → coords acceptable với note trong metadata.

### AP-005 — Skip cleanup

Không press Home cuối case → next case start từ nửa chừng → brittle.

## Reference

- `step-file.schema.json` — JSON schema validation
- `forbidden-ops.md` — FORBID-001..004 detailed rules
- `examples/*.json` — reference files
- `agents/e2e-author.md` — authoring role
- `knowledge/testing/e2e-runtime/runner-neutral-step.md` — design rationale
- `knowledge/testing/e2e-runtime/device-driver-contract.md` — driver interface

## Future (Wave 2+)

- Parameterized cases: 1 step file + fixture data table
- Journey schema: chain cases với session persistence rule
- Visual assertion inline: `{ "assert": { "node": "X", "visual_match": "figma/..." } }`
- Multi-locale run: tag case với supported locales
