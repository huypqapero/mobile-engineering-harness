# Network — Essentials

Ktor Client 3.x cho Compose Multiplatform. Platform engine qua `expect/actual`.

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

## References

- Ktor Client: https://ktor.io/docs/client-create-new-application.html
- kotlinx.serialization: https://github.com/Kotlin/kotlinx.serialization
- `.harness/skills/android-network/SKILL.md`
