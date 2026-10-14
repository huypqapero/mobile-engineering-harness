# E04 — Compose: Lazy List Recomposition + Lifecycle-aware Collect

## Scenario

Yêu cầu agent build Compose screen render list sách lớn (~500 items) với 3 behavior critical:
1. Collect ViewModel state lifecycle-aware
2. Lazy list có key để tránh re-create state
3. Items không bị recompose thừa khi scroll

## Prompt mẫu

> Build `BookListScreen` cho {{PRODUCT_NAME}}: hiển thị LazyColumn 500 cuốn sách, mỗi item có cover + title + bookmark button. Follow `.harness/skills/android-compose/SKILL.md` và `.harness/knowledge/compose/essentials.md`.

## Expected implementation

```kotlin
@Composable
internal fun BookListScreen(
    viewModel: BookListViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()   // ✓ 1
    BookListContent(
        state = state,
        onIntent = viewModel::onIntent,                           // ✓ stable reference
    )
}

@Composable
private fun BookListContent(
    state: BookListState,
    onIntent: (BookListIntent) -> Unit,
) {
    LazyColumn(
        contentPadding = PaddingValues({{THEME_CLASS}}.spacing.md),
    ) {
        items(
            items = state.books,
            key = { it.id },                                       // ✓ 2
            contentType = { "book" },                              // ✓ 3 bonus
        ) { book ->
            BookRow(
                book = book,
                onToggleBookmark = { onIntent(BookListIntent.ToggleBookmark(book.id)) },
            )
        }
    }
}

@Composable
private fun BookRow(
    book: Book,                                                    // ✓ data class stable
    onToggleBookmark: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(modifier = modifier.fillMaxWidth().padding(vertical = {{THEME_CLASS}}.spacing.sm)) {
        BookCover(url = book.coverUrl, modifier = Modifier.size(64.dp))
        Spacer(Modifier.width({{THEME_CLASS}}.spacing.md))
        Column(Modifier.weight(1f)) {
            Text(book.title, style = {{THEME_CLASS}}.typography.titleMedium)
            Text(book.author, style = {{THEME_CLASS}}.typography.bodySmall)
        }
        IconButton(onClick = onToggleBookmark) {
            Icon(
                imageVector = if (book.isBookmarked) Icons.Default.Bookmark else Icons.Default.BookmarkBorder,
                contentDescription = if (book.isBookmarked) "Bỏ bookmark" else "Thêm bookmark",   // ✓ a11y
            )
        }
    }
}
```

## Evaluation checklist

| # | Check | Weight |
|---|---|---|
| 1 | `collectAsStateWithLifecycle()` thay vì `collectAsState()` | 20% |
| 2 | `items(list, key = { it.id })` | 20% |
| 3 | `data class Book` immutable `val` fields | 10% |
| 4 | Callback dùng method reference hoặc stable lambda, không recreate | 10% |
| 5 | Design token (`{{THEME_CLASS}}.spacing/typography/colors`) | 10% |
| 6 | `contentDescription` cho icon-only button | 10% |
| 7 | Stateless `BookRow`, hoisted callback | 10% |
| 8 | Preview có {{THEME_CLASS}} wrap + 2 state (full / empty) | 10% |

## Common failure modes

1. `collectAsState()` không lifecycle
2. `items(list)` không key → scroll gây re-create state item
3. Capture `viewModel` trong lambda item → unstable
4. Hardcode `16.dp`, `Color.Blue`
5. IconButton không `contentDescription`
6. `remember { ... }` cho data phụ thuộc param nhưng không truyền key
7. Logic nghiệp vụ trong Composable
8. Preview không wrap theme

## Advanced bonus (optional +10)

- `contentType = { "book" }` cho LazyColumn khi có nhiều loại item
- `derivedStateOf` cho computed values trong scope `remember(key) { ... }`
- `Modifier.minimumInteractiveComponentSize()` cho a11y

## Scoring

- 90–100: VERIFIED
- 75–89: VERIFIED_WITH_LIMITATIONS
- < 75: Needs rework
