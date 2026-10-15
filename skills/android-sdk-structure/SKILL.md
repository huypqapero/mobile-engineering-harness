---
name: android-sdk-structure
description: Tách một feature nội bộ thành SDK/library module dùng lại cho nhiều sản phẩm, có public API tối thiểu, cho phép host tuỳ biến UI và tuỳ biến luồng mà không lộ MVI internal. Trigger khi feature cần dùng ở 2+ sản phẩm hoặc overlay chuyển sang profile `sdk-library`.
priority: P2
---

# Skill: android-sdk-structure

Procedure tách `presenter/feature/<x>/` thành library module `:feature-<x>`. Đây là phần chi tiết của P-07 trong `skills/android-refactor/SKILL.md`; refactor orchestration dùng `workflows/refactor-module.md`.

**Không thuộc skill này**: tích hợp platform SDK bên thứ ba (ExoPlayer, AVPlayer, Firebase, Billing). Phần đó theo ARCH-010 (`{{MODULE_DATA}}/{androidMain,iosMain}` qua `expect/actual`) và `knowledge/patterns/common-patterns.md §Adapter`.

## Trigger

- Một feature cần dùng lại ở 2+ sản phẩm trong tổ chức
- Overlay chuyển `profile: app` → `profile: sdk-library` (MOD-001..003 lên MUST + binary-compat gate)
- Host app cần đổi giao diện hoặc thứ tự bước của feature mà không fork code

Không dùng khi chỉ 1 sản phẩm dùng feature. Giữ package trong `presenter/` và tuân MOD-001..003 ở mức SHOULD là đủ.

## Inputs

Bắt buộc:
- Tên feature (`<x>` cho module, `<Feature>` cho type)
- Danh sách consumer (sản phẩm nào dùng, version harness/Compose của từng bên)
- Danh sách điểm tuỳ biến mỗi consumer cần: UI (theme, slot, text) và luồng (step bật/tắt, step thay thế/chèn, kết quả trả về)

Optional:
- Feature nào khác đang navigate tới feature này
- Yêu cầu phân phối (module trong monorepo hay artifact Maven nội bộ)

## Prerequisites

1. `.harness/constitution/architecture-rules.md` — ARCH-006, ARCH-007, ARCH-009, ARCH-011, MOD-001..003
2. `.harness/skills/android-refactor/SKILL.md §P-07` — extract theo kiểu preserve-behavior
3. `.harness/knowledge/mvi/essentials.md` — `BaseViewModel`, contract State/Intent/Effect
4. `.harness/knowledge/architecture/architecture-profiles.md` — profile hiện tại của consumer
5. `.harness/verification/architecture-tests/TemplateArchitectureRulesTest.kt` — test MOD-002

## Execution procedure

### Step 1 — Pre-check MOD-001..003 (gate, chạy trong `presenter` trước khi tách)

Extract chỉ bắt đầu khi feature package đã pass cả ba rule ngay tại chỗ:

| Rule | Check | Cách verify |
|---|---|---|
| MOD-001 | Chỉ `<Feature>Api.kt` có declaration `public`; mọi class khác `internal` | `grep -rnE '^(public )?(class\|object\|interface\|fun\|data class\|sealed\|enum)' <package>` chỉ được trả về dòng trong `<Feature>Api.kt` (không modifier = public) |
| MOD-002 | `<Feature>Api.kt` không expose `ViewModel`, `Flow<InternalState>`, composable private | Konsist `MOD-002 feature api files do not expose viewmodel` |
| MOD-003 | Mọi string/drawable dùng prefix `feature_<x>_` | `grep -rnE '(R\|Res)\.(string\|drawable)\.' <package>` rồi đối chiếu prefix |

Grep chỉ là quét nhanh (bỏ sót `val`, `typealias`, dòng có annotation); gate thật là `explicitApi()` ở Step 2.

Thêm ARCH-006: feature không import `feature/<other>/*`. Fail bất kỳ dòng nào → sửa trong `presenter` trước (P-01..P-06 của `android-refactor`), commit riêng, chưa tạo module.

### Step 2 — Module layout

Layout mặc định là **1 module**:

```
feature-<x>/
├── build.gradle.kts
└── src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/feature/<x>/
    ├── <Feature>Api.kt          ← public surface DUY NHẤT (MOD-001)
    ├── <Feature>Screen.kt       ← internal
    ├── <Feature>ViewModel.kt    ← internal, extends BaseViewModel (ARCH-007)
    ├── <Feature>Contract.kt     ← internal State/Intent/Effect
    ├── di/<Feature>Module.kt    ← internal Koin module, expose qua Api
    └── components/              ← internal
```

```kotlin
// feature-<x>/build.gradle.kts
kotlin {
    explicitApi()  // compiler bắt mọi declaration public phải khai báo rõ → MOD-001 có gate compile
}
android { namespace = "{{PACKAGE_ROOT}}.feature.<x>" }
dependencies {
    commonMainImplementation(project(":{{MODULE_DOMAIN}}"))      // UseCase + Repository interface
    commonMainImplementation(project(":core-designsystem"))     // nếu đã tách; không thì giữ token trong feature
    commonMainApi(libs.koin.core)                               // `Module` xuất hiện trong chữ ký Api.kt
    // KHÔNG depend {{MODULE_DATA}}: Repository impl do host bind (ARCH-002)
}
```

Quy tắc:
- **Namespace**: `{{PACKAGE_ROOT}}.feature.<x>`, không trùng namespace của host.
- **Resource**: giữ prefix `feature_<x>_*` (MOD-003). Đổi tên resource sau khi publish = breaking change.
- **Dependency**: `implementation`, không `api`, cho mọi module nội bộ. Dùng `api(...)` chỉ khi type của module đó xuất hiện trong chữ ký `<Feature>Api.kt`. Hạn chế trường hợp này: mỗi type lộ ra là thêm một phần contract.
- **DI**: Koin module của feature để `internal`, expose một hàm trong `<Feature>Api.kt`. Host vẫn bind Repository impl từ `{{MODULE_DATA}}` của mình (ARCH-011 vẫn áp dụng bên trong).
- **Module `-api` tách riêng**: không tạo mặc định. MOD-001 hiện quy định "1 file `<Feature>Api.kt`" cho mỗi feature và chưa nói gì về layout 2 module. Nếu một consumer thật sự cần type contract mà không kéo implementation (ví dụ feature khác navigate tới feature này), dừng lại và mở proposal `evolve` để chốt cách áp MOD-001 trước khi tách.

### Step 3 — Public API design (`<Feature>Api.kt`)

Mọi type public (config, result, slot, token, step) nằm trong **một** file `<Feature>Api.kt`. Ba nhóm:

```kotlin
// <Feature>Api.kt — ví dụ feature Checkout
public data class CheckoutConfig(
    public val currencyCode: String,
    public val theme: CheckoutTheme = CheckoutTheme(),
    public val slots: CheckoutSlots = CheckoutSlots(),
    public val flow: CheckoutFlow = CheckoutFlow(),
)

public sealed interface CheckoutResult {
    public data class Completed(public val orderId: String) : CheckoutResult
    public data object Cancelled : CheckoutResult
    public data class Failed(public val reason: CheckoutFailure) : CheckoutResult
}

public enum class CheckoutFailure { PaymentDeclined, Network, Unknown }

/** 1. Init: host thêm vào startKoin { modules(checkoutKoinModule()) }. */
public fun checkoutKoinModule(): Module = checkoutModule  // `checkoutModule` là internal val trong di/

/** 2. Entry: host đặt vào NavHost của mình. */
@Composable
public fun CheckoutRoute(
    config: CheckoutConfig,
    onResult: (CheckoutResult) -> Unit,
) {
    CheckoutScreen(config = config, onResult = onResult)  // internal
}
```

- **Entry point**: một `@Composable` route nhận `config` + `onResult`. Host giữ NavHost và route type-safe của mình (ARCH-009); SDK không tự định nghĩa route toàn cục của host.
- **Init config**: data class immutable, mọi field có default trừ field bắt buộc thật sự.
- **Kết quả**: sealed interface, luôn có nhánh `Cancelled`. Host không cần đọc state nội bộ để biết flow kết thúc thế nào.
- **Cấm expose** (MOD-002): `ViewModel`, `StateFlow<CheckoutState>`, `CheckoutIntent`, Repository, UseCase, composable `internal`/`private`.

### Step 4 — Tuỳ biến UI

Chọn pattern theo thứ tự từ hẹp đến rộng. Mỗi pattern ghi rõ phần nào là public contract.

**U-1. Theme token qua config + `CompositionLocal` internal**

```kotlin
// <Feature>Api.kt — PUBLIC CONTRACT: tên field + kiểu
public data class CheckoutTheme(
    public val accent: Color = Color.Unspecified,    // Unspecified → dùng MaterialTheme của host
    public val summaryCardShape: Shape? = null,
)

// components/CheckoutThemeLocal.kt — INTERNAL: cách token được đọc
internal val LocalCheckoutTheme = staticCompositionLocalOf { CheckoutTheme() }

@Composable
internal fun CheckoutScreen(config: CheckoutConfig, onResult: (CheckoutResult) -> Unit) {
    CompositionLocalProvider(LocalCheckoutTheme provides config.theme) { /* ... */ }
}
```

Mặc định SDK đọc `MaterialTheme` của host, token chỉ dành cho phần riêng của feature. `CompositionLocal` để `internal`: đổi nó không ảnh hưởng host. Thêm field có default = minor; xoá/đổi kiểu field = major.

**U-2. Slot composable cho phần host thay thế**

```kotlin
// <Feature>Api.kt — PUBLIC CONTRACT: chữ ký lambda + data truyền vào slot
public class CheckoutSlots(
    public val header: (@Composable () -> Unit)? = null,
    public val emptyCart: (@Composable (onBrowse: () -> Unit) -> Unit)? = null,
)

// internal
@Composable
private fun CartEmpty(slots: CheckoutSlots, onIntent: (CheckoutIntent) -> Unit) {
    slots.emptyCart?.invoke { onIntent(CheckoutIntent.Browse) } ?: DefaultCartEmpty { onIntent(CheckoutIntent.Browse) }
}
```

Slot nhận data public hoặc callback, **không** nhận `CheckoutState`/`onIntent`. Callback trong slot được SDK map sang Intent nội bộ, nên luồng vẫn một chiều (ARCH-007). Vị trí đặt slot là internal; số tham số và kiểu tham số là contract.

**U-3. Text và hình qua resource prefix**

- Android resources (`res/values/strings.xml`): host khai báo cùng key `feature_<x>_*` trong module app để override, nhờ resource merging. Danh sách key được phép override là public contract, ghi trong KDoc của `<Feature>Api.kt`.
- Compose Multiplatform resources (`composeResources/`) không merge theo tên. Nếu consumer dùng CMP, đưa text cần tuỳ biến vào config:

```kotlin
public data class CheckoutStrings(public val payButton: String? = null)  // null → dùng resource mặc định
```

**Giới hạn chung**: host không đổi được layout ngoài slot đã mở, không truy cập state nội bộ, không thay composable `internal`. Phát sinh nhu cầu ngoài phạm vi này thì thêm slot mới (minor), không mở rộng visibility.

### Step 5 — Tuỳ biến luồng

Host điều khiển *các bước* và *lối ra*. Reducer, State và Intent vẫn nằm trong SDK (ARCH-007 không đổi).

**F-1. Host sở hữu navigation, SDK báo kết quả**

```kotlin
// Host app
composable<NavRoute.Checkout> {
    CheckoutRoute(config = checkoutConfig) { result ->
        when (result) {
            is CheckoutResult.Completed -> nav.navigate(NavRoute.OrderDone(result.orderId)) { popUpTo<NavRoute.Cart> { inclusive = true } }
            CheckoutResult.Cancelled -> nav.popBackStack()
            is CheckoutResult.Failed -> nav.navigate(NavRoute.Support)
        }
    }
}
```

Bên trong SDK, `onResult` chỉ được gọi khi xử lý `Effect` cuối luồng. SDK không gọi `navController` của host.

**F-2. Bật/tắt step**

```kotlin
// PUBLIC CONTRACT: enum step + quy tắc validate
public enum class CheckoutStep { Address, Shipping, Payment, Review }

public data class CheckoutFlow(
    public val steps: List<CheckoutStep> = CheckoutStep.entries,
    public val insertions: Map<CheckoutStep, HostStep> = emptyMap(),
) {
    init {
        require(CheckoutStep.Payment in steps) { "Payment is a required step" }
        require(steps.distinct() == steps) { "Duplicate step" }
    }
}
```

Step bắt buộc được validate ngay trong `init`, nên cấu hình sai fail lúc host khởi tạo config, không phải giữa luồng. Thêm giá trị enum mới = minor, nhưng host dùng `when` exhaustive trên enum sẽ phải sửa: ghi rõ trong CHANGELOG của SDK.

**F-3. Chèn hoặc thay step bằng step của host**

```kotlin
// PUBLIC CONTRACT: HostStep + StepScope
public interface HostStep {
    @Composable
    public fun Content(scope: StepScope)
}

public interface StepScope {
    public fun next()
    public fun back()
    public fun cancel()
}

// INTERNAL: SDK cài StepScope bằng Intent
internal class StepScopeImpl(private val onIntent: (CheckoutIntent) -> Unit) : StepScope {
    override fun next() = onIntent(CheckoutIntent.HostStepDone)
    override fun back() = onIntent(CheckoutIntent.Back)
    override fun cancel() = onIntent(CheckoutIntent.Cancel)
}
```

`insertions[Shipping]` = step của host chạy sau `Shipping`. Thay một step của SDK = bỏ step đó khỏi `steps` + chèn `HostStep` vào vị trí tương ứng. `StepScope` chỉ có 3 lệnh điều hướng: host không đọc hay ghi state SDK. Data host thu được trong step của mình thì host tự giữ; nếu SDK cần data đó, thêm field vào `CheckoutConfig` hoặc một callback có kiểu rõ ràng (minor), không mở `StepScope` ra thành kênh truyền state.

### Step 6 — Versioning và compatibility

- **Semver** cho artifact/module SDK, độc lập với version app:
  - Major: xoá/đổi tên/đổi kiểu bất kỳ thứ gì trong `<Feature>Api.kt`, đổi tên resource key đã công bố, đổi ý nghĩa `CheckoutResult`.
  - Minor: thêm field có default, thêm slot, thêm nhánh step/result (ghi chú ảnh hưởng `when` exhaustive).
  - Patch: fix internal, không đổi API dump.
- **Binary-compat gate** (profile `sdk-library`): dùng Kotlin Binary Compatibility Validator, commit file `.api` dump; CI chạy `apiCheck`, mọi diff API phải đi kèm `apiDump` trong cùng PR và được reviewer đối chiếu với mức semver. Từ Kotlin 2.2, Kotlin Gradle Plugin có ABI validation tích hợp (experimental, task `checkLegacyAbi` / `updateLegacyAbi`); kiểm tra tài liệu Kotlin của version đang dùng trước khi chọn.
- **Deprecation policy**: không xoá API trong 1 bước. `@Deprecated(level = WARNING, replaceWith = ...)` ở minor N, `ERROR` ở minor/major kế tiếp, xoá ở major. Ghi lịch deprecation trong CHANGELOG của SDK.

SDK dùng nội bộ nhiều sản phẩm nên đây là mức khuyến nghị theo profile `sdk-library`; consumer chọn mức cưỡng chế trong CI của mình.

### Step 7 — Verification

Checklist review trước khi mark DONE:

- [ ] Pre-check MOD-001..003 đã pass trong `presenter` (Step 1), commit riêng trước commit tạo module
- [ ] `explicitApi()` bật; build pass không có public declaration ngoài `<Feature>Api.kt`
- [ ] `<Feature>Api.kt` không chứa `ViewModel`, `StateFlow<...State>`, `Intent`, Repository, UseCase
- [ ] Module không depend `{{MODULE_DATA}}`; host vẫn bind Repository impl
- [ ] Mỗi điểm tuỳ biến có KDoc ghi là public contract, có default hoạt động khi host không truyền gì
- [ ] Flow config sai fail ở `init`, có unit test cho từng `require`
- [ ] ViewModel test: host step `next/back/cancel` → state và `CheckoutResult` đúng
- [ ] API dump commit, `apiCheck` pass
- [ ] Behavior cũ của host gốc giữ nguyên (test suite trước/sau giống nhau, theo `workflows/refactor-module.md`)

Konsist: tái dùng test MOD-002 trong template, đổi scope sang module mới.

```kotlin
// verification/.../ArchitectureRulesTest.kt (copy từ TemplateArchitectureRulesTest)
@Test
fun `MOD-002 feature api files do not expose viewmodel`() {
    if (!shouldRun("MOD-002")) return
    Konsist
        .scopeFromModule("feature-<x>")      // trước extract: "{{MODULE_PRESENTER}}"
        .files
        .withNameEndingWith("Api.kt")
        .assertFalse { file ->
            file.text.contains(": ViewModel") ||
                file.text.contains("ViewModel>") ||
                file.text.contains("<out ViewModel")
        }
}
```

Konsist test riêng cho customization contract chưa có trong template; review dùng checklist trên.

## Required policies

- ARCH-006: feature self-contained, không cross-feature import
- ARCH-007: MVI một chiều giữ nguyên trong SDK; slot và `StepScope` đi qua Intent
- ARCH-009: host giữ navigation type-safe
- ARCH-011: Koin binding chuẩn bên trong SDK
- MOD-001..003: MUST khi extract (profile `sdk-library`)

## Decision guides

### Config flag, slot hay host step?

| Nhu cầu host | Chọn |
|---|---|
| Đổi màu/shape của phần riêng feature | U-1 theme token |
| Thay một khối UI (header, empty state) | U-2 slot |
| Đổi text | U-3 resource key (Android) hoặc `Strings` config (CMP) |
| Bỏ một bước | F-2 `steps` |
| Thêm/thay một bước có UI riêng | F-3 `HostStep` |
| Bật/tắt một hành vi đơn (ví dụ hiện coupon) | Boolean trong config, nếu không đổi layout |

### Extract hay chưa?

- **Extract** khi consumer thứ 2 đã có lịch tích hợp và Step 1 pass.
- **Chưa** khi chỉ dự đoán sẽ dùng lại: giữ trong `presenter`, tuân MOD-001..003 ở mức SHOULD.

## Common mistakes

| Mistake | Fix |
|---|---|
| Tạo module trước khi pass MOD-001..003 | Làm Step 1 trong `presenter`, commit riêng |
| Public type nằm rải rác nhiều file | Gom vào `<Feature>Api.kt`, phần còn lại `internal` |
| Slot nhận `CheckoutState` | Truyền data public hoặc callback |
| `api(project(":core-designsystem"))` cho tiện | `implementation`, trừ khi type của nó nằm trong chữ ký public |
| Đổi resource key `feature_<x>_*` như refactor thường | Breaking change: bump major, ghi CHANGELOG |
| Quên nhánh `Cancelled` | Mọi luồng có lối thoát host xử lý được |

## Output contract

- Module `:feature-<x>` build pass với `explicitApi()`
- `<Feature>Api.kt` là public surface duy nhất, có KDoc cho từng điểm tuỳ biến
- API dump commit + `apiCheck` pass
- Test: ViewModel (step + result), validate config, MOD-002 Konsist trên module mới
- Host gốc chạy giống trước extract
- Report theo `workflows/refactor-module.md §Stage 5`, kèm bảng điểm tuỳ biến (pattern, public contract, default)

## Anti-patterns bị cấm

- Expose `ViewModel`, `StateFlow<State>` hoặc `Intent` ra host (MOD-002)
- Host gọi thẳng Repository/UseCase của SDK để "đọc tạm" state
- SDK giữ `NavController` của host hoặc tự navigate ra ngoài feature
- Thêm hàng chục Boolean flag thay cho slot (`showHeader`, `headerStyle2`, ...)
- `StepScope` có `setState`/`sendIntent` cho host
- Copy feature sang repo sản phẩm thứ 2 rồi sửa (fork) thay vì mở điểm tuỳ biến
- Module SDK depend `{{MODULE_DATA}}` hoặc app module của một sản phẩm cụ thể
