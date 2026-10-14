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
| Async / Flow / cancellation / concurrency | `android-coroutines` |
| API integration, Ktor service, DTO + mapper | `android-network` |
| Local DB SQLDelight, schema, migration, offline-first | `android-database` |
| Refactor module preserve-behavior | `android-refactor` |
| Debug crash / ANR / memory leak / flaky | `android-debug` |
| Performance profile + optimize startup/UI/memory/network | `android-performance` |
| Review PR, diff, module | `android-code-review` |
| Viết unit/UI/integration test | `android-testing` |
| Orchestrate multi-agent / parallel feature build | `android-orchestrator` |

Nhiều task cross-cutting → gọi lần lượt, không chạy song song cùng file.

## Workflows

| Workflow | Khi nào |
|---|---|
| `workflows/feature-development.md` | Implement feature mới end-to-end (5 stages: inspect → plan → implement → verify → report) |
| `workflows/fix-bug.md` | Debug + fix bug (reproduce → isolate → cause → fix → verify) |
| `workflows/review-pull-request.md` | Review PR / diff theo 10 dimensions với evidence-based findings |
| `workflows/refactor-module.md` | Preserve behavior refactor (baseline → plan → refactor → compare → verify) |
| `workflows/release-validation.md` | Release candidate validation (preflight → build → smoke → artifact → regression → sign-off) |
| `workflows/parallel-feature-development.md` | Build N feature độc lập song song từ spec (decompose → isolation → spawn → aggregate → review → verify) |

## Agent roles

Trong workflow, agent có thể chuyển mindset qua các role (xem `agents/*.md`):

- `architect.md` — Plan + inspect + decisions + spec decomposition (parallel mode)
- `implementer.md` — Execute theo plan, minimal scope
- `reviewer.md` — Independent audit, evidence-based findings
- `test-engineer.md` — Behavior coverage, deterministic test
- `orchestrator.md` — Coordinate multi-agent spawn + aggregate (team/parallel-features mode)

Giai đoạn solo (1 agent): 1 agent chuyển mindset qua các role. Giai đoạn multi-agent: subagent dedicated per role.

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
- `constitution/kotlin-conventions.md` — KOT-001..012
- `constitution/definition-of-done.md`
- `knowledge/agent-orchestration/essentials.md` — orchestration modes + Claude Code Task tool patterns
- `knowledge/architecture/architecture-profiles.md` — profile cmp/kmp/android-only + migration
- `knowledge/architecture/clean-mvi.md`
- `knowledge/compose/essentials.md`
- `knowledge/mvi/essentials.md`
- `knowledge/coroutines/essentials.md`
- `knowledge/data/repository-pattern.md`
- `knowledge/data/network.md`
- `knowledge/data/persistence.md`
- `knowledge/data/caching.md`
- `knowledge/patterns/common-patterns.md`
- `knowledge/security/essentials.md`
- `knowledge/performance/essentials.md`
- `skills/android-feature/SKILL.md`
- `skills/android-compose/SKILL.md`
- `skills/android-mvi/SKILL.md`
- `skills/android-coroutines/SKILL.md`
- `skills/android-network/SKILL.md`
- `skills/android-database/SKILL.md`
- `skills/android-refactor/SKILL.md`
- `skills/android-debug/SKILL.md`
- `skills/android-performance/SKILL.md`
- `skills/android-code-review/SKILL.md`
- `skills/android-testing/SKILL.md`
- `skills/android-orchestrator/SKILL.md`
- `blueprints/reference-feature/README.md`
- `blueprints/network-service/README.md`
- `blueprints/compose-screen/README.md`
- `blueprints/repository/README.md`
- `blueprints/usecase/README.md`
- `workflows/feature-development.md`
- `workflows/fix-bug.md`
- `workflows/review-pull-request.md`
- `workflows/refactor-module.md`
- `workflows/release-validation.md`
- `workflows/parallel-feature-development.md`
- `agents/architect.md`
- `agents/implementer.md`
- `agents/reviewer.md`
- `agents/test-engineer.md`
- `agents/orchestrator.md`
- `verification/architecture-tests/TemplateArchitectureRulesTest.kt`
- `verification/scripts/verify.sh.template`
- `verification/detekt/README.md` + `detekt-config-template.yml`
- `verification/lint/README.md`
- `evaluations/templates/e01..e05.md`
- `evaluations/rubrics/README.md` — scoring rubric chung
- `evaluations/regression/README.md` — trend tracking qua versions

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
| `{{PRODUCT_NAME}}` | `product.name` | YourProduct |
| `{{PACKAGE_ROOT}}` | `product.package` | com.example.product |
| `{{PACKAGE_ROOT_PATH}}` | derive từ package | com/example/product |
| `{{MODULE_APP}}` | `modules.app` | composeApp |
| `{{MODULE_PRESENTER}}` | `modules.presenter` | presenter |
| `{{MODULE_DOMAIN}}` | `modules.domain` | domain |
| `{{MODULE_DATA}}` | `modules.data` | data |
| `{{THEME_CLASS}}` | `ui.theme_class` | AppTheme |
| `{{THEME_PREFIX}}` | `ui.theme_prefix` | App |
| `{{MVI_BASE_CLASS}}` | derive hoặc `stack.mvi` | BaseViewModel |
| `{{DI_FRAMEWORK}}` | `stack.di` | koin |
| `{{UI_FRAMEWORK}}` | `stack.ui` | compose-multiplatform |
| `{{NETWORK_FRAMEWORK}}` | `stack.network` | ktor |
| `{{DATABASE_FRAMEWORK}}` | `stack.database` | sqldelight |
| `{{FEATURES_ROOT}}` | `features_root` | feature |

Agent gặp placeholder không resolve được → ghi BLOCKED, hỏi user bổ sung `overlay.yaml`.
