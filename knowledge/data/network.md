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

## Error type mapping

| Exception | DomainError |
|---|---|
| `IOException` | `Network.Offline` |
| `HttpRequestTimeoutException` | `Network.Timeout` |
| `ClientRequestException` (4xx) | `Client(code)` hoặc `NotFound` / `Auth.*` |
| `ServerResponseException` (5xx) | `Server(code)` |
| `SerializationException` | `Parse(message)` |
| Other | `Unknown(message)` |

Mapping ở `BaseRepository.mapError` (xem `skills/android-network`).

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

**Rule**: không catch broad `Exception` nuốt `CancellationException` (CORO-004).

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
client.post("/v1/books") {
    contentType(ContentType.Application.Json)
    setBody(CreateBookRequest(title = "...", author = "..."))
}.body<BookDto>()
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
client.prepareGet(url).execute { response ->
    val channel = response.bodyAsChannel()
    channel.copyAndClose(dest.sink())
}
```

### Pagination (cursor-based preferred)

```kotlin
@Serializable
data class PagedResponse<T>(
    val items: List<T>,
    val nextCursor: String? = null,
)

suspend fun loadPage(cursor: String? = null): PagedResponse<BookDto> =
    client.get("/v1/books") {
        cursor?.let { parameter("cursor", it) }
    }.body()
```

## Testing với MockEngine

```kotlin
val mockEngine = MockEngine { request ->
    when (request.url.encodedPath) {
        "/v1/books/1" -> respond(
            content = """{"id":"1","title":"Atomic","author":"Clear","cover_url":"x","duration":1000}""",
            headers = headersOf(HttpHeaders.ContentType, "application/json"),
        )
        else -> respond("", status = HttpStatusCode.NotFound)
    }
}
val client = HttpClient(mockEngine) {
    install(ContentNegotiation) { json(Json { ignoreUnknownKeys = true }) }
    expectSuccess = true
}
```

## Common mistakes

| Mistake | Fix |
|---|---|
| `expectSuccess = false` → không throw 4xx | Set `true`, catch ở `BaseRepository` |
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
    suspend fun getBook(@Path("id") id: String): BookDto

    @GET("/v1/books/search")
    suspend fun searchBooks(
        @Query("q") query: String,
        @Query("filter") filter: String? = null,
    ): List<BookDto>

    @POST("/v1/books")
    suspend fun create(@Body req: CreateBookRequest): BookDto
}
```

**Rules**:
- Interface `internal`, không expose cross-module
- `suspend fun` — Retrofit 2.6+ hỗ trợ native
- Null body auto-throw `KotlinNullPointerException` → map thành `DomainError` ở Repository

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
            val refreshed = authApi.refresh(authStorage.refreshToken()).getOrNull() ?: return@withLock null
            authStorage.save(refreshed)
            response.request.newBuilder()
                .header("Authorization", "Bearer ${refreshed.accessToken}")
                .build()
        }
    }
}
```

### Repository impl (same pattern)

```kotlin
internal class BookRepositoryImpl(
    private val api: BookApi,
    ioDispatcher: CoroutineDispatcher,
) : BaseRepository(ioDispatcher), BookRepository {

    override suspend fun getBook(id: String): ApiResult<Book> = apiCall {
        api.getBook(id).toDomain()
    }
}
```

### Error mapping (adapt cho Retrofit exceptions)

```kotlin
private fun mapError(e: Throwable): DomainError = when (e) {
    is IOException -> DomainError.Network.Offline
    is SocketTimeoutException -> DomainError.Network.Timeout
    is HttpException -> when (e.code()) {
        401 -> DomainError.Auth.Unauthenticated
        403 -> DomainError.Auth.Forbidden
        404 -> DomainError.NotFound
        in 400..499 -> DomainError.Client(e.code())
        in 500..599 -> DomainError.Server(e.code())
        else -> DomainError.Unknown(e.message ?: "")
    }
    is SerializationException -> DomainError.Parse(e.message ?: "")
    else -> DomainError.Unknown(e.message ?: "")
}
```

### Testing với MockWebServer

```kotlin
class BookApiTest {
    private val server = MockWebServer()
    private val retrofit = Retrofit.Builder()
        .baseUrl(server.url("/"))
        .addConverterFactory(Json.asConverterFactory("application/json".toMediaType()))
        .build()
    private val api = retrofit.create(BookApi::class.java)

    @BeforeTest fun setup() { server.start() }
    @AfterTest fun teardown() { server.shutdown() }

    @Test
    fun `getBook success`() = runTest {
        server.enqueue(MockResponse().setBody("""{"id":"1","title":"Atomic"}"""))
        val result = api.getBook("1")
        assertEquals("Atomic", result.title)
    }
}
```

---

## Option 3 — Ktorfit (KMP + annotation)

Ktor Client + annotation processor giống Retrofit. Dùng khi muốn **KMP + Retrofit-style type-safe interface**.

### Setup

```kotlin
// libs.versions.toml
ktorfit = "2.1.0"
ktor = "3.1.0"

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
    suspend fun getBook(@Path("id") id: String): BookDto

    @GET("/v1/books/search")
    suspend fun searchBooks(
        @Query("q") query: String,
        @Query("filter") filter: String? = null,
    ): List<BookDto>

    @POST("/v1/books")
    suspend fun create(@Body req: CreateBookRequest): BookDto
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
        .build()
}

single { get<Ktorfit>().createBookApi() }    // generated extension function
```

### Error handling

Ktorfit sử dụng Ktor exception → `mapError` giống Ktor Client option.

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
