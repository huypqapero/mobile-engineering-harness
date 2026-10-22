# Design Patterns — Common in Android/Kotlin

Catalog các pattern thực tế dùng trong Android/Kotlin. **Không** liệt kê 23 GoF pattern monolithic — chỉ patterns thực sự dùng được trong codebase.

## Rule: Pattern chỉ áp dụng khi có problem cụ thể

**FORBIDDEN**: chọn pattern vì "code sạch hơn" nhưng không có problem. Mỗi pattern phải có: **Problem → Solution → Cost**.

## Creational

### Factory / Factory function

**Problem**: tạo object cần logic (choose impl, dependency, config) tại call site.

**Solution** (prefer Kotlin top-level function):

```kotlin
fun createHttpClient(engine: HttpClientEngine, isDebug: Boolean): HttpClient =
    HttpClient(engine) {
        install(Logging) { level = if (isDebug) LogLevel.BODY else LogLevel.NONE }
        // ...
    }
```

**Cost**: 1 indirection; không scale khi factory logic nhiều variant → sealed hierarchy.

**Example use case**: Koin `single { }` / `factory { }` block là factory implicit — không cần tạo factory class riêng.

### Builder (DSL)

**Problem**: construct object với nhiều optional field, config step-by-step.

**Solution** (Kotlin DSL với type-safe builders):

```kotlin
class SearchConfig private constructor(
    val query: String,
    val filter: Filter?,
    val sortBy: SortBy,
) {
    class Builder {
        var query: String = ""
        var filter: Filter? = null
        var sortBy: SortBy = SortBy.Relevance
        fun build() = SearchConfig(query, filter, sortBy)
    }

    companion object {
        operator fun invoke(block: Builder.() -> Unit): SearchConfig =
            Builder().apply(block).build()
    }
}

// Call site
val config = SearchConfig {
    query = "harry"
    filter = Filter.MediaType
    sortBy = SortBy.Rating
}
```

**Cost**: boilerplate; data class với default args thường đủ.

**Khi dùng**: config object cho SDK public API, Compose Modifier chain.

### Singleton

**Problem**: 1 instance shared cross-app (DB connection, HttpClient, Analytics).

**Solution** (prefer DI `single { }` qua Koin):

```kotlin
single { HttpClient(...) }
single<Database> { AppDatabase(get<DatabaseDriverFactory>().create()) }
```

**FORBIDDEN**: `object` singleton khi cần test substitute (fake). Dùng DI binding thay.

**Cost**: lifecycle = app process. Memory held suốt app life.

## Structural

### Adapter

**Problem**: wrap incompatible interface để fit expected interface.

**Solution**:

```kotlin
// Wrap callback-based API thành suspend
suspend fun playerPrepare(player: ExoPlayer): Unit = suspendCancellableCoroutine { cont ->
    val listener = object : Player.Listener {
        override fun onPlaybackStateChanged(state: Int) {
            if (state == Player.STATE_READY) {
                player.removeListener(this)
                cont.resume(Unit)
            }
        }
    }
    player.addListener(listener)
    cont.invokeOnCancellation { player.removeListener(listener) }
    player.prepare()
}
```

**Example use case**: adapter 3rd-party (ExoPlayer callback → coroutine), legacy Java API → suspend.

### Facade

**Problem**: expose simple API ẩn complex subsystem.

**Solution**:

```kotlin
// Public: 1 facade
object AnalyticsFacade {
    fun track(event: Event) {
        FirebaseAnalytics.log(event.name, event.params)
        Mixpanel.track(event.name, event.params)
        InternalLogger.log(event)
    }
}
```

**Example use case**: `AnalyticsTracker` interface là facade cho 3rd-party trackers.

### Decorator

**Problem**: add behavior to object without subclass.

**Solution** (Ktor plugin, OkHttp Interceptor, Compose Modifier):

```kotlin
install(DefaultRequest) { header("X-App-Version", APP_VERSION) }
install(Logging) { ... }
install(HttpTimeout) { ... }
```

Mỗi plugin decorate client functionality.

### Composite

**Problem**: tree structure where leaf + node share same interface.

**Solution** (Compose UI tree, menu structure):

```kotlin
sealed interface MenuItem {
    data class Action(val label: String, val onClick: () -> Unit) : MenuItem
    data class Submenu(val label: String, val items: List<MenuItem>) : MenuItem
    data object Divider : MenuItem
}
```

## Behavioral

### Strategy

**Problem**: multiple algorithm, choose at runtime.

**Solution** (prefer function parameter hoặc sealed interface):

```kotlin
// Function parameter — Kotlin idiomatic
fun List<Book>.sortedBy(strategy: SortStrategy): List<Book> = when (strategy) {
    SortStrategy.ByTitle -> sortedBy { it.title }
    SortStrategy.ByRating -> sortedByDescending { it.rating }
    SortStrategy.Recent -> sortedByDescending { it.updatedAt }
}

enum class SortStrategy { ByTitle, ByRating, Recent }
```

**Example use case**: `CatalogFilter` enum + extension function là strategy pattern lite.

### Observer

**Problem**: notify multiple observers when state changes.

**Solution** (Flow / StateFlow — Kotlin idiomatic):

```kotlin
class SessionManager {
    private val _session = MutableStateFlow<Session?>(null)
    val session: StateFlow<Session?> = _session.asStateFlow()

    fun login(session: Session) { _session.value = session }
    fun logout() { _session.value = null }
}

// Observer
scope.launch {
    sessionManager.session.collect { session -> /* react */ }
}
```

**FORBIDDEN**: EventBus pattern (global, hidden coupling). Dùng Flow explicit.

### State

**Problem**: object behavior change dựa trên state.

**Solution** (sealed interface + `when`):

```kotlin
sealed interface AuthState {
    data object Loading : AuthState
    data object SignedOut : AuthState
    data class SignedIn(val user: User) : AuthState
    data class Error(val cause: AuthError) : AuthState
}

@Composable
fun AuthRouter(state: AuthState) = when (state) {
    is AuthState.Loading -> LoadingScreen()
    is AuthState.SignedOut -> SignInScreen()
    is AuthState.SignedIn -> HomeScreen(state.user)
    is AuthState.Error -> ErrorScreen(state.cause)
}
```

Compiler exhaustive check là feature.

### Command

**Problem**: encapsulate action as object (for undo, queue, delay).

**Solution** (sealed interface):

```kotlin
sealed interface UiIntent {
    data object Load : UiIntent
    data class SelectBook(val id: String) : UiIntent
    data class ToggleBookmark(val id: String) : UiIntent
}

fun handle(intent: UiIntent) = when (intent) { ... }
```

**Example use case**: MVI Intent là Command pattern — mỗi user action = 1 Command object.

### Chain of Responsibility

**Problem**: pipeline nhiều handler, mỗi handler tự quyết handle hoặc pass.

**Solution** (Ktor Interceptor, OkHttp chain):

```kotlin
install(createClientPlugin("Pipeline") {
    onRequest { request, _ ->
        // Pre-process
    }
    onResponse { response ->
        // Post-process
    }
})
```

### Repository (Android specific)

Xem `knowledge/coding/data/repository-pattern.md`.

### MVI (Android specific)

Xem `knowledge/coding/mvi/essentials.md`.

## Patterns to AVOID

| Pattern | Lý do |
|---|---|
| **Singleton with public constructor** | Không singleton thực. Dùng DI. |
| **EventBus global** | Hidden coupling. Dùng Flow explicit. |
| **God class / God service** | SRP violation. Split. |
| **Deep inheritance** (>3 levels) | Compose over inherit. |
| **Service Locator global** | Hidden deps. Constructor inject. |
| **Null Object cho business state** | Dùng sealed interface explicit (ví dụ `Loading`, `Empty`). |
| **Marker interface** không behavior | Kotlin có `object` singleton tốt hơn. |

## Pattern selection framework

```
Có problem cụ thể?
  ├─ NO → không áp dụng pattern. KISS.
  └─ YES → tiếp
       │
       └─ Pattern cost < benefit?
           ├─ NO → tìm giải pháp khác đơn giản hơn
           └─ YES → apply pattern + document rationale
```

## References

- Kotlin idioms: https://kotlinlang.org/docs/idioms.html
- "Design Patterns" (GoF) — background theory, không cần đọc hết
- `.harness/constitution/engineering-principles.md §Composition over Inheritance`
