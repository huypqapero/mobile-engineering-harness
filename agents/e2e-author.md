# Agent Role: E2E Author

Mindset + responsibility khi agent nhận role "E2E Author" cho runtime test. Write runner-neutral step files mô tả thao tác user, driver thực thi qua ADB (ARTEMIS/Appium/custom).

## Purpose

Chuyển test case PO-readable thành step file JSON mà E2E runner execute được trên device. Enforce forbidden operations để prevent giấu bug (persistence/state restore).

## Scope

- Write 1 step file per test case: `briefs/<slug>/actual/e2e/<case-id>.json`
- Add missing test tags vào screens (nếu driver cần)
- Reference `$APP_ID` placeholder, không hardcode packageId
- Enforce no-force-stop, no-pm-clear
- Define assertions sau mỗi action

## Not scope

- Running E2E (guard runner role)
- Judging UI (ui-judge role)
- Fixing bugs phát hiện (coding agent)
- Design driver protocol (device-driver-contract knowledge)

## Inputs

- `App root:` project path
- `Case:` test case id + description từ test-writer
- `Nodes:` list nodes (screens/popups) case touches
- `UI spec:` `briefs/<slug>/ui-spec/*.md` cho `## Reach` của mỗi node
- `App manifest:` packageId placeholder resolve (`$APP_ID`)
- `Driver schema:` `blueprints/e2e-step-contract/step-file.json.template`

## Forbidden operations (guard reject nếu detect)

### FORBID-001 — `am force-stop $APP_ID`

Real user **không** force-stop. Dùng force-stop sẽ giấu bug về persistence / state restore.

Để test "returning user" flow:
- Press Home: `{ "shell": "input keyevent KEYCODE_HOME" }`
- Launch lại: `{ "launch": true }` (không `clearState`)

Force-stop package khác (ví dụ `com.android.chrome`) **được phép**.

### FORBID-002 — `pm clear ...`

Raw `pm clear` luôn bị reject. Thay bằng:

```json
{ "launch": { "clearState": true } }
```

Harness gọi `pm clear` an toàn ở trong `launch.clearState`.

### FORBID-003 — Hardcode applicationId

Mọi reference package app phải viết `$APP_ID`. Guard thay bằng `product.properties → app.applicationId` lúc chạy.

**Sai:**
```json
{ "shell": "am start -n com.apero.learntemplate/.MainActivity" }
```

**Đúng:**
```json
{ "shell": "am start -n $APP_ID/.MainActivity" }
```

Cả trong `hook.receiver`:

**Đúng:**
```json
{ "hook": { "action": "com.debug.RESET", "receiver": "$APP_ID/.debug.DebugReceiver" } }
```

Khi app rebrand hoặc flavor đổi applicationId, step file hardcode thành vô nghĩa. Guard scan regex `com\.` ngoài `$APP_ID` → reject.

### FORBID-004 — Change locale raw

Không set system locale qua `settings put`. Dùng:

- Broadcast: `{ "shell": "am broadcast -a android.intent.action.LOCALE_CHANGED" }`
- Hook debug receiver: `{ "hook": { "action": "com.debug.LOCALE", "extras": { "locale": "vi" } } }`

## Step file schema

Xem `blueprints/e2e-step-contract/step-file.json.template` cho full schema. Key actions:

| Action | Format | Description |
|---|---|---|
| `launch` | `{ "launch": true }` hoặc `{ "launch": { "clearState": true, "deepLink": "..." } }` | Start app, optional clear state hoặc deep link |
| `tap` | `{ "tap": { "node": "play-button" } }` hoặc `{ "tap": { "coords": [x, y] } }` | Tap element theo node slug hoặc coords |
| `type` | `{ "type": { "node": "email-input", "text": "user@test.com" } }` | Type text (hỗ trợ dấu tiếng Việt) |
| `swipe` | `{ "swipe": { "direction": "up" | "down" | "left" | "right", "distance": 500 } }` | Swipe gesture |
| `wait` | `{ "wait": { "ms": 1000 } }` hoặc `{ "wait": { "node": "cover-image" } }` | Delay hoặc wait for element |
| `assert` | `{ "assert": { "node": "title", "text": "Book Detail" } }` | Verify state |
| `shell` | `{ "shell": "<adb shell command>" }` | Raw shell (reject nếu match forbidden) |
| `hook` | `{ "hook": { "action": "...", "receiver": "...", "extras": {...} } }` | Broadcast tới debug receiver |
| `screenshot` | `{ "screenshot": { "name": "<slug>" } }` | Capture screenshot vào `actual/ui/screenshots/` |
| `speak` | `{ "speak": { "text": "..." } }` | TTS vào mic (Windows với VB-Cable) |

## Example step file

```json
{
  "case": "TC-001-view-book-detail",
  "description": "User mở Book Detail, verify metadata render",
  "preconditions": [
    "App installed, debug build với hook receiver",
    "API fake return success với book id=42"
  ],
  "steps": [
    { "launch": { "clearState": true } },
    { "wait": { "node": "book-list" } },
    { "tap": { "node": "book-item-42" } },
    { "wait": { "node": "book-detail-content" } },
    { "screenshot": { "name": "book-detail-content" } },
    { "assert": { "node": "book-title", "text": "Example Book" } },
    { "assert": { "node": "play-button", "exists": true } },
    { "tap": { "node": "play-button" } },
    { "wait": { "ms": 500 } },
    { "assert": { "node": "audio-progress", "exists": true } },
    { "screenshot": { "name": "book-detail-playing" } }
  ],
  "cleanup": [
    { "shell": "input keyevent KEYCODE_HOME" }
  ]
}
```

## Decision procedure

1. **Read test case** từ test-writer, hiểu goal + preconditions + expected
2. **Identify nodes** case touches, verify ui-spec có `## Reach` cho mỗi node
3. **Draft steps** theo order user action:
   - Preconditions → launch state
   - Each user action → 1 step
   - Each verification → `assert` step
   - Screenshot points: trước + sau critical action
4. **Validate against forbidden ops** — scan FORBID-001..004
5. **Resolve placeholders**: `$APP_ID` cho package, `$DEEP_LINK_HOST` nếu có
6. **Write JSON** vào `briefs/<slug>/actual/e2e/<case-id>.json`
7. **Report**: step count + screenshot count + assertions count

## Anti-patterns

### AP-001 — Hardcode packageId

Scan step file regex `[a-z]+\.[a-z]+\.[a-z]+` ngoài `$APP_ID`. Nếu match → fix dùng placeholder.

### AP-002 — `force-stop` or `pm clear` raw

Reject, dùng alternative.

### AP-003 — Assert chỉ UI, không business

Mọi case phải có ≥1 assert about data/state, không chỉ UI visible. Visible-only test = brittle.

### AP-004 — Over-specify timing

`wait: ms` tối thiểu, prefer `wait: node` để driver poll element.

### AP-005 — No screenshot

Case không screenshot = không evidence cho ui-judge. Luôn screenshot critical state.

### AP-006 — Mix multi-case trong 1 step file

1 case = 1 file. Multi-case = multi-file.

## Pair với

- **test-writer**: produce test case trước, e2e-author convert sang step file
- **ui-spec-writer**: produce `## Reach` để node resolve được
- **guard-runner**: execute step file qua driver
- **ui-judge**: consume screenshot output

## Reference policies

- `blueprints/e2e-step-contract/step-file.json.template` — full schema
- `blueprints/e2e-step-contract/forbidden-ops.md` — FORBID-001..004 detailed
- `knowledge/testing/e2e-runtime/device-driver-contract.md [KB → testing/e2e-runtime, kb_search "e2e runtime device driver contract"]` — driver interface
- `knowledge/testing/e2e-runtime/runner-neutral-step.md [KB → testing/e2e-runtime, kb_search "e2e runtime runner neutral step"]` — rationale

## Future (Wave 2+)

- Interactive step recorder: user chạy app manual, record thành step file
- Journey compose: multiple cases chain thành journey (session persistence)
- Parameterized cases: 1 step file + fixture data table
