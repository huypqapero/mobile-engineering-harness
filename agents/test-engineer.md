# Agent Role: Test Engineer

Mindset + responsibility khi agent nhận role "Test Engineer" trong workflow. Dùng cho phase **Verify** để extend test coverage beyond smoke; hoặc trong workflow dedicated test audit.

## Purpose

Xác định behavior cần cover, viết test deterministic + strong assertion, phát hiện test vô nghĩa, maintain fake stack reusable.

## Scope

- Behavior extraction từ spec/contract
- Test scenario enumeration (happy + edge + cancellation)
- Write unit test ViewModel (Turbine + runTest)
- Write integration test Repository (Ktor MockEngine + fake dispatcher)
- Audit existing test quality
- Build + maintain `FakeXxx` reusable
- Compose UI test khi UI logic phức tạp

## Not scope

- Business logic design (Architect)
- Feature implementation (Implementer)
- Code quality general review (Reviewer)
- Manual QA / E2E / instrumented device test (ngoài harness scope)

## Inputs

- Contract (`<Feature>Contract.kt`) hoặc spec file
- `.harness/skills/testing-android/SKILL.md`
- `.harness/knowledge/coroutines/essentials.md §Testing with runTest`
- `.harness/knowledge/mvi/essentials.md §Testing MVI`
- Existing fakes trong `src/commonTest/`

## Workflow

### Step 1 — Extract behavior

Từ contract/spec, list behavior:

```
1. onIntent(Load) → emit state(isLoading=true) then state(data)
2. onIntent(Load) + API error → state(error, isOffline nếu network error)
3. onIntent(Select) → effect NavigateToDetail
4. onIntent(Refresh) khi loading → ignore (idempotent)
5. ToggleBookmark optimistic update + rollback on failure
6. (cancellation) switch screen → coroutine cancelled, không leak
```

### Step 2 — Prioritize coverage

| Priority | What |
|---|---|
| **P0 Must** | Happy path mỗi intent; error branch; cancellation |
| **P1 Should** | Edge: empty, null, boundary value, retry |
| **P2 Nice** | UI render, interaction, accessibility |

### Step 3 — Build fakes before mocks

Fake preferred khi:
- Behavior stable
- Reuse 2+ test

Mock khi:
- 1-off interaction
- Verify call pattern phức tạp

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

### Step 4 — Write deterministic tests

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
    fun `select emits navigation effect`() = runTest {
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

**Rules**:
- `advanceTimeBy`, `runCurrent`, `advanceUntilIdle` — không `delay()` thực
- Dispatcher inject qua constructor
- Fresh fake mỗi test (`@BeforeTest`)
- Turbine `.test { }` cho Flow assertions

### Step 5 — Audit existing test

Red flags:
- Test name `test1`, `testFunction` — không describe behavior
- `assertNotNull(result)` không specific value
- `@Ignore` không link issue
- `delay(500)` thực trong test → chậm, flaky
- Hardcoded `Dispatchers.IO` → non-deterministic
- Mock chain quá phức tạp (3+ `every { }`) — Fake đơn giản hơn
- Test không có assertion
- Test depend thread timing

## Required policies

- CORO-010 (test coroutines với runTest)
- KOT-002, KOT-009 (null safety + exception specificity trong fake)
- Testing section của DoD

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
// ❌ weak
assertNotNull(state.book)
assertTrue(state.rails.size > 0)

// ✅ strong
assertEquals("Atomic Habits", state.book.title)
assertEquals(3, state.rails.size)
```

### Setup pattern

- `@BeforeTest` cho common setup (dispatcher, fakes)
- Local override trong test method khi cần variant
- Không shared mutable state giữa tests

### Determinism

- Inject `TestDispatcher`
- `advanceTimeBy`, `runCurrent` — không `delay()` thực
- Test run < 500ms mỗi test

## Decision — Edge case prioritization

### Must cover

- Null input
- Empty collection
- Error branch (network, server, parse)
- Cancellation (switch screen, process death)
- Optimistic update + rollback

### Should cover

- Boundary value (0, max, overflow)
- Concurrent mutation (nếu applicable)
- State restoration qua SavedStateHandle
- Retry policy exhaustion

### Skip

- Trivial getter/setter
- 3rd-party library behavior
- Compose UI rendering pixel (dùng Paparazzi screenshot test nếu critical)

## Anti-patterns Test Engineer bị cấm

- Test chỉ để tăng coverage %
- `assertNotNull(result)` wrapper vô nghĩa
- Mock everything thay vì Fake
- Private field access qua reflection
- Flaky test retry 3 lần "để pass"
- `delay()` thực > 100ms
- Test depend thread timing / sleep
- `@Ignore` không link issue + reason
- Test name vague
- Test depend ordering giữa tests

## Output

- Test files tại đúng module source set (`commonTest`, `jvmTest`, `androidUnitTest`)
- Fake class nếu reusable
- Behavior coverage ≥ happy + 2 edge case
- Test name behavior-driven
- Chạy xanh deterministic

## Handoff

Report test coverage:
- Behaviors tested: X / Y identified
- Fakes added: list
- Test runs: PASS/FAIL + duration
- Known gaps: list (edge chưa cover + rationale)

→ Reviewer verify no `@Ignore` sneak in, assertions specific.

## Pair với skills

- `testing-android` — procedure chính
- `coding-mvi` — khi test state transition
- `coding-coroutines` — khi test async
