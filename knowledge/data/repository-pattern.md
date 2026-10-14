# Repository Pattern — Essentials

## Overview

Repository = façade che các data source (remote API, local DB, cache, pref) và expose domain-shaped contract cho upper layers.

`domain/` sở hữu **interface**. `data/` sở hữu **impl**. ViewModel/UseCase chỉ biết interface.

## Rules

- **MUST** interface ở `domain/repository/`
- **MUST** impl ở `data/repository/`, extend `BaseRepository`
- **MUST** method trả `ApiResult<T>` (success/error typed) hoặc `Flow<T>` cho observable
- **MUST** map DTO/entity → domain model TRƯỚC khi return
- **FORBIDDEN** expose DTO, SQL entity, Firebase types ra ngoài data module
- **FORBIDDEN** throw exception raw (dùng `ApiResult.Error(DomainError)`)

## Interface shape

```kotlin
// domain/repository/BookRepository.kt
interface BookRepository {
    suspend fun getBook(id: String): ApiResult<Book>
    suspend fun searchBooks(query: String): ApiResult<List<Book>>
    suspend fun toggleBookmark(id: String, bookmarked: Boolean): ApiResult<Unit>
    fun observeBookmarked(): Flow<List<Book>>
}
```

### Design decision

| Pattern | Khi dùng |
|---|---|
| `suspend fun X(): ApiResult<T>` | 1-shot read/write, có success/error |
| `fun observe(): Flow<T>` | Reactive stream (DB, user state) |
| `suspend fun X(): Flow<T>` | Hiếm — tránh, prefer sync return `Flow<T>` |
| `fun X(): LiveData<T>` | KHÔNG — platform coupling, dùng Flow |

## Impl pattern

```kotlin
// data/repository/BookRepositoryImpl.kt
internal class BookRepositoryImpl(
    private val api: BookApi,
    private val local: BookLocalSource,
    ioDispatcher: CoroutineDispatcher,
) : BaseRepository(ioDispatcher), BookRepository {

    override suspend fun getBook(id: String): ApiResult<Book> = apiCall {
        api.getBook(id).toDomain().also { book ->
            local.upsert(book.toEntity(now = Clock.System.now().toEpochMilliseconds()))
        }
    }

    override fun observeBookmarked(): Flow<List<Book>> =
        local.observeBookmarked().map { it.map { entity -> entity.toDomain() } }
}
```

## Data source split

Tách DB vs API vs cache thành `*LocalSource`, `*RemoteSource` để test:

```kotlin
internal class BookRemoteSource(private val api: BookApi) {
    suspend fun fetchBook(id: String): BookDto = api.getBook(id)
}

internal class BookLocalSource(private val queries: BookQueries) {
    suspend fun upsert(book: Book) { ... }
    fun observeBookmarked(): Flow<List<Book>> = ...
}
```

Repository impl inject cả 2 source → orchestrate.

**Khi nào tách source**: Repository impl > 100 lines hoặc có ≥ 2 source. Dưới đó → gộp trong impl ok.

## Offline-first strategy

```kotlin
override fun observeBook(id: String): Flow<Book?> =
    local.observeBook(id).map { it?.toDomain() }

override suspend fun refreshBook(id: String): ApiResult<Unit> = apiCall {
    val remote = api.getBook(id).toDomain()
    local.upsert(remote.toEntity(now = Clock.System.now().toEpochMilliseconds()))
}
```

UI observe local → render luôn (fast first paint). Trigger refresh async → local update → Flow re-emit → UI re-render.

**Khi dùng**: feature read-heavy, offline requirement, data không critical realtime.

## Caching strategy

- **No cache**: fetch mỗi lần (data critical realtime, write-rare)
- **In-memory cache**: `Map<K, V>` + TTL (small data, short-lived)
- **DB SSOT**: offline-first pattern
- **HTTP cache**: Ktor cache plugin cho GET đơn giản

Chi tiết: `knowledge/data/caching.md`.

## Error handling

Repository không throw raw. Return `ApiResult.Error(DomainError)`:

```kotlin
sealed interface DomainError {
    sealed interface Network : DomainError {
        data object Offline : Network
        data object Timeout : Network
    }
    data object NotFound : DomainError
    data class Server(val code: Int) : DomainError
    data class Parse(val message: String) : DomainError
    data class Unknown(val message: String) : DomainError
}
```

Mapping ở `BaseRepository.mapError`:

```kotlin
private fun mapError(e: Throwable): DomainError = when (e) {
    is IOException            -> DomainError.Network.Offline
    is HttpRequestTimeoutException -> DomainError.Network.Timeout
    is ClientRequestException -> when (e.response.status.value) {
        404 -> DomainError.NotFound
        else -> DomainError.Client(e.response.status.value)
    }
    is ServerResponseException -> DomainError.Server(e.response.status.value)
    is SerializationException -> DomainError.Parse(e.message ?: "")
    else -> DomainError.Unknown(e.message ?: "")
}
```

## Testing

```kotlin
class BookRepositoryImplTest {
    private val mockApi = FakeBookApi(response = fakeBookDto())
    private val mockLocal = FakeBookLocal()
    private val repo = BookRepositoryImpl(mockApi, mockLocal, UnconfinedTestDispatcher())

    @Test
    fun `getBook success maps dto to domain + cache`() = runTest {
        val result = repo.getBook("1")
        assertTrue(result is ApiResult.Success)
        assertEquals("Atomic", result.data.title)
        assertEquals(1, mockLocal.upsertCalls.size)
    }
}
```

Fake preferred > Mock.

## Common mistakes

| Mistake | Fix |
|---|---|
| Interface + impl trong cùng module (domain) | Interface domain, impl data |
| Return DTO từ Repository public method | Map sang domain trước return |
| Repository impl có business logic | Business logic ở UseCase, Repository là bridge |
| Throw raw Exception | Return `ApiResult.Error(DomainError)` |
| Single Repository "god" cho mọi feature | Chia theo bounded context (BookRepository, UserRepository, ...) |
| `observeX(): LiveData` platform-coupled | Dùng `Flow<T>` |

## References

- Google: [Data layer](https://developer.android.com/topic/architecture/data-layer)
- Clean Architecture: Dependency Rule (domain owns interface)
- `.harness/skills/android-network/SKILL.md`
- `.harness/skills/android-database/SKILL.md`
