# Blueprint: Network Service

Standalone pattern cho implement 1 Ktor service với auth + error mapping + test. Dùng khi cần add API cho feature không warrant full feature blueprint.

**Example service**: `CatalogApi` — fetch list items, search, bookmark toggle.

## Layout

```
{{MODULE_DATA}}/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/{{MODULE_DATA}}/
├── dto/
│   └── ItemDto.kt
├── mapper/
│   └── CatalogMapper.kt
├── remote/
│   └── CatalogApi.kt
└── repository/
    └── CatalogRepositoryImpl.kt
```

## 1. DTO

```kotlin
// {{MODULE_DATA}}/dto/ItemDto.kt
@Serializable
internal data class ItemDto(
    val id: String,
    val title: String,
    val subtitle: String? = null,
    @SerialName("cover_url") val coverUrl: String,
    val duration: Long = 0,
    @SerialName("is_bookmarked") val isBookmarked: Boolean = false,
)

@Serializable
internal data class PagedItemsDto(
    val items: List<ItemDto>,
    @SerialName("next_cursor") val nextCursor: String? = null,
)
```

## 2. API service

```kotlin
// {{MODULE_DATA}}/remote/CatalogApi.kt
internal class CatalogApi(private val client: HttpClient) {

    suspend fun getItems(cursor: String? = null, pageSize: Int = 20): ApiResult<PagedItemsDto> =
        client.safeRequest {
            url(PATH)
            cursor?.let { parameter("cursor", it) }
            parameter("page_size", pageSize)
        }

    suspend fun getItem(id: String): ApiResult<ItemDto> =
        client.safeRequest { url("$PATH/$id") }

    suspend fun search(query: String, filter: String? = null): ApiResult<List<ItemDto>> =
        client.safeRequest {
            url("$PATH/search")
            parameter("q", query)
            filter?.let { parameter("filter", it) }
        }

    suspend fun setBookmark(id: String, bookmarked: Boolean): ApiResult<Unit> =
        client.safeRequest {
            method = HttpMethod.Put
            url("$PATH/$id/bookmark")
            contentType(ContentType.Application.Json)
            setBody(mapOf("bookmarked" to bookmarked))
        }

    companion object {
        private const val PATH = "/v1/catalog"
    }
}
```

## 3. Mapper

```kotlin
// {{MODULE_DATA}}/mapper/CatalogMapper.kt
internal object CatalogMapper {
    fun ItemDto.toDomain(): Item = Item(
        id = id,
        title = title,
        subtitle = subtitle,
        coverUrl = coverUrl,
        durationMs = duration,
        isBookmarked = isBookmarked,
    )

    fun PagedItemsDto.toDomain(): Paged<Item> = Paged(
        items = items.map { it.toDomain() },
        nextCursor = nextCursor,
    )
}
```

## 4. Repository impl

```kotlin
// {{MODULE_DATA}}/repository/CatalogRepositoryImpl.kt
internal class CatalogRepositoryImpl(
    private val api: CatalogApi,
) : CatalogRepository {

    override suspend fun getItems(cursor: String?): ApiResult<Paged<Item>> =
        api.getItems(cursor).map { it.toDomain() }

    override suspend fun getItem(id: String): ApiResult<Item> =
        api.getItem(id).map { it.toDomain() }

    override suspend fun search(query: String): ApiResult<List<Item>> =
        api.search(query).map { dtos -> dtos.map { it.toDomain() } }

    override suspend fun setBookmark(id: String, bookmarked: Boolean): ApiResult<Unit> =
        api.setBookmark(id, bookmarked)
}
```

## 5. Domain interface

```kotlin
// {{MODULE_DOMAIN}}/repository/CatalogRepository.kt
interface CatalogRepository {
    suspend fun getItems(cursor: String? = null): ApiResult<Paged<Item>>
    suspend fun getItem(id: String): ApiResult<Item>
    suspend fun search(query: String): ApiResult<List<Item>>
    suspend fun setBookmark(id: String, bookmarked: Boolean): ApiResult<Unit>
}
```

## 6. DI binding

```kotlin
// {{MODULE_DATA}}/di/DataModule.kt
single { CatalogApi(get()) }
single<CatalogRepository> { CatalogRepositoryImpl(get()) }
```

## 7. Unit test với MockEngine

```kotlin
class CatalogRepositoryImplTest {

    private val mockEngine = MockEngine { request ->
        when {
            request.url.encodedPath == "/v1/catalog/item-1" -> respond(
                content = """{"id":"item-1","title":"Atomic Habits","cover_url":"x","duration":3600000,"is_bookmarked":false}""",
                headers = headersOf(HttpHeaders.ContentType, "application/json"),
            )
            request.url.encodedPath == "/v1/catalog/missing" -> respond("", status = HttpStatusCode.NotFound)
            request.url.encodedPath == "/v1/catalog" -> respond(
                content = """{"items":[],"next_cursor":null}""",
                headers = headersOf(HttpHeaders.ContentType, "application/json"),
            )
            request.url.encodedPath.endsWith("/bookmark") && request.method == HttpMethod.Put -> respond(
                "", status = HttpStatusCode.NoContent,
            )
            else -> respond("", status = HttpStatusCode.NotFound)
        }
    }

    private val client = HttpClient(mockEngine) {
        install(ContentNegotiation) { json(Json { ignoreUnknownKeys = true }) }
        expectSuccess = true
    }
    private val repo = CatalogRepositoryImpl(CatalogApi(client))

    @Test
    fun `getItem success maps dto`() = runTest {
        val result = repo.getItem("item-1")
        assertTrue(result is ApiResult.Success)
        assertEquals("Atomic Habits", result.data.title)
        assertEquals(3_600_000, result.data.durationMs)
    }

    @Test
    fun `getItem 404 returns NotFound`() = runTest {
        val result = repo.getItem("missing")
        assertTrue(result is ApiResult.Error)
        assertTrue((result as ApiResult.Error).cause is DomainError.NotFound)
    }

    @Test
    fun `setBookmark 204 returns Success`() = runTest {
        val result = repo.setBookmark("item-1", true)
        assertTrue(result is ApiResult.Success)
    }

    @Test
    fun `getItems empty page returns empty list`() = runTest {
        val result = repo.getItems(cursor = null)
        assertTrue(result is ApiResult.Success)
        assertTrue(result.data.items.isEmpty())
        assertNull(result.data.nextCursor)
    }
}
```

## Variants hợp lệ

- Nếu cần streaming (SSE/WebSocket) → dùng `webSocket { }` thay REST
- Nếu cần optimistic update → impl trong Repository, revert on failure
- Nếu cần offline → thêm `CatalogLocalSource` + offline-first pattern (xem `blueprints/reference-feature`)
- Nếu auth per-request khác default → `headers { }` cho request specific

## Checklist khi copy pattern

- [ ] DTO `internal`, `@Serializable`, nullable field có default
- [ ] API class `internal`, path constants trong `companion object`
- [ ] Mapper `object` + extension functions (ARCH-005)
- [ ] API class trả `ApiResult<Dto>` qua `safeRequest` (Ktor) / CallAdapter (Retrofit) / Converter (Ktorfit)
- [ ] Repository impl không kế thừa base class, chỉ `map` DTO → domain (ARCH-004)
- [ ] Interface ở `domain/`, impl ở `data/`
- [ ] DI binding: API = `single`, Repository = `single<Interface>`
- [ ] Test MockEngine ≥ 3 scenarios (success, 404, edge)
- [ ] Không `!!` ở mapper
- [ ] Không hardcode secret

## Khi deviate

- Document rationale trong PR
- Vẫn pass Konsist rule MUST
- Reference `skills/android-network/SKILL.md` cho edge case advanced
