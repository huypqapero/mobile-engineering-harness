# Device Driver Contract

Abstract interface mà E2E runner implement để execute step file. Harness không ship driver — downstream chọn adapter (ARTEMIS MCP, Appium, Maestro, custom APK driver). Contract này define method set + response shape.

## Mục đích

Decouple step file schema khỏi driver implementation. Cùng 1 step file chạy được qua nhiều driver nếu adapter implement contract. Swap driver không rewrite test case.

## Interface

Driver implement 10 method chính:

### 1. `fetchHierarchy(): UIHierarchy`

Return UI tree hiện tại:

```typescript
interface UIHierarchy {
  timestamp: string;             // ISO 8601
  nodes: UINode[];
}

interface UINode {
  slug?: string;                 // test-tag nếu có, null nếu chưa gắn
  type: string;                  // Compose/View class name
  text?: string;
  content_description?: string;
  bounds: [number, number, number, number];  // [x, y, width, height]
  visible: boolean;
  enabled: boolean;
  children: UINode[];
}
```

Target latency: ~30ms với persistent connection (như learn-app-plugin UiAutomation). Fallback `uiautomator dump` ~1-3s acceptable.

### 2. `tap(target: TapTarget): TapResult`

```typescript
type TapTarget =
  | { node: string }               // slug lookup
  | { coords: [number, number] };

interface TapResult {
  ok: boolean;
  node_found?: boolean;            // nếu target node, có tìm thấy không
  tap_coords: [number, number];    // actual coords đã tap
  duration_ms: number;
}
```

### 3. `type(target: TypeTarget): TypeResult`

```typescript
interface TypeTarget {
  node: string;
  text: string;                    // hỗ trợ unicode (dấu tiếng Việt)
  clear_first?: boolean;
}
```

Driver phải handle input method (IME) để type text có dấu, không phải chỉ ASCII.

### 4. `swipe(gesture: SwipeGesture): SwipeResult`

```typescript
interface SwipeGesture {
  direction: 'up' | 'down' | 'left' | 'right';
  distance?: number;               // dp, default half screen
  duration_ms?: number;            // default 300
  from_node?: string;              // start from node bounds nếu có
}
```

### 5. `wait(condition: WaitCondition): WaitResult`

```typescript
type WaitCondition =
  | { ms: number }
  | { node: string; timeout?: number };

interface WaitResult {
  ok: boolean;
  elapsed_ms: number;
  node_visible?: boolean;
}
```

Node wait: driver poll hierarchy (interval ~500ms) đến khi element visible hoặc timeout.

### 6. `assert(check: Assertion): AssertResult`

```typescript
interface Assertion {
  node?: string;
  text?: string;
  text_regex?: string;
  exists?: boolean;
  visible?: boolean;
  shell?: string;
  contains?: string;
}

interface AssertResult {
  ok: boolean;
  actual?: string;                 // actual value nếu fail
  message?: string;                // human-readable fail reason
}
```

### 7. `screenshot(name: string, crop?: Rect): ScreenshotResult`

```typescript
interface ScreenshotResult {
  ok: boolean;
  path: string;                    // relative to briefs/<slug>/actual/ui/screenshots/
  width: number;
  height: number;
  size_bytes: number;
}
```

### 8. `shell(cmd: string): ShellResult`

Raw adb shell. Driver scan forbidden ops (xem `blueprints/e2e-step-contract/forbidden-ops.md`) trước execute.

```typescript
interface ShellResult {
  ok: boolean;
  stdout: string;
  stderr: string;
  exit_code: number;
}
```

### 9. `launch(options?: LaunchOptions): LaunchResult`

```typescript
interface LaunchOptions {
  clearState?: boolean;            // safe pm clear trong harness context
  deepLink?: string;
  activity?: string;               // default launcher activity
}

interface LaunchResult {
  ok: boolean;
  app_id: string;                  // resolved $APP_ID
  process_pid: number;
  cold_start_ms: number;
}
```

### 10. `hook(broadcast: Broadcast): HookResult`

```typescript
interface Broadcast {
  action: string;
  receiver: string;                // $APP_ID/.debug.DebugReceiver
  extras?: Record<string, any>;
}
```

Driver resolve `$APP_ID` placeholder trước send broadcast.

## Lifecycle

```
driver.connect(device_serial)
  ↓
  (for each step in step_file.steps)
  driver.<action>(params)
  ↓
driver.disconnect()
```

### Connect

```typescript
interface ConnectOptions {
  device_serial: string;           // adb -s <serial>
  app_id: string;                  // resolve $APP_ID
  timeout_seconds?: number;
}
```

### Disconnect

Driver cleanup: kill UiAutomation session, không touch app state (test cleanup section lo).

## Error handling

### Driver-level errors

```typescript
interface DriverError {
  type: 'device_disconnected' | 'app_crashed' | 'timeout' | 'forbidden_op' | 'other';
  message: string;
  recoverable: boolean;
  action: 'retry' | 'skip' | 'abort';
}
```

Driver report structured error, runner decide retry/skip/abort theo policy.

### Common recovery

- `device_disconnected`: reconnect adb, retry current step
- `app_crashed`: capture logcat, screenshot, mark case failed
- `timeout`: screenshot current state, mark step failed
- `forbidden_op`: abort case, report violation

## Implementation paths

5 paths implement driver contract, trade-off giữa latency, setup cost, maintenance:

| Path | Latency/call | Setup | Unicode | Use case |
|---|---|---|---|---|
| ARTEMIS MCP | ~1-2s | Zero (có sẵn env) | ✅ | Default, < 50 cases |
| Maestro CLI | ~200-500ms | Install Maestro | ✅ | 50-200 cases |
| Appium server | ~1-3s | Appium + driver | ✅ | Team có skill sẵn |
| **Custom APK** | **~30-100ms** | **2-3 tuần build** | **✅ chuẩn** | **200+ cases, Unicode strict** |
| Pure ADB + vision | ~3-5s | Zero | 🟡 | Fallback cho SDK closed UI |

**Chi tiết Custom APK path**: xem `knowledge/e2e-runtime/custom-apk-driver.md` — architecture, protocol spec (HTTP over ADB forward), UiAutomation API cheat sheet, 3 acquisition options (build riêng / fork learn-app / vendor binary).

## Implementation examples

### ARTEMIS MCP adapter (Wave 2 target)

```typescript
class ArtemisDriverAdapter implements DeviceDriver {
  async fetchHierarchy() {
    const result = await mcp.call('mcp__artemis__mobile_get_device_state', {
      view_type: 'hierarchy'
    });
    return parseArtemisHierarchy(result);
  }

  async tap(target) {
    if (target.node) {
      await mcp.call('mcp__artemis__mobile_find_element', { ... });
    }
    return mcp.call('mcp__artemis__mobile_tap', { ... });
  }

  // ... các method khác wrap tương ứng
}
```

### Appium adapter (future community)

Wrap Appium WebDriver client, implement cùng interface.

### Custom APK driver (như learn-app-plugin)

APK built-in với UiAutomation service, communicate qua ADB forward port.

## Performance targets

| Operation | Target | Rationale |
|---|---|---|
| `fetchHierarchy` | < 100ms | Poll nhiều lần/case, phải nhanh |
| `tap` | < 200ms | Including hierarchy fetch + match |
| `type` 50 chars | < 2s | Including IME switching cho unicode |
| `screenshot` | < 500ms | PNG encode + save |
| `shell` | < 1s | Depend on command |
| `launch cold` | < 5s | App startup time |

Nếu driver nào vượt target 2x, log warning, không fail test. Downstream tune hoặc swap driver.

## Portability requirements

- **Platform-agnostic**: macOS, Linux, Windows (Windows có limitation với VB-Cable cho speak action)
- **ADB-based**: không require vendor-specific tool (chỉ Android SDK platform-tools)
- **Serial-addressable**: multiple devices parallel qua `-s <serial>`
- **No root required**: default emulator state, không rely vào root privilege
- **Clean disconnect**: không leave zombie process

## Non-goals

Driver **không** chịu trách nhiệm:
- Build APK (build script lo)
- Install APK (runner setup lo)
- Device provisioning (user manual)
- Firebase/analytics setup (product-specific)
- Ad SDK config (product-specific)

Driver chỉ **operate** device, không orchestrate test lifecycle.

## Enforcement

Downstream adapter phải:

1. Implement **all 10 methods** (hoặc document unsupported với clear error)
2. Return response **matching schema** (type check qua TypeScript hoặc JSON schema)
3. Scan **forbidden ops** trước execute `shell` action
4. Capture **screenshot evidence** cho failed asserts
5. Report structured **DriverError** với recoverable + action

## Reference

- `blueprints/e2e-step-contract/step-file.schema.json` — step file actions driver phải support
- `blueprints/e2e-step-contract/forbidden-ops.md` — ops driver scan + reject
- `knowledge/e2e-runtime/runner-neutral-step.md` — design rationale step file
- ARTEMIS MCP docs — reference implementation path

## Future (Wave 2+)

- Multi-device coordination: parallel tap trên 2 device (test chat 2-way)
- Video record session: driver stream MP4 cho replay
- Network stub: driver intercept HTTP via local proxy
- Battery/thermal stress: driver inject state cho perf test
