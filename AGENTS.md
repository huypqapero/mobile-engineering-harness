# Android Engineering Harness — Entry Point

Harness định hướng AI coding agent (Claude Code, Codex, CLI agents) phát triển sản phẩm **{{PRODUCT_NAME}}** theo chuẩn Clean Architecture + SOLID + MVI + Compose Multiplatform + Coroutines.

Context project (resolve từ `overlay.yaml`):
- Package root: `{{PACKAGE_ROOT}}`
- Modules: `{{MODULE_APP}} → {{MODULE_PRESENTER}} → {{MODULE_DOMAIN}} ← {{MODULE_DATA}}`
- MVI base: `{{MVI_BASE_CLASS}}<S, I, E>`
- Theme: `{{THEME_CLASS}}`
- DI: {{DI_FRAMEWORK}}
- Stack: {{UI_FRAMEWORK}} + {{NETWORK_FRAMEWORK}} + {{DATABASE_FRAMEWORK}}

## Overlay bootstrap check

Trước mọi coding/business/testing task, verify `.harness-overlay/overlay.yaml` tồn tại ở consumer project root. Nếu không:

1. Trigger skill `harness-init` để scaffold overlay (auto-detect gradle + hỏi branding).
2. Sau khi overlay ready, continue task gốc.

Skills không được tự ý hardcode value thay cho overlay. Nếu overlay trống hoặc missing field, abort với status `BLOCKED` và chỉ dẫn user chạy `harness-init`.

## Placeholder resolution

Khi SKILL.md, knowledge, blueprint, workflow chứa `{{X}}`, resolve bằng cách Read `.harness-overlay/overlay.yaml` và map:

| Placeholder | Overlay path | Ví dụ value |
|---|---|---|
| `{{PRODUCT_NAME}}` | `product.name` | `Acme` |
| `{{PACKAGE_ROOT}}` | `product.package` | `com.acme.app` |
| `{{PACKAGE_ROOT_PATH}}` | derived từ `product.package` (dot → slash) | `com/acme/app` |
| `{{MODULE_APP}}` | `modules.app` | `composeApp` |
| `{{MODULE_PRESENTER}}` | `modules.presenter` | `presenter` |
| `{{MODULE_DOMAIN}}` | `modules.domain` | `domain` |
| `{{MODULE_DATA}}` | `modules.data` | `data` |
| `{{THEME_PREFIX}}` | `ui.theme_prefix` | `Acme` |
| `{{THEME_CLASS}}` | `ui.theme_class` | `AcmeTheme` |
| `{{UI_FRAMEWORK}}` | `stack.ui` | `compose-multiplatform` |
| `{{MVI_BASE_CLASS}}` | `stack.mvi` | `BaseViewModel` |
| `{{DI_FRAMEWORK}}` | `stack.di` | `koin` |
| `{{NETWORK_FRAMEWORK}}` | `stack.network` | `ktor` |
| `{{DATABASE_FRAMEWORK}}` | `stack.database` | `sqldelight` |
| `{{FEATURES_ROOT}}` | `features_root` | `feature` |
| `{{ORCHESTRATION_HANDOFF_DIR}}` | fixed `plans/handoff/` | `plans/handoff/` |
| `{{VARS}}` | n/a (legacy, bỏ qua) | — |

Read overlay 1 lần ở đầu session (first task); subsequent tasks reuse cached values trong context.

## Thứ tự đọc khi nhận task

1. **Project root** `CLAUDE.md` — rule project-specific (cao nhất)
2. **Overlay** `.harness-overlay/constitution/` — product extensions
3. **Upstream** `AGENTS.md` (file này) — generic entry + task routing
4. **Upstream** `skills/<skill-tương-ứng>/SKILL.md` — procedure cụ thể
5. **Upstream** `knowledge/` — load khi task yêu cầu (phân cấp 2 tầng: `knowledge/<category>/<domain>/`, index tại `knowledge/README.md`)
6. **Blueprint**: ưu tiên `overlay/blueprints/live-reference-feature.md` (nếu có); fallback `upstream/blueprints/reference-feature/README.md`

## Task routing

### Pipeline entry (skill wrapper high-level — P0 priority)

| Task | Skill |
|---|---|
| Implement feature mới end-to-end (BA → PM → Designer → Tech Lead → Architect → Coder → QA → Release) | `feature` |
| Fix bug với fast-path triage (4 cond → fast/mini/full-flow) | `bugfix` |
| Classify bug không rõ loại (code/design/spec), max 3 retry rồi escalate PM | `bug-triage` |
| Release co-sign Tech Lead + PM (14 tech + 12 business checklist) | `release` |
| Chạy N feature song song cùng sprint (isolation check + shared file aggregation) | `parallel-features` |

### Component-level task

| Task | Skill chính |
|---|---|
| Chuẩn hóa spec + screenshot thành Feature Brief | `business-prepare-feature` |
| Fetch Confluence page + attachment qua MCP | `business-fetch --source confluence` |
| Fetch Figma file + node tree + variables qua MCP | `business-fetch --source figma` |
| Extract requirement + AC từ spec | `business-analyze --phase spec` |
| Extract screen contract từ screenshot/Figma | `business-analyze --phase design` |
| Reconcile conflict giữa spec + design | `business-analyze --phase reconcile` |
| Validate Feature Brief qua 12 quality gates | `business-validate-brief` |
| Run e2e regression test pipeline qua fixtures | `verify-e2e` workflow (bash + Python) |
| Chấm UI compare screenshot vs Figma + spec | `ui-judge` agent |
| Write runner-neutral E2E step files JSON | `e2e-author` agent |
| Distill tester bugs từ Jira/GitHub thành lessons | `lesson-miner` agent + `mine-lessons` workflow |
| Orchestrate E2E runtime round (full/verify) với streaming bugs | `guard-round` workflow |
| Visual compare Figma vs screenshot (perceptual hash + SSIM) | `validate_ui_visual.py` + stage-5-ui-visual |
| Tạo feature mới end-to-end | `coding-feature` |
| Build/sửa Compose UI | `coding-compose` |
| Thiết kế UiState/Intent/Effect, reducer, side-effect | `coding-mvi` |
| Async / Flow / cancellation / concurrency | `coding-coroutines` |
| API integration, Ktor service, DTO + mapper | `coding-network` |
| Local DB SQLDelight, schema, migration, offline-first | `coding-database` |
| Refactor module preserve-behavior | `coding-refactor` |
| Debug crash / ANR / memory leak / flaky | `coding-diagnose --mode bug` |
| Performance profile + optimize startup/UI/memory/network | `coding-diagnose --mode perf` |
| Review PR, diff, module | `coding-review` |
| Viết unit/UI/integration test | `testing-android` |
| Orchestrate multi-agent / parallel feature build | `coding-orchestrator` |
| Scout codebase — tìm file/caller/blast radius trước khi touch | `coding-scout` |
| Brainstorm trade-off trước implementation (lock outcome contract) | `coding-brainstorm` |
| One-shot pipeline brainstorm→scout→implement→test→review→ship | `coding-vibe` |
| Session continuation contract (switch model, long task, handoff human) | `harness-handoff` |
| Maintain / audit / evolve chính harness (meta-agent) | `harness-maintenance` (Guardian) |

Nhiều task cross-cutting → gọi lần lượt, không chạy song song cùng file.

## Workflows

| Workflow | Khi nào |
|---|---|
| `workflows/prepare-feature-brief.md` | Chuẩn hóa spec + design nguồn thành Feature Brief (5 phases: fetch → analyze spec → analyze design → reconcile → validate). Upstream của feature-development. |
| `workflows/feature-development.md` | Implement feature mới end-to-end (5 stages: inspect → plan → implement → verify → report) |
| `workflows/fix-bug.md` | Debug + fix bug (reproduce → isolate → cause → fix → verify) |
| `workflows/review-pull-request.md` | Review PR / diff theo 10 dimensions với evidence-based findings |
| `workflows/refactor-module.md` | Preserve behavior refactor (baseline → plan → refactor → compare → verify) |
| `workflows/release-validation.md` | Release candidate validation (preflight → build → smoke → artifact → regression → sign-off) |
| `workflows/parallel-feature-development.md` | Build N feature độc lập song song từ spec (decompose → isolation → spawn → aggregate → review → verify) |
| `workflows/harness-maintenance.md` | Maintain + evolve harness (signal → triage → impact → draft → validate → review → release) — bởi Guardian |
| `workflows/verify-e2e.md` | E2e regression test pipeline qua fixtures (5 stages: brief → plan → code → gates → report). Hybrid validation (golden snapshot + semantic assertion). |
| `workflows/guard-round.md` | E2E runtime round orchestration (full vs verify, streaming bugs, early-stop, APK cache + round pin). Pattern-only, downstream build runner. |
| `workflows/mine-lessons.md` | Convert tester bugs → structured lessons feed back vào next-run plan checks + review rules. |

## Agent roles

14 agent chia 3 layer. Trong workflow, agent có thể chuyển mindset qua các role (solo mode) hoặc spawn subagent dedicated (multi-agent mode). Xem `agents/*.md` chi tiết, `agents/workflows/README.md` cho routing.

### Product lifecycle layer

- `product-analyst.md` — BA: market research + spec + wireframe (functional)
- `project-manager.md` — PM: backlog, deadline, feasibility, go-to-market, release co-sign
- `designer.md` — Produce UI/UX final từ wireframe + PRD
- `design-analyst.md` — Analyze design nguồn đã có (role khác designer — reverse engineer)

### Engineering layer

- `tech-lead.md` — Bridge business ↔ tech, plan review gate, bug triage, release co-sign (có fast-path skip)
- `architect.md` — Plan + inspect + decisions + spec decomposition (parallel mode)
- `coder.md` — Execute theo plan, minimal scope
- `reviewer.md` — Independent code audit, evidence-based findings
- `qa.md` — Façade verification: Scope A (per-screen) + Scope B (full-flow E2E)
  - `e2e-author.md` — Subagent QA: write runner-neutral step files cho E2E
  - `ui-judge.md` — Subagent QA: visual compare Figma vs app screenshot

### Meta layer

- `orchestrator.md` — Coordinate multi-agent spawn + aggregate (team/parallel-features mode)
- `lesson-miner.md` — Distill bug reports thành lessons feed next-run
- `harness-guardian.md` — Meta: maintain + evolve chính harness (không touch product code)

### Workflow routing

`agents/workflows/` chứa 5 workflow điều hướng:

- `feature-full-flow.md` — Full pipeline BA → PM → Designer → TechLead → Architect → Coder → Reviewer+QA → Release
- `bugfix-fast-path.md` — Rút gọn khi thỏa 4 điều kiện fast-path của Tech Lead
- `bug-triage.md` — Phân loại code/design/spec bug khi QA fail
- `release-gate.md` — Tech Lead + PM co-sign co-sign protocol
- `parallel-features.md` — Chạy multiple feature song song cùng sprint

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
- `knowledge/meta/agent-orchestration/essentials.md` — orchestration modes + Claude Code Task tool patterns
- `knowledge/meta/agent-orchestration/model-tier.md` — model tier routing (lite/balanced/deep)
- `knowledge/meta/harness-governance/essentials.md` — permission levels L0-L3 + protected baseline
- `knowledge/coding/clean-arch/architecture-profiles.md` — profile cmp/kmp/android-only + migration
- `knowledge/cross-cutting/build-strategy/essentials.md` — 4-level build strategy (fast → regression)
- `knowledge/meta/auto-fix/essentials.md` — auto-fix loop + fingerprint + attempt limit
- `knowledge/coding/clean-arch/clean-mvi.md`
- `knowledge/coding/compose/essentials.md`
- `knowledge/coding/mvi/essentials.md`
- `knowledge/coding/coroutines/essentials.md`
- `knowledge/coding/data/repository-pattern.md`
- `knowledge/coding/data/network.md`
- `knowledge/coding/data/persistence.md`
- `knowledge/coding/data/caching.md`
- `knowledge/coding/patterns/common-patterns.md`
- `knowledge/cross-cutting/security/essentials.md`
- `knowledge/cross-cutting/performance/essentials.md`
- `knowledge/product/input-analysis/requirement-extraction-rules.md` — REQ-RULE-001..006
- `knowledge/product/input-analysis/screenshot-reading-rules.md` — DESIGN-RULE-001..012
- `knowledge/product/input-analysis/reconciliation-matrix.md` — matrix + severity rules
- `knowledge/product/input-analysis/confluence-fetch-rules.md` — CONF-RULE-001..012 cho MCP adapter
- `knowledge/product/input-analysis/figma-fetch-rules.md` — FIG-RULE-001..008 + design rule overrides
- `knowledge/testing/e2e-runtime/device-driver-contract.md` — abstract driver interface (10 methods) + 5 implementation paths comparison
- `knowledge/testing/e2e-runtime/custom-apk-driver.md` — architecture + HTTP protocol + UiAutomation cheat sheet + 3 acquisition options (200+ cases/round scale)
- `knowledge/testing/e2e-runtime/guard-round-pattern.md` — full vs verify round orchestration
- `knowledge/testing/e2e-runtime/interruption-patterns.md` — ad/permission/dialog auto-dismiss
- `knowledge/testing/e2e-runtime/runner-neutral-step.md` — step file design rationale
- `knowledge/design/visual-compare/figma-vs-screenshot.md` — perceptual hash + SSIM thresholds
- `skills/feature/SKILL.md` — **P0** entry: feature-full-flow pipeline wrapper (BA → PM → Designer → Tech Lead → Architect → Coder → QA → Release)
- `skills/bugfix/SKILL.md` — **P0** entry: bugfix-fast-path triage + fast/mini/full routing
- `skills/bug-triage/SKILL.md` — bug classify code/design/spec, max 3 retry
- `skills/release/SKILL.md` — **P0** entry: release-gate co-sign Tech Lead + PM
- `skills/parallel-features/SKILL.md` — parallel N feature + isolation check + shared file aggregation
- `skills/business-prepare-feature/SKILL.md` — orchestrator input layer
- `skills/business-fetch/SKILL.md` — MCP adapter Confluence/Figma (dispatcher `--source`)
- `skills/business-analyze/SKILL.md` — spec/design/reconcile dispatcher (`--phase`)
- `skills/business-validate-brief/SKILL.md`
- `skills/coding-feature/SKILL.md`
- `skills/coding-compose/SKILL.md`
- `skills/coding-mvi/SKILL.md`
- `skills/coding-coroutines/SKILL.md`
- `skills/coding-network/SKILL.md`
- `skills/coding-database/SKILL.md`
- `skills/coding-refactor/SKILL.md`
- `skills/coding-diagnose/SKILL.md` — bug/perf dispatcher (`--mode`)
- `skills/coding-review/SKILL.md`
- `skills/testing-android/SKILL.md`
- `skills/coding-orchestrator/SKILL.md`
- `skills/coding-scout/SKILL.md` — fast codebase discovery (read-only)
- `skills/coding-brainstorm/SKILL.md` — trade-off + outcome lock gate
- `skills/coding-vibe/SKILL.md` — end-to-end pipeline (brainstorm→scout→implement→test→review→ship)
- `skills/harness-handoff/SKILL.md` — session continuation contract (markdown)
- `skills/harness-maintenance/SKILL.md` — Guardian procedure (meta)
- `blueprints/reference-feature/README.md`
- `blueprints/network-service/README.md`
- `blueprints/compose-screen/README.md`
- `blueprints/repository/README.md`
- `blueprints/usecase/README.md`
- `blueprints/task-contract/README.md` + `template.yaml` — standardized plan YAML (how to build)
- `blueprints/feature-brief/README.md` + 5 templates — standardized input brief (what to build + why)
- `blueprints/e2e-step-contract/README.md` + schema + template + forbidden-ops — runner-neutral E2E step files
- `blueprints/ui-spec/README.md` + templates — per-node UI contract (Reach + Door + Elements + Tokens + Copy)
- `workflows/prepare-feature-brief.md` — input layer pipeline
- `workflows/feature-development.md`
- `workflows/fix-bug.md`
- `workflows/review-pull-request.md`
- `workflows/refactor-module.md`
- `workflows/release-validation.md`
- `workflows/parallel-feature-development.md`
- `workflows/harness-maintenance.md` — meta (Guardian lifecycle)
- `agents/product-analyst.md` — BA: market research + spec + wireframe
- `agents/project-manager.md` — PM: backlog, deadline, release co-sign
- `agents/designer.md` — produce UI/UX final từ wireframe
- `agents/design-analyst.md` — analyze design nguồn đã có (reverse)
- `agents/tech-lead.md` — plan review gate + fast-path routing + bug triage
- `agents/architect.md` — technical plan + spec decomposition
- `agents/coder.md` — implement theo plan
- `agents/reviewer.md` — independent code audit
- `agents/qa.md` — façade Scope A + Scope B verification
- `agents/e2e-author.md` — subagent QA: step files
- `agents/ui-judge.md` — subagent QA: visual compare
- `agents/orchestrator.md` — multi-agent spawn + aggregate coordinator
- `agents/lesson-miner.md` — distill bugs thành lessons
- `agents/harness-guardian.md` — meta (maintain harness)
- `agents/workflows/README.md` — index 5 workflow routing
- `agents/workflows/feature-full-flow.md` — pipeline đầy đủ cho feature mới
- `agents/workflows/bugfix-fast-path.md` — pipeline rút gọn cho bugfix
- `agents/workflows/bug-triage.md` — phân loại bug (code/design/spec)
- `agents/workflows/release-gate.md` — Tech Lead + PM co-sign
- `agents/workflows/parallel-features.md` — multiple feature song song
- `verification/architecture-tests/TemplateArchitectureRulesTest.kt`
- `verification/scripts/verify.sh.template`
- `verification/detekt/README.md` + `detekt-config-template.yml`
- `verification/lint/README.md`
- `verification/brief-schema/README.md` + `brief.schema.json` — JSON schema cho Feature Brief
- `verification/e2e/README.md` + `runbook.md` — e2e regression test suite
- `verification/e2e/scripts/run-e2e.sh` + stage-1..4 — bash orchestrator
- `verification/e2e/validators/` — Python validators (brief, plan, code, diff, report)
- `verification/e2e/fixtures/book-detail/` — pilot fixture với intentional conflict
- `verification/e2e/scripts/stage-5-ui-visual.sh` — optional UI visual compare stage
- `verification/e2e/validators/validate_ui_visual.py` — perceptual hash + SSIM validator
- `briefs/README.md` — output directory input layer
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
