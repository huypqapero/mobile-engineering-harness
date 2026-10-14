# E03 — Concurrency: Search Debounce + Cancel Previous

## Scenario

Yêu cầu agent implement search với 3 behavior critical:
1. Debounce 300ms user input
2. Cancel previous request khi user tiếp tục gõ
3. Preserve cancellation, không catch-all nuốt lỗi

## Prompt mẫu

> Implement `SearchViewModel` cho {{PRODUCT_NAME}}: user gõ query ở TextField, hiển thị kết quả. Debounce 300ms, cancel previous request khi query mới. Follow `.harness/constitution/concurrency-rules.md` và `.harness/skills/android-mvi/SKILL.md`.

## Expected implementation

```kotlin
internal class SearchViewModel(
    private val search: SearchBooksUseCase,
    dispatcher: CoroutineDispatcher = Dispatchers.Default,
) : BaseViewModel<SearchState, SearchIntent, SearchEffect>(initial = SearchState()) {

    private val queryFlow = MutableStateFlow("")

    init {
        queryFlow
            .debounce(300)
            .filter { it.length >= 2 }
            .distinctUntilChanged()
            .flatMapLatest { q ->                               // ← cancel previous
                flow {
                    emit(SearchState(query = q, isLoading = true))
                    when (val result = search(q)) {
                        is ApiResult.Success -> emit(SearchState(query = q, results = result.data))
                        is ApiResult.Error -> emit(SearchState(query = q, error = result.cause.toUiText()))
                    }
                }.catch { e ->
                    if (e is CancellationException) throw e   // ← preserve cancellation
                    emit(SearchState(error = UiText.Raw(e.message ?: "")))
                }
            }
            .onEach { newState -> updateState { newState } }
            .launchIn(viewModelScope)
    }

    override fun onIntent(intent: SearchIntent) {
        when (intent) {
            is SearchIntent.QueryChanged -> queryFlow.value = intent.text
            SearchIntent.Clear -> queryFlow.value = ""
        }
    }
}
```

## Must-have test

```kotlin
@Test
fun `rapid typing cancels previous and only final query runs`() = runTest {
    val useCase = FakeSearchUseCase(delayMs = 100)
    val vm = SearchViewModel(useCase, testDispatcher)

    vm.onIntent(SearchIntent.QueryChanged("ha"))
    advanceTimeBy(100)
    vm.onIntent(SearchIntent.QueryChanged("har"))
    advanceTimeBy(100)
    vm.onIntent(SearchIntent.QueryChanged("harry"))
    advanceTimeBy(400) // > debounce window
    runCurrent()

    assertEquals(listOf("harry"), useCase.calledWith)
}

@Test
fun `cancellation preserved`() = runTest {
    val useCase = FakeSearchUseCase(delayMs = 500)
    val vm = SearchViewModel(useCase, testDispatcher)

    vm.onIntent(SearchIntent.QueryChanged("foo"))
    advanceTimeBy(400)
    vm.onIntent(SearchIntent.QueryChanged("bar"))
    advanceTimeBy(400)
    runCurrent()

    // "foo" call should have been cancelled before completing
    assertTrue(useCase.cancelledQueries.contains("foo"))
}
```

## Evaluation checklist

| # | Check | Weight |
|---|---|---|
| 1 | Dùng `flatMapLatest` (không `flatMap`, `flatMapConcat`) | 20% |
| 2 | `debounce(300)` ở upstream | 10% |
| 3 | `distinctUntilChanged()` | 5% |
| 4 | `CancellationException` re-throw trong catch | 20% |
| 5 | `viewModelScope.launchIn` không `GlobalScope` | 10% |
| 6 | `MutableStateFlow` cho query NHƯNG `_state` không expose mutable | 10% |
| 7 | Dispatcher inject constructor | 10% |
| 8 | Test deterministic (TestDispatcher + advanceTimeBy, không delay thật) | 15% |

## Common failure modes

1. `flatMap` thay vì `flatMapLatest` → không cancel previous
2. `try { } catch (e: Exception) { }` không re-throw cancellation
3. `GlobalScope` cho search
4. `delay(300)` thay vì `debounce(300)` (manual delay không hoạt động với rapid input)
5. Test dùng `delay()` thật → chạy chậm, flaky
6. Không filter `length >= 2` → search string rỗng
7. Expose `MutableStateFlow` ra ngoài

## Scoring

- 90–100: VERIFIED
- 75–89: VERIFIED_WITH_LIMITATIONS
- < 75: FAIL — concurrency hazard rõ, không ship được
