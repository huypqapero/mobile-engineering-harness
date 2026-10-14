---
name: android-network
description: Build API integration — service contract, DTO, error mapping, auth, retry/timeout. Supports Retrofit (Android), Ktor Client (KMP), Ktorfit (KMP annotation). Trigger khi task touch API layer, add endpoint, refactor error handling, hoặc integrate 3rd-party API.
priority: P1
---

# Skill: android-network

## Trigger

- Thêm endpoint API mới
- Tạo API service cho feature mới
- Refactor error handling, response parsing
- Add auth header / token refresh
- Debug network issue (timeout, 4xx, 5xx mapping)
- Setup network client cho project mới (Retrofit / Ktor / Ktorfit)

## Lib selection

Chọn network lib dựa trên `stack.network` trong `overlay.yaml`:

| Value | Lib | Platform |
|---|---|---|
| `retrofit` | Retrofit + OkHttp | Android-only |
| `ktor` | Ktor Client manual | KMP / CMP |
| `ktorfit` | Ktor + Ktorfit annotation | KMP / CMP (Retrofit-style interface) |

Chi tiết lib comparison + decision guide: `.harness/knowledge/data/network.md §Library selection`.

Pattern + procedure chung mọi lib (tiếp theo). Lib-specific code snippet trong `knowledge/data/network.md`.

## Inputs

- API spec (OpenAPI, Postman, raw doc)
- Auth strategy (bearer token, OAuth, session cookie)
- Base URL + env variants (dev/staging/prod)
- Error contract (HTTP status + body shape)

## Prerequisites

1. `.harness/knowledge/data/network.md`
2. `.harness/knowledge/coroutines/essentials.md §Retry pattern`
3. `.harness/constitution/concurrency-rules.md §CORO-008`
4. `BaseRepository` + `ApiResult` + `DomainError` trong `{{MODULE_DATA}}/core/`

## Execution procedure

### Step 1 — Design Dto layer

Mỗi endpoint 1 request/response Dto:

```kotlin
// {{MODULE_DATA}}/dto/BookDto.kt
@Serializable
data class BookDto(
    val id: String,
    val title: String,
    val author: String,
    @SerialName("cover_url") val coverUrl: String,
    val duration: Long = 0,          // default để tolerant với null
    val chapters: List<ChapterDto> = emptyList(),
)
```

**Rules**:
- Fields nullable → có default
- `@SerialName` khi key JSON khác convention Kotlin
- DTO không expose cross-module (keep `internal`)
- No business logic trong DTO (chỉ data)

### Step 2 — Define API service

Lib-specific. Chọn theo `stack.network`.

**Rules chung mọi lib**:
- API class/interface `internal` — không expose cross-module
- Path constants trong `companion object` hoặc `const val` top-level
- Suspend functions, không callback
- Non-2xx response throw exception → caught ở `BaseRepository.apiCall { }`

#### Variant A — Ktor Client (KMP/CMP)

```kotlin
// {{MODULE_DATA}}/remote/BookApi.kt
internal class BookApi(private val client: HttpClient) {
    suspend fun getBook(id: String): BookDto =
        client.get("$BOOKS_PATH/$id").body()

    suspend fun searchBooks(query: String, filter: String? = null): List<BookDto> =
        client.get("$BOOKS_PATH/search") {
            parameter("q", query)
            filter?.let { parameter("filter", it) }
        }.body()

    companion object { private const val BOOKS_PATH = "/v1/books" }
}
```

#### Variant B — Retrofit (Android-only)

```kotlin
internal interface BookApi {
    @GET("/v1/books/{id}")
    suspend fun getBook(@Path("id") id: String): BookDto

    @GET("/v1/books/search")
    suspend fun searchBooks(
        @Query("q") query: String,
        @Query("filter") filter: String? = null,
    ): List<BookDto>
}
```

#### Variant C — Ktorfit (KMP + annotation)

Interface giống Retrofit, generator tạo impl:

```kotlin
internal interface BookApi {
    @GET("/v1/books/{id}")
    suspend fun getBook(@Path("id") id: String): BookDto
}
```

Chi tiết + builder config + DI binding: xem `.harness/knowledge/data/network.md`.

### Step 3 — Configure client

Example dưới là **Ktor** (KMP). Retrofit builder config + Ktorfit `Ktorfit.Builder()` xem `knowledge/data/network.md §Option 2/3`.

```kotlin
// {{MODULE_DATA}}/di/DataModule.kt
single<HttpClient> {
    HttpClient(engineProvider()) {
        expectSuccess = true  // throw cho non-2xx

        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                coerceInputValues = true
                encodeDefaults = true
            })
        }

        install(HttpTimeout) {
            requestTimeoutMillis = 30_000
            connectTimeoutMillis = 10_000
            socketTimeoutMillis = 30_000
        }

        install(HttpRequestRetry) {
            retryOnServerErrors(maxRetries = 2)
            retryOnException(maxRetries = 2, retryOnTimeout = false)
            exponentialDelay(base = 2.0, baseDelayMs = 500)
        }

        install(Logging) {
            level = if (isDebug()) LogLevel.BODY else LogLevel.NONE
            sanitizeHeader { header ->
                header == HttpHeaders.Authorization || header == "X-Api-Key"
            }
        }

        install(DefaultRequest) {
            url(BuildConfig.BASE_URL)
            header("X-Client-Version", BuildConfig.APP_VERSION)
            header("X-Platform", platformName())
        }

        install(Auth) {
            bearer {
                loadTokens { authStorage.load() }
                refreshTokens { authStorage.refresh() }
            }
        }
    }
}
```

**Rules**:
- `expectSuccess = true` ép throw cho 4xx/5xx → consistent error path
- `ignoreUnknownKeys = true` cho backward compat khi API add field
- `coerceInputValues` tolerant null → default
- `Logging` sanitize sensitive header (token, api key)
- Timeout cụ thể, không default infinite

### Step 4 — Error mapping ở Repository

```kotlin
// {{MODULE_DATA}}/core/BaseRepository.kt (đã có)
abstract class BaseRepository(
    protected val ioDispatcher: CoroutineDispatcher,
) {
    protected suspend fun <T> apiCall(block: suspend () -> T): ApiResult<T> =
        withContext(ioDispatcher) {
            try {
                ApiResult.Success(block())
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                ApiResult.Error(mapError(e))
            }
        }

    private fun mapError(e: Throwable): DomainError = when (e) {
        is IOException            -> DomainError.Network.Offline
        is HttpRequestTimeoutException -> DomainError.Network.Timeout
        is ClientRequestException -> when (e.response.status.value) {
            401 -> DomainError.Auth.Unauthenticated
            403 -> DomainError.Auth.Forbidden
            404 -> DomainError.NotFound
            else -> DomainError.Client(e.response.status.value)
        }
        is ServerResponseException -> DomainError.Server(e.response.status.value)
        is SerializationException -> DomainError.Parse(e.message ?: "Parse error")
        else -> DomainError.Unknown(e.message ?: "Unknown")
    }
}
```

### Step 5 — Repository impl

```kotlin
// {{MODULE_DATA}}/repository/BookRepositoryImpl.kt
internal class BookRepositoryImpl(
    private val api: BookApi,
    ioDispatcher: CoroutineDispatcher,
) : BaseRepository(ioDispatcher), BookRepository {

    override suspend fun getBooks(page: Int): ApiResult<List<Book>> = apiCall {
        api.getBooks(page).map { it.toDomain() }
    }

    override suspend fun searchBooks(query: String): ApiResult<List<Book>> = apiCall {
        api.searchBooks(query).map { it.toDomain() }
    }
}
```

### Step 6 — Test

Chọn mock tool theo lib:
- Ktor / Ktorfit → `MockEngine` (Ktor built-in)
- Retrofit → `MockWebServer` (OkHttp lib)

Example dưới là **Ktor MockEngine**. MockWebServer snippet xem `knowledge/data/network.md §Testing với MockWebServer`.

```kotlin
class BookRepositoryImplTest {
    private val mockEngine = MockEngine { request ->
        when (request.url.encodedPath) {
            "/v1/books/book-1" -> respond(
                content = """{"id":"book-1","title":"Atomic","author":"Clear","cover_url":"x","duration":1000}""",
                headers = headersOf(HttpHeaders.ContentType, "application/json"),
            )
            "/v1/books/missing" -> respond("", status = HttpStatusCode.NotFound)
            else -> respond("", status = HttpStatusCode.NotFound)
        }
    }
    private val client = HttpClient(mockEngine) {
        install(ContentNegotiation) { json(Json { ignoreUnknownKeys = true }) }
        expectSuccess = true
    }
    private val repo = BookRepositoryImpl(BookApi(client), UnconfinedTestDispatcher())

    @Test
    fun `getBook success maps dto to domain`() = runTest {
        val result = repo.getBook("book-1")
        assertTrue(result is ApiResult.Success)
        assertEquals("Atomic", result.data.title)
    }

    @Test
    fun `getBook 404 returns NotFound`() = runTest {
        val result = repo.getBook("missing")
        assertTrue(result is ApiResult.Error)
        assertTrue((result as ApiResult.Error).cause is DomainError.NotFound)
    }
}
```

## Required policies

- ARCH-010 Ktor platform engine chỉ ở `data/{androidMain,iosMain}/` qua `expect`
- ARCH-005 Mapper object + extension
- ARCH-013 Null-safe mapping
- CORO-004 cancellation preservation
- CORO-008 timeout + retry

## Error contract

Dùng `DomainError` sealed interface (define ở `domain/core/`):

```kotlin
sealed interface DomainError {
    sealed interface Network : DomainError {
        data object Offline : Network
        data object Timeout : Network
    }
    sealed interface Auth : DomainError {
        data object Unauthenticated : Auth
        data object Forbidden : Auth
    }
    data object NotFound : DomainError
    data class Client(val code: Int) : DomainError
    data class Server(val code: Int) : DomainError
    data class Parse(val message: String) : DomainError
    data class Unknown(val message: String) : DomainError
}
```

## Common patterns

### Pagination

```kotlin
suspend fun getBooks(cursor: String? = null, pageSize: Int = 20): ApiResult<Paged<Book>> = apiCall {
    val response = api.getBooks(cursor, pageSize)
    Paged(items = response.items.map { it.toDomain() }, nextCursor = response.nextCursor)
}
```

### Multipart upload

```kotlin
suspend fun uploadAvatar(bytes: ByteArray, mime: String): ApiResult<Unit> = apiCall {
    client.submitFormWithBinaryData(
        url = "/v1/upload",
        formData = formData {
            append("file", bytes, Headers.build {
                append(HttpHeaders.ContentType, mime)
                append(HttpHeaders.ContentDisposition, "filename=\"avatar.jpg\"")
            })
        },
    ).body()
}
```

### Stream download

```kotlin
suspend fun downloadFile(url: String, dest: Path): ApiResult<Long> = apiCall {
    client.prepareGet(url).execute { response ->
        var bytesRead = 0L
        response.bodyAsChannel().copyAndClose(dest.sink())
        bytesRead
    }
}
```

## Common mistakes

| Mistake | Fix |
|---|---|
| `expectSuccess = false` (default) → không throw cho 4xx | Set `true`, catch ở BaseRepository |
| Expose `BookDto` ra ngoài data module | Map sang `Book` domain trước khi return |
| Log token/password trong Logging interceptor | `sanitizeHeader` cho Authorization + API key |
| `!!` ở mapper DTO → NullPointerException runtime | Default value hoặc Result/sealed |
| Hardcode `BuildConfig.BASE_URL` trong API class | Config qua `DefaultRequest` plugin |
| Retry 4xx client error | `retryOnServerErrors` only; không retry 4xx |
| Timeout `Long.MAX_VALUE` | Specific timeout (ví dụ 30s request, 10s connect) |

## Output contract

- API class `internal` trong `data/remote/`
- DTO với `@Serializable`, default values, `@SerialName`
- Mapper object + extension function
- Repository impl extend `BaseRepository`, dùng `apiCall { }`
- HttpClient singleton qua Koin
- Unit test với `MockEngine` cho ít nhất: happy path, 404, network error

## Anti-patterns bị cấm

- DTO leak ngoài data module (public hoặc internal visible cross-module)
- Business logic trong API class / DTO
- Hardcode secret/token trong code
- Retry policy bất kể error type
- `GlobalScope.launch` cho network call
- Throw raw exception từ Repository public method (phải map `ApiResult`)
