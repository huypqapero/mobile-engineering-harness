# Concurrency Rules

Coroutines + Flow trong Compose Multiplatform. Áp dụng cho `commonMain` + platform-specific.

## CORO-001 — Scope ownership rõ ràng

- **Severity**: MUST
- **Rule**: Mỗi coroutine thuộc đúng 1 scope có lifecycle quản được.
- **Allowed scopes**:
  - `viewModelScope` — tác vụ gắn ViewModel
  - `CoroutineScope(SupervisorJob() + ioDispatcher)` injected cho Repository stateful
  - `rememberCoroutineScope()` trong Composable — chỉ cho side-effect liên quan UI event
  - `LaunchedEffect(key)` — side-effect gắn composition
- **FORBIDDEN**: `GlobalScope`, `MainScope()` tự tạo trong feature code, scope detached không có owner

## CORO-002 — Dispatcher selection

- **Severity**: MUST
- **Rules**:
  - IO blocking (file, network, DB): `withContext(ioDispatcher)` ở `BaseRepository`
  - CPU-bound (parse lớn, mapping heavy): `withContext(defaultDispatcher)`
  - UI update: Compose state đã thread-safe, không cần `Main` explicit
- **FORBIDDEN**: hardcode `Dispatchers.IO` trong `commonMain` của `domain/presenter` (phải inject qua interface để test được)

## CORO-003 — Structured concurrency

- **Severity**: MUST
- **Rule**: Khởi tạo coroutine con qua `coroutineScope { }` hoặc `supervisorScope { }`, không `launch` detached từ scope cha.
- **supervisorScope** khi tác vụ con độc lập, 1 fail không hủy anh em
- **coroutineScope** khi tác vụ con phải đồng bộ fail/thành công cùng cha
- **Verification**: review manual + eval `E04`

## CORO-004 — Cancellation preservation

- **Severity**: MUST
- **Rule**: `CancellationException` phải propagate; không catch-all nuốt cancellation.
- **Pattern**:
  ```kotlin
  try { ... } catch (e: CancellationException) { throw e }
  catch (e: Exception) { ... }
  ```
- **Verification**: Detekt custom rule `SwallowCancellationException`
- **FORBIDDEN**: `catch (e: Throwable) { log(e) }` khối rộng
- **FORBIDDEN**: `runCatching { ... }` ở nơi có `CancellationException` khả thi mà không re-throw

## CORO-005 — StateFlow vs SharedFlow vs Channel

- **Severity**: MUST
- **Rules**:
  - `StateFlow<UiState>`: trạng thái hiện tại có initial value, dùng cho UI state (reducer output)
  - `SharedFlow<UiEffect>` với `replay=0, extraBufferCapacity=1, onBufferOverflow=DROP_OLDEST`: effect broadcasting (nav, toast)
  - `Channel<T>(Channel.BUFFERED)`: 1-time event guaranteed-delivery (critical nav)
  - `Flow`: stream cold
- **FORBIDDEN**: expose `MutableStateFlow` / `MutableSharedFlow` public (dùng `.asStateFlow()`, `.asSharedFlow()`)

## CORO-006 — Collection lifecycle

- **Severity**: MUST
- **Rule**: Compose collect qua `collectAsStateWithLifecycle()` (androidx.lifecycle.compose), KHÔNG `collectAsState()` raw.
- **Verification**: Detekt custom rule `PreferLifecycleAwareCollect`

## CORO-007 — Flow operator ownership

- **Severity**: SHOULD
- **Rules**:
  - `stateIn(scope, SharingStarted.WhileSubscribed(5000), initial)` khi shared upstream
  - `shareIn` khi cần hot share không cần state
  - `distinctUntilChanged()` cho upstream phát trùng
  - `debounce(ms)` cho user input (search)
  - `flatMapLatest` khi cancel previous là mong muốn (search typeahead)
  - `conflate()` khi downstream chậm, chỉ cần giá trị mới nhất

## CORO-008 — Timeout + retry

- **Severity**: SHOULD
- **Pattern**:
  ```kotlin
  withTimeout(10_000) {
      retry(maxAttempts = 3, delayMillis = { attempt -> 500L * (1 shl attempt) }) {
          api.call()
      }
  }
  ```
- Không retry mù cho error 4xx client

## CORO-009 — Thread-safe shared mutable state

- **Severity**: MUST
- **Rule**: Mutex, atomic, `MutableStateFlow.update { }` cho shared state đồng thời đọc/ghi.
- **FORBIDDEN**: `var` + `synchronized(this)` trong coroutine (preferable là `Mutex` suspend).

## CORO-010 — Test coroutines với runTest

- **Severity**: MUST (khi test có coroutine)
- **Pattern**:
  ```kotlin
  @Test
  fun `search debounces`() = runTest {
      val vm = HomeViewModel(useCase, testDispatcher)
      vm.onIntent(Search("ha"))
      advanceTimeBy(100)
      vm.onIntent(Search("harry"))
      advanceTimeBy(500)
      coVerify(exactly = 1) { useCase("harry") }
  }
  ```
- Dispatcher phải inject được, không hardcode

## Common pitfalls (anti-patterns)

| Pitfall | Fix |
|---|---|
| `GlobalScope.launch` cho background work | Inject scope qua constructor |
| `collectAsState()` không lifecycle-aware | `collectAsStateWithLifecycle()` |
| `runBlocking` trong production code | Dùng suspend fn + `viewModelScope.launch` |
| Catch `Exception` không re-throw `CancellationException` | Catch cụ thể hoặc re-throw |
| 2 request parallel không `supervisorScope` → 1 fail hủy cả | Dùng `supervisorScope { async; async }` |
| State race do emit raw thay vì `update { }` | `_state.update { it.copy(...) }` |
