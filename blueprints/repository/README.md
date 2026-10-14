# Blueprint: Repository (Standalone)

Standalone pattern cho 1 Repository (interface domain + impl data) **không cần** full feature stack. Dùng khi:
- Thêm domain mới cần persistence/fetch
- Refactor existing data access logic
- Prep SDK extraction

Nếu feature mới cần cả UI + MVI contract → dùng `reference-feature` blueprint. Nếu chỉ cần API service → dùng `network-service` blueprint.

## Layout

```
{{MODULE_DOMAIN}}/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/{{MODULE_DOMAIN}}/
├── model/<domain>/<Entity>.kt
├── repository/<Name>Repository.kt           ← interface

{{MODULE_DATA}}/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/{{MODULE_DATA}}/
├── dto/<Name>Dto.kt                          (nếu có remote)
├── mapper/<Name>Mapper.kt
├── remote/<Name>Api.kt                       (nếu có remote)
├── local/<Name>LocalSource.kt                (nếu có local DB)
└── repository/<Name>RepositoryImpl.kt
```

## 1. Domain model

```kotlin
// {{MODULE_DOMAIN}}/model/bookmark/Bookmark.kt
data class Bookmark(
    val id: String,
    val bookId: String,
    val chapter: Int,
    val positionMs: Long,
    val createdAt: Instant,
)
```

Pure Kotlin, immutable `val`, no platform import.

## 2. Repository interface

```kotlin
// {{MODULE_DOMAIN}}/repository/BookmarkRepository.kt
interface BookmarkRepository {
    fun observeBookmarks(bookId: String): Flow<List<Bookmark>>
    suspend fun addBookmark(bookmark: Bookmark): ApiResult<Unit>
    suspend fun removeBookmark(id: String): ApiResult<Unit>
    suspend fun syncBookmarks(): ApiResult<Int>  // return count synced
}
```

Decision guide method shape:
- **Observable → `Flow<T>`**: reactive stream (DB)
- **1-shot CRUD → `suspend fun ApiResult<T>`**: success/error typed

## 3. DTO + Mapper (nếu có remote)

```kotlin
// {{MODULE_DATA}}/dto/BookmarkDto.kt
@Serializable
internal data class BookmarkDto(
    val id: String,
    @SerialName("book_id") val bookId: String,
    val chapter: Int,
    @SerialName("position_ms") val positionMs: Long,
    @SerialName("created_at") val createdAt: Long,
)

// {{MODULE_DATA}}/mapper/BookmarkMapper.kt
internal object BookmarkMapper {
    fun BookmarkDto.toDomain(): Bookmark = Bookmark(
        id = id,
        bookId = bookId,
        chapter = chapter,
        positionMs = positionMs,
        createdAt = Instant.fromEpochMilliseconds(createdAt),
    )

    fun Bookmark.toDto(): BookmarkDto = BookmarkDto(
        id = id,
        bookId = bookId,
        chapter = chapter,
        positionMs = positionMs,
        createdAt = createdAt.toEpochMilliseconds(),
    )
}
```

## 4. Data source(s)

### Remote source

```kotlin
// {{MODULE_DATA}}/remote/BookmarkApi.kt
internal class BookmarkApi(private val client: HttpClient) {
    suspend fun getBookmarks(bookId: String): List<BookmarkDto> =
        client.get("/v1/bookmarks") { parameter("book_id", bookId) }.body()

    suspend fun create(bookmark: BookmarkDto) {
        client.post("/v1/bookmarks") {
            contentType(ContentType.Application.Json)
            setBody(bookmark)
        }
    }

    suspend fun delete(id: String) {
        client.delete("/v1/bookmarks/$id")
    }
}
```

### Local source

```kotlin
// {{MODULE_DATA}}/local/BookmarkLocalSource.kt
internal class BookmarkLocalSource(private val queries: BookmarkQueries) {
    fun observeByBook(bookId: String): Flow<List<Bookmark>> =
        queries.getByBook(bookId).asFlow().mapToList(Dispatchers.Default).map { entities ->
            entities.map { it.toDomain() }
        }

    suspend fun upsert(bookmark: Bookmark) {
        queries.upsert(
            id = bookmark.id,
            book_id = bookmark.bookId,
            chapter = bookmark.chapter,
            position_ms = bookmark.positionMs,
            created_at = bookmark.createdAt.toEpochMilliseconds(),
        )
    }

    suspend fun delete(id: String) {
        queries.delete(id)
    }
}
```

## 5. Repository impl

```kotlin
// {{MODULE_DATA}}/repository/BookmarkRepositoryImpl.kt
internal class BookmarkRepositoryImpl(
    private val api: BookmarkApi,
    private val local: BookmarkLocalSource,
    ioDispatcher: CoroutineDispatcher,
) : BaseRepository(ioDispatcher), BookmarkRepository {

    override fun observeBookmarks(bookId: String): Flow<List<Bookmark>> =
        local.observeByBook(bookId)

    override suspend fun addBookmark(bookmark: Bookmark): ApiResult<Unit> = apiCall {
        local.upsert(bookmark)                    // optimistic
        api.create(bookmark.toDto())              // sync remote
    }

    override suspend fun removeBookmark(id: String): ApiResult<Unit> = apiCall {
        local.delete(id)
        api.delete(id)
    }

    override suspend fun syncBookmarks(): ApiResult<Int> = apiCall {
        // Pull remote
        val remote = api.getBookmarks(bookId = "").map { it.toDomain() }
        remote.forEach { local.upsert(it) }
        remote.size
    }
}
```

**Rollback consideration**: nếu local success + remote fail → user thấy bookmark trong UI nhưng server không có. Options:
- Mark local là "pending sync", retry background
- Rollback local nếu remote fail (strict consistency)
- Fire-and-forget (acceptable cho feature non-critical)

## 6. DI binding

```kotlin
// data/di/DataModule.kt
single { BookmarkApi(get()) }
single { BookmarkLocalSource(get<AppDatabase>().bookmarkQueries) }
single<BookmarkRepository> {
    BookmarkRepositoryImpl(get(), get(), get(named("io")))
}
```

## 7. Unit test

```kotlin
class BookmarkRepositoryImplTest {
    private val api = FakeBookmarkApi()
    private val local = FakeBookmarkLocal()
    private val repo = BookmarkRepositoryImpl(api, local, UnconfinedTestDispatcher())

    @Test
    fun `addBookmark updates local + remote`() = runTest {
        val b = fakeBookmark()
        val result = repo.addBookmark(b)
        assertTrue(result is ApiResult.Success)
        assertEquals(listOf(b), local.upserts)
        assertEquals(listOf(b.toDto()), api.creates)
    }

    @Test
    fun `addBookmark remote fail returns Error`() = runTest {
        val failingApi = FakeBookmarkApi(error = IOException())
        val repo = BookmarkRepositoryImpl(failingApi, local, UnconfinedTestDispatcher())
        val result = repo.addBookmark(fakeBookmark())
        assertTrue(result is ApiResult.Error)
        assertTrue((result as ApiResult.Error).cause is DomainError.Network.Offline)
    }
}
```

## Checklist

- [ ] Interface ở `domain/`, impl ở `data/`
- [ ] Impl extend `BaseRepository`, dùng `apiCall { }`
- [ ] DTO `internal`, `@Serializable`, nullable có default
- [ ] Mapper `object` + extension (ARCH-005)
- [ ] Data source split (`*Api`, `*LocalSource`) nếu > 1 source
- [ ] Flow cho observable, suspend ApiResult cho 1-shot
- [ ] DI binding ở data module
- [ ] Test ít nhất 3 scenarios: happy + error + edge
- [ ] Không `!!` ở mapper (ARCH-013)
- [ ] Không expose DTO/entity cross-module

## Variants

- Only remote → bỏ `*LocalSource`
- Only local → bỏ `*Api`, `*Dto`, `*Mapper` dạng DTO
- No sync → bỏ `syncX()` method
- Read-only (query) → chỉ `observeX()` + `getX()`

## Relation với reference-feature

Repository blueprint này **thành phần** trong feature blueprint. Dùng standalone khi:
- Chia PR nhỏ: data layer trước, UI sau
- Multiple feature share Repository (ví dụ `BookmarkRepository` dùng ở Library + Reader + Detail)
- Khó design state → tách Repository trước, UI design sau

## Reference

- `.harness/skills/android-network/SKILL.md`
- `.harness/skills/android-database/SKILL.md`
- `.harness/knowledge/data/repository-pattern.md`
- `.harness/blueprints/reference-feature/README.md`
