---
name: coding-compose
description: Build hoặc refactor Compose Multiplatform UI theo design system {{PRODUCT_NAME}}. Trigger khi tạo screen, component, hoặc fix UI bug/performance.
priority: P0
---

# Skill: coding-compose

## Trigger

- Tạo Compose screen hoặc component
- Refactor UI (recomposition issue, performance)
- Add animation, transition
- Fix accessibility issue

## Inputs

- Design mock / frame reference (nếu có)
- UI state định nghĩa trong contract
- Design token: color, typography, spacing (xem `docs/design-guidelines.md`)

## Prerequisites

1. `knowledge/compose/essentials.md`
2. `knowledge/compose/ui-resilience.md` — text theo locale, font scale, RTL, edge-to-edge/insets
3. `docs/design-guidelines.md`
4. `docs/ui-catalog/` cho component pattern
5. `presenter/theme/*` cho token available

## Execution procedure

### Step 1 — Decompose UI

Chia screen thành layers:

```
RouteScreen (stateful, ViewModel)
  └── Content (stateless, pure)
       ├── TopAppRow / SectionHeader
       ├── MainArea
       │    ├── LoadingState
       │    ├── EmptyState
       │    ├── ErrorState
       │    ├── OfflineState
       │    └── SuccessContent
       │         └── Items (reusable component)
       └── BottomSheet / FullScreenPlayer (overlay)
```

### Step 2 — Implement stateless first

Build `Content` composable nhận state + callback:

```kotlin
@Composable
private fun BookDetailContent(
    state: BookDetailState,
    onIntent: (BookDetailIntent) -> Unit,
    modifier: Modifier = Modifier,
) {
    when {
        state.isLoading && state.book == null -> LoadingState()
        state.isOffline && state.book == null -> OfflineState(onRetry = { onIntent(BookDetailIntent.Retry) })
        state.error != null && state.book == null -> ErrorState(error = state.error, onRetry = { onIntent(BookDetailIntent.Retry) })
        state.book == null -> EmptyState()
        else -> SuccessContent(book = state.book, onIntent = onIntent)
    }
}
```

### Step 3 — Wrap stateful route

```kotlin
@Composable
fun BookDetailScreen(
    bookId: String,
    onNavigate: (NavRoute) -> Unit,
    viewModel: BookDetailViewModel = koinViewModel { parametersOf(bookId) },
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    EffectHandler(viewModel.effect, onNavigate)
    BookDetailContent(
        state = state,
        onIntent = viewModel::onIntent,
    )
}
```

### Step 4 — Theme + token

```kotlin
Text(
    text = book.title,
    style = {{THEME_CLASS}}.typography.titleLarge,
    color = {{THEME_CLASS}}.colors.textPrimary,
)
Spacer(Modifier.height({{THEME_CLASS}}.spacing.md))
```

**MUST**: không hardcode `Color(0xFF...)` hoặc `16.dp` trong feature code.
Dùng tokens từ `{{THEME_CLASS}}`.

### Step 5 — Lazy list key

```kotlin
LazyColumn {
    items(state.books, key = { it.id }) { book ->
        BookRow(book, onClick = { onIntent(BookDetailIntent.Select(book.id)) })
    }
}
```

### Step 6 — Previews

```kotlin
@Preview
@Composable
private fun BookDetailContentPreview() {
    {{THEME_CLASS}} {
        BookDetailContent(
            state = BookDetailState(book = fakeBook(), isLoading = false),
            onIntent = {},
        )
    }
}

@Preview
@Composable
private fun BookDetailLoadingPreview() {
    {{THEME_CLASS}} {
        BookDetailContent(state = BookDetailState(isLoading = true), onIntent = {})
    }
}

@Preview
@Composable
private fun BookDetailErrorPreview() {
    {{THEME_CLASS}} {
        BookDetailContent(
            state = BookDetailState(error = UiText.Raw("Network error")),
            onIntent = {},
        )
    }
}
```

Preview mọi state visible, không chỉ success.

### Step 7 — Accessibility + UI resilience

- `contentDescription` cho mọi icon-only button
- `semantics { heading() }` cho section header
- Touch target ≥ 48dp (`Modifier.minimumInteractiveComponentSize()`)
- Content scaling: không fix `fontSize` tuyệt đối, dùng `MaterialTheme.typography`
- Text theo locale: container chứa text không cố định width/height; label dài trong Row dùng `Modifier.weight(1f)` hoặc `widthIn`; chỉ đặt `maxLines` + `TextOverflow.Ellipsis` khi cắt là chủ đích (xem `knowledge/compose/ui-resilience.md` §1)
- Font scale: component chứa text dùng `heightIn(min = ...)` thay vì `height(...)` để không cắt text ở font scale 200% (§2)
- RTL: dùng `start`/`end`, không `left`/`right` vật lý; icon có hướng dùng `Icons.AutoMirrored.*` (§3)
- Insets: screen tự xử lý edge-to-edge — dùng `innerPadding` của `Scaffold` hoặc `safeDrawingPadding()` (đã gồm IME); thêm `imePadding()` cho screen có input khi chỉ padding system bars hoặc `innerPadding` (§4)

### Step 8 — Verify

```bash
./gradlew :presenter:assembleDebug
./gradlew :presenter:test
./gradlew detekt
```

Visual verify (chi tiết `knowledge/compose/ui-resilience.md` §5):

- Preview render đủ states; dark theme pass
- Preview font scale 2.0 và RTL: text không bị cắt, layout không vỡ, layout mirror đúng. Dùng cách preview hợp với source set (`ui-resilience.md` §5)
- Locale chuỗi dài: preview `locale = "de"` hoặc chạy pseudo-locale `en-XA` / `ar-XB` trên device (Android): không tràn, không cắt ngoài ý muốn
- Khi có device/emulator: chạy edge-to-edge (target SDK 35+), content không nằm dưới status bar, navigation bar, cutout hoặc bàn phím. Không có device → ghi rõ "insets chưa verify trên device" trong report

## Required policies

- ARCH-006 feature self-contained
- ARCH-007 MVI 1-chiều
- ARCH-008 5 states
- ARCH-012 file < 400 dòng
- CORO-006 lifecycle collect

## Patterns

### Modifier chain discipline

```kotlin
// ❌ modifier chain lộn xộn
BookCover(book).padding(16.dp).fillMaxWidth().clickable { }

// ✅ receiver = component root, modifier chain từ outer-in
BookCover(
    book = book,
    modifier = Modifier
        .fillMaxWidth()
        .padding(16.dp)
        .clickable { onClick() },
)
```

### State hoisting

Hoist state lên owner thấp nhất chung của reader + writer. Leaf composable nhận state qua param, emit event qua lambda.

### Side effect pattern

```kotlin
// Toast handler
LaunchedEffect(Unit) {
    viewModel.effect.collect { effect ->
        when (effect) {
            is Toast -> toastBus.show(effect.text)
            is Navigate -> onNavigate(effect.route)
        }
    }
}
```

## Common mistakes

| Mistake | Fix |
|---|---|
| `collectAsState()` không lifecycle | `collectAsStateWithLifecycle()` |
| Hardcode color/spacing | `{{THEME_CLASS}}.colors/spacing` |
| `items(list)` không key | `items(list, key = { it.id })` |
| `remember { ... }` không key cho data phụ thuộc param | `remember(param) { ... }` |
| Lambda inline `onClick = { ... }` → không stable → recompose | `onClick = viewModel::onAction` |
| Preview chỉ success state | Preview đủ 5 state |
| `Modifier.height(48.dp)` / `width(...)` cố định cho container chứa text | `heightIn(min = ...)`, `weight(1f)`, `widthIn(max = ...)` |
| Content bị status bar / navigation bar che khi edge-to-edge | Dùng `innerPadding` của `Scaffold` hoặc `safeDrawingPadding()` |
| Icon button không `contentDescription` | Thêm cho a11y |
| Logic nghiệp vụ trong Composable | Delegate sang ViewModel |

## Output contract

- Composable mới ở đúng feature package
- Preview ≥ 2 state (ít nhất success + 1 edge)
- Design token sử dụng, không hardcode
- Accessibility smoke pass (content description, min target)

## Validation

- [ ] Preview render đúng mọi state critical
- [ ] Dark theme pass
- [ ] Font scale 200% + locale chuỗi dài + RTL không cắt/tràn text
- [ ] Insets xử lý đúng (system bar, cutout, IME), hoặc report ghi rõ chưa verify trên device
- [ ] Không hardcode color/spacing/typography
- [ ] Lazy list có key
- [ ] `collectAsStateWithLifecycle()` nếu collect Flow
- [ ] Detekt pass

## Anti-patterns

- Composable viết logic repository/API call
- `MutableState` leak sang parent qua reference capture
- Modifier chain quá dài (> 6 operations) → extract Modifier variable
- Preview không {{THEME_CLASS}} wrap

---

## Harness context

- Workflow: `workflows/feature-development.md`
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`


## Overlay gate (D-full)

Trước Step 1, verify `.harness-overlay/overlay.yaml` tồn tại. Nếu không, abort với status `BLOCKED` và chỉ dẫn user:

> Chưa có overlay. Chạy skill `harness-init` để scaffold trước, sau đó quay lại skill này.

Khi gặp placeholder `{{X}}` trong procedure/code example, resolve bằng mapping ở `AGENTS.md §Placeholder resolution` (Read overlay 1 lần đầu session, cache qua context).
