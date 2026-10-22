# Custom APK Driver

Pattern cho custom APK driver — hiệu suất cao (~30-100ms/call) cho E2E test volume lớn hoặc yêu cầu Unicode input chuẩn. Thay thế ARTEMIS MCP (~1-2s/call) khi volume vượt 200+ cases per round.

**Harness không ship binary APK.** Doc này mô tả architecture + protocol spec để downstream product build APK driver riêng, hoặc tham khảo implementation có sẵn (xem phần 10).

## Khi nào cần custom APK driver

Decision matrix:

| Context | Khuyên driver |
|---|---|
| Volume < 50 cases/round | ARTEMIS MCP, không cần APK |
| Volume 50-200 cases/round | ARTEMIS hoặc Maestro, APK optional |
| **Volume 200+ cases/round** | **APK driver bắt buộc** (latency scale) |
| Yêu cầu Unicode input chuẩn (tiếng Việt dấu) | APK driver (clipboard IME) hoặc Maestro |
| SDK closed UI, không có test-tag | APK + vision fallback hybrid |
| CI chạy > 10 round/ngày | APK để giảm total time |

**Threshold concrete**: ARTEMIS ~1.5s × 30 steps × 200 cases = **~2.5 giờ/round**. APK ~30ms × 30 × 200 = **~3 phút/round**. Scale 50x.

## Architecture overview

```
┌──────────────────────────────────────────────────────────┐
│  Host machine (test runner)                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Runner (bash/Python/Node)                         │  │
│  │  - Read step file JSON                             │  │
│  │  - Call driver qua HTTP                            │  │
│  │  - Parse response                                  │  │
│  │  - Capture screenshots + logs                      │  │
│  └────────────────┬───────────────────────────────────┘  │
│                   │ HTTP GET 127.0.0.1:7912               │
│                   │                                        │
│                   │ (adb forward tcp:7912 tcp:7912)        │
└───────────────────┼───────────────────────────────────────┘
                    │
┌───────────────────┼───────────────────────────────────────┐
│  Android device/emulator                                  │
│                   │                                        │
│  ┌────────────────▼───────────────────────────────────┐  │
│  │  Driver APK (instrumentation process)              │  │
│  │  - ServerSocket on 127.0.0.1:7912                  │  │
│  │  - Persistent UiAutomation connection              │  │
│  │  - Endpoints: /ping /tree /shot /tap /settext ... │  │
│  │  - Element locator + ad guard                      │  │
│  └────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

Key difference vs `uiautomator dump`:
- `uiautomator dump` spawn new process mỗi call → 1-3s overhead
- APK driver = **1 instrumentation process** giữ UiAutomation handle suốt run → 30-100ms/call

## Protocol spec

### Transport

- **ADB forward**: `adb forward tcp:<host_port> tcp:7912`
- **HTTP over TCP** trên device port 7912
- **Localhost only**: driver bind `127.0.0.1`, không expose network
- **No auth**: scope test-only, ADB access = trust boundary

### Endpoints

HTTP GET với query string params. Response = JSON.

#### `GET /ping`

Health check.

```json
{ "ok": true, "version": 3 }
```

Driver maintainer bump `version` khi protocol thay đổi.

#### `GET /config?cls=&id=&label=`

Set ad detection regex rules (optional, product-specific).

Response:
```json
{ "ok": true }
```

Harness generic APK driver có thể skip endpoint này nếu không enforce ad detection.

#### `GET /tree`

Dump accessibility tree của all windows, top-most first.

Response (array):
```json
[
  {
    "text": "Book Detail",
    "desc": "Book Detail Screen",
    "id": "com.app:id/title",
    "pkg": "com.app",
    "cls": "android.widget.TextView",
    "clickable": false,
    "parent": -1,
    "window": 0,
    "layer": 0,
    "ad": false,
    "bounds": [0, 100, 1080, 200]
  },
  ...
]
```

Fields:
- `text`: visible text
- `desc`: content-description
- `id`: resource id
- `pkg`: owning package
- `cls`: View/Composable class
- `clickable`: element có click handler
- `parent`: index of parent node trong array (-1 if root)
- `window`: window index (0 = top-most)
- `layer`: Z-order
- `ad`: true nếu match ad detection rules
- `bounds`: `[left, top, right, bottom]` absolute pixel

Runner parse tree → match element by text/desc/id/cls regex → compute center coords.

#### `GET /shot`

Capture screenshot PNG. Response = raw PNG bytes (binary).

Content-Type: `image/png`

#### `GET /tap?x=<X>&y=<Y>[&guard=1&id=&text=]`

Inject tap event tại `(X, Y)`.

Guard mode (`guard=1`):
- Driver kiểm tra element tại `(X, Y)` trước khi tap
- Nếu element đã move khỏi vị trí → `{ "ok": false, "blocked": "changed" }`
- Nếu element là ad (match rules từ `/config`) → `{ "ok": false, "blocked": "ad" }`

Response:
```json
{ "ok": true, "elapsed_ms": 45 }
```

Hoặc:
```json
{ "ok": false, "blocked": "ad" }
```

#### `GET /settext?text=<URL_ENCODED_TEXT>`

Set text của focused editable field. Hỗ trợ **mọi charset** (Unicode, dấu tiếng Việt, emoji) qua AccessibilityNodeInfo setText action — khác với `adb shell input text` chỉ hỗ trợ ASCII tốt.

Response:
```json
{ "ok": true }
```

### Protocol extensions (recommended cho harness)

Harness generic APK driver nên add thêm:

#### `GET /swipe?x1=&y1=&x2=&y2=&duration_ms=`

Inject swipe gesture.

#### `GET /long_press?x=&y=&duration_ms=`

Long press.

#### `GET /launch?pkg=&activity=&clear_state=`

Launch app, optional `pm clear` safe inside driver context.

#### `GET /shell?cmd=<URL_ENCODED>`

Execute shell command on device. Scan forbidden ops regex trước execute.

#### `GET /broadcast?action=&receiver=&extras=<JSON>`

Send broadcast intent (cho debug hook).

## UiAutomation API cheat sheet

Key methods driver sử dụng:

```java
UiAutomation automation = getUiAutomation(UiAutomation.FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES);

// 1. Get all windows (top-most first)
List<AccessibilityWindowInfo> windows = automation.getWindows();

// 2. Walk accessibility tree
AccessibilityNodeInfo root = window.getRoot();
walkTree(root, nodes);  // recursive, serialize to JSON

// 3. Perform click via accessibility action
nodeInfo.performAction(AccessibilityNodeInfo.ACTION_CLICK);

// 4. Inject tap event (raw motion event)
MotionEvent down = MotionEvent.obtain(
    time, time, MotionEvent.ACTION_DOWN,
    x, y, 0
);
automation.injectInputEvent(down, true);
MotionEvent up = MotionEvent.obtain(
    time, time + 50, MotionEvent.ACTION_UP,
    x, y, 0
);
automation.injectInputEvent(up, true);

// 5. Set text via accessibility action (supports unicode)
Bundle args = new Bundle();
args.putCharSequence(
    AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
    text  // "Nguyễn Văn A" works
);
focusedNode.performAction(
    AccessibilityNodeInfo.ACTION_SET_TEXT,
    args
);

// 6. Take screenshot
Bitmap screenshot = automation.takeScreenshot();
```

### AccessibilityServiceInfo flags cần thiết

```java
info.flags |= AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS;
info.flags |= AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS;
info.flags |= AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS;
```

Giúp get đủ nodes + ids resource.

### Pitfalls

- **UiAutomation chết với DeadObjectException** nếu `am instrument` process bị kill. Phải giữ instrumentation process alive suốt run.
- **Node stale**: tree thay đổi liên tục, cache tree quá lâu → tap wrong element. Refresh tree trước mỗi action.
- **Multiple windows**: popup/sheet là window riêng, walk all windows không chỉ top window.
- **System dialogs**: window package = `com.android.systemui`, không phải app → skip khi scan nodes.

## Project structure

Scaffold Android library module:

```
device-driver/
├── build.gradle.kts
├── AndroidManifest.xml
└── src/
    └── main/
        └── java/
            └── com/<org>/driver/
                ├── DriverInstrumentation.java    # entry point
                ├── TreeSerializer.java           # walk + serialize accessibility tree
                ├── ElementLocator.java           # match query → node
                ├── GestureInjector.java          # tap/swipe via injectInputEvent
                ├── UnicodeInput.java             # setText via accessibility action
                ├── ScreenshotCapture.java        # takeScreenshot + PNG encode
                └── HttpServer.java               # ServerSocket + request dispatch
```

### AndroidManifest.xml essentials

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.<org>.driver"
    android:versionCode="1">

    <uses-permission android:name="android.permission.INTERNET" />
    <!-- Localhost only, INTERNET để ServerSocket bind -->

    <application
        android:label="Harness Device Driver"
        android:allowBackup="false" />

    <instrumentation
        android:name=".DriverInstrumentation"
        android:targetPackage="com.<org>.driver"
        android:label="harness device driver" />
</manifest>
```

**Note:** `targetPackage` = chính driver, không phải app under test. UiAutomation hoạt động cross-app qua accessibility, không cần instrument app.

### build.gradle.kts

```kotlin
plugins {
    id("com.android.application")
}

android {
    namespace = "com.<org>.driver"
    compileSdk = 34
    defaultConfig {
        minSdk = 21
        targetSdk = 34
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    buildTypes {
        debug {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

dependencies {
    // Tối thiểu, driver dùng Android framework APIs trực tiếp
}
```

### Launch command

```bash
# 1. Install APK
adb install -r device-driver-debug.apk

# 2. Grant permissions (nếu cần)
# INTERNET auto-granted

# 3. Start instrumentation (background, giữ alive)
adb shell am instrument -w -e port 7912 \
    com.<org>.driver/.DriverInstrumentation &

# 4. Forward port
adb forward tcp:7912 tcp:7912

# 5. Verify
curl http://127.0.0.1:7912/ping
# → {"ok":true,"version":1}
```

Keep `am instrument` process alive suốt test run. Kill (Ctrl-C) khi xong.

## Unicode input strategy

### Vì sao `adb shell input text` không đủ

```bash
adb shell input text "Nguyễn"
# → "Nguyn" (mất dấu) hoặc crash
```

`input` command chuyển text thành KeyEvents, dính limitations:
- Chỉ ASCII tốt
- Dấu tiếng Việt bị drop
- Emoji không support

### Clipboard-based (option 1)

```java
ClipboardManager cm = (ClipboardManager) context.getSystemService(Context.CLIPBOARD_SERVICE);
cm.setPrimaryClip(ClipData.newPlainText("", text));

// Trigger paste
focusedNode.performAction(AccessibilityNodeInfo.ACTION_PASTE);
```

Pros: hoạt động mọi app.
Cons: clobbers user clipboard, có thể trigger clipboard events trong app.

### Accessibility setText (option 2, khuyên)

```java
Bundle args = new Bundle();
args.putCharSequence(
    AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
    text
);
focusedNode.performAction(
    AccessibilityNodeInfo.ACTION_SET_TEXT,
    args
);
```

Pros: direct, không clobber clipboard.
Cons: app phải expose text field qua accessibility (hầu hết Jetpack Compose + View đã expose).

Khuyên: option 2 default, fallback option 1 nếu setText action fail.

## Element locator strategies

### Priority order khi match element từ step file

1. **Resource ID exact match** (`android:id="@+id/play_button"` → `"com.app:id/play_button"`)
2. **Test-tag match** (Compose `Modifier.testTag("play-button")` → content-description nếu auto-exposed, hoặc Compose semantic)
3. **Content-description exact match** (`contentDescription = "play-button"`)
4. **Content-description regex** (fuzzy match)
5. **Text exact match** (visible label)
6. **Text regex** (fuzzy)
7. **Class + bounds** (fallback cho ambiguous)

Element locator cache tree per `/tree` call, không re-fetch mỗi query.

### Jetpack Compose considerations

Compose nodes expose qua accessibility nhưng:
- `Modifier.testTag("X")` không auto-set content-description
- Cần `Modifier.semantics { testTag = "X"; contentDescription = "X" }` để driver tìm được

Downstream product phải consistent test-tag convention.

## Ad detection built-in (optional)

Learn-app-plugin APK có `/config` endpoint set regex rules:

```json
{
  "cls": "com\\.(google\\.android\\.gms\\.ads|applovin|unity3d)\\..*",
  "id": ".*AdView.*",
  "label": "(Sponsored|Quảng cáo)"
}
```

Node khớp rule → `ad: true` trong `/tree` output. Guarded tap từ chối tap vào ad.

Harness generic APK driver có thể:
- Skip ad detection (simpler, interrupt handler lo)
- Hoặc expose `/config` endpoint cho downstream product set rules

Khuyên: skip default. Interrupt handler ở runner xử lý ad dismiss qua pattern (xem `knowledge/testing/e2e-runtime/interruption-patterns.md`).

## Build + sign + install workflow

### Build locally

```bash
# Trong Android Studio project của driver
./gradlew assembleDebug

# Output: app/build/outputs/apk/debug/device-driver-debug.apk
```

### Sign

Debug signing OK cho test (Android auto-sign với debug key).

Production/CI dùng custom debug keystore cố định để APK ID stable qua reinstall:

```kotlin
android {
    signingConfigs {
        create("debug-stable") {
            storeFile = file("debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }
    buildTypes {
        debug {
            signingConfig = signingConfigs.getByName("debug-stable")
        }
    }
}
```

### Install trên device

```bash
# Uninstall cũ nếu có
adb uninstall com.<org>.driver 2>/dev/null || true

# Install mới
adb install -r device-driver-debug.apk
```

### CI integration

GitHub Actions / Jenkins pipeline:

```yaml
- name: Build driver APK
  run: cd driver && ./gradlew assembleDebug

- name: Install driver trên emulator
  run: adb install -r driver/app/build/outputs/apk/debug/driver-debug.apk

- name: Start driver instrumentation
  run: |
    adb shell am instrument -w -e port 7912 \
      com.<org>.driver/.DriverInstrumentation &
    sleep 2
    adb forward tcp:7912 tcp:7912
    curl -f http://127.0.0.1:7912/ping

- name: Run E2E tests
  run: ./harness/verification/e2e/scripts/run-e2e.sh --all
```

## Testing driver reliability

### Self-test suite

Driver repo có `tests/` cho:

- Ping response time < 100ms
- Tree dump 1000+ nodes < 300ms
- Tap latency p95 < 100ms
- Unicode setText preserve 50 chars
- Guarded tap reject ad correctly
- Reconnection sau emulator restart

Chạy self-test mỗi lần build APK.

### Metrics expose

Thêm endpoint `/metrics`:

```json
{
  "uptime_seconds": 3600,
  "requests_total": 15230,
  "p50_latency_ms": 28,
  "p95_latency_ms": 85,
  "p99_latency_ms": 150,
  "errors_total": 3
}
```

Runner collect vào report cho capacity planning.

## 3 acquisition options cho downstream

### Option A — Build riêng từ scratch (recommended)

Scaffold project theo architecture + protocol spec trong doc này. ~2-3 tuần dev time.

**Pros:**
- Full control
- Generic naming (`harness-device-driver` thay vì `learnapp-device-driver`)
- Fit cross-product usage
- No legal/license concern

**Cons:**
- Time investment lớn
- Need Android engineer skill

### Option B — Fork từ learn-app-plugin

Nếu team có access `hung-apero/learn-app-plugin` repo:

```bash
# Copy tools/device-driver/ sang product repo
cp -r learn-app-plugin/tools/device-driver/ my-product/tools/driver/

# Rename package com.apero.learnapp.driver → com.<org>.driver
# Rebuild + sign + test
```

**Pros:**
- Nhanh nhất (vài giờ)
- Battle-tested implementation
- Có ad detection built-in

**Cons:**
- Brand `learnapp` trong package name
- Legal: learn-app-plugin private repo, cần agreement
- Maintenance tie-in với learn-app updates
- Ad detection product-specific, phải adjust

### Option C — Vendor binary APK

Nếu chỉ cần APK binary (không touch source):

```bash
# Copy pre-built APK từ learn-app-plugin
cp learn-app-plugin/tools/device-driver/learnapp-device-driver.apk \
   my-product/tools/

# Install qua ADB như bình thường
adb install -r tools/learnapp-device-driver.apk
```

**Pros:**
- Zero dev time
- Immediate availability

**Cons:**
- Không customize được
- Package name `com.apero.learnapp.driver` fixed
- Phụ thuộc learn-app-plugin updates
- Legal/distribution concern với private binary

**Khuyên:** Option A cho long-term, Option B khi cần nhanh + có access, Option C chỉ cho PoC/temporary.

## Integration với driver contract

Map APK driver endpoints → 10 methods của `device-driver-contract.md`:

| Contract method | APK endpoint |
|---|---|
| `fetchHierarchy()` | `GET /tree` → parse array |
| `tap({ node })` | `GET /tree` → match → `GET /tap?x=&y=&guard=1&id=&text=` |
| `tap({ coords })` | `GET /tap?x=&y=` |
| `long_press` | `GET /long_press?x=&y=&duration_ms=` (extension) |
| `type` | focus field → `GET /settext?text=<url_encoded>` |
| `swipe` | `GET /swipe?x1=&y1=&x2=&y2=&duration_ms=` (extension) |
| `wait` | poll `GET /tree` với timeout |
| `assert` | `GET /tree` → match → compare text/exists/visible |
| `screenshot` | `GET /shot` → save PNG |
| `shell` | `GET /shell?cmd=` (extension, scan forbidden ops) |
| `launch` | `GET /launch?pkg=&activity=&clear_state=` (extension) |
| `hook` | `GET /broadcast?action=&receiver=&extras=` (extension) |

Runner adapter wrap endpoints này thành driver contract calls.

## Rules

- **MUST** 1 instrumentation process giữ UiAutomation suốt run (persistent connection)
- **MUST** HTTP server bind `127.0.0.1` only (không expose network)
- **MUST** URL encode text parameters đầy đủ
- **MUST** refresh tree trước mỗi tap (tránh stale node)
- **MUST** scan forbidden ops ở `/shell` endpoint
- **SHOULD** version endpoint response để runner detect protocol mismatch
- **SHOULD** metrics endpoint cho capacity planning
- **FORBIDDEN** expose driver endpoint ra network (localhost only)
- **FORBIDDEN** ship APK có hardcoded credentials
- **FORBIDDEN** auto-run driver trong production app build (test-only)

## Anti-patterns

### AP-001 — Spawn new UiAutomation per request

Mỗi call tạo mới UiAutomation → mất lợi thế persistent connection (lại 1-3s/call).

### AP-002 — Expose driver ra network

Bind `0.0.0.0` thay vì `127.0.0.1` → security risk, phá sandbox.

### AP-003 — Cache tree quá lâu

Cache 1s thay vì refresh mỗi action → stale node → tap sai element → bug.

### AP-004 — Skip URL encoding

Text có `&`, `=`, space không encode → protocol parse fail.

### AP-005 — Hardcode package của app under test

Driver cần work cross-app. Protocol receive `pkg` parameter, không hardcode.

### AP-006 — No version endpoint

Runner upgrade protocol không detect driver cũ → silent fail.

### AP-007 — Driver auto-restart app under test

Driver chỉ control UI, không manage app lifecycle. Launch là responsibility của runner (`/launch` qua shell `am start`).

## Reference

- `knowledge/testing/e2e-runtime/device-driver-contract.md` — 10 methods abstract contract
- `knowledge/testing/e2e-runtime/guard-round-pattern.md` — round orchestration
- `knowledge/testing/e2e-runtime/runner-neutral-step.md` — step file schema
- Learn-app-plugin reference implementation: `hung-apero/learn-app-plugin/tools/device-driver/` (private repo, cần access)
- UiAutomation docs: Android Developer `android.app.UiAutomation`
- AccessibilityNodeInfo docs: Android Developer `android.view.accessibility.AccessibilityNodeInfo`

## Future (Wave 3+)

- **Compose semantics direct**: thay vì accessibility tree, hook vào Compose semantics tree native cho faster + more accurate
- **Multi-device coordination**: 1 driver instance control 2 devices (chat test)
- **Video stream**: driver stream frames real-time cho replay debugging
- **Network stub**: driver mitm HTTP qua local proxy
- **Stress test**: driver inject thermal/battery state cho perf test
