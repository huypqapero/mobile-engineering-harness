# Coroutines + Flow Essentials

## Overview

Kotlin Coroutines qua `kotlinx.coroutines` dùng ở mọi layer. Compose Multiplatform tương thích hoàn toàn. Mục tiêu: structured concurrency, cancellation safety, deterministic test.

Rules bắt buộc: xem `constitution/concurrency-rules.md` (CORO-001..010).

## Scope ownership — ai sở hữu coroutine

| Scope | Owner | Lifecycle |
|---|---|---|
| `viewModelScope` | ViewModel | Clear khi ViewModel destroyed |
| `rememberCoroutineScope()` | Compose composition | Cancel khi composition leaves |
| Injected `CoroutineScope` | Repository stateful (ví dụ `PlayerRepository`) | Manually cancel ở teardown |
| `LaunchedEffect(key)` | Compose composition + key | Cancel khi key đổi hoặc composition leaves |

**FORBIDDEN**: `GlobalScope.launch`, `CoroutineScope(Dispatchers.IO).launch` tự tạo detached.

## Dispatcher strategy

```kotlin
// Network: suspend call của Retrofit / Ktor / Ktorfit đã main-safe → không withContext
override suspend fun getBook(id: String): ApiResult<Book> =
    api.getBook(id).map { it.toDomain() }

// IO blocking thật (query SQLDelight đồng bộ, file) → local source tự chuyển dispatcher
internal class BookLocalSource(
    private val queries: BookQueries,
    private val ioDispatcher: CoroutineDispatcher,
) {
    suspend fun getById(id: String): BookEntity? = withContext(ioDispatcher) {
        queries.getById(id).executeAsOneOrNull()
    }
}
```

**Rules:**
- Network suspend call → không bọc `withContext` (CORO-002)
- IO blocking work (file, DB đồng bộ) → `withContext(ioDispatcher)` tại nơi blocking
- CPU heavy → `withContext(defaultDispatcher)`
- UI update → không cần explicit (`StateFlow` → Compose đã handle)
- Test → inject `TestDispatcher` qua constructor

## Structured concurrency patterns

### Parallel independent requests

```kotlin
suspend fun loadDetail(id: String): BookDetail = supervisorScope {
    val book = async { bookRepo.getBook(id) }
    val reviews = async { reviewRepo.getReviews(id) }
    val related = async { discoveryRepo.getRelated(id) }
    BookDetail(
        book = book.await(),
        reviews = reviews.await().getOrNull() ?: emptyList(),
        related = related.await().getOrNull() ?: emptyList(),
    )
}
```

`supervisorScope` — reviews fail không hủy book load.
`coroutineScope` — nếu bất kỳ async fail → tất cả cancel.

### Cancel previous (search typeahead)

```kotlin
val query = MutableStateFlow("")

val results: StateFlow<List<Book>> = query
    .debounce(300)
    .filter { it.length >= 2 }
    .distinctUntilChanged()
    .flatMapLatest { q -> searchRepo.search(q).catch { emit(emptyList()) } }
    .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
```

`flatMapLatest` tự động cancel upstream flow trước khi start flow mới.

### Retry with exponential backoff

```kotlin
suspend fun <T> retryExponential(
    maxAttempts: Int = 3,
    initialDelayMs: Long = 500,
    factor: Double = 2.0,
    block: suspend () -> T,
): T {
    var currentDelay = initialDelayMs
    repeat(maxAttempts - 1) {
        try { return block() }
        catch (e: CancellationException) { throw e }
        catch (e: Exception) {
            delay(currentDelay)
            currentDelay = (currentDelay * factor).toLong()
        }
    }
    return block() // last attempt propagate exception
}
```

Không retry 4xx client error — chỉ retry transient (network, 5xx).

## Flow operators — cheat sheet

| Operator | Dùng khi |
|---|---|
| `map` | Transform mỗi emission |
| `filter` | Lọc emission |
| `distinctUntilChanged` | Bỏ emission trùng |
| `debounce(ms)` | User input, delay trước khi process |
| `throttleFirst(ms)` | Button spam prevention |
| `flatMapLatest` | Cancel previous (search typeahead) |
| `flatMapConcat` | Sequential (migration steps) |
| `flatMapMerge` | Concurrent (parallel downloads) |
| `combine(flow1, flow2)` | Reactive combine 2+ sources |
| `zip` | Pair emission 1-1 |
| `stateIn(scope, started, initial)` | Shared hot StateFlow |
| `shareIn(scope, started, replay)` | Shared hot SharedFlow |
| `conflate` | Downstream slow, keep latest |
| `onEach { }` | Side-effect per emission (log) |
| `catch { emit(fallback) }` | Error recovery |
| `onStart { }` / `onCompletion { }` | Lifecycle hooks |
| `retry(n) { it is IOException }` | Retry predicate-based |

## StateFlow vs SharedFlow vs Channel

| Loại | Khi dùng |
|---|---|
| `StateFlow<T>` | Current state, có initial, replay=1, conflated |
| `SharedFlow<T>(replay=0)` | Broadcasting event không state (ví dụ UI effect) |
| `SharedFlow<T>(replay=N)` | Event có history (log stream) |
| `Channel<T>(BUFFERED)` | Guaranteed delivery 1-time, 1 consumer |

**Chọn `Channel` cho UiEffect** của {{PRODUCT_NAME}} — không miss khi screen chưa collect lifecycle.

## Cancellation preservation

```kotlin
// ❌ nuốt CancellationException
try {
    api.call()
} catch (e: Exception) {
    log.e(e)
    return null
}

// ✅ re-throw cancellation
try {
    api.call()
} catch (e: CancellationException) {
    throw e
} catch (e: Exception) {
    log.e(e)
    return null
}

// ✅ alternative — Kotlin stdlib `runCatching` KHÔNG re-throw CancellationException automatic
// → dùng ensureActive() hoặc exception match cụ thể
```

## Flow lifecycle trong Compose

**MUST**: `collectAsStateWithLifecycle()` thay vì `collectAsState()`:

```kotlin
val state by viewModel.state.collectAsStateWithLifecycle()
```

Lý do: khi app ở background, `collectAsState` vẫn collect → leak work. `WithLifecycle` pause khi `STOPPED`.

## Testing with runTest

```kotlin
class HomeViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @BeforeTest fun setup() { Dispatchers.setMain(dispatcher) }
    @AfterTest fun teardown() { Dispatchers.resetMain() }

    @Test
    fun `search debounces input`() = runTest {
        val useCase = FakeSearchUseCase()
        val vm = HomeViewModel(useCase, dispatcher)

        vm.onIntent(HomeIntent.QueryChanged("ha"))
        advanceTimeBy(100)
        vm.onIntent(HomeIntent.QueryChanged("harry"))
        advanceTimeBy(400)
        runCurrent()

        assertEquals(listOf("harry"), useCase.queries)
    }
}
```

`StandardTestDispatcher` + `advanceTimeBy` → test deterministic, không thực chạy delay.

## Common pitfalls

| Pitfall | Fix |
|---|---|
| `GlobalScope.launch` | Inject scope hoặc dùng `viewModelScope` |
| `runBlocking` production | `suspend` + launch trong `viewModelScope` |
| `delay()` + hard-coded dispatcher trong test | `TestDispatcher` + `advanceTimeBy` |
| Catch `Exception` nuốt cancellation | Re-throw `CancellationException` trước |
| 2 request parallel không supervisorScope | `supervisorScope { async; async }` |
| Flow collect raw không lifecycle | `collectAsStateWithLifecycle()` |
| `stateIn(scope, SharingStarted.Eagerly)` khi không cần | `WhileSubscribed(5000)` |

## References

- [Kotlin Coroutines guide](https://kotlinlang.org/docs/coroutines-guide.html)
- [Flow guide](https://kotlinlang.org/docs/flow.html)
- [Android: Coroutines best practices](https://developer.android.com/kotlin/coroutines/coroutines-best-practices)
- `knowledge/coding/data/network.md §ApiResult contract` (error mapping + cancellation ở tầng network)
