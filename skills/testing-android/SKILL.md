---
name: testing-android
description: Viết unit test / integration test / Compose UI test cho {{PRODUCT_NAME}} theo chuẩn Clean Arch + MVI + Coroutines. Dùng Turbine, runTest, Fake preferred over Mock.
priority: P0
---

# Skill: testing-android

## Trigger

- "Write test cho feature X"
- "Add unit test cho ViewModel Y"
- "Integration test cho Repository Z"
- "Audit test quality"

## Inputs

- Target: class / module / feature
- Behavior cần cover (từ spec hoặc contract)

## Prerequisites

1. `knowledge/coroutines/essentials.md §Testing with runTest`
2. `knowledge/mvi/essentials.md §Testing MVI`
3. Project `docs/architecture.md`

## Test strategy

| Layer | Framework | Focus |
|---|---|---|
| Domain | kotlin.test + MockK | UseCase logic, pure functions |
| Data | kotlin.test + MockK + Ktor MockEngine | Repository impl, mapper, DTO parse |
| Presenter (VM) | kotlin.test + Turbine + runTest | State transition, intent handling, effect emission |
| Presenter (UI) | compose-ui-test | Interaction, state render, accessibility |
| Integration | kotlin.test + fake stack | ViewModel + fake Repository + fake API |

## Execution procedure

### Step 1 — Identify behavior

Từ contract hoặc spec, list behavior:

```
1. onIntent(Load) → emit state(isLoading=true) then state(data)
2. onIntent(Load) + API error → emit state(error, isOffline=network error)
3. onIntent(SelectBook) → emit effect NavigateToDetail
4. onIntent(Refresh) khi đang loading → ignore (idempotent)
5. ToggleBookmark optimistic → immediately update + rollback on failure
```

### Step 2 — Build fakes (preferred over mock)

```kotlin
class FakeBookRepository(
    private val book: Book? = fakeBook(),
    private val error: DomainError? = null,
) : BookRepository {
    override suspend fun getBook(id: String): ApiResult<Book> =
        if (error != null) ApiResult.Error(error)
        else ApiResult.Success(book ?: throw IllegalStateException())

    val bookmarkCalls = mutableListOf<String>()
    override suspend fun toggleBookmark(id: String): ApiResult<Unit> {
        bookmarkCalls += id
        return ApiResult.Success(Unit)
    }
}
```

**Rule**: Fake > Mock khi:
- Behavior stable
- Nhiều test reuse

Mock khi:
- 1-off interaction
- Verify call pattern phức tạp

### Step 3 — ViewModel test với Turbine

```kotlin
class BookDetailViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    private lateinit var repo: FakeBookRepository
    private lateinit var vm: BookDetailViewModel

    @BeforeTest fun setup() {
        Dispatchers.setMain(dispatcher)
        repo = FakeBookRepository()
    }

    @AfterTest fun teardown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `load success flow`() = runTest {
        vm = BookDetailViewModel("book-1", repo, dispatcher)

        vm.state.test {
            assertEquals(BookDetailState(isLoading = true), awaitItem())
            val loaded = awaitItem()
            assertFalse(loaded.isLoading)
            assertEquals("book-1", loaded.book?.id)
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun `load network error emits offline`() = runTest {
        repo = FakeBookRepository(error = DomainError.Network.Offline)
        vm = BookDetailViewModel("book-1", repo, dispatcher)

        vm.state.test {
            awaitItem() // loading
            val errored = awaitItem()
            assertTrue(errored.isOffline)
            assertNotNull(errored.error)
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun `toggle bookmark optimistic`() = runTest {
        vm = BookDetailViewModel("book-1", repo, dispatcher)
        advanceUntilIdle() // await initial load

        vm.onIntent(BookDetailIntent.ToggleBookmark)

        vm.state.test {
            val afterToggle = expectMostRecentItem()
            assertTrue(afterToggle.isBookmarked)
            cancelAndIgnoreRemainingEvents()
        }
        assertEquals(listOf("book-1"), repo.bookmarkCalls)
    }

    @Test
    fun `select book emits navigation effect`() = runTest {
        vm = BookDetailViewModel("book-1", repo, dispatcher)
        advanceUntilIdle()

        vm.effect.test {
            vm.onIntent(BookDetailIntent.ReadNow)
            val effect = awaitItem()
            assertTrue(effect is BookDetailEffect.NavigateToReader)
        }
    }
}
```

### Step 4 — Repository test

```kotlin
class BookRepositoryImplTest {
    private val mockEngine = MockEngine { request ->
        when (request.url.encodedPath) {
            "/books/book-1" -> respond(
                content = """{"id":"book-1","title":"Atomic Habits"}""",
                headers = headersOf("Content-Type" to listOf("application/json")),
            )
            else -> respond("", status = HttpStatusCode.NotFound)
        }
    }
    private val client = HttpClient(mockEngine) { install(ContentNegotiation) { json() } }
    private val api = BookApi(client)
    private val repo = BookRepositoryImpl(api)   // BookApi trả ApiResult qua safeRequest

    @Test
    fun `getBook success maps DTO to domain`() = runTest {
        val result = repo.getBook("book-1")
        assertTrue(result is ApiResult.Success)
        assertEquals("Atomic Habits", result.data.title)
    }

    @Test
    fun `getBook 404 returns DomainError NotFound`() = runTest {
        val result = repo.getBook("missing")
        assertTrue(result is ApiResult.Error)
        assertTrue((result as ApiResult.Error).cause is DomainError.NotFound)
    }
}
```

### Step 5 — UseCase test

```kotlin
class GetHomeFeedUseCaseTest {
    @Test
    fun `combines rails from book and discovery repos`() = runTest {
        val bookRepo = FakeBookRepository(featured = fakeBooks)
        val discoveryRepo = FakeDiscoveryRepository(trending = trendingBooks)
        val useCase = GetHomeFeedUseCase(bookRepo, discoveryRepo)

        val result = useCase()

        assertTrue(result is ApiResult.Success)
        assertEquals(2, result.data.size)
    }

    @Test
    fun `partial failure returns remaining rails`() = runTest {
        val bookRepo = FakeBookRepository(featured = fakeBooks)
        val discoveryRepo = FakeDiscoveryRepository(error = DomainError.Network.Offline)
        val useCase = GetHomeFeedUseCase(bookRepo, discoveryRepo)

        val result = useCase()

        assertTrue(result is ApiResult.Success)
        assertEquals(1, result.data.size) // only book-featured rail
    }
}
```

### Step 6 — Compose UI test (optional, khi UI logic phức tạp)

```kotlin
@Test
fun `error state shows retry button`() {
    composeTestRule.setContent {
        {{THEME_CLASS}} {
            BookDetailContent(
                state = BookDetailState(error = UiText.Raw("Network error")),
                onIntent = { },
            )
        }
    }

    composeTestRule.onNodeWithText("Retry").assertIsDisplayed()
}
```

### Step 7 — Verify + report

```bash
./gradlew :domain:test
./gradlew :data:test
./gradlew :presenter:test
./gradlew :composeApp:testDebugUnitTest
```

Report test count + coverage touched behavior.

## Test quality rules

### Naming

```kotlin
// ✅ behavior-driven
@Test fun `load success emits loading then success state`()
@Test fun `toggle bookmark optimistic rolls back on failure`()

// ❌ implementation-driven
@Test fun testLoadFunction()
@Test fun test1()
```

### Assertion strength

```kotlin
// ❌ weak — pass bất kể actual value
assertNotNull(state.book)
assertTrue(state.rails.size > 0)

// ✅ strong — specific expected
assertEquals("Atomic Habits", state.book.title)
assertEquals(3, state.rails.size)
assertEquals(expectedBook, state.book)
```

### Setup pattern

- `@BeforeTest` cho common setup (dispatcher, fake stack)
- Local override trong test method khi cần variant
- Không shared mutable state giữa tests

### Determinism

- Inject `TestDispatcher` qua constructor
- `advanceTimeBy`, `runCurrent`, `advanceUntilIdle` — không `delay()` thật
- Không depend thread timing

## Required policies

- CORO-010 test coroutines với runTest
- DoD testing section

## Common mistakes

| Mistake | Fix |
|---|---|
| `delay(100)` thật trong test | `advanceTimeBy(100)` |
| Shared `@BeforeAll` mutable state | Fresh fake mỗi test |
| Mock chain phức tạp | Tạo Fake class |
| Assertion `assertNotNull` vô nghĩa | Assert specific value |
| Test implementation detail (private field access) | Test behavior qua public API |
| `@Ignore` không link issue | Fix hoặc delete |
| Test runs > 1s | Cách ly I/O, inject TestDispatcher |

## Output contract

- Test file ở đúng module source set
- Fake class nếu reusable
- Behavior coverage ≥ happy path + 2 edge case
- Test name describe behavior, không function name
- Chạy xanh deterministic

## Validation

- [ ] Tất cả test pass
- [ ] Test name behavior-driven
- [ ] Assertion specific, không weak
- [ ] Dispatcher inject, không hardcode
- [ ] Không `@Ignore` không link
- [ ] Edge cases: null, empty, error, cancellation
- [ ] Test runs < 500ms mỗi test

## Anti-patterns

- Test chỉ để tăng coverage, không test behavior
- Mock everything thay vì Fake
- `assertTrue(result != null)` wrapper vô nghĩa
- Private field access qua reflection
- Flaky test retry 3 lần "để pass"
- Test có `delay()` thật > 100ms

---

## Harness context

- Workflow: `workflows/feature-development.md, workflows/verify-e2e.md`
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`


## Overlay gate (D-full)

Trước Step 1, verify `.harness-overlay/overlay.yaml` tồn tại. Nếu không, abort với status `BLOCKED` và chỉ dẫn user:

> Chưa có overlay. Chạy skill `harness-init` để scaffold trước, sau đó quay lại skill này.

Khi gặp placeholder `{{X}}` trong procedure/code example, resolve bằng mapping ở `AGENTS.md §Placeholder resolution` (Read overlay 1 lần đầu session, cache qua context).
