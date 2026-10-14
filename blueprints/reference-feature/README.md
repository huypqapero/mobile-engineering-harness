# Blueprint: Reference Feature (Generic ItemCatalog)

Generic golden reference cho implement feature end-to-end. Fallback khi overlay chưa trỏ `reference_blueprint` tới feature live trong product.

**Example feature** (fictional, neutral): `ItemCatalog` — screen hiển thị list item, load từ API, cho favorite + navigate detail.

> **Lưu ý**: Code mẫu dùng placeholder `{{PACKAGE_ROOT}}`, `{{MODULE_PRESENTER}}`... Trong product overlay, placeholder sẽ resolve qua `install.sh` hoặc agent đọc `overlay.yaml`.

## 1. Package layout

```
{{MODULE_PRESENTER}}/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/{{MODULE_PRESENTER}}/{{FEATURES_ROOT}}/itemcatalog/
├── ItemCatalogApi.kt
├── ItemCatalogScreen.kt
├── ItemCatalogViewModel.kt
├── ItemCatalogContract.kt
└── components/ItemRow.kt

{{MODULE_DOMAIN}}/src/commonMain/kotlin/.../model/catalog/Item.kt
{{MODULE_DOMAIN}}/src/commonMain/kotlin/.../usecase/catalog/GetItemsUseCase.kt
{{MODULE_DOMAIN}}/src/commonMain/kotlin/.../repository/CatalogRepository.kt

{{MODULE_DATA}}/src/commonMain/kotlin/.../dto/ItemDto.kt
{{MODULE_DATA}}/src/commonMain/kotlin/.../mapper/CatalogMapper.kt
{{MODULE_DATA}}/src/commonMain/kotlin/.../remote/CatalogApi.kt
{{MODULE_DATA}}/src/commonMain/kotlin/.../repository/CatalogRepositoryImpl.kt
```

## 2. Public API

```kotlin
@Composable
fun ItemCatalogRoute(onBack: () -> Unit, onNavigate: (NavRoute) -> Unit) {
    ItemCatalogScreen(onBack = onBack, onNavigate = onNavigate)
}
```

Public surface tối thiểu — khi extract SDK, chỉ expose `ItemCatalogRoute`, các class khác `internal`.

## 3. Contract

```kotlin
internal data class ItemCatalogState(
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val isOffline: Boolean = false,
    val error: UiText? = null,
    val items: List<Item> = emptyList(),
) : UiState

internal sealed interface ItemCatalogIntent : UiIntent {
    data object Load : ItemCatalogIntent
    data object Refresh : ItemCatalogIntent
    data object Retry : ItemCatalogIntent
    data class SelectItem(val id: String) : ItemCatalogIntent
    data class ToggleFavorite(val id: String) : ItemCatalogIntent
    data object Back : ItemCatalogIntent
    data class FavoriteResult(val id: String, val success: Boolean) : ItemCatalogIntent
}

internal sealed interface ItemCatalogEffect : UiEffect {
    data object NavigateBack : ItemCatalogEffect
    data class NavigateToDetail(val id: String) : ItemCatalogEffect
    data class ShowToast(val text: UiText) : ItemCatalogEffect
}
```

## 4. ViewModel

```kotlin
internal class ItemCatalogViewModel(
    private val getItems: GetItemsUseCase,
    private val toggleFavorite: ToggleFavoriteUseCase,
) : {{MVI_BASE_CLASS}}<ItemCatalogState, ItemCatalogIntent, ItemCatalogEffect>(
    initial = ItemCatalogState(),
) {
    init { onIntent(ItemCatalogIntent.Load) }

    override fun onIntent(intent: ItemCatalogIntent) {
        when (intent) {
            ItemCatalogIntent.Load, ItemCatalogIntent.Retry -> loadItems()
            ItemCatalogIntent.Refresh -> loadItems(refresh = true)
            is ItemCatalogIntent.SelectItem -> emitEffect(ItemCatalogEffect.NavigateToDetail(intent.id))
            is ItemCatalogIntent.ToggleFavorite -> handleFavorite(intent.id)
            ItemCatalogIntent.Back -> emitEffect(ItemCatalogEffect.NavigateBack)
            is ItemCatalogIntent.FavoriteResult -> handleFavoriteResult(intent)
        }
    }

    private fun loadItems(refresh: Boolean = false) {
        viewModelScope.launch {
            updateState { it.copy(isLoading = !refresh && it.items.isEmpty(), isRefreshing = refresh, error = null) }
            when (val result = getItems()) {
                is ApiResult.Success -> updateState {
                    it.copy(isLoading = false, isRefreshing = false, isOffline = false, items = result.data)
                }
                is ApiResult.Error -> updateState {
                    it.copy(
                        isLoading = false,
                        isRefreshing = false,
                        isOffline = result.cause is DomainError.Network,
                        error = result.cause.toUiText(),
                    )
                }
            }
        }
    }

    private fun handleFavorite(id: String) {
        val prev = state.value.items.firstOrNull { it.id == id }?.isFavorite ?: return
        updateState { it.copy(items = it.items.toggleFavorite(id)) }
        viewModelScope.launch {
            val result = toggleFavorite(id, !prev)
            onIntent(ItemCatalogIntent.FavoriteResult(id, result is ApiResult.Success))
        }
    }

    private fun handleFavoriteResult(intent: ItemCatalogIntent.FavoriteResult) {
        if (!intent.success) {
            updateState { it.copy(items = it.items.toggleFavorite(intent.id)) }
            emitEffect(ItemCatalogEffect.ShowToast(UiText.Raw("Favorite failed")))
        }
    }
}
```

## 5. Screen

```kotlin
@Composable
internal fun ItemCatalogScreen(
    onBack: () -> Unit,
    onNavigate: (NavRoute) -> Unit,
    viewModel: ItemCatalogViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val toastBus = LocalAppToastBus.current

    LaunchedEffect(Unit) {
        viewModel.effect.collect { effect ->
            when (effect) {
                ItemCatalogEffect.NavigateBack -> onBack()
                is ItemCatalogEffect.NavigateToDetail -> onNavigate(NavRoute.Detail(effect.id))
                is ItemCatalogEffect.ShowToast -> toastBus.show(effect.text)
            }
        }
    }

    ItemCatalogContent(state = state, onIntent = viewModel::onIntent)
}

@Composable
private fun ItemCatalogContent(state: ItemCatalogState, onIntent: (ItemCatalogIntent) -> Unit) {
    when {
        state.isLoading && state.items.isEmpty() -> LoadingState()
        state.isOffline && state.items.isEmpty() -> OfflineState(onRetry = { onIntent(ItemCatalogIntent.Retry) })
        state.error != null && state.items.isEmpty() -> ErrorState(error = state.error, onRetry = { onIntent(ItemCatalogIntent.Retry) })
        state.items.isEmpty() -> EmptyState()
        else -> ItemCatalogList(items = state.items, onIntent = onIntent)
    }
}

@Composable
private fun ItemCatalogList(items: List<Item>, onIntent: (ItemCatalogIntent) -> Unit) {
    LazyColumn(contentPadding = PaddingValues({{THEME_CLASS}}.spacing.md)) {
        items(items, key = { it.id }) { item ->
            ItemRow(
                item = item,
                onClick = { onIntent(ItemCatalogIntent.SelectItem(item.id)) },
                onToggleFavorite = { onIntent(ItemCatalogIntent.ToggleFavorite(item.id)) },
            )
        }
    }
}
```

## 6. Domain

```kotlin
data class Item(val id: String, val title: String, val thumbnailUrl: String, val isFavorite: Boolean)

class GetItemsUseCase(private val repo: CatalogRepository) {
    suspend operator fun invoke(): ApiResult<List<Item>> = repo.getItems()
}

interface CatalogRepository {
    suspend fun getItems(): ApiResult<List<Item>>
    suspend fun toggleFavorite(id: String, favorite: Boolean): ApiResult<Unit>
}
```

## 7. Data

```kotlin
@Serializable
data class ItemDto(val id: String, val title: String, val thumbnailUrl: String, val isFavorite: Boolean = false)

internal object CatalogMapper {
    fun ItemDto.toDomain(): Item = Item(id, title, thumbnailUrl, isFavorite)
}

internal class CatalogRepositoryImpl(
    private val api: CatalogApi,            // trả ApiResult<Dto> (skills/android-network Step 4)
) : CatalogRepository {

    override suspend fun getItems(): ApiResult<List<Item>> =
        api.getItems().map { dtos -> dtos.map { it.toDomain() } }

    override suspend fun toggleFavorite(id: String, favorite: Boolean): ApiResult<Unit> =
        api.setFavorite(id, favorite)
}
```

## 8. DI binding

```kotlin
// DataModule
single<CatalogRepository> { CatalogRepositoryImpl(get()) }

// DomainModule
factory { GetItemsUseCase(get()) }

// PresenterModule
viewModel { ItemCatalogViewModel(get(), get()) }
```

## 9. Navigation

```kotlin
@Serializable
sealed class NavRoute {
    @Serializable data object ItemCatalog : NavRoute()
    @Serializable data class Detail(val id: String) : NavRoute()
}

composable<NavRoute.ItemCatalog> {
    ItemCatalogRoute(
        onBack = { navController.popBackStack() },
        onNavigate = { navController.navigate(it) },
    )
}
```

## 10. Tests

```
{{MODULE_PRESENTER}}/.../ItemCatalogViewModelTest.kt
  - load_success_populates_items
  - load_network_error_shows_offline
  - toggle_favorite_optimistic
  - toggle_favorite_failure_rolls_back
  - select_item_emits_navigation_effect

{{MODULE_DATA}}/.../CatalogRepositoryImplTest.kt
  - getItems_success_maps_dto
  - getItems_404_returns_NotFound
  - getItems_io_error_returns_Network_Offline
```

## Variants hợp lệ

- Nếu feature không cần UseCase (chỉ gọi 1 repo method không transform) → bỏ UseCase, ViewModel inject Repository interface
- Nếu feature không có remote data → bỏ `isOffline`, `isLoading`
- Nếu feature chỉ có 1-2 state branch → data class state đơn giản, Intent ít
- Nếu feature có 2 subscreen trong 1 tab → tách thành 2 feature packages, share qua `{{MODULE_PRESENTER}}/components/`

## Khi deviate

- Ghi rationale trong PR
- Nếu product có overlay blueprint live hơn → ưu tiên live reference
- Confirm Konsist test pass sau deviation
