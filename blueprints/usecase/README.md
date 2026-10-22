# Blueprint: UseCase (Standalone)

Standalone pattern cho 1 UseCase (domain business operation). Dùng khi:
- Logic orchestrate 2+ Repository
- Business transform meaningful (ví dụ compute progress %, aggregate feed)
- Validation precondition (entitlement check)
- Reusable giữa 2+ ViewModel

**Khi KHÔNG dùng UseCase**: operation 1-1 với Repository method không có logic. ViewModel inject Repository interface direct — rule ARCH-003 cho phép.

## Layout

```
{{MODULE_DOMAIN}}/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/{{MODULE_DOMAIN}}/
├── usecase/<domain>/<Verb><Noun>UseCase.kt
└── repository/<R>Repository.kt   (dependencies)
```

## 1. UseCase shape — standard

```kotlin
// {{MODULE_DOMAIN}}/usecase/book/GetBookDetailUseCase.kt
class GetBookDetailUseCase(
    private val bookRepo: BookRepository,
    private val historyRepo: HistoryRepository,
) {
    suspend operator fun invoke(bookId: String): ApiResult<BookDetail> {
        return when (val book = bookRepo.getBook(bookId)) {
            is ApiResult.Error -> book
            is ApiResult.Success -> {
                val progress = historyRepo.getProgress(bookId).getOrNull() ?: 0f
                ApiResult.Success(book.data.copy(progress = progress))
            }
        }
    }
}
```

**Rules**:
- **MUST** `class` + constructor inject dependencies (not `object`, không static)
- **MUST** `operator fun invoke(...)` → callable `useCase(args)` natural
- **MUST** `suspend` nếu async
- **SHOULD** return `ApiResult<T>` khi có failure mode
- **SHOULD** stateless (no var field) — DI binding `factory { }`

## 2. Variants

### Simple pass-through (bỏ UseCase)

```kotlin
// Bỏ: ViewModel gọi repo direct
class HomeViewModel(private val repo: BookRepository) {
    private fun load() = viewModelScope.launch { repo.getBooks() }
}
```

**Rule**: nếu UseCase chỉ delegate 1-1 không transform → bỏ, dùng Repository interface.

### Orchestrate multi-source

```kotlin
class GetHomeFeedUseCase(
    private val bookRepo: BookRepository,
    private val discoveryRepo: DiscoveryRepository,
    private val historyRepo: HistoryRepository,
) {
    suspend operator fun invoke(): ApiResult<List<Rail>> = supervisorScope {
        val featured = async { bookRepo.getFeatured() }
        val trending = async { discoveryRepo.getTrending() }
        val continueListening = async { historyRepo.getContinueListening() }

        try {
            val rails = buildList {
                featured.await().getOrNull()?.let { add(Rail.Featured(it)) }
                trending.await().getOrNull()?.let { add(Rail.Trending(it)) }
                continueListening.await().getOrNull()?.let { add(Rail.Continue(it)) }
            }
            if (rails.isEmpty()) ApiResult.Error(DomainError.NotFound)
            else ApiResult.Success(rails)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            ApiResult.Error(DomainError.Unknown(e.message ?: ""))
        }
    }
}
```

**Rule**: `supervisorScope` khi tác vụ con độc lập có thể fail riêng. CORO-003.

### Validation + action

```kotlin
class ToggleBookmarkUseCase(
    private val bookRepo: BookRepository,
    private val entitlementRepo: EntitlementRepository,
) {
    suspend operator fun invoke(bookId: String, bookmarked: Boolean): ApiResult<Unit> {
        if (!entitlementRepo.isPremium.value) {
            return ApiResult.Error(DomainError.Auth.Forbidden)
        }
        return bookRepo.toggleBookmark(bookId, bookmarked)
    }
}
```

### Flow transformation

```kotlin
class ObserveLibraryUseCase(
    private val bookRepo: BookRepository,
    private val historyRepo: HistoryRepository,
) {
    operator fun invoke(): Flow<List<LibraryItem>> =
        combine(
            bookRepo.observeBookmarked(),
            historyRepo.observeInProgress(),
        ) { bookmarked, inProgress ->
            (bookmarked + inProgress).distinctBy { it.id }
                .sortedByDescending { it.updatedAt }
                .map { LibraryItem(book = it, progress = computeProgress(it)) }
        }
}
```

**Rule**: Flow transformation không `suspend` (chạy mỗi collect) — return `Flow<T>` direct.

## 3. DI binding

```kotlin
// {{MODULE_DOMAIN}}/di/DomainModule.kt
factory { GetBookDetailUseCase(get(), get()) }
factory { GetHomeFeedUseCase(get(), get(), get()) }
factory { ToggleBookmarkUseCase(get(), get()) }
factory { ObserveLibraryUseCase(get(), get()) }
```

**MUST** `factory { }` — stateless, cheap to create. Không `single { }` cho UseCase.

## 4. Unit test

```kotlin
class GetBookDetailUseCaseTest {
    private val bookRepo = FakeBookRepository()
    private val historyRepo = FakeHistoryRepository()
    private val useCase = GetBookDetailUseCase(bookRepo, historyRepo)

    @Test
    fun `invoke combines book and progress`() = runTest {
        bookRepo.response = ApiResult.Success(fakeBook())
        historyRepo.progress = 0.7f

        val result = useCase("book-1")

        assertTrue(result is ApiResult.Success)
        assertEquals(0.7f, (result as ApiResult.Success).data.progress)
    }

    @Test
    fun `invoke propagates book error`() = runTest {
        bookRepo.response = ApiResult.Error(DomainError.NotFound)

        val result = useCase("missing")

        assertTrue(result is ApiResult.Error)
        assertTrue((result as ApiResult.Error).cause is DomainError.NotFound)
    }

    @Test
    fun `invoke defaults progress when history missing`() = runTest {
        bookRepo.response = ApiResult.Success(fakeBook())
        historyRepo.progress = null

        val result = useCase("book-1")

        assertEquals(0f, (result as ApiResult.Success).data.progress)
    }
}
```

## Decision tree — "có cần UseCase?"

```
Operation là 1-1 với Repository method, không transform?
  ├─ YES → ❌ KHÔNG tạo UseCase, ViewModel inject Repository
  └─ NO → tiếp
       │
       └─ Có logic orchestrate / transform / validation?
           ├─ YES → ✓ Tạo UseCase
           └─ NO → suy nghĩ lại architecture
```

### Khi nào YES chắc chắn

- Orchestrate 2+ Repository
- Compute derived value từ domain model
- Validate precondition trước action
- Reusable giữa 2+ ViewModel

### Khi nào NO (bỏ UseCase)

- `loadBooks()` chỉ gọi `repo.getBooks()` return → ViewModel gọi repo direct
- "Business" chỉ là wrapper tên khác → dead abstraction

## Checklist

- [ ] Class + constructor inject
- [ ] `operator fun invoke(...)` interface
- [ ] `suspend` nếu async, no suspend nếu return Flow
- [ ] Return `ApiResult<T>` khi có failure
- [ ] Stateless (no var field)
- [ ] DI `factory { }`
- [ ] Preserve `CancellationException` (CORO-004)
- [ ] Supervised scope khi multiple async con độc lập
- [ ] Unit test ít nhất 3 scenarios

## Variants hợp lệ

- Multiple invoke overload với args khác nhau
- Return `Flow<T>` thay `suspend` khi reactive
- Multiple injected scopes/dispatchers (hiếm, prefer inherit)

## Anti-patterns

- `object UseCase { fun execute() }` — không constructor, không testable
- UseCase stateful (var field) → race condition
- UseCase gọi Repository impl `*Impl` → vi phạm ARCH-003 (chỉ gọi interface)
- Reset `CancellationException` catch broad → vi phạm CORO-004
- UseCase 1-1 trivial (`class LoadBooks(repo) { suspend fun invoke() = repo.getBooks() }`) → dead abstraction
- UseCase chứa UI logic / Compose code → vi phạm ARCH-001
- UseCase `single { }` DI binding → waste memory, không stateless

## Reference

- `.harness/knowledge/coding/clean-arch/clean-mvi.md §Dùng UseCase`
- `.harness/skills/android-feature/SKILL.md`
- Rule ARCH-003, ARCH-011 trong `constitution/architecture-rules.md`
