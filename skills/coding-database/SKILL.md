---
name: coding-database
description: Design + implement local persistence — schema, DAO, migration, Flow queries. Supports SQLDelight (KMP + Android) hoặc Room (Android native + KMP 2.7+). Trigger khi task touch database layer, add table, run migration, hoặc cache strategy.
priority: P1
---

# Skill: coding-database

## Trigger

- Thêm table mới cho feature
- Modify schema (add column, index, drop)
- Write migration script
- Add DAO query cho feature mới
- Design offline-first strategy (SSOT local DB)
- Cache invalidation strategy

## Lib selection

Chọn DB lib dựa trên `stack.database` trong `overlay.yaml`:

| Value | Lib | Platform |
|---|---|---|
| `sqldelight` | SQLDelight 2.x | KMP + Android (SQL-first, generated Kotlin API) |
| `room` | Room 2.7+ | Android native + KMP experimental (annotation-based) |
| `datastore` | DataStore Preferences/Proto | Key-value, không relational |
| `none` | — | In-memory / filesystem only |

Chi tiết lib comparison + decision guide: `knowledge/coding/data/persistence.md [KB → team/arch-coding-data, kb_search "data persistence"] §Relational DB`.

Procedure phần lớn generic. Lib-specific snippet đánh dấu rõ.

## Inputs

- Entity shape (fields, nullable, PK, FK)
- Query patterns (filter, order, join)
- Write frequency vs read frequency
- Offline requirement (SSOT từ local hay fetch mỗi lần?)

## Prerequisites

1. `knowledge/coding/data/persistence.md [KB → team/arch-coding-data, kb_search "data persistence"]`
2. `knowledge/coding/data/caching.md [KB → team/arch-coding-data, kb_search "data caching"]`
3. `knowledge/coding/coroutines/essentials.md [KB → team/arch-coding-coroutines, kb_search "coroutines essentials"] §Flow operators`
4. **SQLDelight**: https://cashapp.github.io/sqldelight
5. **Room**: https://developer.android.com/training/data-storage/room (+ KMP support 2.7+)

## Execution procedure

### Step 1 — Design schema

Example dưới là **SQLDelight** `.sq` file. Room `@Entity` + `@Dao` xem `knowledge/coding/data/persistence.md [KB → team/arch-coding-data, kb_search "data persistence"] §Room patterns`.

#### Variant A — SQLDelight

File `.sq` tại `{{MODULE_DATA}}/src/commonMain/sqldelight/<package>/`:

```sql
-- Book.sq
CREATE TABLE Book (
    id TEXT NOT NULL PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    cover_url TEXT NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    is_bookmarked INTEGER AS Boolean NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL
);

CREATE INDEX book_updated_at ON Book(updated_at);
CREATE INDEX book_bookmarked ON Book(is_bookmarked) WHERE is_bookmarked = 1;

-- Queries
getById:
SELECT * FROM Book WHERE id = :id;

getBookmarked:
SELECT * FROM Book WHERE is_bookmarked = 1 ORDER BY updated_at DESC;

upsert:
INSERT OR REPLACE INTO Book(id, title, author, cover_url, duration_ms, is_bookmarked, updated_at)
VALUES (:id, :title, :author, :cover_url, :duration_ms, :is_bookmarked, :updated_at);

toggleBookmark:
UPDATE Book SET is_bookmarked = :is_bookmarked, updated_at = :updated_at WHERE id = :id;

deleteStale:
DELETE FROM Book WHERE updated_at < :threshold AND is_bookmarked = 0;
```

**Rules SQLDelight**:
- `NOT NULL` default — nullable chỉ khi business state hợp lệ
- `INTEGER AS Boolean` cho boolean (SQLite không có native bool)
- Index cho column dùng trong `WHERE` + `ORDER BY` khi > 1000 row
- Partial index cho filtered query thường xuyên (`WHERE is_bookmarked = 1`)
- Named parameter `:name` thay vì positional

#### Variant B — Room

```kotlin
@Entity(
    tableName = "books",
    indices = [Index("updated_at"), Index(value = ["is_bookmarked"])],
)
data class BookEntity(
    @PrimaryKey val id: String,
    val title: String,
    @ColumnInfo(name = "is_bookmarked") val isBookmarked: Boolean = false,
    @ColumnInfo(name = "updated_at") val updatedAt: Long,
)

@Dao
interface BookDao {
    @Query("SELECT * FROM books WHERE id = :id")
    suspend fun getById(id: String): BookEntity?

    @Query("SELECT * FROM books WHERE is_bookmarked = 1 ORDER BY updated_at DESC")
    fun observeBookmarked(): Flow<List<BookEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(book: BookEntity)
}
```

**Rules Room**:
- `@PrimaryKey` required
- `@Entity(tableName = ...)` explicit để tránh class rename impact DB
- `@Query` SQL verified build-time
- `suspend fun` 1-shot, `Flow<T>` reactive
- `@Insert(onConflict = REPLACE)` cho upsert pattern

Chi tiết Room setup + migration + KMP driver: `knowledge/coding/data/persistence.md [KB → team/arch-coding-data, kb_search "data persistence"] §Room patterns`.

### Step 2 — Mapper DB entity ↔ domain

```kotlin
// {{MODULE_DATA}}/mapper/BookEntityMapper.kt
internal object BookEntityMapper {
    fun Book.toDomain(): {{PACKAGE_ROOT}}.{{MODULE_DOMAIN}}.model.Book = {{PACKAGE_ROOT}}.{{MODULE_DOMAIN}}.model.Book(
        id = id,
        title = title,
        author = author,
        coverUrl = cover_url,
        durationMs = duration_ms,
        isBookmarked = is_bookmarked,
    )

    fun {{PACKAGE_ROOT}}.{{MODULE_DOMAIN}}.model.Book.toEntity(now: Long): Book = Book(
        id = id,
        title = title,
        author = author,
        cover_url = coverUrl,
        duration_ms = durationMs,
        is_bookmarked = isBookmarked,
        updated_at = now,
    )
}
```

**Note**: SQLDelight generate class trùng tên với table (ví dụ `Book`) → có thể conflict với domain `Book`. Dùng full qualified path hoặc rename import.

### Step 3 — DataSource wrapper

Tách DB access khỏi Repository impl để test được:

```kotlin
// {{MODULE_DATA}}/local/BookLocalSource.kt
internal class BookLocalSource(
    private val queries: BookQueries,
    private val ioDispatcher: CoroutineDispatcher,   // query SQLDelight đồng bộ → tự chuyển dispatcher (CORO-002)
    private val clock: Clock = Clock.System,
) {
    fun observeBookmarked(): Flow<List<BookEntity>> =
        queries.getBookmarked().asFlow().mapToList(Dispatchers.Default)

    suspend fun getById(id: String): BookEntity? = withContext(ioDispatcher) {
        queries.getById(id).executeAsOneOrNull()
    }

    suspend fun upsert(book: BookEntity): Unit = withContext(ioDispatcher) {
        queries.upsert(
            id = book.id,
            title = book.title,
            author = book.author,
            cover_url = book.coverUrl,
            duration_ms = book.durationMs,
            is_bookmarked = book.isBookmarked,
            updated_at = clock.now().toEpochMilliseconds(),
        )
    }

    suspend fun toggleBookmark(id: String, bookmarked: Boolean): Unit = withContext(ioDispatcher) {
        queries.toggleBookmark(
            is_bookmarked = bookmarked,
            updated_at = clock.now().toEpochMilliseconds(),
            id = id,
        )
    }
}
```

### Step 4 — Repository impl với offline-first

```kotlin
// {{MODULE_DATA}}/repository/BookRepositoryImpl.kt
internal class BookRepositoryImpl(
    private val api: BookApi,               // trả ApiResult<BookDto> (skills/coding-network Step 4)
    private val local: BookLocalSource,
) : BookRepository {

    override fun observeBookmarked(): Flow<List<Book>> =
        local.observeBookmarked().map { entities -> entities.map { it.toDomain() } }

    override suspend fun getBook(id: String): ApiResult<Book> {
        local.getById(id)?.let { return ApiResult.Success(it.toDomain()) }
        return refreshBook(id)
    }

    override suspend fun refreshBook(id: String): ApiResult<Book> =
        api.getBook(id)
            .map { it.toDomain() }
            .onSuccess { local.upsert(it.toEntity(now = Clock.System.now().toEpochMilliseconds())) }
}
```

**Offline-first pattern**: observe local → always re-render; refresh async update local → UI auto refresh qua Flow.

### Step 5 — Migration

File số version tăng dần `.sqm`:

```sql
-- {{MODULE_DATA}}/src/commonMain/sqldelight/migrations/2.sqm
-- Migrate from v1 to v2: add `author` column + backfill
ALTER TABLE Book ADD COLUMN author TEXT NOT NULL DEFAULT '';
```

**Rules migration**:
- 1 file per version bump
- `ALTER TABLE` cho add column (SQLite support)
- Nếu modify column → create new table + copy data + drop old (verbose nhưng chuẩn SQLite)
- Backfill data trong migration khi default không đủ
- Test migration với test fixture snapshot

### Step 6 — Test

```kotlin
class BookLocalSourceTest {
    private lateinit var driver: SqlDriver
    private lateinit var db: AppDatabase
    private lateinit var local: BookLocalSource

    @BeforeTest
    fun setup() {
        driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY).also { AppDatabase.Schema.create(it) }
        db = AppDatabase(driver)
        local = BookLocalSource(db.bookQueries, ioDispatcher = UnconfinedTestDispatcher())
    }

    @AfterTest fun tearDown() { driver.close() }

    @Test
    fun `upsert then observe emits latest`() = runTest {
        local.upsert(fakeBookEntity("1", title = "Atomic"))

        local.observeBookmarked().test {
            assertEquals(emptyList(), awaitItem())
            local.toggleBookmark("1", bookmarked = true)
            val items = awaitItem()
            assertEquals(1, items.size)
            assertEquals("Atomic", items.first().title)
        }
    }

    @Test
    fun `getById returns null when missing`() = runTest {
        val result = local.getById("missing")
        assertNull(result)
    }
}
```

## Required policies

- ARCH-005 Mapper object + extension
- ARCH-010 SQLDelight driver platform-specific chỉ ở `data/{androidMain,iosMain}/`
- ARCH-013 Null-safe mapping
- CORO-005 Flow StateFlow pattern khi expose live data

## Design decisions

### Khi nào dùng local DB

- **Yes**: offline requirement, data lớn, query phức tạp, SSOT local
- **No**: cache nhỏ (<100 items, short-lived) → in-memory `Map` + TTL đủ

### Khi nào SSOT local vs remote

- **SSOT local** (prefer cho feature đọc nhiều, offline): write local trước → observe local → sync remote async
- **SSOT remote** (prefer cho dữ liệu critical, write-rare): fetch mỗi lần, cache ngắn hạn trong-memory

### Transaction scope

```kotlin
suspend fun syncBooks(books: List<Book>) {
    queries.transaction {
        queries.deleteAll()
        books.forEach { queries.upsert(...) }
    }
}
```

Dùng `transaction { }` khi:
- Multiple write liên quan (atomic consistency)
- Bulk insert (performance)

### Index strategy

- Index column trong `WHERE` thường xuyên
- Index column trong `ORDER BY` khi dataset lớn
- Partial index cho filter hay dùng
- Không over-index: mỗi index chậm write + tăng storage

## Common mistakes

| Mistake | Fix |
|---|---|
| Expose SQLDelight entity ra ngoài data module | Map sang domain |
| Query without index trên dataset lớn → UI jank | Add index + measure với `EXPLAIN QUERY PLAN` |
| Migration test chưa chạy → prod crash | Test với fixture pre-migration snapshot |
| `executeAsOne()` khi record có thể missing | `executeAsOneOrNull()` + null check |
| Flow emit mỗi row change → quá nhiều emission | `distinctUntilChanged()` hoặc batching |
| Hardcode `Dispatchers.IO` ở mapToList | Inject dispatcher |
| Lưu PII (token, personal data) không encrypt | SQLCipher hoặc Keystore cho sensitive |
| Lock DB trong hot path | Transaction scope minimize |

## Platform SDK boundary (ARCH-010)

Driver platform-specific:

```kotlin
// commonMain
expect class DatabaseDriverFactory {
    fun create(): SqlDriver
}

// androidMain
actual class DatabaseDriverFactory(private val context: Context) {
    actual fun create(): SqlDriver =
        AndroidSqliteDriver(AppDatabase.Schema, context, "app.db")
}

// iosMain
actual class DatabaseDriverFactory {
    actual fun create(): SqlDriver =
        NativeSqliteDriver(AppDatabase.Schema, "app.db")
}
```

Driver instance qua Koin inject.

## Output contract

- `.sq` file với schema + queries ở `data/src/commonMain/sqldelight/`
- Entity mapper object + extension
- DataSource wrapper (testable)
- Repository impl offline-first pattern (nếu applicable)
- Migration file nếu schema thay đổi
- Unit test với `IN_MEMORY` driver cho ít nhất: upsert, observe, delete, migration

## Anti-patterns bị cấm

- `executeAsOne()` khi row có thể không tồn tại
- Mix business logic trong `.sq` query (business ở domain layer)
- Expose SQLDelight generated types cross-module
- Migration thiếu backfill → NOT NULL vi phạm
- Lưu secret cleartext trong DB
- Transaction scope quá rộng → block UI
- `collectAsState` thay vì `collectAsStateWithLifecycle` khi observe DB Flow

---

## Harness context

- Workflow: `workflows/feature-development.md`
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`


## Overlay gate (D-full)

Trước Step 1, verify `.harness-overlay/overlay.yaml` tồn tại. Nếu không, abort với status `BLOCKED` và chỉ dẫn user:

> Chưa có overlay. Chạy skill `harness-init` để scaffold trước, sau đó quay lại skill này.

Khi gặp placeholder `{{X}}` trong procedure/code example, resolve bằng mapping ở `AGENTS.md §Placeholder resolution` (Read overlay 1 lần đầu session, cache qua context).
