# Jetpack / Compose Multiplatform Essentials

## Overview

Compose Multiplatform 1.8+ dùng chung ở `presenter/src/commonMain/`. Pattern giống Jetpack Compose Android, nhưng tránh `android.*` import trong common.

## Composable responsibility

### Stateless vs stateful

- **Stateless** (ưu tiên): nhận state qua param, emit event qua lambda. Reusable, dễ test.
- **Stateful** (gắn ViewModel): wrapper top-level ở route entry, hoist state cho stateless children.

```kotlin
// ✅ Stateful (route entry)
@Composable
fun HomeScreen(
    viewModel: HomeViewModel = koinViewModel(),
    onNavigate: (NavRoute) -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    EffectHandler(viewModel.effect, onNavigate)
    HomeContent(
        state = state,
        onIntent = viewModel::onIntent,
    )
}

// ✅ Stateless
@Composable
private fun HomeContent(
    state: HomeState,
    onIntent: (HomeIntent) -> Unit,
) { ... }
```

### Route vs content

- Route composable (public): wire ViewModel + nav + top-level scaffold
- Content composable (private hoặc internal): nhận state + callback, không biết ViewModel

## State hoisting

**Hoist state đến owner thấp nhất chung** cho mọi reader + writer.

```kotlin
// ❌ state trong leaf, parent không điều khiển được
@Composable
fun ToggleRow() {
    var checked by remember { mutableStateOf(false) }
    ...
}

// ✅ hoisted
@Composable
fun ToggleRow(checked: Boolean, onToggle: (Boolean) -> Unit) { ... }
```

## Recomposition prevention

### Keys trong lazy list

```kotlin
LazyColumn {
    items(books, key = { it.id }) { book ->
        BookRow(book)
    }
}
```

**MUST** có `key` cho mọi `items(list, key = )` khi list dynamic — tránh re-create state.

### Stability

- `data class` với immutable `val` → stable mặc định
- `List<T>` → immutable interface, nhưng Kotlin reads nó không stable → dùng `ImmutableList` (kotlinx.collections.immutable) khi performance critical
- Compile-time: `compose_stability_config.conf` ở root project đã mark stable cho types tùy chỉnh

### derivedStateOf

```kotlin
// ❌ re-compute mỗi recomposition
val filtered = books.filter { it.rating > 4.0 }

// ✅ chỉ re-compute khi upstream thay đổi
val filtered by remember(books) { derivedStateOf { books.filter { it.rating > 4.0 } } }
```

## Side effects

| API | When |
|---|---|
| `LaunchedEffect(key1, key2)` | Suspending side-effect gắn composition, hủy khi key đổi |
| `DisposableEffect(key)` | Side-effect cần cleanup (register/unregister listener) |
| `SideEffect` | Push state vào non-Compose world sau mỗi successful composition |
| `rememberCoroutineScope()` | Scope cho callback (click → launch) |
| `rememberUpdatedState(x)` | Giữ reference latest x trong long-running `LaunchedEffect` |

### Effect handler pattern cho MVI

```kotlin
@Composable
fun EffectHandler(
    effects: Flow<HomeEffect>,
    onNavigate: (NavRoute) -> Unit,
) {
    val toastBus = LocalToastBus.current
    LaunchedEffect(Unit) {
        effects.collect { effect ->
            when (effect) {
                is HomeEffect.NavigateToDetail -> onNavigate(NavRoute.Detail(effect.bookId))
                is HomeEffect.ShowToast -> toastBus.show(effect.text)
            }
        }
    }
}
```

## Lifecycle-aware collection

**MUST** dùng `collectAsStateWithLifecycle()` thay vì `collectAsState()` để không collect ở background:

```kotlin
// ❌ collect kể cả khi screen off
val state by viewModel.state.collectAsState()

// ✅ pause collect khi lifecycle < STARTED
val state by viewModel.state.collectAsStateWithLifecycle()
```

## Theming

- Design token ở `{{MODULE_PRESENTER}}/theme/{{THEME_PREFIX}}Colors.kt`, `{{THEME_PREFIX}}Typography.kt`, `{{THEME_PREFIX}}SpacingShape.kt`
- `{{THEME_CLASS}} { ... }` wrap root; truy cập qua `{{THEME_CLASS}}.colors`, `{{THEME_CLASS}}.typography`
- Dark mode: single source `isSystemInDarkTheme()` + override thủ công

## Previews

```kotlin
@Preview
@Composable
private fun HomeContentPreview() {
    {{THEME_CLASS}} {
        HomeContent(
            state = HomeState(rails = fakeRails()),
            onIntent = {},
        )
    }
}
```

Preview chỉ cho stateless composable. Không preview Route composable (có ViewModel).

Preview thêm font scale lớn, RTL và chuỗi dài để bắt lỗi cắt/tràn text: xem `knowledge/compose/ui-resilience.md` §5.

## Common mistakes

| Mistake | Fix |
|---|---|
| `collectAsState()` không lifecycle | `collectAsStateWithLifecycle()` |
| `items(list)` không `key =` | Thêm `key = { it.id }` |
| `MutableState` trong leaf, parent không biết | Hoist lên owner |
| Side-effect bodied trong Composable không wrap LaunchedEffect | Wrap `LaunchedEffect(key) { ... }` |
| Lambda capture `viewModel` → recompose ko stable | Dùng `viewModel::onIntent` |
| Rebuild list mỗi recomposition | `remember(key) { ... }` |

## References

- [Compose Multiplatform docs](https://www.jetbrains.com/lp/compose-multiplatform/)
- [Compose runtime](https://developer.android.com/jetpack/compose/mental-model)
- [State in Compose](https://developer.android.com/jetpack/compose/state)
- `knowledge/compose/ui-resilience.md` — text theo locale, font scale, RTL, edge-to-edge/insets
- `presenter/theme/*.kt`, `presenter/components/*`
