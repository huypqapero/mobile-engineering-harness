# Performance — Essentials

Performance budget + optimization techniques cho Android/CMP. Rule tổng: **measure first, never guess**.

## SLO baseline

| Metric | Target p95 | Measurement tool |
|---|---|---|
| Cold start | < 2s | `adb shell am start -S -W` / Macrobenchmark |
| Warm start | < 500ms | Macrobenchmark |
| First screen render | < 1s | Macrobenchmark `TraceSectionMetric` |
| Scroll FPS | 60 (16.6ms/frame) | GPU Rendering Mode / Macrobenchmark `FrameTimingMetric` |
| Main thread block | < 500ms | Profiler CPU |
| App memory nominal | < 150 MB | `adb shell dumpsys meminfo` / Profiler |
| API call | < 2s p95 | OkHttp interceptor / Firebase Performance |
| Image load display | < 500ms | Coil3 instrumentation |

Nếu metric fail SLO → investigate. Chưa fail → không optimize (YAGNI).

## Startup optimization

### Baseline Profile

Pre-compile hot paths (startup + first screen) để AOT, giảm 20-30% cold start.

```kotlin
@RunWith(AndroidJUnit4::class)
class BaselineProfileGenerator {
    @get:Rule val rule = BaselineProfileRule()

    @Test
    fun generate() = rule.collect(packageName = "com.example.app") {
        pressHome()
        startActivityAndWait()
        device.findObject(By.text("Library")).click()
    }
}
```

Output `baseline-prof.txt` → bundle vào APK.

### App Startup library

Aggregate init SDK thay vì mỗi SDK có `ContentProvider` riêng (expensive).

```kotlin
class CrashlyticsInitializer : Initializer<Unit> {
    override fun create(context: Context) {
        FirebaseCrashlytics.getInstance()
    }
    override fun dependencies() = listOf(FirebaseInitializer::class.java)
}
```

### Lazy init

```kotlin
// ❌ eager — chạy mỗi app start
val heavyComputation = computeExpensive()

// ✓ lazy — chỉ chạy khi dùng
val heavyComputation by lazy { computeExpensive() }
```

### DI binding

```kotlin
// ❌ created at start → delay cold start
single(createdAtStart = true) { HeavyService() }

// ✓ lazy
single { HeavyService() }
```

### Avoid `Application.onCreate` heavy work

Keep `Application.onCreate` < 100ms:
- DI init
- Crash reporter early init
- Logging config

Defer:
- Analytics (via App Startup)
- Remote config fetch (post-launch, cached fallback)
- DB migration (background thread)

## Compose performance

### Stability

Compose compiler mark class stable → skip recomposition khi param không đổi.

**Stable mặc định**:
- Primitive (Int, Long, Boolean, Float)
- `data class` with `val` immutable
- Compose-stable types (`State<T>`, `MutableState<T>`)
- `kotlinx.collections.immutable.ImmutableList`, `ImmutableSet`, `ImmutableMap`

**Unstable mặc định**:
- Kotlin `List<T>`, `Set<T>`, `Map<K, V>` (interface, compiler không biết immutable)
- Class with `var` field
- Class từ 3rd-party library compiler không analyze

### Enable Compose compiler reports

```kotlin
// build.gradle.kts (:presenter)
composeCompiler {
    reportsDestination = layout.buildDirectory.dir("compose_compiler")
    metricsDestination = layout.buildDirectory.dir("compose_compiler")
}
```

Chạy:
```bash
./gradlew :presenter:assembleDebug
cat presenter/build/compose_compiler/*-classes.txt
```

Output show stability per class. Unstable → fix.

### Fix unstable

```kotlin
// Option A: convert to data class with val
data class Rail(val id: String, val items: List<Book>)  // List vẫn unstable

// Option B: use ImmutableList (recommended)
import kotlinx.collections.immutable.ImmutableList
data class Rail(val id: String, val items: ImmutableList<Book>)

// Option C: wrap với @Stable annotation
@Stable
data class Rail(val id: String, val items: List<Book>)
```

### Recomposition prevention

1. **Lazy list key**:
```kotlin
items(books, key = { it.id }) { ... }
```

2. **Method reference** stable hơn lambda inline:
```kotlin
Child(onClick = viewModel::onIntent)  // ✓ stable
Child(onClick = { viewModel.onIntent(x) })  // ✗ new lambda mỗi recompose
```

3. **remember + derivedStateOf** cho computed:
```kotlin
val filtered by remember(books) { derivedStateOf { books.filter { ... } } }
```

4. **State hoisting lowest common owner**: không hoist cao hơn cần thiết.

5. **SideEffect debug** đếm recompose:
```kotlin
@Composable
fun BookRow(book: Book) {
    SideEffect { Log.d("Recompose", "BookRow ${book.id}") }
    // ...
}
```

## Memory

### Common leak sources

- Static reference tới `Context` / `View` / `Activity`
- Non-static inner class capture outer (fix: `static class` hoặc top-level)
- Listener không unregister (`DisposableEffect` cleanup)
- Coroutine detached scope không cancel

### LeakCanary (debug variant)

```kotlin
dependencies {
    debugImplementation("com.squareup.leakcanary:leakcanary-android:2.14")
}
```

Auto-detect leak + trace analysis.

### Image memory

Coil3 default:
- Memory cache: 25% max heap
- Disk cache: 2% user data partition (clamp 10-250 MB)

Resize load:
```kotlin
AsyncImage(
    model = ImageRequest.Builder(context)
        .data(url)
        .size(width = 320, height = 320)   // ← don't load full res for small view
        .build(),
    ...
)
```

### Bitmap pool

Khi process nhiều bitmap (gallery, feed scroll) → reuse pool thay vì create mỗi lần.

## Lazy list optimization

```kotlin
LazyColumn(
    state = rememberLazyListState(),
    contentPadding = PaddingValues(16.dp),
) {
    items(
        items = books,
        key = { it.id },
        contentType = { "book" },      // reusable viewpool
    ) { book ->
        BookRow(book, modifier = Modifier.height(80.dp))   // fixed height optimize measure
    }
}
```

Rule:
- `key` **MUST** cho dynamic list
- `contentType` **SHOULD** khi có multiple layout types
- Fixed size `Modifier.height(X.dp)` giúp LazyColumn skip measure
- Nested `LazyColumn` + `LazyRow` OK, nhưng limit depth 2

## Network optimization

### HTTP/2 (automatic với OkHttp)

Multiplexing, header compression, prioritization.

### Compression

```kotlin
install(DefaultRequest) {
    header(HttpHeaders.AcceptEncoding, "gzip")
}
```

Server trả gzipped → Ktor auto decompress.

### Caching

- **HTTP cache** cho GET với `Cache-Control` / `ETag`
- **DB cache SSOT** cho offline-first
- Xem `knowledge/coding/data/caching.md`

### Pagination

Cursor-based > offset-based (consistent khi data insert giữa pages).

### Prefetch

Smart prefetch next page khi user scroll gần cuối:

```kotlin
LaunchedEffect(lazyListState.layoutInfo) {
    val lastVisible = lazyListState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: return@LaunchedEffect
    if (lastVisible >= books.size - 5) {
        viewModel.loadMore()
    }
}
```

## Database query optimization

### Index strategy

```sql
CREATE INDEX book_updated_at ON Book(updated_at);
CREATE INDEX book_bookmarked_updated ON Book(is_bookmarked, updated_at) WHERE is_bookmarked = 1;
```

### EXPLAIN QUERY PLAN

```sql
EXPLAIN QUERY PLAN SELECT * FROM Book WHERE updated_at > :threshold ORDER BY updated_at DESC;
```

Check `USING INDEX` → ok. `SCAN TABLE` → missing index (nếu dataset lớn).

### Projection

```sql
-- ❌ fetch toàn bộ
SELECT * FROM Book

-- ✓ chỉ fetch cần
SELECT id, title, cover_url FROM Book WHERE is_bookmarked = 1
```

### Transaction cho bulk write

```kotlin
queries.transaction {
    books.forEach { queries.upsert(it) }
}
```

1 transaction >> 1000 individual write.

## Battery

- **WorkManager** cho background task, không `AlarmManager`
- **Firebase Messaging push** thay poll
- **Doze mode compliance**: không wake lock trừ critical
- **Location**: significant change only, không continuous
- **Audio foreground service** chỉ khi playing

## Profiling workflow

```
┌──────────┐   ┌───────────────┐   ┌──────────────┐   ┌───────────────┐
│ Measure  │──▶│  Hypothesize  │──▶│   Optimize   │──▶│  Re-measure   │
└──────────┘   └───────────────┘   └──────────────┘   └───────────────┘
      ▲                                                        │
      └────────────────────────── loop ────────────────────────┘
```

- Baseline metric before
- Isolate 1 optimization at a time
- Measure after
- Keep nếu delta > 10% + consistent; revert nếu không

## Common mistakes

| Mistake | Fix |
|---|---|
| Optimize chưa đo baseline | Measure before + after |
| Random "faster" fix không hypothesis | Profile-guided |
| Over-cache → stale UI | TTL + invalidation strategy |
| Image full res display small view | Coil3 `.size()` resize |
| `List<T>` passing qua Compose làm recompose | `ImmutableList` |
| Nested recomposition cascade | Hoist state lowest owner |
| Eager init SDK trong `Application.onCreate` | Lazy + App Startup library |
| Query without index trên 10k row | Add index + EXPLAIN QUERY PLAN |
| `GlobalScope.launch` background work | WorkManager hoặc inject scope |
| Blocking main thread (sync IO/DB read) | Move to `withContext(ioDispatcher)` |

## References

- Android Performance docs: https://developer.android.com/topic/performance
- Compose stability: https://developer.android.com/jetpack/compose/performance/stability
- Macrobenchmark: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview
- `.harness/skills/coding-diagnose/SKILL.md` (mode `perf`)
