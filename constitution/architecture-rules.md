# Architecture Rules

Lift & formalize từ 14 non-negotiable rules trong project `CLAUDE.md §3`. Mỗi rule có `Severity`, `Scope`, `Rationale`, `Verification`, `Violation example`.

Dependency graph bất biến: `composeApp → presenter → domain ← data`.

## ARCH-001 — Domain purity

- **Severity**: MUST
- **Scope**: `domain/src/commonMain/`
- **Rationale**: Domain là business lõi, phải chạy được bất kỳ platform; coupling với Android/iOS/Firebase chặn test và chặn tương lai extract SDK.
- **Verification**: Konsist `ArchitectureRulesTest.domain_has_no_platform_imports`
- **Forbidden imports**: `android.*`, `androidx.*`, `platform.*` (iOS), `com.google.firebase.*`, `com.revenuecat.*`, `io.ktor.client.engine.*`
- **Violation**:
  ```kotlin
  // ❌ trong domain/
  import android.content.Context
  class BookUseCase(private val ctx: Context) { ... }
  ```

## ARCH-002 — Presenter không gọi data

- **Severity**: MUST
- **Scope**: `presenter/src/`
- **Rationale**: Presenter chỉ biết domain interface; nếu import data impl → leak layer, chặn thay thế impl.
- **Verification**: Konsist `presenter_does_not_import_data`
- **Forbidden imports**: `{{PACKAGE_ROOT}}.data.*`
- **Exception**: không có

## ARCH-003 — ViewModel chỉ gọi UseCase hoặc Repository interface

- **Severity**: MUST
- **Scope**: `presenter/.../*ViewModel.kt`
- **Rationale**: ViewModel orchestrate; business logic ở UseCase. Nhưng với operation thuần (ví dụ `repo.observeHistory()`) không có logic → được gọi `Repository` interface trực tiếp (không gọi `*Impl`).
- **Verification**: Konsist `viewmodel_depends_on_domain_only`; cấm field type `*RepositoryImpl`
- **Violation**:
  ```kotlin
  // ❌
  class HomeViewModel(private val repo: BookRepositoryImpl) ...
  // ✅
  class HomeViewModel(private val useCase: GetHomeFeedUseCase) ...
  ```

## ARCH-004 — Repository impl không kế thừa base class, network trả `ApiResult`

- **Severity**: MUST
- **Scope**: `data/src/.../repository/*Impl.kt`, `data/src/.../remote/*Api.kt`
- **Rationale**: Kế thừa base class chỉ để dùng chung error mapping + dispatcher gây coupling không cần thiết, và mỗi method phải tự bọc — quên bọc là exception thô lọt ra. Retrofit (`CallAdapter.Factory`) và Ktorfit (`Converter.Factory`) có cơ chế chính thức để trả `ApiResult` ngay tầng network; mapping lỗi chỉ viết một lần.
- **Pattern**:
  - Repository impl chỉ implement interface ở `domain/repository/`, không kế thừa class nào; nhiệm vụ còn lại là map DTO → domain: `api.getBook(id).map { it.toDomain() }`
  - API service trả `ApiResult<Dto>` qua `ApiResultCallAdapterFactory` (Retrofit), `ApiResultConverterFactory` (Ktorfit) hoặc `HttpClient.safeRequest` / `safeCall` (Ktor thuần)
  - Exception → `DomainError` ở một `ErrorMapper` duy nhất (`data/core/network/`); `CancellationException` luôn rethrow
  - Không bọc network call bằng `withContext(ioDispatcher)` (suspend call đã main-safe, xem CORO-002)
- **Verification**: Konsist `ARCH-004 repository impl does not extend base repository` (check theo tên parent `*BaseRepository`; base class tên khác bắt ở review) + `ARCH-004 remote api suspend functions return ApiResult` (suspend fun không private trong `remote/*Api.kt`, **phải khai báo return type tường minh**)
- **Exception**: endpoint cần response thô (`HttpResponse`, stream channel) → đặt ở class không nằm trong file `*Api.kt` (ví dụ `*Downloader`) hoặc bọc `safeCall { }`
- **Detail**: `knowledge/data/network.md §ApiResult contract`, `§Migration từ BaseRepository`
- **Violation**:
  ```kotlin
  // ❌
  internal class BookRepositoryImpl(api: BookApi, io: CoroutineDispatcher) : BaseRepository(io), BookRepository {
      override suspend fun getBook(id: String) = apiCall { api.getBook(id).toDomain() }
  }
  // ✅
  internal class BookRepositoryImpl(private val api: BookApi) : BookRepository {
      override suspend fun getBook(id: String): ApiResult<Book> = api.getBook(id).map { it.toDomain() }
  }
  ```

## ARCH-005 — Mapper là object + extension

- **Severity**: MUST
- **Scope**: `data/src/.../mapper/*.kt`
- **Pattern**:
  ```kotlin
  internal object BookMapper {
      fun BookDto.toDomain(): Book = Book(...)
  }
  ```
- **Verification**: Konsist `mappers_are_object_with_extensions`

## ARCH-006 — Feature package tự chứa

- **Severity**: MUST
- **Scope**: `presenter/src/commonMain/.../feature/<name>/`
- **Nội dung package**: `*Screen.kt`, `*ViewModel.kt`, `*Contract.kt` (State/Intent/Effect), optional `components/`.
- **Rationale**: Future-SDK Discipline — mỗi feature phải extract thành module library mà không phải xé code chéo.
- **Verification**: Konsist `feature_package_self_contained`
- **Forbidden**: feature-A import `feature-B/*` ngang hàng (cross-feature). Chia sẻ qua `presenter/components/` hoặc `presenter/core/`.

## ARCH-007 — MVI một chiều

- **Severity**: MUST
- **Scope**: `presenter/.../*ViewModel.kt`
- **Pattern**: `BaseViewModel<S : UiState, I : UiIntent, E : UiEffect>`; ViewModel emit `State` qua `StateFlow`, phát `Effect` qua `Channel`/`SharedFlow`, nhận `Intent` qua hàm `onIntent(intent)`.
- **Verification**: Konsist `viewmodel_extends_base_viewmodel`
- **Forbidden**: expose mutable collection, callback field ngược chiều, event bus global.

## ARCH-008 — 5 UI states đầy đủ

- **Severity**: MUST
- **Scope**: mọi screen có remote data
- **States**: `loading`, `empty`, `error`, `offline`, `success`
- **Verification**: review manual + eval scenario `E01`
- **Note**: 1 UiState data class có `isLoading`, `error`, `data`, `isOffline` + helper `isEmpty()` ok; miễn đủ coverage.

## ARCH-009 — Navigation type-safe

- **Severity**: MUST
- **Scope**: `presenter/navigation/NavRoute.kt`
- **Pattern**: `@Serializable sealed class NavRoute { @Serializable data class ... }`
- **Verification**: Konsist `nav_routes_are_sealed_serializable`
- **Forbidden**: route string literal rải rác, Bundle-based args.

## ARCH-010 — Platform SDK boundary

- **Severity**: MUST
- **Scope**: `data/src/{androidMain,iosMain}/`
- **Rationale**: ExoPlayer, AVPlayer, Firebase, Billing là platform-specific; chỉ phép xuất hiện trong `data/androidMain` hoặc `data/iosMain`, expose qua `expect/actual`.
- **Verification**: Konsist `platform_sdk_only_in_data_platform_source`
- **Forbidden**: import `androidx.media3.*` trong `commonMain` của bất kỳ module nào.

## ARCH-011 — DI binding chuẩn

- **Severity**: MUST
- **UseCase**: `factory { ... }` (stateless, cheap)
- **Repository**: `single { ... }` (stateful, cache state)
- **ViewModel**: `viewModelOf(::X)` hoặc `factory { ... }`
- **Verification**: review manual + Konsist `koin_bindings_follow_lifecycle`

## ARCH-012 — File size

- **Severity**: SHOULD (strict < 400 dòng)
- **Rationale**: readability + review scope
- **Verification**: Detekt rule `LargeClass` max 400

## ARCH-013 — Null-safe mapping

- **Severity**: MUST
- **Scope**: `data/mapper/`
- **Pattern**: dùng default value hoặc Result/sealed error, không ép `!!`
- **Verification**: Detekt `UnsafeCallOnNullableType` severity error ở `data/mapper/`
- **Forbidden**: `dto.field!!` trong mapper

## ARCH-014 — Mini-player persistent

- **Severity**: MUST
- **Scope**: `presenter/root/MainTabsScreen.kt` + `RootScaffold`
- **Pattern**: `MiniPlayerBar` render ở `RootScaffold` NGOÀI `NavHost`, không duplicate per screen.
- **Verification**: review manual + eval `E05`

---

## Future-SDK Discipline (sẵn sàng cho phase 2)

Feature module hiện tại là package trong `presenter/`. Khi extract thành library module tương lai, phải sẵn sàng ngay bây giờ:

- **MOD-001**: Mỗi feature có 1 file `<Feature>Api.kt` là public surface (route entry + optional init config). Các class khác `internal`.
- **MOD-002**: Public API không expose `ViewModel` type, `Flow<InternalState>`, hoặc Compose private component.
- **MOD-003**: Resource namespace: `feature_<name>_*` (string, drawable) để tránh collision khi tách module.

Severity hiện tại: **SHOULD**. Khi quyết định extract → promote lên **MUST**.
