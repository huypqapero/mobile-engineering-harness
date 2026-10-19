# Overlay schema mapping — detection rules + decision guide

Reference này mô tả cách `detect-stack.sh` suy ra 8 overlay key từ gradle metadata, và cách xử lý ambiguous cases.

## Detection matrix

| Overlay key | Marker trong `libs.versions.toml` / `build.gradle(.kts)` | Fallback |
|---|---|---|
| `stack.ui` | `org.jetbrains.compose` → compose-multiplatform; `androidx.compose` → compose-android; `com.android.application` only → xml-android | compose-android |
| `stack.di` | `dagger.hilt` → hilt; `insert-koin` → koin | manual |
| `stack.network` | `ktorfit` plugin → ktorfit; `retrofit2` → retrofit; `ktor-client` → ktor | ktor |
| `stack.database` | `app.cash.sqldelight` plugin → sqldelight; `androidx.room` → room; `androidx.datastore` → datastore | none |
| `stack.mvi` | Không auto-detect, default = `BaseViewModel`; user override khi project có class base khác | BaseViewModel |
| `product.package` | `namespace =` trong `build.gradle.kts` top-level; `package="..."` trong `AndroidManifest.xml` | `com.example.app` |
| `modules.app` | First module trong `settings.gradle.kts include(...)` | `composeApp` |
| `modules.presenter/domain/data` | Luôn hardcode default; nếu project đặt tên khác (vd `features`, `core-data`) user phải sửa overlay thủ công sau |

## Branding keys (không auto-detect)

Interactive via `AskUserQuestion`:

| Key | Hướng dẫn |
|---|---|
| `product.name` (PRODUCT_NAME) | CamelCase, 2-20 ký tự, không space. Ví dụ: `Acme`, `NovaWallet`. Default suggestion: inflect từ repo folder name. |
| `ui.theme_prefix` | Thường trùng `product.name`. Dùng cho generated class name (`<prefix>Colors`, `<prefix>Typography`). |
| `ui.theme_class` | Default `<theme_prefix>Theme`. Dùng cho composable wrapper. |

## Multi-module layout

Nếu `settings.gradle.kts` include nhiều hơn 4 module (vd có `core`, `shared`, `feature-login`, `feature-home`...), skill chỉ map 4 role chính (`app`, `presenter`, `domain`, `data`). Các module khác không vào overlay.

Nếu project **không** có module tên `presenter/domain/data` (vd dùng `app/feature/common/network`), skill cảnh báo:

```
WARN: project modules [app, feature, common, network] không khớp Clean Arch 4-layer.
Nếu project theo convention khác, overlay default sẽ không reflect đúng. Pick:
  1. Giữ overlay default (presenter/domain/data) + sửa thủ công sau
  2. Abort + reconfigure project theo Clean Arch 4-layer
```

## DI framework decision

Khi detect ambiguous (vd project có cả Hilt annotation + Koin dependencies — rare):

```
WARN: Phát hiện cả hilt + koin markers. Chọn primary:
  1. hilt — nếu Android-only và prefer compile-time DI
  2. koin — nếu KMP và prefer runtime DI
```

## Network framework decision

| Project profile | Suggested |
|---|---|
| KMP share code iOS/desktop | ktor |
| KMP + type-safe interface style | ktorfit |
| Android-only, mature OkHttp ecosystem | retrofit |

## Database framework decision

| Project profile | Suggested |
|---|---|
| KMP + relational | sqldelight |
| Android-only + annotation-based | room |
| Key-value only, no relational | datastore |
| In-memory / filesystem | none |

## Overlay version compat

`harness_version: ">=0.1.0"` → semver range cho upstream. Skill set default `>=0.1.0`; user có thể lock khi upgrade.

## Idempotency

Nếu `.harness-overlay/overlay.yaml` đã tồn tại:

- Compare existing với newly-generated → nếu không khác, no-op.
- Nếu khác, hỏi user: `overwrite / merge / abort`.
- Merge: ưu tiên user-filled fields (không null, không enum default), chỉ fill fields trống hoặc default.

## Validation failures — recovery guide

| Error | Recovery |
|---|---|
| `product.name empty` | Hỏi user, re-render |
| `stack.ui=xml-android + targets contains ios` | Hỏi user: đổi targets hoặc đổi ui_framework |
| `modules.presenter empty` | Project không có presenter module; đổi tên hoặc skip overlay cho layer này |
| Enum mismatch | In allowed values, hỏi user chọn 1 |
