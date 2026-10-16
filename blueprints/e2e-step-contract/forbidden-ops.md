# Forbidden Operations

Rules reject khi driver parse step file. Enforce ở schema level (`step-file.schema.json`) + runtime level (driver scan trước execute).

## FORBID-001 — `am force-stop $APP_ID`

### Vi phạm

```json
{ "shell": "am force-stop $APP_ID" }
{ "shell": "am force-stop com.company.product" }
```

### Lý do

Real user **không bao giờ** force-stop app của họ. Force-stop sẽ:

- **Giấu bug về persistence**: ViewModel state restore sau process death không được test
- **Giấu bug về state restoration**: `savedInstanceState`, DataStore, Room cache không reload path thực tế
- **Bypass background work**: WorkManager, foreground service bị kill không natural

### Alternative

Để test "returning user" flow (thoát app rồi quay lại):

```json
{ "shell": "input keyevent KEYCODE_HOME" }
{ "wait": { "ms": 2000 } }
{ "launch": true }
```

Không `clearState`, launch intent lại sẽ bring app ra foreground qua natural lifecycle (same như user tap launcher icon).

### Exception

Force-stop **package khác** (không phải app đang test) được phép:

```json
{ "shell": "am force-stop com.android.chrome" }
```

Guard scan regex: `am\s+force-stop\s+\$APP_ID` → reject. `am\s+force-stop\s+<other-package>` → OK.

---

## FORBID-002 — `pm clear ...`

### Vi phạm

```json
{ "shell": "pm clear $APP_ID" }
{ "shell": "pm clear com.company.product" }
```

### Lý do

Raw `pm clear` bypass harness safety:

- Delete file ngoài scope (ví dụ external storage share với app khác)
- Reset permission grants mà test không chủ ý
- Trigger first-run flow mà test không expect

### Alternative

```json
{ "launch": { "clearState": true } }
```

Harness runner thực thi `pm clear` **an toàn** trong context này:
- Only clear data directory của app
- Grant lại permissions đã có trước clear
- Preserve external storage files
- Reset first-run flag chỉ cho test current

### Exception

Không có. Mọi `pm clear` raw bị reject.

---

## FORBID-003 — Hardcode applicationId

### Vi phạm

```json
{ "shell": "am start -n com.apero.learntemplate/.MainActivity" }
{ "shell": "am broadcast -a com.debug.X --receiver com.ailanguageassistant.y/.Receiver" }
{ "hook": { "receiver": "com.company.product/.debug.DebugReceiver" } }
```

### Lý do

Khi app rebrand hoặc build flavor đổi applicationId:

- Step file hardcode thành vô nghĩa
- Test fail silent (component not found error)
- Review ko catch dễ dàng vì không có syntax error

### Alternative

Dùng placeholder `$APP_ID`:

```json
{ "shell": "am start -n $APP_ID/.MainActivity" }
{ "hook": { "action": "com.debug.X", "receiver": "$APP_ID/.debug.DebugReceiver" } }
```

Runner resolve `$APP_ID` từ `product.properties → app.applicationId` lúc chạy.

### Detection

Guard scan regex trong `shell` + `hook.receiver` + any string value:

```regex
(?<!\$APP_ID)\b[a-z]+\.[a-z]+\.[a-z]+\b
```

Match 3-segment package name không prefix `$APP_ID` → reject.

### Exception

Package khác (Chrome, Settings, Launcher) không reject:

```json
{ "shell": "am start -n com.android.chrome/.Main" }
```

Detector allow-list: `com.android.*`, `com.google.*`, `com.sec.android.*` (system packages).

---

## FORBID-004 — Change locale raw

### Vi phạm

```json
{ "shell": "settings put system system_locales en-US" }
```

### Lý do

`settings put` không trigger `onConfigurationChanged` cho running activities. App không re-render với locale mới → test locale không valid.

### Alternative

#### Option A: Broadcast system

```json
{ "shell": "am broadcast -a android.intent.action.LOCALE_CHANGED" }
```

System broadcast → Android framework trigger config change.

#### Option B: Hook debug receiver (khuyên)

```json
{
  "hook": {
    "action": "com.debug.LOCALE",
    "receiver": "$APP_ID/.debug.DebugReceiver",
    "extras": { "locale": "vi" }
  }
}
```

App debug build có receiver xử lý: `AppCompatDelegate.setApplicationLocales(LocaleList(Locale("vi")))`.

#### Option C: Via metadata flag

```json
{
  "metadata": { "require_locale": "vi" },
  "steps": [ ... ]
}
```

Runner tự set locale qua broadcast trước launch.

### Detection

Regex: `settings\s+put\s+(system|secure|global)\s+(system_locales|.*locale.*)`

---

## Additional soft forbids (warnings)

### Fixed sleep

```json
{ "shell": "sleep 5" }
```

→ Warning: prefer `{ "wait": { "node": "...", "timeout": 5000 } }` để adaptive.

### Hardcoded coords

```json
{ "tap": { "coords": [540, 1200] } }
```

→ Warning: brittle với resolution khác. Chỉ dùng khi element không expose semantic (SDK UI closed) + note trong metadata.

### No screenshot

Case 0 screenshot → warning: không có evidence cho ui-judge.

### No assert

Case 0 assertion → warning: không verify behavior, chỉ "chạy không crash".

---

## Enforcement layers

1. **Schema validation**: `step-file.schema.json` reject known patterns (shellAction regex)
2. **Author lint**: `e2e-author` agent self-check trước khi write
3. **Driver pre-execution scan**: guard parse step file, reject before run
4. **Report post-execution**: nếu bypass qua obfuscation, test fail trace rõ "force-stop detected"

4 layers → defense in depth.

## Reference

- `blueprints/e2e-step-contract/step-file.schema.json` — schema enforcement
- `agents/e2e-author.md` — author rules
- `knowledge/e2e-runtime/runner-neutral-step.md` — design rationale
