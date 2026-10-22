# Compose UI Resilience — Locale, Font scale, RTL, Edge-to-edge

## Overview

UI chạy đúng với chuỗi tiếng Anh, font mặc định và portrait trên một máy vẫn có thể vỡ khi user đổi ngôn ngữ, tăng cỡ chữ, dùng ngôn ngữ RTL, hoặc khi app chạy edge-to-edge dưới system bar. File này bổ sung `knowledge/compose/essentials.md`, gom các pattern để tránh text bị cắt/tràn và content bị system UI che.

Đây là guidance (nên / tránh), không phải rule MUST trong `constitution/`.

### Source set

Profile `cmp` viết UI trong `{{MODULE_PRESENTER}}/src/commonMain/`; profile `kmp` chỉ có Compose ở phía Android (iOS dùng SwiftUI); profile `android-only` không có `commonMain`. Bảng dưới cho biết mỗi API dùng được ở đâu:

| API | `cmp` | `kmp` (Android UI) / `android-only` |
|---|---|---|
| `Text(maxLines, overflow, softWrap, minLines)`, `Modifier.weight/widthIn/heightIn` | `commonMain` | có |
| `LocalLayoutDirection`, `Icons.AutoMirrored.*`, `ImageVector.Builder(autoMirror = true)` | `commonMain` | có |
| `WindowInsets.safeDrawing/systemBars/ime/displayCutout`, `safeDrawingPadding()`, `windowInsetsPadding()`, `imePadding()`, `consumeWindowInsets()`, `Scaffold(contentWindowInsets)` | `commonMain` (CMP 1.5+) | có |
| `@Preview(locale, fontScale)` | `commonMain` từ CMP 1.10 (render qua Android tooling); trước đó chỉ `androidMain` | có |
| `@PreviewFontScale`, `@PreviewScreenSizes`, `@PreviewLightDark` | `androidMain` | có |
| `enableEdgeToEdge()`, `WindowCompat`, `android:supportsRtl`, pseudo-locale | `{{MODULE_APP}}/src/androidMain` (Activity) | app module Android |

Không import `androidx.activity.*` hoặc `android.*` vào `commonMain`: code common không compile được cho iOS.

## 1. Text theo locale

Chuỗi dịch thường dài hơn tiếng Anh. Chuỗi ngắn bị ảnh hưởng nặng nhất: theo bảng IBM do W3C trích dẫn, chuỗi tiếng Anh ≤ 10 ký tự khi dịch có thể dài 200–300%, chuỗi > 70 ký tự khoảng 130%. Checklist localization cũ của Android khuyên chừa thêm "up to 30%" chỗ trống. Vì vậy label của button, tab và chip là chỗ hay vỡ nhất.

### Không cố định kích thước container chứa text

```kotlin
// ❌ tiếng Đức / Nga bị cắt chữ
Button(onClick = onSave, modifier = Modifier.size(width = 120.dp, height = 40.dp)) {
    Text(stringResource(Res.string.save))
}

// ✅ để text quyết định kích thước, chỉ đặt giới hạn tối thiểu
Button(onClick = onSave, modifier = Modifier.heightIn(min = 48.dp)) {
    Text(stringResource(Res.string.save))
}
```

### Row có label dài: `weight` hoặc `widthIn`

```kotlin
// ❌ title dài đẩy action ra ngoài màn hình
Row {
    Text(book.title)
    IconButton(onClick = onBookmark) { ... }
}

// ✅ title chiếm phần còn lại, action luôn hiện
Row(verticalAlignment = Alignment.CenterVertically) {
    Text(
        text = book.title,
        modifier = Modifier.weight(1f),
        maxLines = 2,
        overflow = TextOverflow.Ellipsis,
    )
    IconButton(onClick = onBookmark) { ... }
}
```

### `maxLines` + `TextOverflow` có chủ đích

- Chỉ đặt `maxLines` khi thiết kế cho phép cắt (title trong list item, preview text). Khi đó luôn đi kèm `overflow = TextOverflow.Ellipsis` để user biết text bị cắt.
- Không đặt `maxLines = 1` cho thông báo lỗi, label button hoặc nội dung user cần đọc đủ. Để wrap (`softWrap = true` là mặc định).
- Cần giữ chiều cao ổn định giữa các item (grid) → dùng `minLines` thay vì `height(...)`.

```kotlin
// ❌ cắt im lặng, user không biết thiếu chữ
Text(error.message, maxLines = 1)

// ✅ thông báo lỗi được wrap đủ dòng
Text(error.message, style = {{THEME_CLASS}}.typography.bodyMedium)
```

### Button và tab có label dài

- Tab nhiều mục hoặc label dài → `PrimaryScrollableTabRow` / `SecondaryScrollableTabRow` (Material 3; `ScrollableTabRow` đã deprecate ở M3, chỉ dùng với Material 2) thay vì tab row chia đều width.
- Hai button cạnh nhau có thể không vừa ở locale dài → dùng `FlowRow`, hoặc chuyển sang xếp dọc khi không đủ chỗ.
- Bottom navigation label nên ngắn; vẫn kiểm tra ở pseudo-locale `en-XA` (xem §5).

## 2. Font scale

Từ Android 14, system cho phép font scale đến 200% với đường cong nonlinear: chữ nhỏ phóng to nhiều hơn chữ lớn. Android khuyên luôn dùng `sp` cho text, không dùng `sp` cho padding, và không đặt chiều cao view dựa vào cỡ chữ.

- Text dùng `sp` qua typography token (`{{THEME_CLASS}}.typography.*`), layout dùng `dp`.
- Tránh `Modifier.height(...)` hoặc `size(...)` cố định cho container chứa text. Dùng `heightIn(min = ...)`.
- Không tính chiều cao từ `fontSize` (ví dụ `height = 16.sp.toDp() + 8.dp`): với nonlinear scaling, `4.sp + 20.sp` không chắc bằng `24.sp`.
- Screen có nhiều text nên scroll được (`verticalScroll` / `LazyColumn`) để content không bị đẩy khỏi màn hình ở 200%.

```kotlin
// ❌ ở fontScale 2.0 chữ bị cắt nửa dưới
Box(Modifier.height(40.dp)) {
    Text("Next", fontSize = 14.sp)
}

// ✅ token typography + chiều cao tối thiểu
Box(Modifier.heightIn(min = 48.dp), contentAlignment = Alignment.Center) {
    Text(stringResource(Res.string.next), style = {{THEME_CLASS}}.typography.labelLarge)
}
```

## 3. RTL

Compose tự mirror layout theo `LocalLayoutDirection` (arabic, hebrew, persian...). Code chỉ cần không phá cơ chế đó.

- Dùng `start`/`end` (`padding(start = ...)`, `Alignment.Start`, `Arrangement.Start`). Tránh `absolutePadding(left = ...)`, `AbsoluteAlignment.Left`, `Arrangement.Absolute.*` trừ khi thật sự cần hướng vật lý.
- Icon có hướng (back, forward, send, list bullet...) dùng `Icons.AutoMirrored.*`. Vector tự định nghĩa đặt `autoMirror = true` trong `ImageVector.Builder`. Logo, icon media (play) và số không mirror.
- Cần vẽ/offset theo hướng → đọc `LocalLayoutDirection.current`, không giả định LTR.
- Text số, số điện thoại, mã code nên giữ LTR ngay cả trong RTL.

```kotlin
// ❌ RTL: icon back chỉ sai hướng, padding nằm sai cạnh
Icon(Icons.Filled.ArrowBack, contentDescription = stringResource(Res.string.back))
Text(title, modifier = Modifier.absolutePadding(left = 16.dp))

// ✅ tự mirror theo layout direction
Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(Res.string.back))
Text(title, modifier = Modifier.padding(start = {{THEME_CLASS}}.spacing.md))
```

Android-only: khai báo `android:supportsRtl="true"` trong `AndroidManifest.xml` để app nhận layout direction RTL. Drawable XML có hướng đặt `android:autoMirrored="true"`.

## 4. Edge-to-edge và WindowInsets

Trên Android 15, app target SDK 35 mặc định edge-to-edge: content vẽ dưới status bar và navigation bar. App target SDK 36 chạy trên Android 16 không còn opt-out được (`windowOptOutEdgeToEdgeEnforcement` bị disable). Screen phải tự xử lý insets.

### Scaffold: dùng `innerPadding`

`Scaffold` nhận insets qua `contentWindowInsets` nhưng không tự áp lên content. Content phải dùng `innerPadding`.

```kotlin
// ❌ bỏ qua innerPadding → item đầu nằm dưới top bar, item cuối dưới navigation bar
Scaffold(topBar = { TopBar() }) { _ ->
    LazyColumn { ... }
}

// ✅
Scaffold(topBar = { TopBar() }) { innerPadding ->
    LazyColumn(contentPadding = innerPadding) { ... }
}
```

### Screen không có Scaffold

- `Modifier.safeDrawingPadding()` (tương đương `windowInsetsPadding(WindowInsets.safeDrawing)`) cho content không được vẽ dưới system UI. `safeDrawing` gồm system bars, display cutout và bàn phím (IME).
- Background/ảnh full-bleed vẫn vẽ tràn, chỉ content tương tác mới padding.
- Chỉ padding `systemBars` / `statusBars` (không dùng `safeDrawing`) mà screen có text field → thêm `Modifier.imePadding()` để bàn phím không che input.
- Cutout: dùng `WindowInsets.displayCutout`, `safeContent` hoặc `safeDrawing`. Không hardcode chiều cao status bar (24dp...).
- Inset padding modifier (`windowInsetsPadding`, `safeDrawingPadding`, `imePadding`) tự consume phần đã áp, nên lồng nhau không padding trùng. `Modifier.padding(innerPadding)` thì không consume: nếu child còn dùng inset modifier, thêm `.consumeWindowInsets(innerPadding)`.

```kotlin
// ❌ hardcode chiều cao status bar; sai trên máy có cutout, không xử lý bàn phím
Column(Modifier.padding(top = 24.dp)) { LoginForm() }

// ✅
Column(
    Modifier
        .fillMaxSize()
        .safeDrawingPadding(), // gồm cả IME
) { LoginForm() }

// ❌ Scaffold + child imePadding: padding(innerPadding) không consume → bottom bị cộng hai lần
Scaffold { innerPadding ->
    Column(Modifier.padding(innerPadding).imePadding()) { LoginForm() }
}

// ✅
Scaffold { innerPadding ->
    Column(
        Modifier
            .padding(innerPadding)
            .consumeWindowInsets(innerPadding)
            .imePadding(),
    ) { LoginForm() }
}
```

### Android-only: bật edge-to-edge và màu icon system bar

- Gọi `enableEdgeToEdge()` trong `onCreate` của Activity (app module, `androidMain`), sau `super.onCreate` và trước `setContent`. Cần cho máy chạy Android 14 trở xuống; Android 15+ với target SDK 35 đã edge-to-edge sẵn. Mặc định system bar trong suốt, riêng navigation 3 nút có scrim mờ.
- `enableEdgeToEdge()` thuộc `androidx.activity` (stable 1.13). Release notes `activity 1.14.0-alpha03` khuyên dùng `WindowCompat.enableEdgeToEdge(window)` (core 1.17+) thay thế; biến thể này không nhận `SystemBarStyle`, nên phải tự set màu icon như dòng dưới. Dùng API khớp version trong `libs.versions.toml` của product.
- Màu icon status bar / navigation bar phải tương phản với background ở cả light và dark theme: `WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars = !isDark`.

```kotlin
// ✅ {{MODULE_APP}}/src/androidMain/.../MainActivity.kt
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    enableEdgeToEdge()
    setContent { App() }
}
```

iOS (cmp): cùng API `WindowInsets` áp dụng cho safe area; kiểm tra trên simulator có notch / Dynamic Island.

## 5. Cách kiểm tra

### Preview

Common, mọi version CMP: override `LocalDensity` / `LocalLayoutDirection` trong preview. `Density(fontScale = 2f)` phóng to tuyến tính, mạnh hơn đường cong nonlinear của Android 14, nên an toàn để bắt lỗi cắt chữ.

```kotlin
@Preview
@Composable
private fun BookRowLargeFontRtlPreview() {
    val density = LocalDensity.current
    CompositionLocalProvider(
        LocalDensity provides Density(density.density, fontScale = 2f),
        LocalLayoutDirection provides LayoutDirection.Rtl,
    ) {
        {{THEME_CLASS}} { BookRow(book = fakeBook(title = "Ein sehr langer deutscher Buchtitel")) }
    }
}
```

Android (`androidMain`, profile `kmp`/`android-only`; `@Preview(locale, fontScale)` cũng dùng được trong `commonMain` từ CMP 1.10): dùng tham số của `androidx.compose.ui.tooling.preview.Preview`.

```kotlin
// ❌ chỉ 1 locale, font mặc định → không thấy lỗi cắt chữ
@Preview
@Composable
private fun SettingsPreview() { ... }

// ✅
@Preview(name = "de", locale = "de")
@Preview(name = "ar RTL", locale = "ar")
@PreviewFontScale            // 7 mức font scale, đến 2.0
@Composable
private fun SettingsPreview() { ... }
```

Multipreview có sẵn từ `ui-tooling-preview` 1.6.0: `@PreviewFontScale`, `@PreviewScreenSizes`, `@PreviewLightDark`, `@PreviewDynamicColors`. Preview với `locale` chỉ đổi chuỗi khi product có resource cho locale đó; nếu không, truyền chuỗi dài giả vào preview.

### Pseudo-locale (Android)

- `en-XA`: thêm dấu và kéo dài chuỗi tiếng Anh → lộ text bị cắt, chuỗi hardcode chưa dịch.
- `ar-XB`: đổi hướng sang RTL → lộ layout không mirror.
- Bật trong debug build: `buildTypes { debug { isPseudoLocalesEnabled = true } }`, rồi chọn "English (XA)" / "AR (XB)" trong Settings > Languages (cần bật developer options).

### Checklist test tay

- [ ] Pseudo-locale `en-XA`: không label nào bị cắt ngoài ý muốn, không chuỗi hardcode
- [ ] Pseudo-locale `ar-XB` hoặc locale `ar`: layout và icon có hướng mirror đúng
- [ ] Font size lớn nhất (200%) + display size lớn: text không bị cắt, screen scroll được
- [ ] Thiết bị / emulator target SDK 35+: content không nằm dưới status bar, navigation bar (cả gesture và 3 nút), cutout
- [ ] Mở bàn phím ở screen có input: field đang focus không bị che
- [ ] Light + dark theme: icon status bar / navigation bar đọc được

## Common mistakes

| Mistake | Fix |
|---|---|
| `Modifier.size(w, h)` / `height(...)` cố định cho button, chip chứa text | `heightIn(min = ...)`, để text quyết định width |
| Row có title dài không `weight` → đẩy action ra ngoài | `Modifier.weight(1f)` cho text |
| `maxLines = 1` không `overflow` | Thêm `TextOverflow.Ellipsis`, hoặc bỏ `maxLines` nếu cần đọc đủ |
| Tab row chia đều với label dài | `PrimaryScrollableTabRow` / `SecondaryScrollableTabRow` |
| `fontSize = 14.sp` hardcode, tính chiều cao từ `sp` | Typography token, `heightIn(min = ...)` |
| `absolutePadding(left = ...)`, `AbsoluteAlignment.Left` | `padding(start = ...)`, `Alignment.Start` |
| `Icons.Filled.ArrowBack` (không mirror) | `Icons.AutoMirrored.Filled.ArrowBack` |
| Bỏ qua `innerPadding` của `Scaffold` | `contentPadding = innerPadding` / `Modifier.padding(innerPadding)` |
| `padding(innerPadding)` rồi child `imePadding()` → padding trùng | Thêm `.consumeWindowInsets(innerPadding)` |
| Hardcode `padding(top = 24.dp)` cho status bar | `safeDrawingPadding()` / `windowInsetsPadding(WindowInsets.statusBars)` |
| Input bị bàn phím che | `imePadding()` |
| Import `androidx.activity` / `enableEdgeToEdge` trong `commonMain` | Đặt ở Activity trong `androidMain` |
| Preview chỉ 1 locale, 1 font scale | Thêm preview font scale 2.0, RTL, chuỗi dài |

## References

- Text expansion: [W3C — Text size in translation](https://www.w3.org/International/articles/article-text-size) (bảng IBM); [Android localization checklist (archived)](https://web.archive.org/web/20170107002824/https://developer.android.com/distribute/tools/localization-checklist.html) — "up to 30% more is normal"
- [Compose — Configure text layout](https://developer.android.com/develop/ui/compose/text/configure-layout) — `maxLines`, `overflow`
- [Android 14 — Nonlinear font scaling to 200%](https://developer.android.com/about/versions/14/features#non-linear-font-scaling)
- [Compose — Support user-scalable content](https://developer.android.com/develop/ui/compose/accessibility/scalable-content); [Google Accessibility Help — Text scaling](https://support.google.com/accessibility/android/answer/12159181)
- [Support different languages and cultures (RTL)](https://developer.android.com/training/basics/supporting-devices/languages); [`Icons.AutoMirrored`](https://developer.android.com/reference/kotlin/androidx/compose/material/icons/Icons.AutoMirrored); [Compose custom layouts — `LocalLayoutDirection`](https://developer.android.com/develop/ui/compose/layouts/custom); [CMP RTL](https://kotlinlang.org/docs/multiplatform/compose-rtl.html)
- [Android 15 behavior changes — edge-to-edge for target SDK 35](https://developer.android.com/about/versions/15/behavior-changes-15); [Android 16 behavior changes — opt-out disabled for target SDK 36](https://developer.android.com/about/versions/16/behavior-changes-16)
- [Compose — Set up edge-to-edge](https://developer.android.com/develop/ui/compose/system/setup-e2e); [Window insets](https://developer.android.com/develop/ui/compose/system/insets); [Inset modifiers](https://developer.android.com/develop/ui/compose/system/insets-ui); [Material insets / Scaffold](https://developer.android.com/develop/ui/compose/system/material-insets); [Display cutouts](https://developer.android.com/develop/ui/compose/system/cutouts)
- [androidx.activity releases](https://developer.android.com/jetpack/androidx/releases/activity) — 1.14.0-alpha03: dùng `WindowCompat#enableEdgeToEdge(Window)` thay `EdgeToEdge#enable()`
- [Pseudolocales](https://developer.android.com/guide/topics/resources/pseudolocales)
- [Compose previews](https://developer.android.com/develop/ui/compose/tooling/previews); [`@PreviewFontScale`](https://developer.android.com/reference/kotlin/androidx/compose/ui/tooling/preview/PreviewFontScale); [CMP previews](https://kotlinlang.org/docs/multiplatform/compose-previews.html)
- `knowledge/compose/essentials.md` — state, recomposition, theming, previews
