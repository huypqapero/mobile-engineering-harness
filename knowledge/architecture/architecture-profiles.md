# Architecture Profiles

Harness support 3 architecture profiles qua `architecture.profile` trong `overlay.yaml`. Mỗi profile tune rule applicability + stack assumptions phù hợp target.

Chọn 1 profile khi init product; thay đổi sau cần migration + rerun `mehcli install`.

## Comparison

| Dimension | `cmp` | `kmp` | `android-only` |
|---|---|---|---|
| **Target platforms** | Android + iOS (shared UI) | Android + iOS (native UI) | Android only |
| **UI framework** | Compose Multiplatform | Compose (Android) + SwiftUI (iOS) | Jetpack Compose |
| **Share scope** | UI + logic + data | Logic + data | — (single platform) |
| **Module split** | 4-module (composeApp/presenter/domain/data) | 3-module (composeApp/presenter/shared) hoặc 4-module | 2 → 4-module tùy scale |
| **expect/actual** | Nhiều (UI + data + platform SDK) | Trung bình (data + platform SDK) | Không |
| **ARCH-010 (platform SDK boundary)** | **MUST enforce** | **MUST enforce** | **SKIP** (relaxed) |
| **MVI pattern** | `BaseViewModel<S, I, E>` common | `BaseViewModel` common hoặc platform-specific | `BaseViewModel` Android |
| **Testing** | Common test + Android test | Common test + platform test | Android test chủ yếu |
| **Build time** | Chậm hơn (multiplatform compile) | Trung bình | Nhanh nhất |

## Profile: `cmp` (Compose Multiplatform)

### Use case

Product muốn **share UI code** giữa Android + iOS (+ desktop/web optional). Design system common. Compose Multiplatform.

### Rules áp dụng

Tất cả 14 ARCH + 10 CORO + 12 KOT rules. Đặc biệt:
- ARCH-010 platform SDK chỉ ở `data/{androidMain,iosMain}/` qua `expect/actual`
- Theme + UI common trong `presenter/src/commonMain/`
- MOD-001..003 (Future-SDK Discipline) applicable

### Module layout

```
composeApp/src/{androidMain,iosMain}/kotlin   # Entry per platform
presenter/src/commonMain/kotlin                # UI + MVI + Nav shared
domain/src/commonMain/kotlin                   # Business logic
data/src/{commonMain,androidMain,iosMain}/     # Repo impl + platform SDK
```

### Example overlay.yaml

```yaml
architecture:
  profile: cmp
targets: [android, ios]
stack:
  ui: compose-multiplatform
  network: ktor
  database: sqldelight
platform_sdks:
  - androidx.media3
  - platform.AVFoundation
  - com.google.firebase
```

### Trade-offs

- **Pro**: 70-80% code share. 1 design system. Shared bug fixes.
- **Con**: Build chậm. iOS Compose runtime maturity thấp hơn SwiftUI. Platform-specific UI tweaks phải expect/actual.

## Profile: `kmp` (Kotlin Multiplatform — shared logic only)

### Use case

Product giữ **native UI** (SwiftUI iOS + Compose Android) nhưng share **business + data layer**. Prefer native UX, không trade-off UI maturity.

### Rules áp dụng

Core ARCH + CORO + KOT rules. Khác với `cmp`:
- UI layer **không share**; `presenter` chỉ exist ở Android target
- iOS có presenter riêng (Swift) không managed bởi harness
- ARCH-010 vẫn enforce (data + platform SDK boundary)

### Module layout

```
androidApp/                                    # Android app module
iosApp/                                        # Xcode project (bỏ ngoài harness scope)
shared/
├── src/commonMain/kotlin/                     # Shared domain + data
│   ├── domain/
│   ├── data/
│   └── presenter/                             # ViewModel + State shared (optional)
└── src/{androidMain,iosMain}/                 # Platform-specific impl
```

Hoặc 4-module shared:
```
androidApp/
shared-presenter/src/commonMain/              # ViewModel + Flow (shared logic)
shared-domain/src/commonMain/                 # Pure Kotlin
shared-data/src/commonMain/                   # DTO + Repo
```

### Example overlay.yaml

```yaml
architecture:
  profile: kmp
targets: [android, ios]
stack:
  ui: compose-android              # UI chỉ Android trong harness
  network: ktor                    # hoặc ktorfit
  database: sqldelight             # hoặc room 2.7+
modules:
  app: androidApp
  presenter: shared-presenter
  domain: shared-domain
  data: shared-data
```

### Trade-offs

- **Pro**: Native UX full. iOS team dùng Swift như bình thường. Logic test 1 lần apply cả 2 platform.
- **Con**: UI 2 lần (Android Compose + iOS SwiftUI). Design system khó enforce consistent cross-platform.

## Profile: `android-only` (Jetpack Compose Android)

### Use case

Product **chỉ Android**, không plan iOS/multiplatform tương lai. Jetpack Compose + Android ecosystem thuần. Simpler build.

### Rules áp dụng

Core ARCH + CORO + KOT rules. Khác với `cmp`/`kmp`:
- **ARCH-010 SKIP**: platform SDK boundary relaxed (không có concept iOS)
- Không `expect/actual`
- `platform_sdks` list dùng cho organize code, không enforce boundary cross-platform
- Có thể 2-module (`:app` + `:core`) hoặc 4-module đầy đủ

### Module layout (4-module khuyến nghị cho scale)

```
app/src/main/kotlin/           # Entry Activity + DI init
presenter/src/main/kotlin/     # UI + MVI + Nav (Compose Android)
domain/src/main/kotlin/        # Pure Kotlin
data/src/main/kotlin/          # Repo impl + Retrofit + Room
```

Hoặc 2-module (small project):
```
app/src/main/kotlin/           # UI + ViewModel
core/src/main/kotlin/          # Business + data
```

### Example overlay.yaml

```yaml
architecture:
  profile: android-only
targets: [android]
stack:
  ui: compose-android
  network: retrofit               # hoặc ktor nếu familiar
  database: room                  # hoặc sqldelight
platform_sdks:                    # Advisory list, không enforce boundary
  - androidx.media3
  - com.google.firebase
```

### Trade-offs

- **Pro**: Build nhanh nhất. Jetpack ecosystem full (WorkManager, Paging3, Hilt tốt). Lint rules Android native tốt.
- **Con**: Scale ra iOS cost cao (phải refactor lại). Logic test chỉ apply 1 platform.

## Migration giữa profiles

### `android-only` → `cmp`

**Scope lớn**: thêm KMP source sets, expect/actual cho platform SDK, config iOS target.

Steps:
1. Add Kotlin Multiplatform plugin
2. Chuyển code `src/main/kotlin/` → `src/commonMain/kotlin/` (remove Android deps)
3. Platform-specific code → `src/{androidMain,iosMain}/`
4. Thay Retrofit → Ktor, Room → SQLDelight (hoặc Room 2.7+ KMP)
5. Update `overlay.yaml` → `architecture.profile: cmp`
6. Rerun `mehcli install`

### `kmp` → `cmp`

**Scope trung bình**: thêm shared UI layer.

Steps:
1. Move Android Compose UI → `presenter/src/commonMain/`
2. Rewrite iOS SwiftUI UI → Compose MP
3. Common design tokens
4. Update `overlay.yaml` → `architecture.profile: cmp`

### `cmp` → `kmp` (reverse)

**Rare**: khi iOS Compose runtime không meet UX bar, team quyết native SwiftUI.

Steps:
1. iOS: build SwiftUI UI consume ViewModel qua kotlin-interop
2. Keep shared `domain` + `data` + `presenter` logic
3. Remove iOS Compose target
4. Update `overlay.yaml` → `architecture.profile: kmp`

## Profile-aware agent behavior

Khi AI agent read `overlay.yaml`:
1. Resolve `architecture.profile` trước mọi task
2. Load skill/knowledge section tương ứng profile
3. Konsist test render theo profile (via `install.sh`) — rule skip automatic nếu không applicable
4. Blueprint variant: `cmp` → `reference-feature` default; `android-only` → `blueprints/compose-screen` lite hơn

## Common mistakes

| Mistake | Fix |
|---|---|
| Pick `cmp` nhưng project chưa plan iOS → over-engineering | Start `android-only`, migrate khi thực sự plan iOS |
| Pick `android-only` cho project có 70% logic muốn share | Chọn `kmp` ngay từ đầu |
| Mix `android-only` + `platform_sdks` cho iOS → không hợp lý | Chỉ list Android platform SDK |
| Rename module nhưng không update `overlay.yaml` modules field | Update `modules.*` match thực tế |
| Profile `cmp` nhưng chọn `stack.network: retrofit` → không fit | Chọn `ktor` hoặc `ktorfit` (KMP) |

## References

- Compose Multiplatform: https://www.jetbrains.com/lp/compose-multiplatform/
- Kotlin Multiplatform guide: https://kotlinlang.org/docs/multiplatform.html
- Jetpack Compose: https://developer.android.com/jetpack/compose
- `.harness/overlay.schema.yaml` — field reference
- `.harness/constitution/architecture-rules.md` — rule list
