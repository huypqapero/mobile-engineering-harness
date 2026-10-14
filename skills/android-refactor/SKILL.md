---
name: android-refactor
description: Preserve-behavior refactor cho Android codebase — extract, inline, rename, move, split theo cause rõ. Trigger khi task refactor không có user-visible change (chỉ internal structure).
priority: P2
---

# Skill: android-refactor

Procedure chi tiết: dùng kèm `workflows/refactor-module.md`. Skill file này focus pattern + Android/Kotlin specific guidance.

## Trigger

- Extract function/class/package khi file > 400 lines
- Inline abstraction không giá trị thêm (interface 1 impl, UseCase 1-1 không logic)
- Move file giữa layer (Business logic từ Composable → ViewModel)
- Rename cho clarity (BookRepo → BookRepository)
- Split module (presenter → core/presenter + feature/* khi > 20 feature)
- Prep for SDK extraction (MOD-001..003 enforcement)

## Prerequisites

1. `.harness/workflows/refactor-module.md` — 5-stage orchestration
2. `.harness/constitution/architecture-rules.md`
3. `.harness/constitution/kotlin-conventions.md`

## Refactor patterns

### P-01 — Extract function

Trigger: function > 50 lines, multiple responsibility, repeated inline logic.

```kotlin
// Before
fun BookDetailViewModel.loadBook(id: String) {
    viewModelScope.launch {
        updateState { it.copy(isLoading = true) }
        try {
            val book = repo.getBook(id)
            val progress = history.getProgress(id)
            val merged = book.copy(progress = progress)
            updateState { it.copy(isLoading = false, book = merged) }
        } catch (e: Exception) {
            if (e is CancellationException) throw e
            updateState { it.copy(isLoading = false, error = e.toUiText()) }
        }
    }
}

// After
fun BookDetailViewModel.loadBook(id: String) {
    viewModelScope.launch {
        updateState { it.copy(isLoading = true) }
        val result = fetchBookWithProgress(id)
        updateState(result::applyToState)
    }
}

private suspend fun BookDetailViewModel.fetchBookWithProgress(id: String): LoadResult = ...
```

### P-02 — Extract class

Trigger: Class > 400 lines, SRP violation (2+ unrelated responsibility).

Common splits:
- ViewModel + Mapper/Reducer tách rời
- Repository impl + DataSource (Local, Remote, Cache)
- Composable + State holder (`rememberStateHolder`)

### P-03 — Inline abstraction

Trigger: Interface 1 impl + không có test fake dùng → remove interface.

```kotlin
// Before
interface BookStorage { suspend fun save(book: Book) }
class BookStorageImpl : BookStorage { ... }

// After (nếu không có 2+ impl hoặc test fake)
class BookStorage { suspend fun save(book: Book) { ... } }
```

**Caution**: giữ interface nếu plan test fake hoặc tương lai 2+ impl (ví dụ platform expect/actual).

### P-04 — Move cross-layer

Trigger: Business logic ở sai layer (Composable chứa coroutine business, ViewModel chứa Compose state).

```kotlin
// Anti: logic trong Composable
@Composable
fun BookScreen() {
    val coroutineScope = rememberCoroutineScope()
    val repo = koinInject<BookRepository>()
    LaunchedEffect(Unit) {
        coroutineScope.launch {
            val book = repo.getBook("x")
            ...
        }
    }
}

// Fix: move sang ViewModel
@Composable
fun BookScreen(viewModel: BookViewModel = koinViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    // UI render only
}
```

### P-05 — Rename for clarity

- `data` → `response` cho DTO
- `BookRepo` → `BookRepository` (full)
- `onClick` → `onBookmarkToggle` (specific intent)
- `isOk` → `isValid` (positive assertion)

### P-06 — Split file

File > 400 lines → tách theo responsibility, giữ public API path.

```kotlin
// Before: BookDetailViewModel.kt (500 lines)

// After:
// BookDetailViewModel.kt (150 lines)
// BookDetailContract.kt (80 lines - moved out)
// BookDetailReducer.kt (120 lines - pure reducer)
// BookDetailAnalytics.kt (50 lines - event tracking)
```

### P-07 — Extract feature module

Trigger: Future-SDK extraction. Move `presenter/feature/<x>/` thành library module `:feature-<x>`.

Steps:
1. Enforce MOD-001..003 trước (public API minimal, internal default)
2. Create new Gradle module
3. Move files, update namespace
4. Update DI binding
5. Verify no cross-feature import

Chi tiết trong `android-sdk-structure` skill (future khi có).

## Common refactor smells to detect

| Smell | Pattern | Action |
|---|---|---|
| Long method (> 50 lines) | Multiple paragraph of logic | P-01 extract function |
| God class (> 400 lines) | Mixing responsibility | P-02 extract class |
| Interface 1 impl no fake | Unused abstraction | P-03 inline |
| Shotgun surgery | Change ripple through many files | Rethink architecture, maybe P-04 |
| Feature envy | Composable touching Repository | P-04 move to VM |
| Primitive obsession | `String` for ID, `Long` for timestamp | Introduce value class |
| Dead code | Unused class/function | Delete after `grep` confirm no reference |
| Duplicated code | Same logic 3+ places | P-01 extract function or object |
| Comment explains WHAT | Comment duplicates code | Rename or extract function |
| Magic number | `if (count > 42)` | Extract `const val` with name |

## Required policies

- Workflow `refactor-module.md`: preserve behavior; test suite identical before/after
- ARCH-001..014 (layer boundary vẫn hold sau refactor)
- KOT-001..012 (naming, visibility, immutability)
- Không gộp feature work vào refactor PR

## Decision guides

### Refactor hay rewrite?

- **Refactor** nếu: public API stable, test coverage đủ, incremental steps feasible
- **Rewrite** nếu: API cần redesign, test không đủ confidence → viết test trước, rồi refactor hoặc rewrite

### Interface giữ hay bỏ?

Giữ interface khi:
- 2+ impl thực sự tồn tại
- Test cần fake
- Platform expect/actual
- Public SDK contract

Bỏ interface khi:
- 1 impl, no test fake, no plan
- Abstraction leak (interface expose detail impl)

### Khi deviate blueprint

- Ghi rationale trong PR
- Vẫn pass Konsist rule MUST
- Reference blueprint ở `blueprints/reference-feature/`

## Common mistakes

| Mistake | Fix |
|---|---|
| Refactor + feature work gộp 1 PR | Tách commit riêng |
| Change behavior "incidentally" | Phải là feature work, dùng workflow khác |
| Commit broken intermediate | Mỗi commit compile + test pass |
| Rename public API không migration | Add deprecated alias nếu library |
| Over-abstract: tạo interface cho hypothetical | YAGNI, add when 2nd impl appears |
| Scope creep: refactor ngoài target package | Dừng, mở PR riêng |

## Output contract

- Code pass test suite identical trước/sau (behavior preserved)
- Konsist/Detekt pass hoặc baseline shrink
- File size reduced hoặc organization clearer
- Commit history clean (small atomic commits)
- Report theo `workflows/refactor-module.md §Stage 5`

## Anti-patterns bị cấm

- Gộp refactor + bugfix + feature
- Big-bang refactor (một PR 1000+ lines)
- Skip baseline test → không biết regression
- Rename "while I'm here" ngoài scope
- Dead code rename thay vì delete
- Over-engineering: tạo abstraction cho feature chưa tồn tại
