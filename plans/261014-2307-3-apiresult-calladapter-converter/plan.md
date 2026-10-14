---
title: "Bỏ BaseRepository/apiCall, chuẩn hoá ApiResult qua CallAdapter (Retrofit) / Converter (Ktorfit)"
status: completed
issue: 3
branch: refactor/3-apiresult-calladapter-converter
route: feature
mode: official
created: 2026-10-14
---

# Plan — ApiResult tại tầng network, Repository impl không kế thừa base class

Source of truth: https://github.com/huypqapero/mobile-engineering-harness/issues/3

## Outcome

Harness hướng dẫn agent viết data layer theo contract mới: API service trả `ApiResult<Dto>` trực tiếp
(Retrofit `CallAdapter.Factory`, Ktorfit `Converter.Factory` + `SuspendResponseConverter`, Ktor thuần
`HttpClient.safeRequest`), error mapping gom về một `ErrorMapper`, Repository impl là class thuần chỉ
implement interface domain và map DTO → domain. Không còn tài liệu nào yêu cầu `BaseRepository` hay `apiCall`.

## Locked decisions (from issue assumptions — defaults accepted, flagged in PR)

1. Wrapper là `ApiResult<T>` hiện có (`Success(data)` / `Error(cause: DomainError)`), **không** dùng `kotlin.Result`.
   Cấu trúc `ApiResult`/`DomainError` không đổi; chỉ thêm extension `map`, `flatMap`, `onSuccess`, `getOrNull` (inline, cho phép gọi suspend trong lambda).
2. Retrofit dùng `CallAdapter.Factory`; Ktorfit dùng `Converter.Factory.suspendResponseConverter`.
3. Ktor Client thuần dùng extension `HttpClient.safeRequest<T>()` (một try/catch duy nhất ở tầng API), không bắt buộc Ktorfit cho KMP.
4. `ErrorMapper` là `internal object` ở `{{MODULE_DATA}}/core/network/ErrorMapper.kt`. Status-code mapping dùng chung (`fromStatus`), nhánh exception theo lib được chú thích rõ (dự án chỉ giữ nhánh của lib mình dùng, vì Retrofit và Ktor không cùng classpath trong KMP commonMain).
5. Timeout exception được match **trước** `IOException` (vì `SocketTimeoutException`/`HttpRequestTimeoutException` là subclass của IOException).
6. Bỏ `withContext(ioDispatcher)` khỏi network call. Blocking IO thật (SQLDelight query đồng bộ, file) tự bọc `withContext(ioDispatcher)` tại local source sở hữu nó.
7. Lỗi DB/local không được thiết kế cơ chế wrap mới (ngoài phạm vi); tài liệu chỉ ghi rõ ranh giới.
8. Version bump: `0.11.0` (thay đổi rule ARCH-004, breaking cho product đang theo pattern cũ).

## Non-goals

- Không đổi cấu trúc `DomainError`/`ApiResult`.
- Không đổi retry, auth, interceptor.
- Không thiết kế wrap lỗi DB.
- Không sửa `CHANGELOG.md` entries cũ (lịch sử giữ nguyên, kể cả mention `BaseRepository` trong entries cũ).

## Acceptance criteria (from issue #3)

- [ ] ARCH-004 viết lại: không yêu cầu `BaseRepository`, network service trả `ApiResult<T>` qua CallAdapter (Retrofit) / Converter (Ktorfit)
- [ ] `skills/android-network/SKILL.md` có snippet `ApiResultCallAdapterFactory` + `ApiResultConverterFactory`, kèm đăng ký vào builder
- [ ] Một `ErrorMapper` dùng chung, có bảng mapping cho exception Ktor và Retrofit
- [ ] `CancellationException` không bị nuốt trong adapter/converter
- [ ] `grep -rn "BaseRepository\|apiCall" constitution knowledge skills blueprints agents workflows` chỉ còn ghi chú migration
- [ ] Mục "Migration từ BaseRepository" trong `knowledge/data/network.md`
- [ ] `TemplateArchitectureRulesTest.kt` có Konsist test cho ARCH-004 mới
- [ ] Rubric cập nhật mô tả ARCH-004 + chốt severity (HIGH)
- [ ] Ví dụ test MockEngine/MockWebServer assert `ApiResult.Error(DomainError.X)` từ tầng API

## Phases

| # | Phase | Files | Status |
|---|---|---|---|
| 1 | [Core network contract](phase-01-core-network-contract.md) | `knowledge/data/network.md`, `skills/android-network/SKILL.md` | done |
| 2 | [Rules, rubric, Konsist](phase-02-rules-rubric-konsist.md) | `constitution/*.md`, `evaluations/rubrics/README.md`, `verification/architecture-tests/TemplateArchitectureRulesTest.kt` | done |
| 3 | [Propagate to docs/skills/blueprints](phase-03-propagate-examples.md) | 15 files listed in phase | done |
| 4 | [Compile-check + release notes](phase-04-compile-check-release.md) | scratch project outside repo, `CHANGELOG.md`, `README.md` | done |

Dependencies: 1 → 2 → 3 → 4 (phase 3 copies the canonical snippets from phase 1).

## Deviations after plan red-team (kongming)

- `ApiResult` canonical definition added (it was referenced everywhere but never defined in the harness).
- `ErrorMapper` published as two complete variants (`ktor|ktorfit`, `retrofit`) sharing an identical `fromStatus`, instead of one object with commented branches — agents copy snippets verbatim.
- Ktor thuần gets `safeCall { }` (single try/catch) with `safeRequest` built on it, so multipart/stream endpoints keep the contract.
- Konsist API rule scoped to suspend, non-private functions in `remote/*Api.kt`.
- Research findings applied: OkHttp call timeout is `InterruptedIOException`; Ktor wraps JSON errors in `JsonConvertException` (`ContentConvertException`); Ktorfit wraps `CancellationException` into `KtorfitResult.Failure`.

## Global verification

```bash
grep -rn "BaseRepository\|apiCall" constitution knowledge skills blueprints agents workflows evaluations verification
```
Pass condition (after phase 3): every hit is one of the allowlisted residual sites, all of which forbid or detect the old pattern rather than instruct it:
- `knowledge/data/network.md` §Migration từ BaseRepository
- `constitution/architecture-rules.md` ARCH-004 `// ❌` violation example + Detail link to the migration section
- `knowledge/data/repository-pattern.md` Common mistakes row (anti-pattern → migration link)
- `verification/architecture-tests/TemplateArchitectureRulesTest.kt` ARCH-004 detector (`endsWith("BaseRepository")`)

Red state before phase 1: 56 instructional hits (verified).
