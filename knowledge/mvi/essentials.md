# MVI Essentials — {{PRODUCT_NAME}} pattern

## Overview

MVI = Model-View-Intent. 1 chiều: UI phát `Intent` → ViewModel reduce → emit `State` + optional `Effect` → UI render + consume effect.

{{PRODUCT_NAME}} dùng `BaseViewModel<S : UiState, I : UiIntent, E : UiEffect>` tự viết, ở `presenter/core/mvi/`.

## 3 contract chuẩn

```kotlin
// MviContracts.kt
interface UiState
interface UiIntent
interface UiEffect
```

Mỗi feature định nghĩa triple tương ứng ở `feature/<name>/<Feature>Contract.kt`.

## BaseViewModel pattern

```kotlin
abstract class BaseViewModel<S : UiState, I : UiIntent, E : UiEffect>(
    initial: S,
) : ViewModel() {

    private val _state = MutableStateFlow(initial)
    val state: StateFlow<S> = _state.asStateFlow()

    private val _effect = Channel<E>(capacity = Channel.BUFFERED)
    val effect: Flow<E> = _effect.receiveAsFlow()

    protected fun updateState(reducer: (S) -> S) {
        _state.update(reducer)
    }

    protected fun emitEffect(effect: E) {
        viewModelScope.launch { _effect.send(effect) }
    }

    abstract fun onIntent(intent: I)
}
```

Project đã có file này. Khi tạo ViewModel mới, extend `BaseViewModel`, override `onIntent`.

## State modeling patterns

### Pattern 1: Single data class (ưu tiên)

Khi screen render luôn render cùng shape, khác field value.

```kotlin
data class BookDetailState(
    val isLoading: Boolean = false,
    val book: Book? = null,
    val isOffline: Boolean = false,
    val error: UiText? = null,
    val isBookmarked: Boolean = false,
    val isDownloaded: Boolean = false,
) {
    val isEmpty: Boolean get() = book == null && !isLoading && error == null
}
```

### Pattern 2: Sealed interface

Khi state branches render UI hoàn toàn khác.

```kotlin
sealed interface AuthState : UiState {
    data object SignedOut : AuthState
    data object Loading : AuthState
    data class SignedIn(val user: User) : AuthState
    data class Error(val cause: AuthError) : AuthState
}
```

**Chọn Pattern 1** cho screen có data load (Home, Detail, Library, Search, …).
**Chọn Pattern 2** cho screen có luồng trạng thái mutex (Auth, LFO, Paywall).

## Intent design

```kotlin
sealed interface HomeIntent : UiIntent {
    // User intents
    data object Load : HomeIntent
    data object Refresh : HomeIntent
    data class SelectBook(val id: String) : HomeIntent
    data class ToggleBookmark(val id: String) : HomeIntent

    // Internal intents (optional, khi muốn modeled)
    data class BookmarkToggled(val id: String, val result: Result<Unit>) : HomeIntent
}
```

### Khi nào dùng internal intent

- Khi reducer cần modeling kết quả async thành transition rõ (ví dụ `BookmarkToggled` branch success/fail)
- Khi muốn test state transition deterministic qua intent sequence

### Khi KHÔNG cần internal intent

- Khi async handling đơn giản, update state trực tiếp từ `viewModelScope.launch` ok

## Effect vs State

| Loại | Thuộc |
|---|---|
| "Current selected tab" | **State** — persistent, re-render khi recompose |
| "Show toast" | **Effect** — 1-time, không persistent |
| "Navigate to detail" | **Effect** |
| "Error message current" | **State** nếu persistent trong UI (banner), **Effect** nếu toast transient |
| "Form field value" | **State** |

**Rule**: nếu config change (rotate) rồi state cần retain → đó là **State**. Nếu không → **Effect**.

## Reducer vs direct update

{{PRODUCT_NAME}} dùng `_state.update { it.copy(...) }` thay vì reducer function tách rời. Lý do: feature nhỏ, không cần reducer tách; khi logic complex (>10 transition) có thể extract thành pure function:

```kotlin
// Simple — inline update
updateState { it.copy(isLoading = true) }

// Complex — pure reducer function (optional)
private fun reduce(current: BookDetailState, event: Event): BookDetailState = when (event) {
    is Event.Loaded -> current.copy(isLoading = false, book = event.book)
    is Event.LoadFailed -> current.copy(isLoading = false, error = event.cause.toUiText())
    ...
}
updateState { reduce(it, event) }
```

## Side-effect dispatch

```kotlin
override fun onIntent(intent: HomeIntent) {
    when (intent) {
        is HomeIntent.SelectBook -> emitEffect(HomeEffect.NavigateToDetail(intent.id))
        HomeIntent.Load -> loadFeed()
    }
}
```

Effect consume ở Composable qua `EffectHandler` (xem `knowledge/compose/essentials.md`).

## Navigation là State hay Effect?

**Effect** mặc định — single-shot, không muốn re-navigate khi config change.

Exception: nếu muốn deep-link survive process death → encode trong `SavedStateHandle` qua Navigation args, không trong state.

## One-time events — pattern cho {{PRODUCT_NAME}}

Dùng `Channel<Effect>(BUFFERED)` + `receiveAsFlow()`:
- Đảm bảo delivery (không miss khi screen chưa collect)
- Không replay cho lifecycle restart (unlike `SharedFlow(replay=1)`)

**FORBIDDEN**: `MutableSharedFlow(replay=1)` cho navigation — gây navigate 2 lần khi rotate.

## State restoration

```kotlin
class BookDetailViewModel(
    savedStateHandle: SavedStateHandle,
    private val repo: BookRepository,
) : BaseViewModel<BookDetailState, _, _>(initial = ...) {
    private val bookId: String = savedStateHandle.get<String>("bookId")!!
}
```

Nav args pass qua `SavedStateHandle` (androidx.navigation CMP support). Transient UI state (scroll pos, expanded card) không cần restore trừ khi UX yêu cầu.

## Testing MVI

```kotlin
@Test
fun `load emits loading then success`() = runTest {
    val useCase = FakeGetHomeFeedUseCase(
        result = ApiResult.Success(fakeRails)
    )
    val vm = HomeViewModel(useCase)

    vm.state.test {
        assertEquals(HomeState(), awaitItem())
        vm.onIntent(HomeIntent.Load)
        assertEquals(HomeState(isLoading = true), awaitItem())
        assertEquals(HomeState(rails = fakeRails), awaitItem())
    }
}
```

Dùng `turbine` cho Flow assertions. `runTest` cho suspend + coroutine time control.

## Common mistakes

| Mistake | Fix |
|---|---|
| Effect dùng cho persistent UI concern | Chuyển sang State |
| State dùng cho navigation → re-nav khi rotate | Dùng Effect + Channel |
| `MutableStateFlow` public | `.asStateFlow()` |
| Reducer side-effect (log, nav) | Reducer phải pure, side-effect ở launch block |
| Intent chỉ 1 case `Load` quá rộng | Split per action |

## References

- `presenter/core/mvi/BaseViewModel.kt`
- `presenter/core/mvi/MviContracts.kt`
- Project `docs/architecture.md §5.1 MVI`
- [Android UI events guidance](https://developer.android.com/topic/architecture/ui-layer/events)
