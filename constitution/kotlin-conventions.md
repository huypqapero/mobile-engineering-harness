# Kotlin Conventions

Rules Kotlin-level cho mọi module. Cấp độ: **MUST / SHOULD / FORBIDDEN**.

## KOT-001 — Naming

- **MUST**: Class/Object/Interface → `PascalCase`. Function/property/variable → `camelCase`. Constant top-level → `UPPER_SNAKE_CASE`.
- **MUST**: Boolean prefix `is`, `has`, `should`, `can`. Ví dụ: `isLoading`, `hasError`.
- **MUST**: Composable function → `PascalCase` (theo Compose guideline).
- **FORBIDDEN**: Hungarian notation (`strName`, `iCount`). Tên viết tắt mơ hồ (`mgr`, `ctx` ngoài scope local).

## KOT-002 — Null safety

- **MUST**: Prefer non-null type khi contract đảm bảo. Dùng `?` chỉ khi null là business state hợp lệ.
- **FORBIDDEN**: `!!` non-null assertion operator trừ khi có comment giải thích tại sao null không thể xảy ra tại điểm đó.
- **MUST**: Sử dụng `?.`, `?:`, `let`, `takeIf` thay vì manual null check.
- **FORBIDDEN**: `requireNotNull` ở hot path không có message giải thích contract.
- **Verification**: Detekt `UnsafeCallOnNullableType` enabled, severity error ở `data/mapper/` + `domain/`.

## KOT-003 — Immutability

- **MUST**: `val` by default. Dùng `var` chỉ cho local mutable scope hoặc `MutableState*` nội bộ.
- **MUST**: `data class` fields toàn bộ `val`. Expose `List<T>`, `Set<T>`, `Map<K, V>` immutable interface, không `MutableList`.
- **FORBIDDEN**: Expose `MutableStateFlow`, `MutableSharedFlow`, `MutableList` ra ngoài class.
- **Pattern**: `.asStateFlow()` + `.toImmutableList()` ở getter.

## KOT-004 — Visibility modifiers

- **MUST**: Default `internal` cho class/function trong module. `public` chỉ cho API intentionally exposed cross-module.
- **MUST**: `private` cho helper function nội class.
- **SHOULD**: Rule `MOD-002` — mọi class ngoài `*Api.kt` phải `internal` (Future-SDK Discipline).
- **FORBIDDEN**: `public` wildcard khi không có plan reuse.

## KOT-005 — Data class + sealed types

- **MUST**: `data class` cho value object không có behavior.
- **MUST**: `sealed interface` (prefer) hoặc `sealed class` cho state branches, error typed. Compiler exhaustive `when` check là feature.
- **FORBIDDEN**: `enum` với associated data (dùng `sealed interface` thay).
- **Pattern**:
  ```kotlin
  sealed interface AuthState {
      data object SignedOut : AuthState
      data object Loading : AuthState
      data class SignedIn(val user: User) : AuthState
      data class Error(val cause: AuthError) : AuthState
  }
  ```

## KOT-006 — Extension functions

- **SHOULD**: Extension functions cho logic add-on không đáng tạo class mới. Scope: file-level cho reuse module, class member cho scope hẹp.
- **MUST**: Extension function trên 3rd-party type → file đặt gần nơi dùng, không scatter.
- **FORBIDDEN**: Extension function thay thế abstraction đáng có (ví dụ extension làm công việc UseCase).

## KOT-007 — Scope functions

- **Pattern selection**:
  | Fn | When |
  |---|---|
  | `let` | Null check + transform |
  | `apply` | Config object sau khi tạo |
  | `also` | Side-effect inline (log, add to list) |
  | `run` | Scoped block có return value |
  | `with` | Call multiple methods cùng receiver |
- **FORBIDDEN**: Chain quá 3 scope function liên tiếp (readability drops).

## KOT-008 — Companion object + top-level

- **MUST**: Hằng số module-wide → `const val` top-level hoặc `companion object` của class liên quan.
- **SHOULD**: Factory function → top-level function thay vì `companion object { fun create(...) }` nếu không có state.

## KOT-009 — Exception handling

- **FORBIDDEN**: `catch (e: Throwable)` nuốt mọi lỗi. Phạm vi catch phải specific (`IOException`, `HttpException`...).
- **MUST**: Re-throw `CancellationException` khi catch broader (xem `concurrency-rules.md §CORO-004`).
- **MUST**: Dùng typed error (`DomainError`, `ApiResult.Error`) ở domain boundary, không throw raw.
- **FORBIDDEN**: `runCatching` ở nơi có thể bắt `CancellationException` mà không re-throw.

## KOT-010 — Collection operations

- **SHOULD**: Sequence (`asSequence()`) cho pipeline > 2 operations trên list > 100 items.
- **MUST**: Prefer immutable builder (`buildList`, `buildMap`, `buildSet`) trên scratch mutation.
- **FORBIDDEN**: `.toList()` ở middle của pipeline (break laziness).

## KOT-011 — String + resource

- **MUST**: User-facing text qua resource (`stringResource(Res.string.xxx)`), không hardcode trong code.
- **MUST**: Resource key namespace `feature_<name>_*` cho feature package (`PRODUCT-RES-001`).
- **FORBIDDEN**: Concatenation string với `+` cho template; dùng `"$var"` hoặc `String.format`.

## KOT-012 — Documentation

- **MUST**: KDoc cho public API (hàm/class public). Format tối thiểu: 1 câu purpose + `@param` nếu không self-explanatory + `@return` nếu không trivial.
- **FORBIDDEN**: KDoc chỉ lặp lại tên hàm.
- **SHOULD**: Internal/private không bắt buộc KDoc trừ khi có invariant non-obvious.

## Verification mapping

| Rule | Enforcement |
|---|---|
| KOT-002 | Detekt `UnsafeCallOnNullableType` |
| KOT-003 | Manual review + Konsist `*ViewModel` không expose `Mutable*` |
| KOT-004 | Konsist `MOD-002` + manual |
| KOT-005 | Manual review |
| KOT-009 | Detekt `TooGenericExceptionCaught` + `SwallowedException` |
| Others | Manual review (code-review skill) |
