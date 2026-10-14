# Network — Essentials

Networking lib selection phụ thuộc target platform. Harness support 3 options chính qua `stack.network` trong `overlay.yaml`.

## Library selection

| Target | Recommended | Alternative | Note |
|---|---|---|---|
| **Android-only** | **Retrofit** (+ OkHttp) | Ktor Client | Mature ecosystem; interceptor familiar; large community |
| **KMP / CMP** (shared network) | **Ktor Client 3.x** | Ktorfit | Platform engines expect/actual; cross-platform native |
| **KMP annotation-based** (Retrofit-style) | **Ktorfit** (= Ktor + annotation processor) | Ktor manual | Type-safe interface + KMP support; mix tốt với Retrofit mindset |

### Decision guide

```
Target: Android-only?
  ├─ YES → Retrofit (hoặc Ktor nếu team đã dùng)
  └─ NO (KMP/CMP) → tiếp
       │
       └─ Prefer annotation interface (Retrofit-style)?
           ├─ YES → Ktorfit
           └─ NO  → Ktor Client manual
```

### Khi migrate Retrofit → Ktor/Ktorfit

Trigger: Android app chuyển sang CMP, hoặc share logic với iOS.

Migration path:
1. Add Ktor dep song song, giữ Retrofit
2. Convert endpoints incrementally (new feature dùng Ktor, legacy stay Retrofit)
3. Verify behavior parity qua test
4. Remove Retrofit sau khi 100% migrate

## Common patterns across libs

Config checklist chung cho mọi lib:

- `expectSuccess`/`throwOnFailure` — throw cho non-2xx (consistent error path)
- JSON parse với tolerant mode: `ignoreUnknownKeys`, `coerceInputValues`, default values
- Timeout cụ thể (request / connect / socket), never infinite
- Retry: 5xx + 408 + 429; **không** retry 4xx client error
- Log sanitize: no token / API key / PII
- Base URL + default header (version, platform) qua interceptor/plugin
- Auth: bearer token với auto refresh flow

## ApiResult contract (mọi lib)

API service trả `ApiResult<Dto>` **trực tiếp**. Exception → `DomainError` được map một lần tại tầng network, không ở Repository:

| `stack.network` | Cơ chế | Đăng ký |
|---|---|---|
| `retrofit` | `ApiResultCallAdapterFactory` (`CallAdapter.Factory`) | `Retrofit.Builder().addCallAdapterFactory(...)` |
| `ktorfit` | `ApiResultConverterFactory` (`Converter.Factory` + `SuspendResponseConverter`) | `Ktorfit.Builder().converterFactories(...)` |
| `ktor` | Extension `HttpClient.safeRequest<T> { }` (dựng trên `safeCall { }`) | Gọi trong API class |

Repository impl không kế thừa base class, chỉ map DTO → domain: `api.getBook(id).map { it.toDomain() }` (ARCH-004).

### `ApiResult` + extensions

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

Extension là `inline` → lambda gọi được `suspend fun` (ví dụ `local.upsert(...)` trong `onSuccess`). `DomainError` định nghĩa ở `{{MODULE_DOMAIN}}/core/` (xem `skills/android-network §Error contract`).

### Error mapping — `ErrorMapper`

Một `internal object ErrorMapper` ở `{{MODULE_DATA}}/core/network/ErrorMapper.kt`, dùng chung cho adapter / converter / `safeCall`. `fromStatus` giống nhau mọi lib; `fromThrowable` chọn variant theo `stack.network` (Retrofit và Ktor không cùng classpath trong KMP `commonMain`).

| Nguyên nhân | Ktor / Ktorfit | Retrofit (OkHttp) | `DomainError` |
|---|---|---|---|
| Timeout | `HttpRequestTimeoutException`, `ConnectTimeoutException`, `SocketTimeoutException` (Ktor) | `InterruptedIOException` (gồm `SocketTimeoutException` + call timeout) | `Network.Timeout` |
| Mất mạng / IO | `kotlinx.io.IOException` | `java.io.IOException` | `Network.Offline` |
| HTTP 401 / 403 / 404 | `ResponseException` → `fromStatus` | response non-2xx → `fromStatus` | `Auth.Unauthenticated` / `Auth.Forbidden` / `NotFound` |
| HTTP 4xx khác / 5xx | `ResponseException` → `fromStatus` | response non-2xx → `fromStatus` | `Client(code)` / `Server(code)` |
| JSON lỗi | `ContentConvertException` (Ktor bọc thành `JsonConvertException`), `SerializationException` | `SerializationException` (từ converter) | `Parse(message)` |
| Body rỗng cho type khác `Unit` | — | 204/205 `body() == null` | `Parse("Empty body")` |
| Khác | — | — | `Unknown(message)` |

**Thứ tự `when` quan trọng**: timeout exception là subclass của `IOException` → match timeout **trước** `IOException`. `CancellationException` không bao giờ đi vào `ErrorMapper` — adapter/converter/`safeCall` rethrow trước (CORO-004).

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

```kotlin
// {{MODULE_DATA}}/core/network/ErrorMapper.kt — stack.network = retrofit
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
        is InterruptedIOException -> DomainError.Network.Timeout          // SocketTimeoutException + OkHttp call timeout
        is IOException -> DomainError.Network.Offline
        is HttpException -> fromStatus(e.code())
        is SerializationException -> DomainError.Parse(e.message.orEmpty())
        else -> DomainError.Unknown(e.message ?: e::class.simpleName.orEmpty())
    }
}
```

### Dispatcher

Retrofit (suspend), Ktor và Ktorfit đều main-safe → **không** bọc network call bằng `withContext(ioDispatcher)`. Chỉ giữ `withContext` cho IO blocking thật (query SQLDelight đồng bộ, file) tại local source sở hữu IO đó (CORO-002).

---

## Option 1 — Ktor Client (KMP/CMP)

Ktor Client 3.x. Platform engine qua `expect/actual`.

## HttpClient config checklist

- `expectSuccess = true` — throw cho 4xx/5xx (consistent error path)
- `ContentNegotiation` + `kotlinx.serialization` — JSON parse
- `HttpTimeout` — request / connect / socket (never infinite)
- `HttpRequestRetry` — retry server errors + exponential backoff (**không** retry 4xx)
- `Logging` — level BODY debug, NONE release; `sanitizeHeader` cho Authorization + API key
- `DefaultRequest` — base URL + default header (version, platform)
- `Auth` plugin — bearer token refresh flow

## JSON config

```kotlin
Json {
    ignoreUnknownKeys = true    // tolerant khi API add field
    coerceInputValues = true    // null → default khi field có default
    encodeDefaults = true       // serialize default values ra wire
    explicitNulls = false       // không serialize null fields
}
```

## DTO conventions

- `@Serializable` + `data class`
- Nullable field → có default: `val x: String? = null`
- Non-null expected → có default fallback: `val count: Int = 0`
- `@SerialName("snake_case")` khi JSON key khác convention
- DTO **không** cross-module (keep `internal`)

## Auth strategies

### Bearer token refresh

```kotlin
install(Auth) {
    bearer {
        loadTokens {
            BearerTokens(authStorage.accessToken(), authStorage.refreshToken())
        }
        refreshTokens {
            val new = authApi.refresh(oldTokens?.refreshToken ?: return@refreshTokens null)
            authStorage.save(new)
            BearerTokens(new.accessToken, new.refreshToken)
        }
    }
}
```

### API key header

```kotlin
install(DefaultRequest) {
    header("X-Api-Key", BuildConfig.API_KEY)
}
```

API key **không** hardcode trong code → BuildConfig từ `local.properties` không commit.

## Platform engine (ARCH-010)

```kotlin
// commonMain
expect fun engineProvider(): HttpClientEngineFactory<*>

// androidMain
actual fun engineProvider(): HttpClientEngineFactory<*> = OkHttp

// iosMain
actual fun engineProvider(): HttpClientEngineFactory<*> = Darwin
```

Engine chọn:
- Android: `OkHttp` (familiar, interceptor ecosystem)
- iOS: `Darwin` (native URLSession, tốt pin certificate)
- Shared: `CIO` (pure Kotlin, no platform dep nếu không cần)

## Ktor Client — `safeCall` / `safeRequest`

Ktor Client thuần không có converter cho kiểu trả về → dùng 2 helper ở `{{MODULE_DATA}}/core/network/SafeCall.kt`. Đây là chỗ **duy nhất** có try/catch cho network; chỉ gọi từ API class trong `remote/`, không gọi từ Repository.

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

```kotlin
// {{MODULE_DATA}}/remote/BookApi.kt
internal class BookApi(private val client: HttpClient) {
    suspend fun getBook(id: String): ApiResult<BookDto> =
        client.safeRequest { url("/v1/books/$id") }

    suspend fun create(req: CreateBookRequest): ApiResult<BookDto> =
        client.safeRequest {
            method = HttpMethod.Post
            url("/v1/books")
            contentType(ContentType.Application.Json)
            setBody(req)
        }
}
```

`safeRequest` mặc định `GET` (method của `HttpRequestBuilder`). Request không đi qua `body<T>()` (stream download, multipart cần đọc response thủ công) → bọc bằng `safeCall { }`.

## Retry policy

- **MUST** retry 5xx server error (2-3 attempts, exponential backoff)
- **FORBIDDEN** retry 4xx (except 408 timeout, 429 rate limit)
- **FORBIDDEN** retry POST không idempotent (write side-effect)
- **SHOULD** retry transient IO exception

```kotlin
install(HttpRequestRetry) {
    retryOnServerErrors(maxRetries = 2)
    retryOnException(maxRetries = 2, retryOnTimeout = false)
    exponentialDelay(base = 2.0, baseDelayMs = 500, maxDelayMs = 5_000)
}
```

## Request cancellation

Ktor suspend function cancel qua coroutine cancellation. Khi `viewModelScope` cancelled (screen leave) → request tự abort.

**Rule**: không catch broad `Exception` nuốt `CancellationException` (CORO-004). `safeCall`, `ApiResultCallAdapterFactory`, `ApiResultConverterFactory` đều rethrow cancellation.

## Common patterns

### Query params

```kotlin
client.get("/v1/books") {
    parameter("page", page)
    parameter("filter", filter)
}
```

### Request body

```kotlin
client.safeRequest<BookDto> {
    method = HttpMethod.Post
    url("/v1/books")
    contentType(ContentType.Application.Json)
    setBody(CreateBookRequest(title = "...", author = "..."))
}
```

### Multipart upload

```kotlin
client.submitFormWithBinaryData(
    url = "/v1/upload",
    formData = formData {
        append("file", bytes, Headers.build {
            append(HttpHeaders.ContentType, "image/jpeg")
            append(HttpHeaders.ContentDisposition, "filename=\"avatar.jpg\"")
        })
    },
)
```

### Stream large response

```kotlin
suspend fun download(url: String, dest: Path): ApiResult<Unit> = safeCall {
    client.prepareGet(url).execute { response ->
        response.bodyAsChannel().copyAndClose(dest.sink())
    }
}
```

### Pagination (cursor-based preferred)

```kotlin
@Serializable
data class PagedResponse<T>(
    val items: List<T>,
    val nextCursor: String? = null,
)

suspend fun loadPage(cursor: String? = null): ApiResult<PagedResponse<BookDto>> =
    client.safeRequest {
        url("/v1/books")
        cursor?.let { parameter("cursor", it) }
    }
```

## Testing với MockEngine

Assert `ApiResult` ngay ở tầng API — contract lỗi được test một lần, Repository test chỉ cần fake API.

```kotlin
class BookApiTest {
    private val mockEngine = MockEngine { request ->
        when (request.url.encodedPath) {
            "/v1/books/1" -> respond(
                content = """{"id":"1","title":"Atomic","author":"Clear","cover_url":"x","duration":1000}""",
                headers = headersOf(HttpHeaders.ContentType, "application/json"),
            )
            else -> respond("", status = HttpStatusCode.NotFound)
        }
    }
    private val client = HttpClient(mockEngine) {
        install(ContentNegotiation) { json(Json { ignoreUnknownKeys = true }) }
        expectSuccess = true
    }
    private val api = BookApi(client)

    @Test
    fun `getBook success`() = runTest {
        val result = api.getBook("1")
        assertEquals("Atomic", (result as ApiResult.Success).data.title)
    }

    @Test
    fun `getBook 404 maps to NotFound`() = runTest {
        assertEquals(ApiResult.Error(DomainError.NotFound), api.getBook("missing"))
    }
}
```

## Common mistakes

| Mistake | Fix |
|---|---|
| Gọi `client.get(...).body()` thô trong API class → exception lọt lên Repository | Dùng `safeRequest` / `safeCall`, API trả `ApiResult<Dto>` |
| Bọc network call bằng `withContext(ioDispatcher)` | Bỏ — Ktor suspend call đã main-safe |
| Log full Authorization header | `sanitizeHeader { it == HttpHeaders.Authorization }` |
| Hardcode token/API key trong code | BuildConfig + local.properties (gitignored) |
| DTO leak cross-module | Keep `internal`, map sang domain |
| Retry 4xx mù | Chỉ 5xx + 408 + 429 |
| Infinite timeout default | Specific per-field (request 30s, connect 10s) |
| No `ignoreUnknownKeys` → crash khi API add field | Set `true` for forward compat |
| Serialize `null` field cho API không chấp nhận | `explicitNulls = false` |

---

## Option 2 — Retrofit (Android-only)

Retrofit 2.x + OkHttp 4.x. Dành cho **Android-only** project; không support KMP native.

### Setup

```kotlin
// build.gradle.kts (:data)
dependencies {
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-kotlinx-serialization:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
}
```

### Service interface

```kotlin
internal interface BookApi {
    @GET("/v1/books/{id}")
    suspend fun getBook(@Path("id") id: String): ApiResult<BookDto>

    @GET("/v1/books/search")
    suspend fun searchBooks(
        @Query("q") query: String,
        @Query("filter") filter: String? = null,
    ): ApiResult<List<BookDto>>

    @POST("/v1/books")
    suspend fun create(@Body req: CreateBookRequest): ApiResult<BookDto>

    @DELETE("/v1/books/{id}")
    suspend fun delete(@Path("id") id: String): ApiResult<Unit>   // 204 → Success(Unit)
}
```

**Rules**:
- Interface `internal`, không expose cross-module
- `suspend fun` trả `ApiResult<Dto>` — `ApiResultCallAdapterFactory` lo map lỗi, không có exception nào lọt ra
- 204/205 body rỗng → `Success(Unit)` nếu kiểu là `Unit`, ngược lại `Error(Parse("Empty body"))`

### Retrofit builder

```kotlin
// {{MODULE_DATA}}/di/DataModule.kt
single {
    val okHttp = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .addInterceptor(createAuthInterceptor(get()))
        .addInterceptor(createDefaultHeaderInterceptor())
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY else HttpLoggingInterceptor.Level.NONE
            redactHeader("Authorization")
            redactHeader("X-Api-Key")
        })
        .build()

    Retrofit.Builder()
        .baseUrl(BuildConfig.BASE_URL)
        .client(okHttp)
        .addConverterFactory(
            Json {
                ignoreUnknownKeys = true
                coerceInputValues = true
            }.asConverterFactory("application/json".toMediaType())
        )
        .addCallAdapterFactory(ApiResultCallAdapterFactory())
        .build()
}

single { get<Retrofit>().create(BookApi::class.java) }
```

### Auth interceptor + token refresh

```kotlin
internal class AuthInterceptor(
    private val authStorage: AuthStorage,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        if (request.header("Authorization") != null) return chain.proceed(request)

        val token = authStorage.accessToken()
        val authenticated = request.newBuilder()
            .header("Authorization", "Bearer $token")
            .build()
        return chain.proceed(authenticated)
    }
}

internal class TokenAuthenticator(
    private val authStorage: AuthStorage,
    private val authApi: AuthApi,
) : Authenticator {
    private val mutex = Mutex()

    override fun authenticate(route: Route?, response: Response): Request? = runBlocking {
        mutex.withLock {
            val currentToken = authStorage.accessToken()
            val requestToken = response.request.header("Authorization")?.removePrefix("Bearer ")
            if (currentToken != requestToken) {
                return@withLock response.request.newBuilder()
                    .header("Authorization", "Bearer $currentToken")
                    .build()
            }
            val refreshed = authApi.refresh(authStorage.refreshToken()).getOrNull() ?: return@withLock null  // ApiResult.getOrNull()
            authStorage.save(refreshed)
            response.request.newBuilder()
                .header("Authorization", "Bearer ${refreshed.accessToken}")
                .build()
        }
    }
}
```

### `ApiResultCallAdapterFactory`

Với `suspend fun getBook(): ApiResult<BookDto>`, Retrofit hỏi adapter cho kiểu `Call<ApiResult<BookDto>>`. Adapter khai báo `responseType() = BookDto` (để converter JSON parse đúng kiểu) và bọc `Call<BookDto>` thành `Call<ApiResult<BookDto>>` luôn trả `Response.success(...)`:

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

Đăng ký: `.addCallAdapterFactory(ApiResultCallAdapterFactory())` trong Retrofit builder (xem trên). Chỉ dùng cho `suspend fun` — khai báo non-suspend `Call<ApiResult<T>>` sẽ fail ở `execute()`. `ErrorMapper` dùng variant Retrofit (xem §ApiResult contract).

### Repository impl

```kotlin
internal class BookRepositoryImpl(
    private val api: BookApi,
) : BookRepository {

    override suspend fun getBook(id: String): ApiResult<Book> =
        api.getBook(id).map { it.toDomain() }
}
```

### Testing với MockWebServer

```kotlin
class BookApiTest {
    private val server = MockWebServer()
    private lateinit var api: BookApi

    @BeforeTest fun setup() {
        server.start()
        api = Retrofit.Builder()
            .baseUrl(server.url("/"))
            .addConverterFactory(Json.asConverterFactory("application/json".toMediaType()))
            .addCallAdapterFactory(ApiResultCallAdapterFactory())
            .build()
            .create(BookApi::class.java)
    }
    @AfterTest fun teardown() { server.shutdown() }

    @Test
    fun `getBook success`() = runTest {
        server.enqueue(MockResponse().setBody("""{"id":"1","title":"Atomic"}"""))
        val result = api.getBook("1")
        assertEquals("Atomic", (result as ApiResult.Success).data.title)
    }

    @Test
    fun `getBook 404 maps to NotFound`() = runTest {
        server.enqueue(MockResponse().setResponseCode(404))
        assertEquals(ApiResult.Error(DomainError.NotFound), api.getBook("1"))
    }

    @Test
    fun `disconnect maps to Offline`() = runTest {
        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AT_START))
        assertEquals(ApiResult.Error(DomainError.Network.Offline), api.getBook("1"))
    }
}
```

---

## Option 3 — Ktorfit (KMP + annotation)

Ktor Client + annotation processor giống Retrofit. Dùng khi muốn **KMP + Retrofit-style type-safe interface**.

### Setup

```kotlin
// libs.versions.toml
ktorfit = "2.7.3"   # ApiResultConverterFactory verified trên 2.7.3 (KtorfitResult API)
ktor = "3.3.3"

[plugins]
ktorfit = { id = "de.jensklingenberg.ktorfit", version.ref = "ktorfit" }
```

```kotlin
// build.gradle.kts (:data)
plugins {
    alias(libs.plugins.ktorfit)
}

dependencies {
    implementation(libs.ktor.client.core)
    implementation(libs.ktor.serialization.kotlinx.json)
    implementation("de.jensklingenberg.ktorfit:ktorfit-lib:$ktorfit")
}
```

### Service interface (Retrofit-style annotation)

```kotlin
internal interface BookApi {
    @GET("/v1/books/{id}")
    suspend fun getBook(@Path("id") id: String): ApiResult<BookDto>

    @GET("/v1/books/search")
    suspend fun searchBooks(
        @Query("q") query: String,
        @Query("filter") filter: String? = null,
    ): ApiResult<List<BookDto>>

    @POST("/v1/books")
    suspend fun create(@Body req: CreateBookRequest): ApiResult<BookDto>
}
```

Giống Retrofit **100%** interface shape — migration dễ.

### Ktorfit builder

```kotlin
// commonMain DataModule
single {
    val httpClient = HttpClient(engineProvider()) {
        expectSuccess = true
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                coerceInputValues = true
            })
        }
        install(HttpTimeout) {
            requestTimeoutMillis = 30_000
        }
    }
    Ktorfit.Builder()
        .httpClient(httpClient)
        .baseUrl(BuildConfig.BASE_URL)
        .converterFactories(ApiResultConverterFactory())
        .build()
}

single { get<Ktorfit>().createBookApi() }    // generated extension function
```

### `ApiResultConverterFactory`

Ktorfit gọi `suspendResponseConverter` cho mỗi `suspend fun` có kiểu trả về khớp. Factory trả `null` cho kiểu khác → Ktorfit dùng converter mặc định.

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

Đăng ký: `.converterFactories(ApiResultConverterFactory())` trong `Ktorfit.Builder()` (xem trên). Converter không phụ thuộc `expectSuccess`: `true` → lỗi HTTP tới dưới dạng `Failure(ResponseException)`; `false` → tới dưới dạng `Success` với status non-2xx. `ErrorMapper` dùng variant Ktor.

Test: dùng `MockEngine` như Option 1, build `Ktorfit` với `httpClient(HttpClient(mockEngine))` + `converterFactories(ApiResultConverterFactory())`, assert `ApiResult.Error(DomainError.NotFound)` từ `api.getBook("missing")`.

### Why Ktorfit over Ktor manual

- **Type-safe interface** compile-time check
- **Familiar** cho team đến từ Retrofit background
- **KMP support** full
- **Dependencies**: hơn Ktor 1 annotation processor (slower build), nhưng DX tốt hơn

### Why Ktor manual over Ktorfit

- **Simpler** build (không annotation processor)
- **Flexibility** cao hơn (manual url builder, headers per request)
- **No extra dep**: giảm attack surface

---

## Migration từ BaseRepository

Product đang dùng pattern cũ (`Repository impl : BaseRepository(ioDispatcher)` + `apiCall { }`):

1. Thêm `ErrorMapper` (chuyển nội dung `BaseRepository.mapError` sang, đổi thứ tự cho timeout đứng trước `IOException`) và extension `map` / `flatMap` / `onSuccess` / `getOrNull` cho `ApiResult`.
2. Đăng ký adapter theo `stack.network`: Retrofit `addCallAdapterFactory(ApiResultCallAdapterFactory())`, Ktorfit `converterFactories(ApiResultConverterFactory())`, Ktor thuần thêm `safeCall` / `safeRequest`.
3. Đổi kiểu trả về API service từ `Dto` sang `ApiResult<Dto>` (từng service một; compiler chỉ ra mọi call site).
4. Repository impl: bỏ `: BaseRepository(ioDispatcher)` + tham số `ioDispatcher`, thay `apiCall { api.x().toDomain() }` bằng `api.x().map { it.toDomain() }`. Bỏ `get(named("io"))` khỏi DI binding tương ứng.
5. Repository kết hợp remote + local: `api.x().map { it.toDomain() }.onSuccess { local.upsert(it.toEntity(...)) }`. Local source chạy query blocking tự bọc `withContext(ioDispatcher)`.
6. Xoá `BaseRepository.kt` khi không còn subclass; chạy Konsist ARCH-004.

**Ranh giới lỗi**: `ApiResult` chỉ bao network boundary. `apiCall` cũ vô tình bắt cả exception của local DB; sau migration, exception từ local source (Room/SQLDelight) không còn tự map sang `DomainError`. Harness hiện chưa định nghĩa cơ chế wrap lỗi DB — coi exception DB là lỗi lập trình/storage, code trong `onSuccess { local... }` không được throw cho điều kiện mong đợi (ví dụ dùng upsert thay vì insert).

## Comparison table

| Feature | Retrofit | Ktor Client | Ktorfit |
|---|---|---|---|
| Platform | Android | KMP | KMP |
| Interface style | Annotation | Builder (manual) | Annotation |
| Serialization | Converter (kotlinx/moshi/gson) | ContentNegotiation plugin | ContentNegotiation plugin |
| HTTP engine | OkHttp | Platform-specific (OkHttp/Darwin/CIO) | Platform-specific |
| Interceptor | OkHttp Interceptor | Ktor plugin | Ktor plugin |
| Mock test | MockWebServer | MockEngine | MockEngine |
| Learning curve | Low (Java heritage) | Medium | Low cho Retrofit user |
| Code generation | Reflection + proxy | None | KSP annotation processor |
| Build time | Fast | Fast | Slower (KSP) |

## References

- Retrofit: https://square.github.io/retrofit/
- Ktor Client: https://ktor.io/docs/client-create-new-application.html
- Ktorfit: https://foso.github.io/Ktorfit/
- kotlinx.serialization: https://github.com/Kotlin/kotlinx.serialization
- `.harness/skills/android-network/SKILL.md`
