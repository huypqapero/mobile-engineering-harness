---
name: coding-network
description: Build API integration — service contract, DTO, error mapping, auth, retry/timeout. Supports Retrofit (Android), Ktor Client (KMP), Ktorfit (KMP annotation). Trigger khi task touch API layer, add endpoint, refactor error handling, hoặc integrate 3rd-party API.
priority: P1
---

# Skill: coding-network

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

Chi tiết lib comparison + decision guide: `knowledge/coding/data/network.md [KB → develop/coding-data, kb_search "data network"] §Library selection`.

Pattern + procedure chung mọi lib (tiếp theo). Lib-specific code snippet trong `knowledge/coding/data/network.md [KB → develop/coding-data, kb_search "data network"]`.

## Inputs

- API spec (OpenAPI, Postman, raw doc)
- Auth strategy (bearer token, OAuth, session cookie)
- Base URL + env variants (dev/staging/prod)
- Error contract (HTTP status + body shape)

## Prerequisites

1. `knowledge/coding/data/network.md [KB → develop/coding-data, kb_search "data network"]`
2. `knowledge/coding/coroutines/essentials.md [KB → develop/coding-coroutines, kb_search "coroutines essentials"] §Retry pattern`
3. `constitution/concurrency-rules.md [KB → develop/constitution, kb_search "concurrency rules"] §CORO-008`
4. `ApiResult` + `DomainError` trong `{{MODULE_DOMAIN}}/core/`; `ErrorMapper` + adapter/converter trong `{{MODULE_DATA}}/core/network/` (Step 4)

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
- Function trả `ApiResult<Dto>` — non-2xx / IO / parse error được map sang `DomainError` ngay tầng network (Step 4), không exception nào lọt lên Repository

#### Variant A — Ktor Client (KMP/CMP)

```kotlin
// {{MODULE_DATA}}/remote/BookApi.kt
internal class BookApi(private val client: HttpClient) {
    suspend fun getBook(id: String): ApiResult<BookDto> =
        client.safeRequest { url("$BOOKS_PATH/$id") }

    suspend fun searchBooks(query: String, filter: String? = null): ApiResult<List<BookDto>> =
        client.safeRequest {
            url("$BOOKS_PATH/search")
            parameter("q", query)
            filter?.let { parameter("filter", it) }
        }

    companion object { private const val BOOKS_PATH = "/v1/books" }
}
```

#### Variant B — Retrofit (Android-only)

```kotlin
internal interface BookApi {
    @GET("/v1/books/{id}")
    suspend fun getBook(@Path("id") id: String): ApiResult<BookDto>

    @GET("/v1/books/search")
    suspend fun searchBooks(
        @Query("q") query: String,
        @Query("filter") filter: String? = null,
    ): ApiResult<List<BookDto>>
}
```

#### Variant C — Ktorfit (KMP + annotation)

Interface giống Retrofit, generator tạo impl:

```kotlin
internal interface BookApi {
    @GET("/v1/books/{id}")
    suspend fun getBook(@Path("id") id: String): ApiResult<BookDto>
}
```

Chi tiết + builder config + DI binding: xem `knowledge/coding/data/network.md [KB → develop/coding-data, kb_search "data network"]`.

### Step 3 — Configure client

Example dưới là **Ktor** (KMP). Retrofit builder config + Ktorfit `Ktorfit.Builder()` xem `knowledge/coding/data/network.md [KB → develop/coding-data, kb_search "data network"] §Option 2/3`; đăng ký adapter/converter ở Step 4.

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
- `expectSuccess = true` ép throw cho 4xx/5xx → `safeCall` / converter map qua `ErrorMapper` (khi `false`, helper tự check status — kết quả `ApiResult` như nhau)
- `ignoreUnknownKeys = true` cho backward compat khi API add field
- `coerceInputValues` tolerant null → default
- `Logging` sanitize sensitive header (token, api key)
- Timeout cụ thể, không default infinite

### Step 4 — ApiResult tại tầng network (ErrorMapper + adapter)

Contract: API service trả `ApiResult<Dto>`; exception → `DomainError` map **một lần** ở `ErrorMapper`. Bảng mapping đầy đủ + variant Retrofit của `ErrorMapper`: `knowledge/coding/data/network.md [KB → develop/coding-data, kb_search "data network"] §ApiResult contract`.

`ApiResult` + extension (domain):

```kotlin
// {{MODULE_DOMAIN}}/core/ApiResult.kt — pure Kotlin, dùng được trong domain interface
sealed interface ApiResult<out T> {
    data class Success<out T>(val data: T) : ApiResult<T>
    data class Error(val cause: DomainError) : ApiResult<Nothing>
}

inline fun <T, R> ApiResult<T>.map(transform: (T) -> R): ApiResult<R> = when (this) {
    is ApiResult.Success -> ApiResult.Success(transform(data))
    is ApiResult.Error -> this
}

inline fun <T, R> ApiResult<T>.flatMap(transform: (T) -> ApiResult<R>): ApiResult<R> = when (this) {
    is ApiResult.Success -> transform(data)
    is ApiResult.Error -> this
}

inline fun <T> ApiResult<T>.onSuccess(action: (T) -> Unit): ApiResult<T> {
    if (this is ApiResult.Success) action(data)
    return this
}

fun <T> ApiResult<T>.getOrNull(): T? = (this as? ApiResult.Success)?.data
```

`ErrorMapper` — variant `ktor` / `ktorfit` (variant `retrofit`: `InterruptedIOException` → Timeout, `IOException` → Offline, `HttpException` → `fromStatus`, xem knowledge):

```kotlin
// {{MODULE_DATA}}/core/network/ErrorMapper.kt — stack.network = ktor | ktorfit
internal object ErrorMapper {

    fun fromStatus(code: Int): DomainError = when (code) {
        401 -> DomainError.Auth.Unauthenticated
        403 -> DomainError.Auth.Forbidden
        404 -> DomainError.NotFound
        in 400..499 -> DomainError.Client(code)
        in 500..599 -> DomainError.Server(code)
        else -> DomainError.Unknown("HTTP $code")
    }

    fun fromThrowable(e: Throwable): DomainError = when (e) {
        is HttpRequestTimeoutException,
        is ConnectTimeoutException,
        is SocketTimeoutException -> DomainError.Network.Timeout          // trước IOException
        is ResponseException -> fromStatus(e.response.status.value)       // expectSuccess = true
        is ContentConvertException -> DomainError.Parse(e.message.orEmpty())
        is SerializationException -> DomainError.Parse(e.message.orEmpty())
        is IOException -> DomainError.Network.Offline                     // kotlinx.io.IOException
        else -> DomainError.Unknown(e.message ?: e::class.simpleName.orEmpty())
    }
}
```

#### 4A — Ktor Client: `safeCall` / `safeRequest`

```kotlin
// {{MODULE_DATA}}/core/network/SafeCall.kt
internal inline fun <T> safeCall(block: () -> T): ApiResult<T> = try {
    ApiResult.Success(block())
} catch (e: CancellationException) {
    throw e                                   // CORO-004: không nuốt cancellation
} catch (e: Exception) {
    ApiResult.Error(ErrorMapper.fromThrowable(e))
}

internal suspend inline fun <reified T> HttpClient.safeRequest(
    block: HttpRequestBuilder.() -> Unit,
): ApiResult<T> = safeCall {
    val response = request(block)
    if (!response.status.isSuccess()) {
        return ApiResult.Error(ErrorMapper.fromStatus(response.status.value)) // khi expectSuccess = false
    }
    response.body<T>()
}
```

#### 4B — Retrofit: `ApiResultCallAdapterFactory`

```kotlin
// {{MODULE_DATA}}/core/network/ApiResultCallAdapterFactory.kt
internal class ApiResultCallAdapterFactory : CallAdapter.Factory() {
    override fun get(returnType: Type, annotations: Array<out Annotation>, retrofit: Retrofit): CallAdapter<*, *>? {
        if (getRawType(returnType) != Call::class.java || returnType !is ParameterizedType) return null
        val callType = getParameterUpperBound(0, returnType)
        if (getRawType(callType) != ApiResult::class.java || callType !is ParameterizedType) return null
        return ApiResultCallAdapter<Any>(successType = getParameterUpperBound(0, callType))
    }
}

private class ApiResultCallAdapter<T : Any>(
    private val successType: Type,
) : CallAdapter<T, Call<ApiResult<T>>> {
    override fun responseType(): Type = successType
    override fun adapt(call: Call<T>): Call<ApiResult<T>> = ApiResultCall(call, successType)
}

private class ApiResultCall<T : Any>(
    private val delegate: Call<T>,
    private val successType: Type,
) : Call<ApiResult<T>> {

    override fun enqueue(callback: Callback<ApiResult<T>>) {
        delegate.enqueue(object : Callback<T> {
            override fun onResponse(call: Call<T>, response: Response<T>) {
                callback.onResponse(this@ApiResultCall, Response.success(response.toApiResult()))
            }

            override fun onFailure(call: Call<T>, t: Throwable) {
                // IOException (kể cả OkHttp callTimeout), SerializationException từ converter, ...
                // Coroutine bị cancel: Retrofit đã resume continuation bằng cancellation, callback này bị bỏ qua
                callback.onResponse(this@ApiResultCall, Response.success(ApiResult.Error(ErrorMapper.fromThrowable(t))))
            }
        })
    }

    @Suppress("UNCHECKED_CAST")
    private fun Response<T>.toApiResult(): ApiResult<T> {
        if (!isSuccessful) return ApiResult.Error(ErrorMapper.fromStatus(code()))
        val body = body()
        return when {
            body != null -> ApiResult.Success(body)
            successType == Unit::class.java -> ApiResult.Success(Unit as T)   // 204 / 205
            else -> ApiResult.Error(DomainError.Parse("Empty body"))
        }
    }

    override fun clone(): Call<ApiResult<T>> = ApiResultCall(delegate.clone(), successType)
    override fun execute(): Response<ApiResult<T>> =
        throw UnsupportedOperationException("ApiResultCall chỉ hỗ trợ suspend fun")
    override fun isExecuted(): Boolean = delegate.isExecuted
    override fun cancel() = delegate.cancel()
    override fun isCanceled(): Boolean = delegate.isCanceled
    override fun request(): Request = delegate.request()
    override fun timeout(): Timeout = delegate.timeout()
}
```

Đăng ký vào builder:

```kotlin
Retrofit.Builder()
    .baseUrl(BuildConfig.BASE_URL)
    .client(okHttp)
    .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
    .addCallAdapterFactory(ApiResultCallAdapterFactory())
    .build()
```

#### 4C — Ktorfit: `ApiResultConverterFactory`

```kotlin
// {{MODULE_DATA}}/core/network/ApiResultConverterFactory.kt
internal class ApiResultConverterFactory : Converter.Factory {

    override fun suspendResponseConverter(
        typeData: TypeData,
        ktorfit: Ktorfit,
    ): Converter.SuspendResponseConverter<HttpResponse, *>? {
        if (typeData.typeInfo.type != ApiResult::class) return null
        val successType = typeData.typeArgs.first().typeInfo

        return object : Converter.SuspendResponseConverter<HttpResponse, ApiResult<Any?>> {
            override suspend fun convert(result: KtorfitResult): ApiResult<Any?> = when (result) {
                is KtorfitResult.Failure -> {
                    val error = result.throwable
                    // Ktorfit bọc MỌI exception (kể cả CancellationException) vào Failure → phải rethrow
                    if (error is CancellationException) throw error
                    ApiResult.Error(ErrorMapper.fromThrowable(error))
                }
                is KtorfitResult.Success -> try {
                    val response = result.response
                    if (response.status.isSuccess()) {
                        ApiResult.Success(response.body(successType))
                    } else {
                        ApiResult.Error(ErrorMapper.fromStatus(response.status.value)) // khi expectSuccess = false
                    }
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    ApiResult.Error(ErrorMapper.fromThrowable(e))                // body parse lỗi → Parse
                }
            }
        }
    }
}
```

Đăng ký vào builder:

```kotlin
Ktorfit.Builder()
    .httpClient(httpClient)
    .baseUrl(BuildConfig.BASE_URL)
    .converterFactories(ApiResultConverterFactory())
    .build()
```

**Rules**:
- `CancellationException` luôn rethrow (CORO-004) — Ktorfit bọc cả cancellation vào `KtorfitResult.Failure`, nên dòng rethrow trong converter là bắt buộc
- Không `withContext(ioDispatcher)` quanh network call — suspend call của Retrofit / Ktor / Ktorfit đã main-safe

### Step 5 — Repository impl

Impl là class thuần, chỉ implement interface domain và map DTO → domain (ARCH-004):

```kotlin
// {{MODULE_DATA}}/repository/BookRepositoryImpl.kt
internal class BookRepositoryImpl(
    private val api: BookApi,
) : BookRepository {

    override suspend fun getBook(id: String): ApiResult<Book> =
        api.getBook(id).map { it.toDomain() }

    override suspend fun searchBooks(query: String): ApiResult<List<Book>> =
        api.searchBooks(query).map { dtos -> dtos.map { it.toDomain() } }
}
```

Kết hợp nhiều call: `flatMap` (call sau phụ thuộc call trước), `onSuccess` (ghi cache local).

### Step 6 — Test

Chọn mock tool theo lib:
- Ktor / Ktorfit → `MockEngine` (Ktor built-in)
- Retrofit → `MockWebServer` (OkHttp lib)

Test contract lỗi ở **tầng API** (assert `ApiResult.Error(DomainError.X)`); Repository test chỉ cần fake API trả `ApiResult`. Example dưới là **Ktor MockEngine**. MockWebServer snippet xem `knowledge/coding/data/network.md [KB → develop/coding-data, kb_search "data network"] §Testing với MockWebServer`.

```kotlin
val bookMockEngine = MockEngine { request ->
    when (request.url.encodedPath) {
        "/v1/books/book-1" -> respond(
            content = """{"id":"book-1","title":"Atomic","author":"Clear","cover_url":"x","duration":1000}""",
            headers = headersOf(HttpHeaders.ContentType, "application/json"),
        )
        "/v1/books/offline" -> throw IOException("offline")
        else -> respond("", status = HttpStatusCode.NotFound)
    }
}

class BookApiTest {
    private val client = HttpClient(bookMockEngine) {
        install(ContentNegotiation) { json(Json { ignoreUnknownKeys = true }) }
        expectSuccess = true
    }
    private val api = BookApi(client)

    @Test
    fun `getBook success`() = runTest {
        val result = api.getBook("book-1")
        assertEquals("Atomic", (result as ApiResult.Success).data.title)
    }

    @Test
    fun `getBook 404 returns NotFound`() = runTest {
        assertEquals(ApiResult.Error(DomainError.NotFound), api.getBook("missing"))
    }

    @Test
    fun `getBook io failure returns Offline`() = runTest {
        assertEquals(ApiResult.Error(DomainError.Network.Offline), api.getBook("offline"))
    }
}

class BookRepositoryImplTest {
    // BookApi (Ktor) là class final → dùng lại MockEngine; Retrofit/Ktorfit API là interface → có thể fake trực tiếp
    private val repo = BookRepositoryImpl(BookApi(HttpClient(bookMockEngine) { install(ContentNegotiation) { json(Json { ignoreUnknownKeys = true }) } }))

    @Test
    fun `getBook maps dto to domain`() = runTest {
        assertEquals("Atomic", (repo.getBook("book-1") as ApiResult.Success).data.title)
    }

    @Test
    fun `getBook error passes through unchanged`() = runTest {
        assertEquals(ApiResult.Error(DomainError.NotFound), repo.getBook("missing"))
    }
}
```

## Required policies

- ARCH-010 Ktor platform engine chỉ ở `data/{androidMain,iosMain}/` qua `expect`
- ARCH-004 Repository impl không kế thừa base class; API trả `ApiResult`
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
// Repository impl — API trả ApiResult<PagedResponse<BookDto>>
suspend fun getBooks(cursor: String? = null, pageSize: Int = 20): ApiResult<Paged<Book>> =
    api.getBooks(cursor, pageSize).map { response ->
        Paged(items = response.items.map { it.toDomain() }, nextCursor = response.nextCursor)
    }
```

### Multipart upload

```kotlin
// API class (remote/) — request không đi qua safeRequest → bọc safeCall
suspend fun uploadAvatar(bytes: ByteArray, mime: String): ApiResult<Unit> = safeCall {
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
// API class (remote/)
suspend fun downloadFile(url: String, dest: Path): ApiResult<Unit> = safeCall {
    client.prepareGet(url).execute { response ->
        response.bodyAsChannel().copyAndClose(dest.sink())
    }
}
```

## Common mistakes

| Mistake | Fix |
|---|---|
| API class trả DTO thô (`client.get(...).body()`) → exception lọt lên Repository | Trả `ApiResult<Dto>` qua `safeRequest` / CallAdapter / Converter |
| Quên rethrow `CancellationException` trong converter/helper | Rethrow trước khi map (CORO-004) |
| Bọc network call bằng `withContext(ioDispatcher)` | Bỏ — suspend call của Retrofit/Ktor/Ktorfit đã main-safe |
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
- API service trả `ApiResult<Dto>` (Retrofit `ApiResultCallAdapterFactory` / Ktorfit `ApiResultConverterFactory` / Ktor `safeRequest`), mapping ở `ErrorMapper`
- Repository impl không kế thừa base class, chỉ `api.x().map { it.toDomain() }` (ARCH-004)
- HttpClient singleton qua Koin
- Unit test API với `MockEngine` / `MockWebServer` cho ít nhất: happy path, 404, network error — assert `ApiResult.Error(DomainError.X)`

## Anti-patterns bị cấm

- DTO leak ngoài data module (public hoặc internal visible cross-module)
- Business logic trong API class / DTO
- Hardcode secret/token trong code
- Retry policy bất kể error type
- `GlobalScope.launch` cho network call
- Throw raw exception từ Repository public method (phải map `ApiResult`)

---

## Harness context

- Workflow: `workflows/feature-development.md`
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`


## Overlay gate (D-full)

Trước Step 1, verify `.harness-overlay/overlay.yaml` tồn tại. Nếu không, abort với status `BLOCKED` và chỉ dẫn user:

> Chưa có overlay. Chạy skill `harness-init` để scaffold trước, sau đó quay lại skill này.

Khi gặp placeholder `{{X}}` trong procedure/code example, resolve bằng mapping ở `AGENTS.md §Placeholder resolution` (Read overlay 1 lần đầu session, cache qua context).
