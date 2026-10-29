---
name: coding-coroutines
description: Design + implement async / concurrent code với Kotlin Coroutines + Flow. Trigger khi task liên quan structured concurrency, cancellation, Flow operators, dispatcher selection, hoặc fix bug concurrency.
priority: P0
---

# Skill: coding-coroutines

## Trigger

- Implement API call với retry/timeout
- Build search typeahead (debounce + cancel previous)
- Parallel request orchestration
- Background sync / long-running task
- Fix bug: race condition, lost update, zombie coroutine, cancellation leak
- Refactor callback-based API thành suspend function

## Inputs

- Context: scope ownership (ViewModel / Repository / global)
- Dispatcher constraint (IO / CPU / Main)
- Cancellation requirement
- Error handling policy (silent / notify / retry)

## Prerequisites

1. `knowledge/coding/coroutines/essentials.md [KB → develop/coding-coroutines, kb_search "coroutines essentials"]` — full patterns + anti-patterns
2. `constitution/concurrency-rules.md [KB → develop/constitution, kb_search "concurrency rules"]` — CORO-001..010
3. `knowledge/coding/data/network.md [KB → develop/coding-data, kb_search "data network"] §ApiResult contract` — network call main-safe, cancellation rethrow ở adapter/converter

## Execution procedure

### Step 1 — Identify ownership + lifecycle

Hỏi 3 câu:

1. **Scope**: viewModelScope / inject repository scope / rememberCoroutineScope?
2. **Dispatcher**: IO (file/network/DB), Default (CPU heavy), Main (Compose state — usually implicit)?
3. **Cancellation**: cần cancel khi screen leave? Hay giữ running trong background?

### Step 2 — Choose Flow type

| Need | Choose |
|---|---|
| Current state có initial, replay=1 | `StateFlow<T>` |
| Broadcast event không state, 1-time | `Channel<T>(BUFFERED)` + `.receiveAsFlow()` |
| Hot event có history (log) | `SharedFlow<T>(replay=N)` |
| Cold stream | `Flow<T>` |

**MUST**: `.asStateFlow()`, `.asSharedFlow()`, `.receiveAsFlow()` để expose immutable interface (CORO-005).

### Step 3 — Apply operator pipeline

| User scenario | Operator |
|---|---|
| Debounce typing | `debounce(300)` |
| Cancel previous (search) | `flatMapLatest { }` |
| Parallel independent | `supervisorScope { async; async }` |
| Combine 2+ sources | `combine(a, b) { ... }` |
| Shared hot | `stateIn(scope, SharingStarted.WhileSubscribed(5000), initial)` |
| Downstream slow | `conflate()` |
| Side-effect per emission | `onEach { }` |
| Error recovery | `catch { emit(fallback) }` |
| Retry transient | `retry(3) { it is IOException }` |

### Step 4 — Cancellation preservation

```kotlin
try {
    api.call()
} catch (e: CancellationException) {
    throw e   // ← always rethrow
} catch (e: Exception) {
    // handle specific
}
```

`runCatching` **không** auto-rethrow Cancellation → bọc thêm hoặc dùng try/catch cụ thể.

### Step 5 — Dispatcher injection

```kotlin
class SearchViewModel(
    private val search: SearchUseCase,
    private val dispatcher: CoroutineDispatcher = Dispatchers.Default,  // injectable
) : BaseViewModel<...>(...) {
    // dispatcher dùng trong launch nếu cần override
}
```

**FORBIDDEN**: hardcode `Dispatchers.IO`/`Default` trong `commonMain` của `{{MODULE_DOMAIN}}`/`{{MODULE_PRESENTER}}` — không test deterministic được.

### Step 6 — Testing

```kotlin
@Test
fun `search debounces input`() = runTest {
    val useCase = FakeSearchUseCase()
    val vm = SearchViewModel(useCase, StandardTestDispatcher(testScheduler))

    vm.onIntent(Search("ha"))
    advanceTimeBy(100)
    vm.onIntent(Search("harry"))
    advanceTimeBy(400)
    runCurrent()

    assertEquals(listOf("harry"), useCase.queries)
}
```

`advanceTimeBy` + `runCurrent` thay vì `delay` thực. Test chạy < 100ms.

## Required policies

- CORO-001..010 (từ `concurrency-rules.md`)
- KOT-002 null safety
- KOT-009 exception handling

## Common patterns

### Parallel independent requests

```kotlin
suspend fun loadDetail(id: String): Detail = supervisorScope {
    val main = async { mainRepo.get(id) }
    val extra1 = async { extraRepo1.get(id) }
    val extra2 = async { extraRepo2.get(id) }
    Detail(
        main = main.await(),
        extras = listOf(extra1.await().getOrNull(), extra2.await().getOrNull())
    )
}
```

### Search typeahead

```kotlin
val query = MutableStateFlow("")
val results: StateFlow<List<Item>> = query
    .debounce(300)
    .filter { it.length >= 2 }
    .distinctUntilChanged()
    .flatMapLatest { q ->
        flow {
            emit(SearchState.Loading)
            emit(SearchState.Success(repo.search(q)))
        }.catch { e ->
            if (e is CancellationException) throw e
            emit(SearchState.Error(e.toUiText()))
        }
    }
    .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), initial)
```

### Retry with exponential backoff

```kotlin
suspend fun <T> retryExponential(
    maxAttempts: Int = 3,
    initialDelayMs: Long = 500,
    factor: Double = 2.0,
    block: suspend () -> T,
): T {
    var delay = initialDelayMs
    repeat(maxAttempts - 1) {
        try { return block() }
        catch (e: CancellationException) { throw e }
        catch (e: IOException) {
            delay(delay)
            delay = (delay * factor).toLong()
        }
    }
    return block()  // last attempt propagates exception
}
```

### Shared cold flow

```kotlin
val user: StateFlow<User?> = authRepo.observeUser()
    .stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = null,
    )
```

## Common mistakes

| Mistake | Fix |
|---|---|
| `GlobalScope.launch` | Inject scope hoặc dùng `viewModelScope` |
| `flatMap` cho search → không cancel previous | `flatMapLatest` |
| Catch `Exception` nuốt cancellation | Re-throw `CancellationException` |
| `delay()` thực trong test | `advanceTimeBy()` + `TestDispatcher` |
| 2 request parallel coroutineScope → 1 fail hủy cả | `supervisorScope { async; async }` |
| Expose `MutableStateFlow` public | `.asStateFlow()` |
| Hard-coded `Dispatchers.IO` common | Inject qua constructor |
| `collectAsState()` Compose | `collectAsStateWithLifecycle()` |
| `runBlocking` production | `suspend` + launch trong scope đúng |

## Output contract

- Code pass Konsist `CORO-001` (no GlobalScope)
- Dispatcher inject được, test deterministic với `TestDispatcher`
- Flow operator pipeline rõ intent, không chain quá 6 operators không comment
- Error path cover: network, server, cancellation, timeout
- Test ≥ 2 scenarios: happy path + 1 edge (cancellation hoặc error)

## Anti-patterns bị cấm

- `GlobalScope.launch` production
- `runBlocking` ngoài test setup
- `delay()` thực trong unit test
- Catch broader than needed không re-throw Cancellation
- Flow collect raw không `collectAsStateWithLifecycle()`
- Shared mutable state không `Mutex`/atomic/`update { }`

---

## Harness context

- Workflow: `workflows/feature-development.md`
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`


## Overlay gate (D-full)

Trước Step 1, verify `.harness-overlay/overlay.yaml` tồn tại. Nếu không, abort với status `BLOCKED` và chỉ dẫn user:

> Chưa có overlay. Chạy skill `harness-init` để scaffold trước, sau đó quay lại skill này.

Khi gặp placeholder `{{X}}` trong procedure/code example, resolve bằng mapping ở `AGENTS.md §Placeholder resolution` (Read overlay 1 lần đầu session, cache qua context).
