# Runner-Neutral Step Design Rationale

Design document cho runner-neutral JSON step file schema. Giải thích **tại sao** step file có shape như vậy, trade-off decisions, so sánh với alternative approaches.

## Vấn đề cần giải quyết

Khi viết E2E test cho Android:

1. **Test case format fragmented**: Espresso (Kotlin), Appium (JSON/YAML config), UIAutomator (Java), Maestro (YAML DSL), Detox (JS) — mỗi runner có syntax riêng
2. **Vendor lock-in**: viết Espresso → không chạy được qua Maestro, phải rewrite
3. **Review khó**: PO không đọc được Kotlin test code, không review scope test được
4. **AI-friendly**: LLM generate test cần format consistent + schema-validatable

Runner-neutral step file giải quyết bằng cách tách:

- **Test intent** (steps JSON schema) — portable, LLM-friendly, PO-readable (nếu add description)
- **Runner implementation** (device driver adapter) — mỗi runner implement cùng contract

## Design principles

### 1. Declarative, không imperative

Step file **mô tả** action, không code logic:

**Imperative (Espresso):**
```kotlin
onView(withId(R.id.play_button)).perform(click())
onView(withId(R.id.audio_progress)).check(matches(isDisplayed()))
```

**Declarative (step file):**
```json
{ "tap": { "node": "play-button" } },
{ "assert": { "node": "audio-progress", "exists": true } }
```

Lý do: LLM write JSON tốt hơn code. Reviewer đọc nhanh hơn.

### 2. Node slug thay cho view id

**View id approach (Espresso):**
```kotlin
onView(withId(R.id.play_button))
```
→ Tie-in resource ID, break khi refactor.

**Node slug (step file):**
```json
{ "tap": { "node": "play-button" } }
```
→ Semantic name, driver resolve qua test-tag (Compose), content-description (Views), hoặc accessibility label (SwiftUI nếu port iOS).

Mỗi platform có cách map:
- Compose: `Modifier.testTag("play-button")`
- Views: `android:contentDescription="play-button"` hoặc `android:tag="play-button"`
- Fallback: ARIA role + accessibility label

### 3. JSON over YAML

Trade-off:

| | JSON | YAML |
|---|---|---|
| Readability | Verbose brackets | Clean indent |
| Schema validation | JSON Schema standard | JSON Schema qua convert |
| LLM output quality | Better (training data) | Worse |
| Tool support | Universal | Fragmented |

Chọn JSON cho:
- JSON Schema Draft 2020-12 native validation
- LLM write JSON stable hơn YAML (ít indent error)
- CI tools (jq, jsonschema) universal

Trade-off accept: verbose hơn.

### 4. Placeholder resolution at runtime

**Hardcode packageId:**
```json
{ "shell": "am start -n com.company.product/.MainActivity" }
```
→ Break khi rebrand hoặc flavor khác.

**Placeholder:**
```json
{ "shell": "am start -n $APP_ID/.MainActivity" }
```
→ Resolver thay bằng `product.properties → app.applicationId`.

Supported placeholders:
- `$APP_ID` — applicationId
- `$DEEP_LINK_HOST` — deep link base URL
- `$FIXTURE_PATH` — path tới fixture data file
- `$DEVICE_SERIAL` — adb device serial

Future: `${VAR_NAME}` syntax cho user-defined.

### 5. Forbidden operations enforced at schema level

Thay vì rely vào runtime catch forbidden ops, enforce ở JSON Schema:

```json
"shellAction": {
  "type": "string",
  "pattern": "^(?!.*\\bam\\s+force-stop\\s+\\$APP_ID)(?!.*\\bpm\\s+clear\\b).*"
}
```

Regex reject match patterns. Validator (`check-jsonschema`) catch trước khi driver execute.

Multi-layer defense:
1. Schema validation (CI pre-check)
2. Author lint (`e2e-author` agent self-check)
3. Driver pre-execution scan
4. Report trace post-execution

### 6. Metadata flags for driver behavior

Separate test logic (`steps`) từ driver config (`metadata`):

```json
{
  "metadata": {
    "ad_aware": true,
    "require_locale": "vi",
    "require_remote_config": { "feature_x": true }
  },
  "steps": [ ... ]
}
```

Steps không pollute với "set locale", "disable ad". Driver read metadata trước run, setup accordingly.

### 7. Preconditions as prose, not code

```json
{
  "preconditions": [
    "App installed with debug build + hook receiver",
    "API fake return success for /books endpoint"
  ]
}
```

→ Human-readable requirement. Runner không execute preconditions (lo của test setup script).

Alternative rejected: `"setup_steps": [...]` — khiến step file chứa 2 kind of logic (setup vs test), blurry.

## So sánh với alternatives

### vs Maestro (YAML DSL)

Maestro:
```yaml
appId: com.company.product
---
- launchApp
- tapOn: "Play"
- assertVisible: "Progress"
```

Trade-off:
- ✅ Maestro cleaner syntax
- ❌ Maestro locked-in Maestro runtime
- ❌ Maestro không support hook/broadcast cho debug receiver
- ❌ Maestro không có forbidden ops enforcement

Runner-neutral step file win: portable + enforce rules + driver-agnostic.

### vs Appium (JSON config)

Appium capabilities + session commands:

```json
{
  "capabilities": { "appium:platformName": "Android", ... },
  "commands": [
    { "method": "POST", "endpoint": "/session/.../element", "data": {...} }
  ]
}
```

Trade-off:
- ❌ Appium WebDriver JSON wire protocol — verbose, low-level
- ❌ Appium capabilities = driver-specific config
- ✅ Appium ecosystem lớn

Runner-neutral win: high-level, semantic.

### vs Espresso (Kotlin DSL)

Trade-off:
- ✅ Espresso fast execution (in-process)
- ❌ Espresso Kotlin code — LLM write kém, PO không review
- ❌ Espresso Android-only
- ❌ Espresso không có schema validation

Runner-neutral win: LLM-friendly + reviewable + schema-valid.

### vs Detox (JS)

Trade-off:
- ✅ Detox cross-platform (iOS + Android)
- ❌ Detox JS code — nested async, hard review
- ❌ Detox vendor lock (jest + testing lib)

Runner-neutral win: declarative, không async pyramid.

## When NOT to use runner-neutral step file

**Low-level perf test:**
```kotlin
// Measure specific function call
measureNanoTime { repository.fetchBook(42) }
```

→ Use JVM test / Instrumented test / microbenchmark lib. Step file high-level, không measure nanosecond.

**Flaky visual regression:**

Screenshot pixel-perfect compare qua step file có thể false-positive. Use dedicated tool (Paparazzi, Shot) cho visual test.

**Unit test:**

Step file for E2E user flow. Unit test logic → JUnit / Spek / Kotest.

## Mapping step actions to runner primitives

| Step action | Espresso | Appium | Maestro | ARTEMIS MCP |
|---|---|---|---|---|
| `launch` | `ActivityScenario.launch` | `startActivity` | `launchApp` | `mobile_launch_app` |
| `tap node` | `onView(withTag).perform(click())` | `elementByXPath.click()` | `tapOn` | `mobile_tap` |
| `type` | `onView.perform(typeText)` | `element.sendKeys` | `inputText` | `mobile_type` |
| `assert node text` | `onView.check(matches(withText))` | `element.getText == x` | `assertVisible` | `mobile_find_element` + check |
| `screenshot` | `UiDevice.takeScreenshot` | `driver.getScreenshot` | `takeScreenshot` | `mobile_take_screenshot` |
| `shell` | `UiDevice.executeShellCommand` | `driver.executeScript` | custom | `mobile_shell` |
| `hook broadcast` | `instrumentation.context.sendBroadcast` | custom | custom | `mobile_shell` am broadcast |

Mỗi runner có path. Adapter map step → native call.

## Schema evolution strategy

### v1 (current)

- Basic actions (launch, tap, type, swipe, wait, assert, screenshot, shell, hook, speak, press_key)
- Placeholders ($APP_ID, $DEEP_LINK_HOST)
- Forbidden ops regex
- Metadata flags

### v2 (future, Wave 2+)

- Parameterized cases: step file + fixture data CSV/JSON
- Journey composition: chain cases với state persistence rule
- Conditional steps: `if element exists then ... else ...`
- Loop: `repeat N times` for stress test

### Backward compat

Schema `$id` versioned (`v1.json`, `v2.json`). Driver support multiple versions:

```typescript
driver.supportedSchemaVersions = ['v1', 'v2'];
```

## Rules of thumb

- **MUST** step file < 50 steps (bigger = split into journey)
- **MUST** screenshot ≥ 1 critical state
- **MUST** assertion ≥ 1 about data/state (không chỉ UI visible)
- **MUST** cleanup section press Home
- **SHOULD** preconditions prose cho human review
- **SHOULD** metadata explicit (ad_aware, locale, timeout)
- **FORBIDDEN** hardcode coords (dùng node slug)
- **FORBIDDEN** fixed sleep (dùng wait node)
- **FORBIDDEN** hardcode packageId (dùng $APP_ID)
- **FORBIDDEN** force-stop / pm clear raw

## Reference

- `blueprints/e2e-step-contract/step-file.schema.json` — formal schema
- `blueprints/e2e-step-contract/forbidden-ops.md` — detailed rules
- `knowledge/testing/e2e-runtime/device-driver-contract.md` — adapter interface
- Maestro docs — similar philosophy comparison
- Appium docs — JSON wire protocol comparison

## Note về generic vs product-specific

Schema generic. learn-app-plugin có `lib/e2e-*.cjs` + `bin/e2e-worker.cjs` wrap step file into custom runner với built-in APK driver. Harness document pattern, downstream build runner.
