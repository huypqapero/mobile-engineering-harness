---
name: android-performance
description: Diagnose + optimize performance — startup time, UI jank, memory, network latency. Measure → hypothesize → optimize → re-measure. Trigger khi task touches performance, UI jank, startup slow, memory high, hoặc profile analysis.
priority: P2
---

# Skill: android-performance

## Trigger

- UI jank visible (dropped frame, scroll stutter)
- Cold start > 3s
- Memory high (>200 MB nominal app)
- OOM crash
- Network latency slow (p95 > 3s)
- Baseline Profile setup
- Compose recomposition excessive
- Battery drain user complaint

## Approach — Measure first, never guess

**Golden rule**: optimize **có evidence**. Random "performance" fix thường không impact hoặc regress elsewhere.

```
┌──────────┐   ┌───────────────┐   ┌──────────────┐   ┌───────────────┐
│ Measure  │──▶│  Hypothesize  │──▶│   Optimize   │──▶│  Re-measure   │
└──────────┘   └───────────────┘   └──────────────┘   └───────────────┘
      ▲                                                        │
      └────────────────────────── loop ────────────────────────┘
```

## Prerequisites

1. `.harness/knowledge/performance/essentials.md`
2. `.harness/knowledge/compose/essentials.md §Recomposition prevention`
3. Android Studio Profiler setup

## Measurement tools

### CPU + Rendering

- **Android Studio Profiler**: CPU trace, Method sampling
- **Perfetto** (`adb shell perfetto`): System-wide trace
- **systrace** (deprecated, use Perfetto)
- **GPU Rendering Mode** (Developer Options): visual frame time bars

### Memory

- **Android Studio Profiler**: Memory tab, Heap dump, Allocation tracking
- **LeakCanary** (debug variant): auto-detect leak
- **adb shell dumpsys meminfo <package>**: snapshot

### Startup

- **adb shell am start -S -W <package>/<activity>**: cold start time
- **Macrobenchmark** library: automated baseline profile + startup measurement
- **Baseline Profile**: pre-compile hot paths

### Network

- **OkHttp interceptor**: log request duration
- **Firebase Performance Monitoring**: real-user metrics
- **Charles Proxy / Flipper**: inspect request/response

### Compose

- **Compose compiler reports** (`enableComposeCompilerReports=true`): class stability
- **Layout Inspector** → Recomposition count

## Common optimization patterns

### P-01 — Startup optimization

**Target**: cold start < 2s (p95)

Techniques:
1. **Baseline Profile**: pre-compile hot paths. 20-30% faster cold start.
2. **App Startup library**: aggregate init của library (Firebase, WorkManager, etc.)
3. **Lazy initialization**: `by lazy`, Koin `single { }` không `createdAtStart`
4. **Reduce manifest INIT**: không cần `ContentProvider` cho SDK init
5. **R8 full mode**: minify + optimize class

```kotlin
// Avoid work in Application.onCreate()
class App : Application() {
    override fun onCreate() {
        super.onCreate()
        // Core: logging, DI
        startKoin { modules(appModule) }
        // Defer: Analytics, Crashlytics → App Startup library
    }
}
```

### P-02 — Compose recomposition reduction

Techniques:
1. **Stable types**: `data class` with `val` immutable (compiler marks stable)
2. **ImmutableList** (kotlinx.collections.immutable) khi `List<T>` thường xuyên recompose
3. **`remember(key)`** cho computed value
4. **`derivedStateOf`** cho derived state không re-compute mỗi recompose
5. **`key(id) { }`** cho item trong list render
6. **Method reference** `onClick = viewModel::onIntent` thay lambda inline
7. **Hoist state** tới owner thấp nhất (không recompose grandparent)

```kotlin
// ❌ unstable lambda — grandparent recompose → child recompose
Child(onClick = { viewModel.onIntent(Intent.Click) })

// ✅ stable method reference
Child(onClick = viewModel::handleClick)
```

### P-03 — Lazy list optimization

```kotlin
LazyColumn {
    items(
        items = books,
        key = { it.id },                 // ← stable identity
        contentType = { "book" },         // ← reusable viewpool
    ) { book ->
        BookRow(book)                     // ← stable param
    }
}
```

- **key**: tránh re-create state khi scroll
- **contentType**: viewpool reuse khi scrolling nhanh
- **Fixed size items** (Modifier.height(X.dp)): LazyColumn optimize measure

### P-04 — Memory optimization

Techniques:
1. **Bitmap size**: sample khi load, không full res (Coil3 default handle)
2. **Clear reference**: `WeakReference` cho callback, không hold Context trong static
3. **DiskCache**: image / video → disk, không in-memory
4. **Pool reuse**: `BitmapPool`, `ByteArrayPool`
5. **Stream large payload**: `BodyChannel` thay vì load full bytes

### P-05 — Network optimization

Techniques:
1. **HTTP/2** (automatic với OkHttp)
2. **Compression** (`Accept-Encoding: gzip`)
3. **Cache-Control**: ETag + max-age
4. **Request coalescing**: debounce + batch
5. **Pagination** (cursor-based > offset)
6. **Prefetch**: smart prefetch next page khi user scroll
7. **Image CDN**: resize server-side thay vì client crop

### P-06 — Database query optimization

Techniques:
1. **Index** column dùng `WHERE` + `ORDER BY`
2. **Partial index** cho filter thường
3. **EXPLAIN QUERY PLAN** check cost
4. **Projection**: `SELECT col1, col2` thay `SELECT *`
5. **Transaction** cho bulk write
6. **Flow debounce** nếu DB trigger emit quá nhanh

### P-07 — Battery optimization

Techniques:
1. **WorkManager** cho background task (not AlarmManager)
2. **Firebase Messaging** push thay poll
3. **Doze mode compliance**: không wake lock trừ khi critical
4. **Location**: significant change only, không continuous
5. **Audio**: `foreground service` chỉ khi playing

## Measurement workflow

### Startup

```bash
adb shell am force-stop com.example.app
adb shell am start -S -W com.example.app/.MainActivity
# Reports: WaitTime, TotalTime, LaunchState
```

Run 10 times, discard outlier, average.

### UI jank

```kotlin
// Enable in Developer Options → GPU Rendering Mode → On screen as bars
// Each bar > green line = dropped frame
```

Or Macrobenchmark:

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

### Memory

```bash
adb shell dumpsys meminfo com.example.app
# TOTAL PSS, Private Dirty — compare over time
```

Or Profiler → Memory → Record native allocations.

## Decision guides

### Khi nào optimize?

- **Yes** nếu: metric fail SLO (startup > 3s, p95 jank, OOM user report)
- **No** nếu: metric chưa đo, "cảm thấy chậm" không data

### Measure vs assume

**Assume** gần như luôn sai. Measure:
- Before: baseline metric
- After: new metric
- Delta: significant? (statistically, > 10% + consistent)

### Scope

Optimize **hot path** first:
- App startup (user wait, perceived performance)
- First screen render
- Main scroll feed
- Payment / critical conversion flow

Không optimize cold path:
- Settings screen rare visited
- Legal page
- Internal admin tool

## Common mistakes

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

## SLO targets (gợi ý)

| Metric | Target p95 |
|---|---|
| Cold start | < 2s |
| Warm start | < 500ms |
| First screen render | < 1s after start |
| Main scroll FPS | 60 |
| App memory | < 150 MB nominal |
| Image load display | < 500ms |
| API call | < 2s p95 |

## Output contract

- Baseline metric recorded (before)
- Hypothesis + evidence trong plan
- Optimization applied, isolated
- Re-measured metric (after)
- Delta > 10% + consistent → ship
- Report: metric before/after + technique used

## Anti-patterns bị cấm

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
- `.harness/knowledge/performance/essentials.md`
