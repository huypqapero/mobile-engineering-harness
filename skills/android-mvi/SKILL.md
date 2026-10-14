---
name: android-mvi
description: Thiết kế hoặc refactor UiState / UiIntent / UiEffect contract, reducer, side-effect, navigation policy cho ViewModel. Trigger khi tạo mới ViewModel, add state branch, hoặc fix state management bug.
priority: P0
---

# Skill: android-mvi

## Trigger

- Tạo ViewModel + contract mới
- Add intent / state branch
- Refactor state management phức tạp
- Fix bug state race, event lost, event duplicate khi rotate

## Inputs

- Feature requirement
- User interactions list → map ra intents
- Visible UI states → map ra state field hoặc sealed branch
- Side-effect types: navigation, toast, dialog, system call

## Prerequisites

1. `.harness/knowledge/mvi/essentials.md`
2. `presenter/core/mvi/BaseViewModel.kt` + `MviContracts.kt`
3. Project `docs/architecture.md §5.1 MVI`

## Execution procedure

### Step 1 — List interactions

Viết ra:

```
User tap book card           → navigate detail
User pull to refresh         → re-fetch feed
User tap bookmark icon       → toggle bookmark + optimistic update
User tap "retry" khi error   → re-fetch
User scroll bottom           → load more (nếu paginated)
Network reconnect            → auto re-fetch
```

### Step 2 — Design Intent sealed interface

```kotlin
sealed interface HomeIntent : UiIntent {
    data object Load : HomeIntent
    data object Refresh : HomeIntent
    data object LoadMore : HomeIntent
    data class SelectBook(val id: String) : HomeIntent
    data class ToggleBookmark(val id: String) : HomeIntent

    // Internal — khi cần modeled state transition
    data class BookmarkResult(val id: String, val success: Boolean) : HomeIntent
}
```

**Rule**: 1 user action = 1 intent. Không bundle nhiều action vào 1 intent với enum "type".

### Step 3 — Design State

**Decision tree:**

- Screen render luôn render cùng shape? → **data class**
- Screen có branches render UI khác nhau mutex? → **sealed interface**

```kotlin
// data class pattern (phổ biến)
data class HomeState(
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val isOffline: Boolean = false,
    val error: UiText? = null,
    val rails: List<Rail> = emptyList(),
    val hasMore: Boolean = true,
) : UiState
```

**Rules:**
- Tách `isLoading` (initial) vs `isRefreshing` (pull-to-refresh)
- Field `error: UiText?` — nullable, không `errorMessage: String = ""` ambiguous
- Nested state collection → `List<Item>` immutable
- Derived values → extension property, không stored

### Step 4 — Design Effect

```kotlin
sealed interface HomeEffect : UiEffect {
    data class NavigateToDetail(val bookId: String) : HomeEffect
    data class ShowToast(val text: UiText) : HomeEffect
    data object ShowBookmarkedSnackbar : HomeEffect
}
```

**Rule**: Effect chỉ cho 1-time event. "Current selected tab" = **State**, không Effect.

### Step 5 — Implement ViewModel

```kotlin
class HomeViewModel(
    private val getHomeFeed: GetHomeFeedUseCase,
    private val toggleBookmark: ToggleBookmarkUseCase,
    private val dispatcher: CoroutineDispatcher = Dispatchers.Default,
) : BaseViewModel<HomeState, HomeIntent, HomeEffect>(initial = HomeState()) {

    init { onIntent(HomeIntent.Load) }

    override fun onIntent(intent: HomeIntent) {
        when (intent) {
            HomeIntent.Load -> loadFeed(initial = true)
            HomeIntent.Refresh -> loadFeed(initial = false)
            HomeIntent.LoadMore -> loadMore()
            is HomeIntent.SelectBook -> emitEffect(HomeEffect.NavigateToDetail(intent.id))
            is HomeIntent.ToggleBookmark -> handleBookmark(intent.id)
            is HomeIntent.BookmarkResult -> handleBookmarkResult(intent)
        }
    }

    private fun loadFeed(initial: Boolean) {
        viewModelScope.launch {
            updateState {
                it.copy(
                    isLoading = initial,
                    isRefreshing = !initial,
                    error = null,
                )
            }
            when (val result = getHomeFeed()) {
                is ApiResult.Success -> updateState {
                    it.copy(
                        isLoading = false,
                        isRefreshing = false,
                        rails = result.data,
                        isOffline = false,
                    )
                }
                is ApiResult.Error -> updateState {
                    it.copy(
                        isLoading = false,
                        isRefreshing = false,
                        error = result.cause.toUiText(),
                        isOffline = result.cause is DomainError.Network,
                    )
                }
            }
        }
    }

    private fun handleBookmark(id: String) {
        viewModelScope.launch {
            // Optimistic update
            updateState { it.copy(rails = it.rails.toggleBookmark(id)) }
            val result = toggleBookmark(id)
            onIntent(HomeIntent.BookmarkResult(id, result is ApiResult.Success))
        }
    }

    private fun handleBookmarkResult(intent: HomeIntent.BookmarkResult) {
        if (!intent.success) {
            // Revert
            updateState { it.copy(rails = it.rails.toggleBookmark(intent.id)) }
            emitEffect(HomeEffect.ShowToast(UiText.StringResId(Res.string.bookmark_failed)))
        } else {
            emitEffect(HomeEffect.ShowBookmarkedSnackbar)
        }
    }
}
```

### Step 6 — Test state transitions

```kotlin
@Test
fun `load emits loading then success`() = runTest {
    val useCase = FakeGetHomeFeedUseCase(ApiResult.Success(fakeRails))
    val vm = HomeViewModel(useCase, FakeToggleBookmark())

    vm.state.test {
        awaitItem() // initial
        awaitItem().also { assertTrue(it.isLoading) }
        awaitItem().also {
            assertFalse(it.isLoading)
            assertEquals(fakeRails, it.rails)
        }
    }
}
```

## Required policies

- ARCH-007 MVI 1-chiều
- ARCH-008 5 states coverage
- CORO-001 scope ownership (viewModelScope)
- CORO-004 cancellation preservation
- CORO-005 StateFlow / Channel đúng chỗ

## Decision guides

### Internal intent hay inline update

**Dùng internal intent** khi:
- Logic branch success/fail cần modeled rõ
- Test state transition qua intent sequence muốn deterministic
- 2+ async operations cùng chạy, kết quả cần merge

**Inline update** khi:
- Logic 1-step, không branching phức tạp
- Only 1 async operation

### Reducer function tách rời

Khi `onIntent` > 150 dòng → extract pure reducer function:

```kotlin
private fun reduce(state: HomeState, event: Event): HomeState = when (event) {
    is Event.Loaded -> state.copy(...)
    is Event.LoadFailed -> state.copy(...)
    ...
}
```

Reducer phải PURE — không side effect, không coroutine, không log.

### Optimistic update

- UI update ngay khi intent → user cảm nhận instant
- Async call thực hiện background
- Fail → revert state + emit effect toast

## Common mistakes

| Mistake | Fix |
|---|---|
| Expose `MutableStateFlow` | `.asStateFlow()` |
| Expose `MutableSharedFlow` cho effect | Dùng `Channel` + `receiveAsFlow()` |
| Nav là State → navigate 2 lần khi rotate | Nav là Effect |
| State dirty read trong launch | `updateState { it.copy(...) }` atomic |
| Intent "generic" `data class UserAction(val type: Type)` | 1 action = 1 intent sealed |
| `init { loadFeed() }` không expose intent | Expose qua `init { onIntent(Load) }` để test được |
| Mix `delay` + `runBlocking` → test non-deterministic | Inject TestDispatcher |

## Output contract

- Contract file (`<Feature>Contract.kt`) với 3 sealed interface
- ViewModel extend `BaseViewModel`
- Unit test ít nhất 3 scenarios: happy path, error, edge case
- State transition deterministic qua intent

## Validation

- [ ] 1 user action = 1 intent, không bundle
- [ ] State immutable `data class` hoặc `sealed interface`
- [ ] Effect chỉ 1-time event
- [ ] Nav là Effect, không State
- [ ] Mutable state không expose
- [ ] viewModelScope cho mọi async
- [ ] Cancellation preserved

## Anti-patterns

- Expose mutable collection
- Reducer có side-effect (log, nav, I/O)
- Intent "god" bundle nhiều action
- State modeling cho field không bao giờ visible
- `init { }` làm business work mà không expose qua Intent (hard to test)
