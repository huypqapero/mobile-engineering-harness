# Phase 1 — Core network contract

Goal: `knowledge/data/network.md` và `skills/android-network/SKILL.md` chứa contract canonical mới mà mọi file khác copy theo.

## Task 1.1 — ApiResult extensions + ErrorMapper (network.md)
- Target: `knowledge/data/network.md` — section `## Error type mapping` (dòng ~129-140).
- Steps:
  1. Thay section bằng `## Error mapping — ErrorMapper` gồm: bảng mapping 2 cột lib (Ktor/Ktorfit | Retrofit) → `DomainError`; snippet `internal object ErrorMapper` ở `{{MODULE_DATA}}/core/network/ErrorMapper.kt` với `fun fromStatus(code: Int): DomainError` và `fun fromThrowable(e: Throwable): DomainError`; timeout match trước `IOException`; comment đánh dấu nhánh theo `stack.network`.
  2. Thêm `## ApiResult extensions` với `inline` `map`, `flatMap`, `onSuccess`, `getOrNull` ở `{{MODULE_DOMAIN}}/core/ApiResult.kt`.
- Success: section mới có `ErrorMapper`, `fromStatus`, `fromThrowable`, bảng có cả `HttpException` và `ClientRequestException`.
- Verify: `grep -c "ErrorMapper" knowledge/data/network.md` ≥ 5 and `grep -n "HttpException\|ClientRequestException" knowledge/data/network.md` prints lines inside the table.

## Task 1.2 — Ktor thuần: safeRequest
- Target: `knowledge/data/network.md` Option 1.
- Steps: thêm `### ApiResult contract — safeRequest` snippet `suspend inline fun <reified T> HttpClient.safeRequest(block: HttpRequestBuilder.() -> Unit): ApiResult<T>`; rethrow `CancellationException`; API class ví dụ dùng nó. Sửa Common mistakes row `expectSuccess` (không còn "catch ở BaseRepository").
- Verify: `grep -n "safeRequest" knowledge/data/network.md` ≥ 2 lines; `grep -n "catch (e: CancellationException) { throw e }\|is CancellationException" knowledge/data/network.md` ≥ 1.

## Task 1.3 — Retrofit: ApiResultCallAdapterFactory
- Target: `knowledge/data/network.md` Option 2 — thay `### Repository impl (same pattern)` + `### Error mapping (adapt cho Retrofit exceptions)`.
- Steps: snippet `ApiResultCallAdapterFactory : CallAdapter.Factory()` + `ApiResultCall<T> : Call<ApiResult<T>>` (enqueue always delivers `Response.success(ApiResult)`; non-2xx → `ErrorMapper.fromStatus`; failure → `ErrorMapper.fromThrowable`; empty body + `Unit` → `Success(Unit)`); đăng ký `.addCallAdapterFactory(ApiResultCallAdapterFactory())` trong builder; service interface trả `ApiResult<BookDto>`; repository impl thuần; MockWebServer test assert `ApiResult.Error(DomainError.NotFound)`.
- Verify: `grep -n "addCallAdapterFactory(ApiResultCallAdapterFactory())" knowledge/data/network.md` prints 1 line.

## Task 1.4 — Ktorfit: ApiResultConverterFactory
- Target: `knowledge/data/network.md` Option 3 — `### Error handling`.
- Steps: snippet `ApiResultConverterFactory : Converter.Factory` override `suspendResponseConverter`; `KtorfitResult.Failure` → rethrow nếu `CancellationException`, else `ErrorMapper.fromThrowable`; `Success` → `response.body(typeData.typeArgs.first().typeInfo)` trong try/catch rethrow cancellation; đăng ký `.converterFactories(ApiResultConverterFactory())`.
- Verify: `grep -n "converterFactories(ApiResultConverterFactory())" knowledge/data/network.md` prints 1 line.

## Task 1.5 — Migration section + MockEngine test
- Steps: thêm `## Migration từ BaseRepository` (5 bước ngắn) trước `## Comparison table`; cập nhật `## Testing với MockEngine` thành test API trả `ApiResult.Error(DomainError.NotFound)`.
- Verify: `grep -n "^## Migration từ BaseRepository" knowledge/data/network.md` prints 1 line.

## Task 1.6 — skills/android-network/SKILL.md
- Steps: Prerequisites #4 → `ApiResult` + `DomainError` (domain/core) + `ErrorMapper` (data/core/network); Step 2 rules: non-2xx mapped bởi adapter/converter/safeRequest; Variants A/B/C trả `ApiResult<Dto>`; Step 3 thêm đăng ký adapter/converter; Step 4 → "ErrorMapper + adapter" với snippet `ErrorMapper` + `ApiResultCallAdapterFactory` + `ApiResultConverterFactory` (đầy đủ, kèm builder); Step 5 repository impl thuần; Step 6 test API-level + repo-level; Common patterns bỏ `apiCall`; Common mistakes + Output contract cập nhật.
- Verify: `grep -c "BaseRepository\|apiCall" skills/android-network/SKILL.md` prints 0; `grep -c "ApiResultCallAdapterFactory\|ApiResultConverterFactory" skills/android-network/SKILL.md` ≥ 4.

## Failure Protocol
If any Verify step does not meet its stated pass condition, STOP this phase.
Do not improvise a fix, retry blindly, or reason around the failure.
Spawn the `kongming` subagent for next-step counsel and pass:
- the phase and task id,
- what you attempted (the steps you ran),
- the exact command and its full output,
- the pass condition it failed to meet.
Apply kongming's guidance, then re-run the Verify step.
If `kongming` cannot be spawned in this environment, STOP and report the same
failure evidence to the user. Never continue by self-reasoning.
