# Mobile Engineering Harness (Upstream)

Harness chung cho các sản phẩm Android / Compose Multiplatform theo concept **Clean Architecture + SOLID + MVI + Compose + Coroutines**.

Upstream generic; mỗi sản phẩm consume qua `.harness-overlay/` riêng, parameterize bằng `overlay.yaml`.

## Install (one-liner)

```bash
curl -fsSL https://raw.githubusercontent.com/huypqapero/mobile-engineering-harness/main/bootstrap.sh | bash
```

Script tự clone upstream vào `~/.mobile-engineering-harness/` và symlink CLI thành `mehcli` ở `~/.local/bin/`.

Sau khi install (lần đầu add `~/.local/bin` vào PATH nếu chưa có):

```bash
mehcli help
mehcli init --project /path/to/your/android-project
mehcli install --overlay /path/to/your/android-project/.harness-overlay
mehcli self-update                      # pull latest từ GitHub
```

**One-liner install + chạy luôn**:

```bash
curl -fsSL https://raw.githubusercontent.com/huypqapero/mobile-engineering-harness/main/bootstrap.sh | bash -s init --project .
```

### Env vars cho bootstrap (optional)

| Var | Default |
|---|---|
| `MEH_INSTALL_DIR` | `$HOME/.mobile-engineering-harness` |
| `MEH_BIN_DIR` | `$HOME/.local/bin` |
| `MEH_REF` | `main` (hoặc specify tag như `v0.3.0`) |

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

## CLI usage

Sau khi install, `mehcli` có 6 subcommands + flags chung (`--dry-run`, `--yes`):

```bash
mehcli init         --project <path>              # scaffold overlay + schema template
mehcli install      --overlay <path>              # render templates + write manifest
mehcli update       --overlay <path>              # idempotent re-render (alias install)
mehcli uninstall    --overlay <path> [--purge]    # remove rendered; --purge xóa toàn bộ overlay
mehcli self-update                                # git pull upstream
mehcli version                                    # show installed version
mehcli help
```

Nếu không install qua `bootstrap.sh`, dùng path đầy đủ `./install.sh <subcommand>` cũng ok.

### Quick start cho product mới (3 lệnh)

```bash
# 1. Scaffold overlay (tự tạo symlink upstream)
/path/to/mobile-engineering-harness/install.sh init --project /path/to/your/android-project

# 2. Edit .harness-overlay/overlay.yaml — fill product vars (xem overlay.schema.yaml)

# 3. Render templates + create manifest
/path/to/mobile-engineering-harness/install.sh install --overlay /path/to/your/android-project/.harness-overlay
```

Setup time ~15 phút gồm điền `overlay.yaml`.

### Chi tiết subcommand

**`init`** — scaffold overlay structure:
- Tạo `.harness-overlay/` trong project
- Copy `overlay.schema.yaml` → `.harness-overlay/overlay.yaml`
- Symlink `.harness-overlay/upstream` → upstream repo
- KHÔNG render; đợi user điền overlay.yaml xong

**`install`** — render templates:
- Đọc `overlay.yaml`, validate required fields
- Render 4 files: `verification/architecture-tests/ArchitectureRulesTest.kt`, `verification/scripts/verify.sh`, `harness.yaml`, `README.md`
- Ghi `.manifest.yaml` track rendered files + upstream commit
- Idempotent — chạy lại OK (re-render)

**`update`** — alias của `install`. Dùng khi upstream pull version mới hoặc `overlay.yaml` thay đổi.

**`uninstall`** — remove rendered artifacts:
- Default: xóa 4 rendered files + `.manifest.yaml`; **preserve** `overlay.yaml`, `constitution/`, `blueprints/`, `upstream` symlink
- `--purge`: xóa toàn bộ `.harness-overlay/` (require 2x confirm)
- Konsist test đã copy sang `<module>/src/jvmTest/...` phải xóa thủ công (ngoài scope)

### Flags chung

| Flag | Hiệu lực |
|---|---|
| `--dry-run` | Print actions, không execute |
| `--yes`, `-y` | Skip confirmation (cho CI) |

### Submodule thay vì symlink (cho CI)

Nếu product cần CI friendly, thay symlink bằng submodule sau khi `init`:

```bash
cd /path/to/your/android-project/.harness-overlay
rm upstream
cd ..
git submodule add https://github.com/huypqapero/mobile-engineering-harness.git .harness-overlay/upstream
```

### Legacy manual flow (không khuyến nghị)

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
