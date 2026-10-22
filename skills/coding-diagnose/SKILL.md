---
name: coding-diagnose
description: Diagnose Android issues — bug mode (reproduce, isolate, prove root cause before fix) hoặc perf mode (measure, hypothesize, optimize, re-measure). Dispatcher theo --mode bug|perf. Trigger khi task fix bug/crash/ANR, hoặc optimize startup/jank/memory/network.
priority: P2
---

# Skill: coding-diagnose

Dispatcher 2 mode: `--mode bug` cho reactive diagnosis (crash, ANR, flaky test, unexpected behavior), `--mode perf` cho proactive optimization (startup, jank, memory, network). Cả hai dùng chung tool chain (Profiler, Perfetto, logcat) nhưng khác methodology.

Procedure chi tiết cho bug mode: `workflows/fix-bug.md`. Perf mode preserve Measure-Hypothesize-Optimize-Re-measure loop.

## Trigger

**Mode `bug`:**
- Crash report (Crashlytics, Play Console)
- ANR (Application Not Responding)
- Memory leak suspect (LeakCanary)
- Flaky test (fail không deterministic)
- Coroutine zombie / cancellation leak
- Platform-specific behavior (iOS vs Android divergence trong CMP)
- Compose recompose excessive **do bug** (vs do unstable param cố ý)

**Mode `perf`:**
- UI jank visible (dropped frame, scroll stutter) không gắn crash
- Cold start > 3s
- Memory high (>200 MB nominal app) không OOM crash
- OOM crash (overlap với bug mode — chọn perf nếu root cause là memory pressure)
- Network latency slow (p95 > 3s)
- Baseline Profile setup
- Compose recomposition excessive do unstable param
- Battery drain user complaint

**Khi overlap (UI jank do performance regression):** chọn `--mode bug` khi có baseline xanh gần đó (bisect fit); chọn `--mode perf` khi cần measurement-driven tuning từ đầu.

## Inputs

Bắt buộc:
- `--mode: bug | perf`

Mode `bug`:
- Bug description + repro steps (nếu có)
- Crash stack trace / log / error message (nếu có)

Mode `perf`:
- Metric target (SLO) hoặc complaint cụ thể
- Baseline measurement (nếu có) hoặc flag cần đo mới

## Prerequisites

Chung:
- `knowledge/coding/coroutines/essentials.md` cho cancellation/scope
- `knowledge/coding/compose/essentials.md` cho recomposition/stability

Mode `bug`:
- `workflows/fix-bug.md` — 5-stage orchestration

Mode `perf`:
- `knowledge/cross-cutting/performance/essentials.md`
- `knowledge/coding/compose/essentials.md §Recomposition prevention`
- Android Studio Profiler setup

---

## Mode: bug

### D-01 — Reproduce deterministic

Trước mọi fix, bug phải repro được:
- Minimal steps < 10 interactions
- Same env (device model, OS version, build variant)
- Record repro trong plan/report
- Không repro → stop, không fix guess

Tools:
- Device emulator snapshot (consistent state)
- Instrumented test với fixed input
- Screen recording cho visual bug
- `adb` for state manipulation

### D-02 — Isolate scope

```bash
# Git bisect nếu có baseline xanh
git bisect start
git bisect bad HEAD
git bisect good <known-good-commit>
```

- Comment out code để shrink surface
- Reduce input (binary search)
- Try different device/OS → narrow platform-specific
- Clear cache/data → separate state vs code bug

### D-03 — Logging + breakpoint

```kotlin
Log.d("BookVM", "loadBook id=$id, state=${state.value}")
```

Rules:
- Tag ngắn stable (`"BookVM"` không `"BookDetailViewModel.kt - loadBook function"`)
- Log sau fix → remove hoặc downgrade `Log.v` + wrap `BuildConfig.DEBUG`
- Không log PII (token, email, phone)

Breakpoint: IntelliJ/Android Studio debugger cho stepping, conditional breakpoint cho reproduce specific state, watch expression cho state value monitoring.

### D-04 — Prove root cause

Không fix mù. Mỗi fix cần evidence:
- Bug-first test fail → sau fix PASS
- Log trace path showing wrong state
- Debugger step confirming hypothesis
- Classify (xem `workflows/fix-bug.md §Stage 3`):
  - **Logic**: wrong state transition, missing branch
  - **Concurrency**: race, cancellation leak, zombie coroutine
  - **State**: lost on config change, incorrect SavedStateHandle
  - **Compose**: recomposition skip, unstable param
  - **Data**: null leak, mapper bug, DTO shape change
  - **Platform**: lifecycle event ordering, permission edge

### D-05 — Platform-specific debug

**Android:**
- `adb logcat` → view runtime log
- `adb shell dumpsys meminfo <package>` → memory
- `adb shell dumpsys gfxinfo <package>` → frame rendering
- Android Studio Profiler: CPU, memory, network, energy

**iOS (CMP):**
- Xcode Console → runtime log
- Instruments → Time Profiler, Allocations, Network
- Simulator vs Device (behavior khác)

**Common:**
- Firebase Crashlytics → prod crash
- Firebase Performance → startup time, trace
- Firebase Analytics → event flow

### D-06 — Common bug patterns

| Symptom | Likely cause | Technique |
|---|---|---|
| UI not update after state change | Not observing with lifecycle | `collectAsStateWithLifecycle()` |
| State lost on rotation | Not using `SavedStateHandle` | Nav args qua `SavedStateHandle` |
| Coroutine không cancel | `GlobalScope.launch` hoặc detached scope | Dùng `viewModelScope` |
| Flow emit duplicate | Missing `distinctUntilChanged()` | Add operator |
| Compose recompose excessive | Unstable lambda/data class | Use `remember`, method reference |
| Memory leak | Static ref to Context/View | Weak ref, lifecycle-aware |
| ANR | Blocking main thread > 5s | Move to IO dispatcher |
| Crash on nav | Route not registered | Verify `AppNavHost` composable mapping |
| 401 after sign in | Token refresh race | Serialize refresh với `Mutex` |
| App crash on resume | Config change recreate killed state | SavedStateHandle restore |

### D-07 — Coroutine debugging

```kotlin
// Debug build only
System.setProperty("kotlinx.coroutines.debug", "on")

viewModelScope.launch(CoroutineName("loadBook")) {
    ...
}
```

Dumps coroutine stack trace với name. Khi crash → stack trace show "loadBook" context.

### D-08 — Compose recomposition debugging

```kotlin
@Composable
fun BookRow(book: Book) {
    SideEffect {
        Log.d("Recompose", "BookRow ${book.id}")
    }
}
```

Count recompose per screen. Nếu > expected → investigate stability. Compose compiler report:

```
./gradlew assembleDebug -PenableComposeCompilerReports=true
```

Sinh `*-stability.txt` show class stability. Unstable → wrap `@Stable` hoặc convert sang data class immutable.

### Failure classifier (R-04)

Trước khi start fix, **classify failure**. Classification wrong → wrong fix path.

| Category | Pattern | Who fixes | Example |
|---|---|---|---|
| **build** | Compile error, dep conflict, Gradle config | Coder | Missing import, type mismatch, Gradle sync fail |
| **code** | Logic bug, NPE, race, wrong state | Coder + QA | Null leak, concurrency, UI not update |
| **test** | Flaky, wrong assertion, test setup bug | QA + Reviewer | `assertEquals("expected", actualDifferent)`, flaky timing |
| **device** | ADB offline, emulator timeout, device busy | **User (infra)** | `adb: device not found`, device lock conflict |
| **infra** | OOM, disk full, network timeout CI | **User (infra)** | Gradle OOM, no space left, DNS fail |
| **env** | JDK/Kotlin/SDK version mismatch | **User (setup)** | `Unsupported Kotlin version`, SDK path missing |

**Fingerprint** cho detect "same error loop" (xem `knowledge/meta/auto-fix/essentials.md`):

```python
fingerprint = sha1(f"{task_name}:{exception_class}:{stack_top_3_frames_normalized}")
```

Normalize = strip line number, keep class + method name.

**Routing matrix:**

```yaml
build:
  retry_tier: implementer
  retry_strategy: fix_immediate_error → check_surrounding_context
  max_attempts: 3
code:
  retry_tier: implementer + test_engineer
  retry_strategy: fix_cause → add_regression_test
  max_attempts: 3
test:
  retry_tier: test_engineer + reviewer
  retry_strategy: REVIEW_ASSERTION_CORRECTNESS_FIRST (not "make it pass")
  max_attempts: 2
device:
  retry_tier: NONE
  escalate: user
  pattern: "Please restart ADB / reconnect device"
infra:
  retry_tier: NONE
  escalate: user
  pattern: "Clean disk / scale VPS / check network"
env:
  retry_tier: NONE
  escalate: user
  pattern: "Update toolchain to <version>"
```

**Classification procedure:**

1. Read error message + stack trace + context
2. Match pattern:
   - "cannot find symbol" / "unresolved reference" → **build**
   - "NullPointerException" / "IllegalStateException" / "race" / "deadlock" → **code**
   - Test fail với clear expected/actual → **test**
   - `adb: no devices` / "emulator timeout" → **device**
   - "OutOfMemoryError" / "No space left" / connection timeout → **infra**
   - "Unsupported Java version" / "SDK not found" → **env**
3. Compute fingerprint
4. Check `plans/<date>/fix-attempts.yaml`:
   - Fingerprint lặp without progress → ESCALATE
   - `current_attempts >= max_fix_attempts` → ESCALATE
5. Else apply classification routing + append attempt

**Example classification:**

```
STACK:
java.lang.NullPointerException: Attempt to invoke virtual method 'getUser' on null
	at BookDetailViewModel.loadBook(BookDetailViewModel.kt:42)

CLASSIFY: code (NPE, business logic layer)
FINGERPRINT: sha1("BookDetailViewModel.loadBook:NullPointerException:...")
ROUTE: implementer (fix cause: null check or non-null contract) + qa (regression test)
```

### Fix tại cause hay tại symptom?

**Luôn fix cause:**
- UI crash do null → fix data layer non-null contract (không chỉ null-check UI)
- Race → add proper synchronization (không retry)
- Memory leak → fix reference, không giảm Heap size

**Exception:** tạm workaround ở symptom khi cause fix tốn > 1 ngày + có user impact critical → thêm comment + issue link.

### Khi bug không repro được

1. Collect more info từ user (device, steps, timing)
2. Add defensive logging + release build
3. Monitor Crashlytics / telemetry
4. **Không fix guess** — document "cannot reproduce" trạng thái

### Khi suspect flaky test

1. Run 10 lần local → confirm flakiness
2. Isolate: timing dependency? Shared state? Thread?
3. Fix cause (không retry):
   - Timing: dùng `advanceTimeBy` thay `delay()` thật
   - Shared state: fresh fake per test
   - Thread: inject dispatcher

### Khi bug cross-module

- Reproduce ở integration level trước
- Isolate per module via disable + mock
- Fix tại module gốc, không spread patch

### Common mistakes (bug mode)

| Mistake | Fix |
|---|---|
| Fix bằng try/catch nuốt exception | Fix cause, không mask |
| Null-check UI khi data layer phải non-null | Fix contract data, không UI defense |
| Disable test đang fail | Fix hoặc delete; không disable |
| "Temporary" fix không issue link | Add TODO(#issue) + plan proper fix |
| Fix multiple bugs 1 PR | Reviewer khó verify, split |
| Add defensive null-check "để chắc" | Trust type system; non-null = non-null |
| Hard-reset state khi UI edge case | Fix state transition logic đúng |
| Add retry cho logic bug | Retry chỉ cho transient (network), không cho logic |

---

## Mode: perf

### Golden rule — Measure first, never guess

Optimize **có evidence**. Random "performance" fix thường không impact hoặc regress elsewhere.

```
┌──────────┐   ┌───────────────┐   ┌──────────────┐   ┌───────────────┐
│ Measure  │──▶│  Hypothesize  │──▶│   Optimize   │──▶│  Re-measure   │
└──────────┘   └───────────────┘   └──────────────┘   └───────────────┘
      ▲                                                        │
      └────────────────────────── loop ────────────────────────┘
```

### Measurement tools

**CPU + Rendering:**
- **Android Studio Profiler**: CPU trace, Method sampling
- **Perfetto** (`adb shell perfetto`): System-wide trace
- **GPU Rendering Mode** (Developer Options): visual frame time bars

**Memory:**
- **Android Studio Profiler**: Memory tab, Heap dump, Allocation tracking
- **LeakCanary** (debug variant): auto-detect leak
- **adb shell dumpsys meminfo <package>**: snapshot

**Startup:**
- **adb shell am start -S -W <package>/<activity>**: cold start time
- **Macrobenchmark**: automated baseline profile + startup measurement
- **Baseline Profile**: pre-compile hot paths

**Network:**
- **OkHttp interceptor**: log request duration
- **Firebase Performance Monitoring**: real-user metrics
- **Charles Proxy / Flipper**: inspect request/response

**Compose:**
- **Compose compiler reports** (`enableComposeCompilerReports=true`): class stability
- **Layout Inspector** → Recomposition count

### Common optimization patterns

**P-01 — Startup optimization.** Target: cold start < 2s (p95).

1. **Baseline Profile**: pre-compile hot paths. 20-30% faster cold start.
2. **App Startup library**: aggregate init của library (Firebase, WorkManager, etc.)
3. **Lazy initialization**: `by lazy`, Koin `single { }` không `createdAtStart`
4. **Reduce manifest INIT**: không cần `ContentProvider` cho SDK init
5. **R8 full mode**: minify + optimize class

```kotlin
class App : Application() {
    override fun onCreate() {
        super.onCreate()
        // Core: logging, DI
        startKoin { modules(appModule) }
        // Defer: Analytics, Crashlytics → App Startup library
    }
}
```

**P-02 — Compose recomposition reduction.**

1. **Stable types**: `data class` with `val` immutable (compiler marks stable)
2. **ImmutableList** (kotlinx.collections.immutable) khi `List<T>` thường xuyên recompose
3. **`remember(key)`** cho computed value
4. **`derivedStateOf`** cho derived state không re-compute mỗi recompose
5. **`key(id) { }`** cho item trong list render
6. **Method reference** `onClick = viewModel::onIntent` thay lambda inline
7. **Hoist state** tới owner thấp nhất

```kotlin
// ❌ unstable lambda — grandparent recompose → child recompose
Child(onClick = { viewModel.onIntent(Intent.Click) })

// ✅ stable method reference
Child(onClick = viewModel::handleClick)
```

**P-03 — Lazy list optimization.**

```kotlin
LazyColumn {
    items(
        items = books,
        key = { it.id },                 // ← stable identity
        contentType = { "book" },         // ← reusable viewpool
    ) { book ->
        BookRow(book)
    }
}
```

- **key**: tránh re-create state khi scroll
- **contentType**: viewpool reuse khi scrolling nhanh
- **Fixed size items** (Modifier.height(X.dp)): LazyColumn optimize measure

**P-04 — Memory optimization.**

1. **Bitmap size**: sample khi load, không full res (Coil3 default handle)
2. **Clear reference**: `WeakReference` cho callback, không hold Context trong static
3. **DiskCache**: image / video → disk, không in-memory
4. **Pool reuse**: `BitmapPool`, `ByteArrayPool`
5. **Stream large payload**: `BodyChannel` thay vì load full bytes

**P-05 — Network optimization.**

1. **HTTP/2** (automatic với OkHttp)
2. **Compression** (`Accept-Encoding: gzip`)
3. **Cache-Control**: ETag + max-age
4. **Request coalescing**: debounce + batch
5. **Pagination** (cursor-based > offset)
6. **Prefetch**: smart prefetch next page khi user scroll
7. **Image CDN**: resize server-side thay vì client crop

**P-06 — Database query optimization.**

1. **Index** column dùng `WHERE` + `ORDER BY`
2. **Partial index** cho filter thường
3. **EXPLAIN QUERY PLAN** check cost
4. **Projection**: `SELECT col1, col2` thay `SELECT *`
5. **Transaction** cho bulk write
6. **Flow debounce** nếu DB trigger emit quá nhanh

**P-07 — Battery optimization.**

1. **WorkManager** cho background task (not AlarmManager)
2. **Firebase Messaging** push thay poll
3. **Doze mode compliance**: không wake lock trừ khi critical
4. **Location**: significant change only, không continuous
5. **Audio**: `foreground service` chỉ khi playing

### Measurement workflow

**Startup:**

```bash
adb shell am force-stop com.example.app
adb shell am start -S -W com.example.app/.MainActivity
# Reports: WaitTime, TotalTime, LaunchState
```

Run 10 times, discard outlier, average.

**UI jank:** Enable Developer Options → GPU Rendering Mode → On screen as bars. Each bar > green line = dropped frame.

Hoặc Macrobenchmark:

```kotlin
@RunWith(AndroidJUnit4::class)
class ScrollBenchmark {
    @get:Rule val rule = MacrobenchmarkRule()

    @Test
    fun scrollLibrary() = rule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(FrameTimingMetric()),
        iterations = 10,
        startupMode = StartupMode.COLD,
    ) {
        pressHome()
        startActivityAndWait()
        device.findObject(By.res("library")).fling(Direction.DOWN)
    }
}
```

**Memory:**

```bash
adb shell dumpsys meminfo com.example.app
# TOTAL PSS, Private Dirty — compare over time
```

Hoặc Profiler → Memory → Record native allocations.

### Decision guides

**Khi nào optimize?**
- **Yes** nếu: metric fail SLO (startup > 3s, p95 jank, OOM user report)
- **No** nếu: metric chưa đo, "cảm thấy chậm" không data

**Measure vs assume:** Assume gần như luôn sai. Measure:
- Before: baseline metric
- After: new metric
- Delta: significant? (statistically, > 10% + consistent)

**Scope:** Optimize **hot path** first:
- App startup (user wait, perceived performance)
- First screen render
- Main scroll feed
- Payment / critical conversion flow

Không optimize cold path:
- Settings screen rare visited
- Legal page
- Internal admin tool

### Common mistakes (perf mode)

| Mistake | Fix |
|---|---|
| Optimize without baseline | Measure before, optimize, measure after |
| Optimize cold path | Focus hot path (90% user flow) |
| Micro-optimize assembler | Profiler-guided, don't guess |
| Compose `remember { ... }` cho data thay đổi mỗi param | `remember(key) { ... }` with key |
| Image full res display 100x100 pixel | Coil3 `.size()` resize |
| Startup eagerly init SDK | App Startup library + lazy |
| `List<T>` passing qua Compose | `ImmutableList` hoặc split screen state |
| Thread hopping excessive | Batch work, flow operators |
| Query without index on 10k rows | Add index + EXPLAIN QUERY PLAN |
| Local DB SELECT * trong Flow emit mỗi row change | Projection + distinctUntilChanged |

### SLO targets (gợi ý)

| Metric | Target p95 |
|---|---|
| Cold start | < 2s |
| Warm start | < 500ms |
| First screen render | < 1s after start |
| Main scroll FPS | 60 |
| App memory | < 150 MB nominal |
| Image load display | < 500ms |
| API call | < 2s p95 |

---

## Required policies

Chung:
- CORO-004 preserve cancellation
- KOT-002 null safety
- KOT-009 exception specificity

Mode `bug`:
- Workflow `fix-bug.md` orchestration
- Không `@Ignore` test không issue link

## Output contract

Mode `bug`:
- Bug repro deterministic + minimal steps
- Root cause classified (logic/concurrency/state/compose/data/platform)
- Evidence stated (log/test/debugger output)
- Fix tại cause level
- Bug-first test PASS sau fix
- Regression test added
- Related features không regression

Mode `perf`:
- Baseline metric recorded (before)
- Hypothesis + evidence trong plan
- Optimization applied, isolated
- Re-measured metric (after)
- Delta > 10% + consistent → ship
- Report: metric before/after + technique used

## Anti-patterns bị cấm

Mode `bug`:
- Fix bằng try/catch mask
- Null-check UI thay vì fix data layer
- Add retry cho logic bug
- "Should work" claim không có evidence
- Random fix thử-sai không hypothesis
- Fix + refactor + feature trong 1 PR

Mode `perf`:
- Optimize chưa đo baseline
- "Should be faster" claim không data
- Micro-optimize ở path không hot
- Add caching chỉ "để chắc" không measure
- Remove feature "để chạy nhanh hơn" (scope creep)
- Optimize memory bằng cách giảm functionality
- Multiple optimizations 1 PR → không isolate impact

## References

- [Android App Performance](https://developer.android.com/topic/performance)
- [Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Compose stability](https://developer.android.com/jetpack/compose/performance/stability)
- `knowledge/cross-cutting/performance/essentials.md`

---

## Harness context

- Workflow: `workflows/fix-bug.md`
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`


## Overlay gate (D-full)

Trước Step 1, verify `.harness-overlay/overlay.yaml` tồn tại. Nếu không, abort với status `BLOCKED` và chỉ dẫn user:

> Chưa có overlay. Chạy skill `harness-init` để scaffold trước, sau đó quay lại skill này.

Khi gặp placeholder `{{X}}` trong procedure/code example, resolve bằng mapping ở `AGENTS.md §Placeholder resolution` (Read overlay 1 lần đầu session, cache qua context).
