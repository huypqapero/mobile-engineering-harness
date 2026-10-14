# Caching — Essentials

Strategy chọn tùy data volatility, size, offline requirement.

## Cache tiers

| Tier | Latency | Lifetime | Capacity | Use case |
|---|---|---|---|---|
| L1 — In-memory | μs | Process | 10–100 items | Hot read, UI session |
| L2 — DB (SQLDelight) | ms | Device | 10k+ | Offline-first, structured |
| L3 — Filesystem | ms-s | Device | GB | Binary (image, audio, downloaded) |
| L4 — Remote | 100ms-s | Server-side | ∞ | SSOT nếu không offline |

## Strategy selection

### No cache

- Data critical realtime (chat message, live score)
- Write-rare / strong consistency
- Small dataset (<10 items, fast fetch)

### In-memory only (L1)

- UI session scoped (search typeahead results)
- Expensive to compute, cheap to re-fetch
- Flow + `stateIn(scope, WhileSubscribed(5000), initial)`

### DB SSOT (L2) — Offline-first

- Read-heavy, write-rare
- Offline requirement
- Observable with Flow

### HTTP cache (Ktor cache plugin)

- GET endpoints với ETag / Cache-Control header
- Simple fetch-again if changed
- Server controls TTL

### Hybrid (L1 + L2 + L4)

- Hot items in-memory + full set DB + remote source of truth

## In-memory cache patterns

### Simple LRU

```kotlin
class LruCache<K, V>(private val maxSize: Int) {
    private val entries = LinkedHashMap<K, V>(0, 0.75f, true /* accessOrder */)
    private val mutex = Mutex()

    suspend fun get(key: K, loader: suspend (K) -> V): V = mutex.withLock {
        entries.getOrPut(key) {
            if (entries.size >= maxSize) {
                entries.remove(entries.keys.iterator().next())
            }
            loader(key)
        }
    }

    suspend fun invalidate(key: K) = mutex.withLock { entries.remove(key) }
    suspend fun clear() = mutex.withLock { entries.clear() }
}
```

### TTL cache

```kotlin
class TtlCache<K, V>(private val ttl: Duration) {
    private data class Entry<V>(val value: V, val expiresAt: Instant)
    private val entries = mutableMapOf<K, Entry<V>>()
    private val mutex = Mutex()
    private val clock = Clock.System

    suspend fun get(key: K, loader: suspend () -> V): V = mutex.withLock {
        val now = clock.now()
        entries[key]?.takeIf { it.expiresAt > now }?.value
            ?: run {
                val fresh = loader()
                entries[key] = Entry(fresh, now + ttl)
                fresh
            }
    }
}
```

### `stateIn(WhileSubscribed)` cho hot shared

```kotlin
val user: StateFlow<User?> = authRepo.observeUser()
    .stateIn(
        scope = applicationScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = null,
    )
```

`WhileSubscribed(5000)`: cold khi không subscriber + 5s grace (survive quick nav).

## DB cache patterns

### Offline-first

```kotlin
override fun observeBook(id: String): Flow<Book?> =
    local.observeBook(id).map { it?.toDomain() }

override suspend fun refreshBook(id: String): ApiResult<Unit> = apiCall {
    val remote = api.getBook(id).toDomain()
    local.upsert(remote.toEntity(now = Clock.System.now().toEpochMilliseconds()))
}

// UI
val book by viewModel.book.collectAsStateWithLifecycle()  // observe local
LaunchedEffect(bookId) {
    viewModel.refresh(bookId)  // trigger remote update
}
```

### Fallback remote-first

```kotlin
override suspend fun getBook(id: String): ApiResult<Book> = apiCall {
    local.getById(id)?.toDomain()  // cached nếu có
        ?: run {
            val remote = api.getBook(id).toDomain()
            local.upsert(remote.toEntity(now = Clock.System.now().toEpochMilliseconds()))
            remote
        }
}
```

## HTTP cache (Ktor)

```kotlin
install(HttpCache) {
    // publicStorage: HttpCacheStorage.Unlimited()
}
```

Server cần set `Cache-Control: max-age=600` hoặc `ETag`. Client auto 304-check.

**Khi dùng**: endpoints GET với TTL rõ, server-controlled. Không dùng cho endpoint cần offline-first (DB SSOT better).

## Invalidation

**Hardest part của cache**. Rules:

### Explicit invalidate

```kotlin
suspend fun invalidateBook(id: String) {
    local.delete(id)
    inMemoryCache.invalidate(id)
}
```

### Trigger invalidate on write

```kotlin
suspend fun toggleBookmark(id: String, bookmarked: Boolean): ApiResult<Unit> = apiCall {
    api.toggleBookmark(id, bookmarked)
    local.updateBookmark(id, bookmarked)  // local update ngay — in-memory tự re-emit qua Flow
}
```

### TTL expiry

```kotlin
val remote = if (local.lastUpdated(id) < Clock.System.now() - 1.hours) {
    api.getBook(id).also { local.upsert(it.toEntity()) }
} else {
    local.getById(id).toDomain()
}
```

### Version-based

- API trả `version: Long`
- Client compare với local version
- Mismatch → re-fetch

### Push-based (realtime)

- Server push qua WebSocket / FCM
- Client receive → invalidate affected keys

## Common patterns per use case

### Image cache

Dùng Coil3 — built-in in-memory + disk cache:

```kotlin
ImageLoader.Builder(context)
    .memoryCache { MemoryCache.Builder().maxSizePercent(context, 0.25).build() }
    .diskCache { DiskCache.Builder().directory(cacheDir / "image_cache").maxSizeBytes(50_000_000).build() }
    .build()
```

### Pagination cache

```kotlin
// Paging3 (Android) hoặc tự impl
override fun pagingSource(filter: Filter): PagingSource<String, Book> = ...

// Local store page cursor
queries.upsertPage(cursor = "...", items = ...)
```

### User session cache

```kotlin
// SessionManager với StateFlow
class SessionManager(
    private val secureStorage: SecureStorage,
    scope: CoroutineScope,
) {
    private val _session = MutableStateFlow<Session?>(null)
    val session: StateFlow<Session?> = _session.asStateFlow()

    init {
        scope.launch {
            _session.value = loadFromSecure()
        }
    }
}
```

## Decision guides

### "Cache cái này không?"

1. Fetch latency > 500ms? → yes
2. Fetch cost tiền? → yes (API quota)
3. Data không đổi > 1 phút? → yes
4. Có offline requirement? → yes DB cache
5. Rest → in-memory TTL ok

### TTL chọn bao lâu

- Dữ liệu static (ngôn ngữ, country list): 24h+
- Content thường (book list, feed): 5-60 phút
- User-specific (profile, settings): 1-5 phút hoặc Flow observe
- Realtime (price, notification): no cache hoặc < 10s

### Size limit

- L1 in-memory: 10-100 items, không hardcap byte (dùng LRU)
- L2 DB: tuỳ feature, cleanup task định kỳ xoá stale
- L3 filesystem: 50-100 MB (image), 500 MB-1 GB (audio downloaded)

## Common mistakes

| Mistake | Fix |
|---|---|
| Cache cố định không invalidate → stale forever | TTL hoặc write-through |
| Cache phần UI state → không survive config change | Use SavedStateHandle |
| In-memory cache mà không thread-safe | `Mutex` hoặc atomic |
| Cache per-request (không shared) → defeats purpose | Singleton qua DI |
| Cache secret in-memory → memory dump leak | SecureStorage |
| Cache size unbounded → OOM | LRU + max size |
| Invalidate quá aggressive → cache miss luôn | Monitor hit rate |
| HTTP cache mà server không send Cache-Control header | Fix server hoặc skip HTTP cache |

## References

- `.harness/knowledge/data/persistence.md`
- `.harness/knowledge/data/network.md`
- Coil3: https://coil-kt.github.io/coil
- SQLDelight: https://cashapp.github.io/sqldelight
