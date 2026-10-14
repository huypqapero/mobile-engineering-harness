# Android Engineering Harness — Entry Point

Harness định hướng AI coding agent (Claude Code, Codex, CLI agents) phát triển sản phẩm **{{PRODUCT_NAME}}** theo chuẩn Clean Architecture + SOLID + MVI + Compose Multiplatform + Coroutines.

Context project (resolve từ `overlay.yaml`):
- Package root: `{{PACKAGE_ROOT}}`
- Modules: `{{MODULE_APP}} → {{MODULE_PRESENTER}} → {{MODULE_DOMAIN}} ← {{MODULE_DATA}}`
- MVI base: `{{MVI_BASE_CLASS}}<S, I, E>`
- Theme: `{{THEME_CLASS}}`
- DI: {{DI_FRAMEWORK}}
- Stack: {{UI_FRAMEWORK}} + {{NETWORK_FRAMEWORK}} + {{DATABASE_FRAMEWORK}}

## Thứ tự đọc khi nhận task

1. **Project root** `CLAUDE.md` — rule project-specific (cao nhất)
2. **Overlay** `.harness-overlay/constitution/` — product extensions
3. **Upstream** `AGENTS.md` (file này) — generic entry + task routing
4. **Upstream** `skills/<skill-tương-ứng>/SKILL.md` — procedure cụ thể
5. **Upstream** `knowledge/` — load khi task yêu cầu
6. **Blueprint**: ưu tiên `overlay/blueprints/live-reference-feature.md` (nếu có); fallback `upstream/blueprints/reference-feature/README.md`

## Task routing

| Task | Skill chính |
|---|---|
| Tạo feature mới end-to-end | `android-feature` |
| Build/sửa Compose UI | `android-compose` |
| Thiết kế UiState/Intent/Effect, reducer, side-effect | `android-mvi` |
| Review PR, diff, module | `android-code-review` |
| Viết unit/UI/integration test | `android-testing` |

Nhiều task cross-cutting → gọi lần lượt, không chạy song song cùng file.

## Workflow mặc định

`workflows/feature-development.md` điều phối: inspect → plan → implement → verify → report. Mỗi stage có completion criteria rõ.

## Quality gates bắt buộc

Trước khi báo cáo DONE, chạy đủ:

1. `./gradlew :{{MODULE_DOMAIN}}:test :{{MODULE_PRESENTER}}:test :{{MODULE_DATA}}:test`
2. `./gradlew konsistTest` — architecture rules
3. `./gradlew detekt`
4. Build smoke: `./gradlew :{{MODULE_APP}}:assembleDebug`

Fail bất kỳ gate nào → không được tuyên bố DONE. Xem `constitution/definition-of-done.md`.

## Overlay vs upstream — precedence

Nếu cùng rule ID xuất hiện ở `overlay/constitution/` và `upstream/constitution/`:
- Overlay thắng
- Overlay chỉ nên override khi có lý do product-specific rõ

Nếu rule chỉ ở overlay → product-specific rule, không propagate upstream.

## File index

- `harness.yaml.template` + `overlay.schema.yaml` — config
- `constitution/engineering-principles.md`
- `constitution/architecture-rules.md` — ARCH-001..014 + MOD-001..003
- `constitution/concurrency-rules.md` — CORO-001..010
- `constitution/definition-of-done.md`
- `knowledge/architecture/clean-mvi.md`
- `knowledge/compose/essentials.md`
- `knowledge/mvi/essentials.md`
- `knowledge/coroutines/essentials.md`
- `skills/*/SKILL.md` — 5 skills
- `blueprints/reference-feature/README.md` — generic demo
- `workflows/feature-development.md`
- `verification/architecture-tests/TemplateArchitectureRulesTest.kt` — Konsist, cần render
- `verification/scripts/verify.sh.template` — gate runner, cần render
- `evaluations/templates/` — scenario templates

## Report format

Mọi task kết thúc bằng report theo mẫu `constitution/definition-of-done.md §Report`:

```
Status: VERIFIED | VERIFIED_WITH_LIMITATIONS | BLOCKED | FAILED
Summary: 1-2 câu
Files changed: list
Rules compliance: PASS/FAIL per rule
Verification: compile/konsist/detekt/tests
Open questions: optional
```

Không tuyên bố DONE khi check thất bại hoặc không chạy được. Document limitation thay vì ẩn.

## Placeholder reference

Khi đọc file upstream, các placeholder dưới đây sẽ được resolve từ overlay.yaml:

| Placeholder | Nguồn | Ví dụ |
|---|---|---|
| `{{PRODUCT_NAME}}` | `product.name` | AudioBookApp |
| `{{PACKAGE_ROOT}}` | `product.package` | com.audiobook |
| `{{PACKAGE_ROOT_PATH}}` | derive từ package | com/audiobook |
| `{{MODULE_APP}}` | `modules.app` | composeApp |
| `{{MODULE_PRESENTER}}` | `modules.presenter` | presenter |
| `{{MODULE_DOMAIN}}` | `modules.domain` | domain |
| `{{MODULE_DATA}}` | `modules.data` | data |
| `{{THEME_CLASS}}` | `ui.theme_class` | AudiobookTheme |
| `{{THEME_PREFIX}}` | `ui.theme_prefix` | Audiobook |
| `{{MVI_BASE_CLASS}}` | derive hoặc `stack.mvi` | BaseViewModel |
| `{{DI_FRAMEWORK}}` | `stack.di` | koin |
| `{{UI_FRAMEWORK}}` | `stack.ui` | compose-multiplatform |
| `{{NETWORK_FRAMEWORK}}` | `stack.network` | ktor |
| `{{DATABASE_FRAMEWORK}}` | `stack.database` | sqldelight |
| `{{FEATURES_ROOT}}` | `features_root` | feature |

Agent gặp placeholder không resolve được → ghi BLOCKED, hỏi user bổ sung `overlay.yaml`.
