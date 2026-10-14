# E05 — Test Quality Audit

## Scenario

Giao agent 1 test file có 5 test "pass" nhưng chất lượng kém. Agent dùng skill `android-testing` audit và viết lại.

## Prompt mẫu

> Audit test file `BookRepositoryImplTest.kt` dưới đây. Nêu finding theo severity + rewrite tests theo chuẩn `.harness/skills/android-testing/SKILL.md`.

## Bad fixture

```kotlin
class BookRepositoryImplTest {

    @Test
    fun test1() {                                              // BAD-1 naming
        val repo = BookRepositoryImpl(mockk(), Dispatchers.IO) // BAD-2 real dispatcher
        runBlocking {                                           // BAD-3 runBlocking
            val result = repo.getBook("x")
            assertNotNull(result)                               // BAD-4 weak assertion
        }
    }

    @Test
    fun `test loading`() {
        val api = mockk<BookApi>()
        coEvery { api.getBook(any()) } coAnswers {
            delay(500)                                          // BAD-5 real delay
            BookDto("1", "title", "author")
        }
        val repo = BookRepositoryImpl(api, Dispatchers.IO)
        runBlocking {
            val result = repo.getBook("1")
            assertTrue(result is ApiResult.Success)
        }
    }

    @Test
    @Ignore("flaky — figure out later")                        // BAD-6 ignore no issue link
    fun `test error`() { ... }

    @Test
    fun `getBook returns success`() {
        val api = FakeApi(response = BookDto("1", "A", "B"))
        val repo = BookRepositoryImpl(api, UnconfinedTestDispatcher())
        runTest {
            val result = repo.getBook("1")
            assertTrue(result != null)                          // BAD-4 weak again
        }
    }

    @Test
    fun `error handling`() {                                   // BAD-7 vague name
        val api = FakeApi(error = IOException())
        val repo = BookRepositoryImpl(api, UnconfinedTestDispatcher())
        runTest {
            try {
                repo.getBook("1")
                fail("should throw")
            } catch (e: Exception) {                            // BAD-8 catch-all; also BAD contract (ApiResult, không throw)
                assertNotNull(e)
            }
        }
    }
}
```

## Expected findings

| # | Severity | Issue | Rule |
|---|---|---|---|
| 1 | MEDIUM | Test name `test1` không describe behavior | Testing §Naming |
| 2 | HIGH | Hardcoded `Dispatchers.IO` không inject | CORO-002 |
| 3 | HIGH | `runBlocking` trong test → chậm, chặn thread, không advance time | CORO-010 |
| 4 | MEDIUM | `assertNotNull(result)` / `assertTrue(result != null)` quá weak | Testing §Assertion strength |
| 5 | HIGH | `delay(500)` thật trong test → chạy chậm, flaky | Testing §Determinism |
| 6 | HIGH | `@Ignore` không link issue | Testing §Anti-patterns |
| 7 | LOW | Test name `error handling` vague | Testing §Naming |
| 8 | HIGH | Catch raw `Exception` + assertNotNull — không verify behavior cụ thể. Thêm nữa, repo return `ApiResult`, không throw → test sai contract | Testing §Assertion strength |

## Expected rewrite

```kotlin
class BookRepositoryImplTest {

    private val testDispatcher = StandardTestDispatcher()

    @Test
    fun `getBook success maps dto to domain`() = runTest {
        val api = FakeBookApi(response = BookDto(id = "1", title = "Atomic", author = "Clear"))
        val repo = BookRepositoryImpl(api, testDispatcher)

        val result = repo.getBook("1")

        assertTrue(result is ApiResult.Success)
        assertEquals("Atomic", (result as ApiResult.Success).data.title)
        assertEquals("Clear", result.data.author)
    }

    @Test
    fun `getBook with delay still deterministic`() = runTest {
        val api = FakeBookApi(response = BookDto("1", "T", "A"), responseDelayMs = 500)
        val repo = BookRepositoryImpl(api, testDispatcher)

        val deferred = async { repo.getBook("1") }
        advanceTimeBy(600)
        val result = deferred.await()

        assertTrue(result is ApiResult.Success)
    }

    @Test
    fun `getBook network IO error returns DomainError Network Offline`() = runTest {
        val api = FakeBookApi(error = IOException("timeout"))
        val repo = BookRepositoryImpl(api, testDispatcher)

        val result = repo.getBook("1")

        assertTrue(result is ApiResult.Error)
        assertTrue((result as ApiResult.Error).cause is DomainError.Network.Offline)
    }

    @Test
    fun `getBook server 500 returns DomainError Server`() = runTest {
        val api = FakeBookApi(httpStatus = 500)
        val repo = BookRepositoryImpl(api, testDispatcher)

        val result = repo.getBook("1")

        assertTrue(result is ApiResult.Error)
        assertTrue((result as ApiResult.Error).cause is DomainError.Server)
    }

    @Test
    fun `getBook 404 returns DomainError NotFound`() = runTest {
        val api = FakeBookApi(httpStatus = 404)
        val repo = BookRepositoryImpl(api, testDispatcher)

        val result = repo.getBook("missing")

        assertTrue(result is ApiResult.Error)
        assertTrue((result as ApiResult.Error).cause is DomainError.NotFound)
    }
}
```

## Scoring

- 8/8 findings + rewrite đủ chất lượng: 100
- 6-7/8 + rewrite ổn: 85
- 4-5/8: 65
- < 4/8: FAIL

Trừ điểm nếu rewrite:
- Vẫn `runBlocking` thay vì `runTest`
- Vẫn hardcode `Dispatchers.IO`
- Vẫn assertion weak
- Không add fake class reusable

## Baseline comparison

Agent không harness thường catch 3-4/8 findings. Với harness: ≥ 6/8.
