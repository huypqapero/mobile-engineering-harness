# Persistence — Essentials

Local storage: SQLDelight (DB), DataStore (preferences), filesystem (large binary).

## When to use what

| Type | Choose |
|---|---|
| Structured relational, >100 items, offline-first | **SQLDelight** |
| Key-value user preference, settings, feature flags | **DataStore (Preferences)** |
| Typed single object (user session, config) | **DataStore (Proto)** |
| Large binary (image cache, audio file, download) | **Filesystem** + manifest trong DB |
| Secret (token, API key stored client) | **KeyStore (Android) / Keychain (iOS)** qua expect/actual |
| Simple scratch < 10 kv | **In-memory `Map` + Flow** (nếu không cần persist) |

**FORBIDDEN**: SharedPreferences cho data mới (legacy only). Migrate sang DataStore.

## SQLDelight patterns

Chi tiết: `.harness/skills/android-database/SKILL.md`.

### Schema basics

```sql
CREATE TABLE Book (
    id TEXT NOT NULL PRIMARY KEY,
    title TEXT NOT NULL,
    is_bookmarked INTEGER AS Boolean NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL
);

CREATE INDEX book_updated_at ON Book(updated_at);

getBookmarked:
SELECT * FROM Book WHERE is_bookmarked = 1 ORDER BY updated_at DESC;
```

### Flow-based query

```kotlin
queries.getBookmarked().asFlow().mapToList(Dispatchers.Default)
```

### Transaction cho atomic multi-write

```kotlin
queries.transaction {
    books.forEach { queries.upsert(...) }
}
```

### Migration file `.sqm`

```sql
-- 2.sqm: v1 → v2
ALTER TABLE Book ADD COLUMN author TEXT NOT NULL DEFAULT '';
```

### Platform driver (ARCH-010)

```kotlin
// commonMain
expect class DatabaseDriverFactory { fun create(): SqlDriver }

// androidMain
actual class DatabaseDriverFactory(context: Context) {
    actual fun create(): SqlDriver = AndroidSqliteDriver(AppDatabase.Schema, context, "app.db")
}

// iosMain
actual class DatabaseDriverFactory {
    actual fun create(): SqlDriver = NativeSqliteDriver(AppDatabase.Schema, "app.db")
}
```

## DataStore patterns

### Preferences DataStore (key-value)

```kotlin
// commonMain abstraction
interface PreferenceStore {
    fun observeTheme(): Flow<Theme>
    suspend fun setTheme(theme: Theme)
}

// androidMain impl
class PreferenceStoreImpl(private val dataStore: DataStore<Preferences>) : PreferenceStore {
    private val themeKey = stringPreferencesKey("theme")

    override fun observeTheme(): Flow<Theme> = dataStore.data.map { prefs ->
        Theme.fromString(prefs[themeKey] ?: Theme.System.name)
    }

    override suspend fun setTheme(theme: Theme) {
        dataStore.edit { it[themeKey] = theme.name }
    }
}
```

**Rules**:
- Key naming: `snake_case`, prefix feature (`reader_font_size`, `auth_tokens`)
- Type-safe key: dùng `stringPreferencesKey`, `intPreferencesKey`...
- Default value explicit, không rely null
- Migration DataStore qua `.migrateFromSharedPreferences()` nếu legacy

### Proto DataStore (typed object)

Dùng khi object có structure (session, config nested).

```proto
message UserSession {
    string user_id = 1;
    string access_token = 2;
    int64 expires_at = 3;
}
```

Benefit: type-safe, backward compat qua field number, nhỏ hơn JSON.

Trade-off: setup Protobuf plugin + build config.

## Filesystem

### Khi dùng

- Image cache > 1 MB
- Audio/video downloaded
- Export file (CSV, PDF)

### Pattern

```kotlin
// Store path trong DB, binary trong filesystem
suspend fun saveAudio(bookId: String, bytes: ByteArray): Path {
    val file = cacheDir / "audio" / "$bookId.mp3"
    file.parent.createDirectories()
    file.writeBytes(bytes)
    queries.insertAudio(bookId, file.toString(), bytes.size.toLong())
    return file
}
```

**Rules**:
- Path tương đối hoặc relative to app directory (không hardcode absolute path)
- Cleanup strategy: TTL + size limit + LRU eviction
- Media/documents → `cacheDir` (OS reclaim) vs `filesDir` (persistent until app uninstall)

## Secret storage

```kotlin
// commonMain
expect class SecureStorage {
    suspend fun save(key: String, value: String)
    suspend fun load(key: String): String?
    suspend fun delete(key: String)
}

// androidMain
actual class SecureStorage(context: Context) {
    private val encryptedPrefs: SharedPreferences = EncryptedSharedPreferences.create(...)
    actual suspend fun save(key: String, value: String) = withContext(Dispatchers.IO) {
        encryptedPrefs.edit { putString(key, value) }
    }
    // ...
}

// iosMain
actual class SecureStorage {
    actual suspend fun save(key: String, value: String) {
        // Keychain Services API
    }
}
```

**MUST** cho:
- Auth tokens (access, refresh)
- API key client stored (hạn chế này, prefer BuildConfig server-signed)
- Payment card số (PCI compliance — thường outsource)

**FORBIDDEN**:
- Lưu secret trong SharedPreferences plain
- Lưu secret trong DB plain
- Log secret (sanitize)

## Thread safety

- SQLDelight queries thread-safe (via driver)
- DataStore thread-safe (single writer internally)
- Filesystem concurrent write → có thể corrupt → `Mutex` quanh write operation

```kotlin
private val fileMutex = Mutex()
suspend fun safeWrite(path: Path, bytes: ByteArray) = fileMutex.withLock {
    path.writeBytes(bytes)
}
```

## Lifecycle

- **DB connection**: single instance, long-lived (closed khi app process ends)
- **DataStore**: single instance per file (don't create multiple same file)
- **Cursor**: close bằng `use { }` block hoặc Flow (SQLDelight auto)

## Testing

### SQLDelight in-memory

```kotlin
val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY).also {
    AppDatabase.Schema.create(it)
}
val db = AppDatabase(driver)
```

### DataStore in-memory

```kotlin
val tempDir = Files.createTempDirectory("test")
val dataStore = PreferenceDataStoreFactory.create { tempDir.resolve("test.preferences_pb").toFile() }
```

### Migration test

```kotlin
@Test
fun `migrate v1 to v2 adds author column`() {
    val v1Driver = createDriverAtVersion(1)  // seed v1 schema + data
    AppDatabase.Schema.migrate(v1Driver, 1, 2)
    val db = AppDatabase(v1Driver)
    val book = db.bookQueries.getById("1").executeAsOne()
    assertEquals("", book.author)  // backfill default
}
```

## Common mistakes

| Mistake | Fix |
|---|---|
| SharedPreferences cho data mới | DataStore |
| SQLDelight entity leak cross-module | Map sang domain |
| Secret plain trong SharedPreferences | KeyStore/Keychain |
| Migration thiếu backfill | ALTER + UPDATE trong .sqm |
| No index trên column dùng `WHERE` 1000+ row | Add index, measure với EXPLAIN QUERY PLAN |
| `executeAsOne()` khi row optional | `executeAsOneOrNull()` |
| Multiple DataStore cùng file | Singleton qua Koin |
| Cursor leak không close | Dùng Flow hoặc `use { }` |
| Filesystem concurrent write | `Mutex.withLock { }` |
| Lưu bitmap trong DB | DB giữ path, file ở filesystem |

## References

- SQLDelight: https://cashapp.github.io/sqldelight
- DataStore: https://developer.android.com/topic/libraries/architecture/datastore
- `.harness/skills/android-database/SKILL.md`
- `.harness/knowledge/data/caching.md`
