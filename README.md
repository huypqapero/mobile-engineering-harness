# Android Engineering Harness (Upstream)

Harness chung cho các sản phẩm Android/Compose Multiplatform theo concept **Clean Architecture + SOLID + MVI + Compose + Coroutines**.

Harness này là **upstream generic**. Mỗi sản phẩm consume qua `.harness-overlay/` của riêng nó, parameterize bằng `overlay.yaml`.

## Mục tiêu

- 1 source of truth cho rule + skill + workflow + verification
- Mỗi sản phẩm chỉ cần overlay vài file khai báo (package, module names, theme, SDK dùng)
- Rule update ở upstream → tất cả sản phẩm nhận được qua rerender
- Blueprint có 2 tầng: generic demo (upstream) + live reference (overlay)

## Phạm vi áp dụng

| Loại sản phẩm | Fit |
|---|---|
| Compose Multiplatform (Android + iOS) | ✓ chính |
| Android-only Jetpack Compose | ✓ (bỏ platform SDK iOS section) |
| Android XML/MVVM legacy | ⚠ MVI rule phần lớn apply, Compose rule skip |
| Kotlin Multiplatform (shared logic + native UI) | ✓ (customize profile) |

## Structure

```
mobile-engineering-harness/
├── README.md                        ← bạn đang đọc
├── AGENTS.md                        ← entry point generic (có {{VARS}})
├── CLAUDE.md                        ← short entry
├── harness.yaml.template            ← config template
├── install.sh                       ← render templates vào overlay
├── overlay.schema.yaml              ← schema cho overlay.yaml
│
├── constitution/                    ← luật universal
├── knowledge/                       ← kiến thức nền
├── skills/                          ← procedures
├── blueprints/
│   └── reference-feature/           ← generic ItemCatalog demo
├── workflows/
├── verification/
│   ├── architecture-tests/
│   │   └── TemplateArchitectureRulesTest.kt   với {{PLACEHOLDERS}}
│   └── scripts/
│       └── verify.sh.template
└── evaluations/
    └── templates/                   ← scenario templates per-product
```

## Cài đặt cho sản phẩm mới

### Bước 1 — Tạo overlay folder trong project

```bash
cd /path/to/your/android-project
mkdir -p .harness-overlay
```

### Bước 2 — Tạo `overlay.yaml`

Copy template từ `overlay.schema.yaml` và điền giá trị:

```yaml
product:
  name: YourProduct
  package: com.yourcompany.product
  app_display_name: Your Product

modules:
  app: composeApp         # tên module entry
  presenter: presenter
  domain: domain
  data: data

ui:
  theme_prefix: YourProduct
  theme_class: YourProductTheme

stack:
  ui: compose-multiplatform
  mvi: BaseViewModel
  di: koin
  network: ktor
  database: sqldelight

features_root: feature

platform_sdks:
  - androidx.media3
  - platform.AVFoundation
  - com.google.firebase

reference_blueprint:
  feature_name: ""        # trỏ feature live khi có; để trống dùng generic demo
  path: ""
```

### Bước 3 — Symlink hoặc clone upstream

```bash
# Option A (dev local, nhanh):
ln -s /Users/kohuyn/StudioProjects/mobile-engineering-harness .harness-overlay/upstream

# Option B (CI friendly):
git submodule add https://... .harness-overlay/upstream
```

### Bước 4 — Chạy install

```bash
/Users/kohuyn/StudioProjects/mobile-engineering-harness/install.sh \
  --overlay .harness-overlay
```

Install sẽ:
- Validate `overlay.yaml` theo schema
- Render `verification/architecture-tests/ArchitectureRulesTest.kt` từ template với vars
- Render `verification/scripts/verify.sh` từ template
- Render `harness.yaml` từ template
- Tạo `.harness-overlay/README.md` tham chiếu upstream

### Bước 5 — Add Konsist dependency

Trong `gradle/libs.versions.toml`:

```toml
[versions]
konsist = "0.17.3"

[libraries]
konsist = { module = "com.lemonappdev:konsist", version.ref = "konsist" }
```

Copy rendered Konsist test vào `<module>/src/jvmTest/kotlin/<package>/harness/`.

### Bước 6 — Verify

```bash
./.harness-overlay/upstream/verification/scripts/verify.sh  # hoặc rendered copy
```

## Agent resolution order

Khi AI agent nhận task trong project có overlay:

1. Đọc project `CLAUDE.md` (nếu có) — rule project-specific cao nhất
2. Đọc `.harness-overlay/overlay.yaml` — vars
3. Đọc `.harness-overlay/upstream/AGENTS.md` — generic entry, substitute vars
4. Load skill từ `upstream/skills/<name>/SKILL.md`
5. Load constitution/knowledge khi cần
6. Overlay-specific additions ở `.harness-overlay/constitution/`, `.harness-overlay/blueprints/` override hoặc extend upstream

Rule precedence (cao → thấp):
1. Project `CLAUDE.md`
2. Overlay constitution (product extensions)
3. Upstream constitution

## Governance

- **Upstream owner** sửa generic rule, bump version theo semver
- **Product overlay** chỉ add delta, không fork upstream rule
- **Promote overlay → upstream** khi 2+ product độc lập có cùng rule
- Breaking rule change: `harness_version` constraint trong `overlay.yaml`

## Version

Current: `0.1.0` (initial extraction từ AudioBookApp .harness v1.0)

Changelog: xem `CHANGELOG.md` (sẽ tạo khi có rule change đầu tiên).

## Phase 2 — SDK extraction mode

Khi feature extract thành library module:
- Promote `MOD-001..003` severity SHOULD → MUST
- Thêm skill `android-sdk-development`
- Thêm verification `binary-compat/`
- Overlay specify `profile: sdk-library`
