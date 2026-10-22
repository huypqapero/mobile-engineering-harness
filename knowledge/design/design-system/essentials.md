# Design System knowledge — essentials

Knowledge nền cho `designer` agent (produce UI/UX final từ wireframe + PRD). Token architecture, screen states, accessibility, dark mode, responsive, asset format.

## 1. Token layer architecture

### 3 tầng token (bắt buộc)

```
Primitive          Semantic           Component
─────────          ─────────          ─────────
blue-500           color.primary      Button.filled.bg
blue-700           color.primary.hover
gray-50            color.surface      Card.bg
gray-900           color.on-surface   Card.text
8dp                spacing.sm         Button.padding.v
16dp               spacing.md         Card.padding
```

### Rule
- **Primitive**: raw value, KHÔNG expose cho component. Chỉ dùng define semantic.
- **Semantic**: dùng mọi nơi trong UI. Flip theo theme (light ↔ dark).
- **Component**: chỉ khi component có variant riêng (ví dụ `Button.filled.bg` khác `Button.outlined.border`).

### Anti-patterns
- `Color(0xFF2196F3)` hardcode trong Compose → BLOCKER
- `Modifier.padding(16.dp)` hardcode magic number → dùng `spacing.md`
- Semantic trùng tên primitive (`color.blue500 = blue-500`) → defeat purpose

## 2. 5 screen states (bắt buộc cho remote-data screen)

| State | Visual | When | Notes |
|---|---|---|---|
| **loading** | Skeleton / Shimmer / Spinner | Fetching | Match layout shape (skeleton > spinner) |
| **empty** | Illustration + message + CTA | Data count = 0 | N/A nếu screen có id = must-have-data |
| **error** | ErrorView + retry CTA | API fail, parse fail | Specific message theo error class |
| **offline** | OfflineBanner trên top + cached data | No network | Cached preferred over empty |
| **success** | Full layout | Data loaded OK | Default state |

### Decision — sealed interface vs data class

| Pattern | Khi dùng |
|---|---|
| **sealed interface** cho state | Render shape khác biệt giữa states (ví dụ `AuthState: SignedOut \| Loading \| SignedIn`) |
| **data class** với flag | Shape giống nhau, chỉ khác value (ví dụ `BookDetailState(isLoading, data, error)`) |

Default: `data class` cho remote-data screen (5 states share same layout shell).

## 3. Accessibility (WCAG 2.1 AA)

### Checklist cứng

- [ ] **Contrast ratio** body text ≥ 4.5:1 với background
- [ ] **Contrast ratio** large text (18pt+) ≥ 3:1
- [ ] **Touch target** min 48dp × 48dp (Android) / 44pt × 44pt (iOS)
- [ ] **Content description** mọi image/icon có semantic meaning (null OK cho decorative)
- [ ] **Focus order** keyboard nav / screen reader → logical reading order
- [ ] **No color-only signal** — error không chỉ dùng màu đỏ, phải có text/icon kèm
- [ ] **Font scaling** support ≥ 200% không break layout
- [ ] **Click vs long-press** — long-press phải có fallback (menu button)

### Compose implementation hint

```kotlin
Image(
    painter = painterResource(R.drawable.ic_bookmark),
    contentDescription = stringResource(R.string.bookmark_action), // không null nếu interactive
    modifier = Modifier
        .size(48.dp)  // touch target
        .semantics { role = Role.Button }
)
```

## 4. Dark mode

### Flip rule
Semantic token flip automatically. Component code KHÔNG check `isDarkMode`:

```kotlin
// ✅ Correct — token flip theo theme
Surface(color = MaterialTheme.colorScheme.surface) { ... }

// ❌ Wrong — code logic branch theme
val bg = if (isDarkMode) Color.Black else Color.White
```

### Verify contrast cả 2 theme
- Light mode: body 4.5:1 OK
- Dark mode: body 4.5:1 OK (dễ fail hơn vì gray-on-dark)
- Dùng tool verify (ví dụ Compose Material Theme Builder)

### Image + icon
- Vector drawable + `tint = MaterialTheme.colorScheme.onSurface` → flip theo theme
- Raster image có brand color → không flip, giữ nguyên
- Illustration có nền trắng → cần dark variant riêng

## 5. Responsive breakpoint

### Scope
Áp dụng khi project support tablet / foldable. Phone-only → skip.

### Breakpoint matrix (Material 3 Window Size Class)

| Class | Width | Device | Layout |
|---|---|---|---|
| Compact | 0-599dp | Phone portrait | Single column, bottom nav |
| Medium | 600-839dp | Phone landscape, small tablet, foldable unfolded | Two column list-detail |
| Expanded | 840dp+ | Large tablet, desktop | Three column, side rail nav |

### Rule
- Design cho Compact mặc định
- Medium / Expanded: adaptive variant chỉ khi có value rõ (list-detail pattern, dashboard)
- Không duplicate design cho mọi breakpoint

## 6. Asset format matrix

| Asset type | Format preferred | Fallback | Notes |
|---|---|---|---|
| Icon | Vector drawable XML (Android) | SVG | Scalable, tint-able |
| Illustration | SVG | PNG @1x@2x@3x | Có brand color → raster |
| Logo | Vector preferred | PNG | Brand-approved only |
| Photo | WebP (lossy) | PNG | WebP < 1/2 size PNG |
| Animation | Lottie JSON | GIF | Lottie < 1/10 size GIF |
| Hero banner | WebP + srcset | PNG | Responsive load |

### Export path
Save tại `briefs/<slug>/assets/design/`:
- `icons/*.xml` (vector drawable)
- `illustrations/*.svg`
- `photos/*.webp`
- `lottie/*.json`

### Rule
- Icon size: 24dp x 24dp mặc định, 48dp cho standalone trigger
- Illustration height ≤ 240dp (phone) để không chiếm quá nửa màn
- Photo max dimension 1920px (3x on 640dp wide screen)

## 7. Component reuse

### Decision tree

```
Có component existing cover 80%+ use case?
├─ YES → REUSE
├─ Cover 50-80% → EXTEND (add variant param)
└─ Cover < 50% → NEW (flag "new component needed" cho Tech Lead review)
```

### Audit before design
1. Check `docs/design-guidelines.md` component library
2. Check existing Compose component trong `{{MODULE_PRESENTER}}/.../components/`
3. Nếu NEW: justify trong `design.md` section "New components"

## 8. Anti-patterns

- Design chỉ success state, bỏ loading/empty/error
- Hardcode color/spacing thay vì semantic token
- Tạo component mới khi existing cover 80%+
- Contrast < WCAG AA (body 4.5:1)
- Touch target < 48dp
- Icon interactive không content description
- Dark mode "để sau" cho project support dark mode
- Override user flow PRD mà không raise ChangeRequest
- Export icon dưới dạng PNG thay vì vector
- Design-spec field vague ("make it modern", "clean look") — Coder không execute được

## 9. Dependency

- `agents/designer.md` — role spec
- `agents/workflows/feature-full-flow.md` — Stage 3 Design
- `agents/product-analyst.md` — upstream (wireframe + PRD)
- Project `docs/design-guidelines.md` (nếu có design system)
- Material 3 Compose docs
- WCAG 2.1 standard

## 10. Last updated

- Date: 2026-10-22
- Dependency version: harness v0.21.0, Compose Material 3 1.3+
- Review trigger: khi design system project update major version, hoặc WCAG 2.2 adoption
