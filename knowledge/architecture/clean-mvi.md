# Clean Architecture + MVI trong {{PRODUCT_NAME}}

## Overview

Clean Architecture + MVI đóng vai nền tảng tổ chức code. Clean Architecture tách layers (presentation / domain / data), đảm bảo business rules độc lập platform. MVI mô hình hóa UI theo 1 chiều: Intent → reducer → State + Effect.

## Layer model

```
composeApp (entry)
    ↓
presenter (UI + MVI + Nav)
    ↓
domain (models, UseCase, Repo interface)
    ↑
data (Repo impl, DTO, SDK, mapper)
```

### Trách nhiệm

| Layer | Trách nhiệm | Cấm |
|---|---|---|
| composeApp | Entry Android/iOS, Koin init, platform wire | business logic |
| presenter | UI Composable, ViewModel, Nav, Theme | gọi data direct, chứa domain model impl |
| domain | business model, UseCase, Repository interface | import Android/iOS/Firebase |
| data | DTO, DataSource, mapper, Repository impl | expose DTO ra ngoài module |

## When to use what

### Dùng UseCase

- Business logic cần orchestrate 2+ nguồn (ví dụ `GetBookDetailUseCase` combine `BookRepository` + `HistoryRepository`)
- Transform business meaningful (ví dụ compute "progress %" từ `playbackPosition` + `durationMs`)
- Operation có validation/precondition (ví dụ `AddToCollectionUseCase` check entitlement trước)
- Reusable giữa 2+ ViewModel

### KHÔNG cần UseCase

- Operation 1-1 với repository method không transform (ví dụ `repo.observeHistory()`)
- Delegation thuần không giá trị thêm
- "Clean Arch bảo tạo UseCase cho tất cả" — sai, Google guide xem domain layer là optional

Trong case này, ViewModel inject `Repository` interface từ `domain/`, gọi trực tiếp. Rule ARCH-003 cho phép, chỉ cấm gọi `*RepositoryImpl`.

## When NOT to use

- Không tạo interface cho mỗi class — chỉ interface khi có 2+ impl hoặc test cần fake
- Không tạo mapper nếu DTO = Domain model identical (data class shape giống)
- Không tạo module riêng cho feature nhỏ — package trong `presenter/` ok cho giai đoạn app

## MVI contract

```kotlin
// contract/HomeContract.kt
sealed interface HomeIntent {
    data object Load : HomeIntent
    data class SelectBook(val id: String) : HomeIntent
    data object Refresh : HomeIntent
}

data class HomeState(
    val isLoading: Boolean = false,
    val isOffline: Boolean = false,
    val error: UiText? = null,
    val rails: List<Rail> = emptyList(),
) {
    val isEmpty: Boolean get() = rails.isEmpty() && !isLoading && error == null
}

sealed interface HomeEffect {
    data class NavigateToDetail(val bookId: String) : HomeEffect
    data class ShowToast(val text: UiText) : HomeEffect
}
```

```kotlin
// HomeViewModel.kt
class HomeViewModel(
    private val getHomeFeed: GetHomeFeedUseCase,
) : BaseViewModel<HomeState, HomeIntent, HomeEffect>(initial = HomeState()) {

    override fun onIntent(intent: HomeIntent) {
        when (intent) {
            HomeIntent.Load -> loadFeed()
            is HomeIntent.SelectBook -> emitEffect(HomeEffect.NavigateToDetail(intent.id))
            HomeIntent.Refresh -> loadFeed(refresh = true)
        }
    }

    private fun loadFeed(refresh: Boolean = false) {
        viewModelScope.launch {
            updateState { it.copy(isLoading = true, error = null) }
            when (val result = getHomeFeed(refresh)) {
                is ApiResult.Success -> updateState {
                    it.copy(isLoading = false, rails = result.data)
                }
                is ApiResult.Error -> updateState {
                    it.copy(isLoading = false, error = result.toUiText())
                }
            }
        }
    }
}
```

## State modeling guide

**Dùng data class** khi UI render luôn render cùng cấu trúc, chỉ khác field value (loading flag, data, error flag):

```kotlin
data class HomeState(val isLoading, val error, val data)
```

**Dùng sealed interface** khi mỗi "trạng thái" render UI hoàn toàn khác nhau:

```kotlin
sealed interface AuthState {
    data object SignedOut : AuthState
    data object Loading : AuthState
    data class SignedIn(val user: User) : AuthState
    data class Error(val cause: AuthError) : AuthState
}
```

Trong {{PRODUCT_NAME}}, screen có data load → **data class pattern** tiêu chuẩn vì có 5 states (loading / empty / error / offline / success) có thể combine.

## Common mistakes

- Tạo UseCase trivial 1-1 → bỏ, gọi repo interface direct
- Expose `BookDto` qua `BookRepository` interface → map ở data, trả `Book` domain
- `isLoading` vừa đại diện initial load vừa refresh → tách `isLoading` + `isRefreshing`
- Effect dùng cho state (ví dụ "selected tab") → đó là state, không phải effect

## Verification checklist

- [ ] domain không import Android/iOS → ARCH-001
- [ ] presenter không import data → ARCH-002
- [ ] ViewModel chỉ dùng UseCase/Repository interface → ARCH-003
- [ ] UiState immutable `data class` hoặc `sealed interface` → ARCH-007
- [ ] 5 states coverage ở screen remote data → ARCH-008

## References

- Google: [Guide to app architecture](https://developer.android.com/topic/architecture)
- Google: [UI layer](https://developer.android.com/topic/architecture/ui-layer)
- `docs/architecture.md` project
- `presenter/core/mvi/BaseViewModel.kt` + `MviContracts.kt`
