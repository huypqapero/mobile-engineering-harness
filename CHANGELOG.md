# Changelog

Tất cả thay đổi đáng chú ý của Mobile Engineering Harness.

Format tuân theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) và semver.

## [0.21.0] — 2026-10-19

### Added — Software-factory agent model (14 agent, 5 workflow routing)

Tái cấu trúc agent registry từ **11 engineering-focused agent** sang **14 agent chia 3 layer** (product lifecycle / engineering / meta) để pipeline đi từ ý tưởng (BA + market research) đến release co-sign (Tech Lead + PM) có artifact ownership rõ, không trùng vai, có fast-path cho bugfix.

#### Rename — 3 agent file (git mv preserved history)

- `agents/input-analyst.md` → `agents/product-analyst.md` — BA. Mở scope: thêm **Market mode** (competitor + user pain research) và **Wireframe mode** (low-fi functional) ngoài **Spec mode** cũ.
- `agents/implementer.md` → `agents/coder.md` — role name match 7-role chuẩn, nhấn mạnh "không tự duyệt thay đổi kiến trúc, không sửa domain contract khi fix bug".
- `agents/test-engineer.md` → `agents/qa.md` — thành **façade** với 2 scope mode: Scope A (per-screen) và Scope B (full-flow E2E), route xuống `e2e-author` + `ui-judge` subagent.

#### Added — 3 agent mới

- **`agents/tech-lead.md`** — Technical Delivery Owner. Bridge BA/PM ↔ Architect/Coder/QA. Nhận PRD + deadline → Tech Brief → delegate Architect → review plan (6 dimensions) → verdict APPROVE / REQUEST_CHANGES / ESCALATE_TO_PM → delegate Coder. **Fast-path skip rule** (user confirmed): thỏa cả 4 điều kiện (≤ 1 file presenter / không shared file / label bugfix-tweak-single-screen / no new dep) → Architect → Coder thẳng, skip plan review. Cấm fast-path cho security, ADR-011 high-risk, cross-feature contract, migration. Max 2 revise rồi auto-escalate PM. Bug triage phân loại code/design/spec. Co-sign Release Gate với PM.
- **`agents/project-manager.md`** — PM: backlog, feasibility scoring (business value × urgency × confidence × tech), milestone + deadline, scope negotiation khi Tech Lead escalate, go-to-market, progress tracking qua handoff state. Co-sign Release Gate. Không chọn kỹ thuật, không viết spec.
- **`agents/designer.md`** — Produce UI/UX cuối cùng từ wireframe + PRD. Design tokens, 5 states/screen remote, interaction, accessibility (WCAG AA, 48dp touch target), dark mode, responsive. Output `design.md` + `design-spec.json` + asset. ChangeRequest ngược về Product Analyst khi phát hiện PRD gap. Khác `design-analyst` (role reverse analyze design nguồn).

#### Added — Workflow routing folder

Folder mới `agents/workflows/` chứa 5 workflow điều hướng + 1 index:

- **`agents/workflows/README.md`** — 14-agent routing map + artifact ownership table + ChangeRequest flow + handoff doc format bắt buộc.
- **`agents/workflows/feature-full-flow.md`** — 8-stage pipeline cho feature mới (BA → PM → Designer → Tech Lead → Architect → Tech Lead review gate → Coder → Reviewer + QA → Release). Gate rõ sau mỗi stage, timeline guideline, skip-stage rules.
- **`agents/workflows/bugfix-fast-path.md`** — 3-stage rút gọn khi 4 fast-path conditions MATCH, 4-stage mini-plan khi PARTIAL, fallback full-flow khi NO. So sánh thời gian: fast-path 1-4h vs full-flow days-weeks.
- **`agents/workflows/bug-triage.md`** — Tech Lead phân loại 3 nhánh: **code bug** (Coder fix, không đổi contract) / **design bug** (Architect revise plan) / **spec bug** (Product Analyst update PRD + cascade). Max 3 retry cùng failure signature rồi auto-escalate PM. Lesson feedback vào `lesson-miner`.
- **`agents/workflows/release-gate.md`** — Co-sign protocol Tech Lead (14-item tech checklist) + PM (12-item business checklist) với decision matrix (READY / READY_WITH_WARNINGS / NOT_READY). Rollback trigger + staged rollout plan + post-release monitoring.
- **`agents/workflows/parallel-features.md`** — N feature parallel với isolation check (SAFE vs UNSAFE rules), spec decomposition qua Architect, shared file aggregation sequential, token budget guide.

#### Changed — References cập nhật

Batch rename qua word-boundary perl replace trong 25 file active (giữ nguyên `CHANGELOG.md` + `plans/` làm historical record):

- Patterns: `input-analyst` → `product-analyst`, `implementer.md` → `coder.md`, `test-engineer` → `qa`, `Input Analyst` → `Product Analyst`, `Implementer` → `Coder`, `Test Engineer` → `QA`.
- Files touched: `AGENTS.md`, `README.md`, `overlay.schema.yaml`, `blueprints/task-contract/template.yaml`, `blueprints/ui-spec/README.md`, `workflows/*.md` (7), `knowledge/**/*.md` (5), `skills/**/SKILL.md` (6), `verification/e2e/fixtures/book-detail/expected/brief.golden.yaml`.

- **`AGENTS.md`** — section "Agent roles" tái cấu trúc theo 3 layer (product / engineering / meta); file index phần `agents/` bổ sung `tech-lead`, `project-manager`, `designer` + 6 file trong `agents/workflows/`.
- **`README.md`** — table "Agent roles" cập nhật từ "4 roles" sang "14 agents (3 layer)".

#### Rationale

Plan ChatGPT (`Downloads/ChatGPT-Thiết kế agent chuyên trách-...md`) + plan brainstorm hợp nhất. User chốt 4 decision:

1. **Giữ nguyên thư mục `agents/`** + thêm `tech-lead.md` (không chuyển sang `software-factory/` sub-dir)
2. **Orchestrator = LLM agent** (không phải script workflow engine)
3. **Tech Lead review có fast-path skip** (4 điều kiện AND)
4. **Reviewer giữ riêng, không gộp vào Tech Lead** (khác thời điểm gate: Tech Lead = plan review pre-impl, Reviewer = code review post-impl)

Scope: 11 → 14 agent (+ 3), tạo folder workflow routing (6 file mới), batch update references (25 file), git mv (3 file), word-boundary safe (không false match với English "implementer" trong prose).

#### Known gaps

- Workflow files gốc `workflows/*.md` có overlap với `agents/workflows/*.md` — chưa quyết định migrate hay dual-track. `agents/workflows/README.md` note "legacy, overlap với folder này sẽ migrate dần".
- Chưa tạo schema cứng cho handoff doc (`plans/handoff/<feature>/*.md`) + ChangeRequest (`briefs/<slug>/change-requests/CR-<id>.md`). Hiện là markdown template inline trong workflow file.
- Fast-path telemetry chưa có (chưa đo tỷ lệ fast-path approve vs full-path, chưa đo rate of fast-path mis-triage).

## [0.20.0] — 2026-10-19

### Added — Harness-init skill + D-full overlay runtime integration

Consumer onboarding thu về **1 skill invocation**: `/harness-init` auto-detect gradle stack, interactive branding, render overlay, validate schema, và install project-local Claude Code symlinks + SessionStart hook. Giữ nguyên 17 placeholder trong harness source; model resolve runtime từ `.harness-overlay/overlay.yaml`.

#### Skill — harness-init

- **`skills/harness-init/SKILL.md`** — 9-step procedure cho consumer bootstrap.
- **`skills/harness-init/scripts/detect-stack.sh`** — auto-detect UI/DI/Network/Database framework + package root + modules từ `libs.versions.toml`, `settings.gradle.kts`, `AndroidManifest.xml`.
- **`skills/harness-init/scripts/render-overlay.sh`** — build `.harness-overlay/overlay.yaml` từ stack JSON + branding env vars.
- **`skills/harness-init/scripts/validate-overlay.py`** — schema check: required keys, enum values, dependency conflicts (vd `targets contains ios` + `ui=xml-android`).
- **`skills/harness-init/references/overlay-schema-mapping.md`** — detection matrix + decision guides cho multi-module, ambiguous DI/Network/DB stacks.

#### D-full placeholder resolution

- **`AGENTS.md`** thêm 2 section:
  - `## Overlay bootstrap check` — nhắc trigger `harness-init` khi overlay missing; skills abort với `BLOCKED` nếu overlay thiếu field.
  - `## Placeholder resolution` — mapping table 17 placeholder → overlay path (`{{MODULE_APP}}` → `modules.app`, `{{PRODUCT_NAME}}` → `product.name`, v.v.).
- **20 SKILL.md** append `## Overlay gate (D-full)` section + `## Harness context` (workflow + guardrails pointer).
- **`install.sh`** header mark `init` subcommand DEPRECATED; prefer skill `harness-init`.

#### Scripts (consumer install/uninstall)

- **`scripts/activate-claude-agents.sh`** — symlink `agents/*.md` → consumer `.claude/agents/` (install/uninstall/status).
- **`scripts/check-overlay.sh`** — SessionStart hook script, remind trigger `harness-init` khi `.harness-overlay/overlay.yaml` missing.
- **`scripts/install-session-hook.sh`** — patch consumer `.claude/settings.json` SessionStart entry + symlink hook vào `.claude/hooks/`.
- **`scripts/uninstall-all.sh`** — orchestrate full teardown (skills + agents + hook); `--purge` flag xóa luôn `.harness-overlay/`.

#### README

- `## Install` thêm "Alternative: skill-based onboarding qua Claude Code" subsection (gọi `/harness-init` thay vì `mehcli init`).
- `## Install` thêm "Uninstall / offboarding" subsection với `uninstall-all.sh` command + giải thích scope khác `mehcli uninstall`.

#### Rationale (D-full vs D-lite)

Thảo luận trade-off: giữ 17 placeholder + auto-trigger harness-init (D-full) vs bỏ 9 placeholder hardcode default (D-lite). Chọn D-full vì:

- Zero code change trong 39 harness source file (safer khi upstream evolve).
- Overlay là **explicit audit trail** cho consumer convention (vd `stack.di=hilt` doc rõ).
- Multi-product consume harness mà convention khác nhau: mỗi product có overlay riêng, không chia default.
- Rollback khi default sai: sửa overlay 1 file thay vì bulk patch 39 file.

Mitigation ~5% miss-resolve risk:
- Hard-enforce SessionStart hook `check-overlay.sh` (deterministic).
- Soft-enforce `## Overlay gate (D-full)` ở top mỗi SKILL.md.
- Mapping table full ở `AGENTS.md §Placeholder resolution`.

### Added — Workflow + session skills (học từ ak catalog)

Add 4 skill cover gap với ak pattern: fast scouting, pre-implement brainstorm gate, end-to-end pipeline, session handoff. Harness skill count: 16 → 20 → 21 (+ harness-init).

#### Skills (4)

- **`skills/coding-scout/SKILL.md`** — Fast codebase scouting. Native Glob/Grep/Read wrapper trả về file paths + layer classification + blast radius + suggested next skill. Read-only, không spawn agent cho simple query. Pattern từ `ak-scout`.
- **`skills/coding-brainstorm/SKILL.md`** — Gate skill trước implementation. Lock outcome contract (desired/constraints/non-goals/AC) + enumerate 2-3 approach với trade-off matrix (6 dimension) + red team mỗi approach + recommend primary + fallback. Hard cap 3 approach. Pattern từ `ak-brainstorm`.
- **`skills/coding-vibe/SKILL.md`** — End-to-end pipeline orchestrator. Chain brainstorm → scout → implement (feature/diagnose/refactor) → test → review → ship PR với 7 explicit quality gates. Max retry per stage documented. Auto `harness-handoff` khi retry exceed. Pattern từ `ak-vibe` nhưng chain Android/KMP skills thay vì React.
- **`skills/harness-handoff/SKILL.md`** — Portable session continuation contract (markdown). Capture outcome, decisions, verification state, blockers với attempted + next step, file inventory, environment state, explicit next action. Self-contained — successor không cần chat history. `--redact` strip secrets. Pattern từ `ak-handoff` (chỉ file, không dispatch).

#### Updated cross-refs

- `AGENTS.md` task routing table + file index — thêm 4 skill mới
- `scripts/activate-claude-skills.sh install` reinstalls → 20 symlinks trong `~/.claude/skills/`

#### Rationale

Phân tích ak catalog (~160 skills) vs harness (16) tìm pattern đáng học. Scope harness vertical Android nên không copy marketing/design kits. Add 4 skill cover 4 use case thiếu:

1. **Scout:** trước đây ad-hoc grep per task; giờ consistent discovery + layer classify
2. **Brainstorm:** gate chống scope creep + decision debt; outcome contract reusable cho downstream `coding-feature`
3. **Vibe:** entry point one-shot cho user muốn full pipeline, không phải orchestrate từng skill thủ công
4. **Handoff:** critical cho long task cross-session (Android cross-module feature thường > 1 session) + model switch (opus → sonnet)

Giữ skill count ở 20 — không copy toàn bộ ak catalog. Nguyên tắc: adopt pattern, không clone content; respect harness vertical scope.

## [0.19.0] — 2026-10-19

### Changed — Skill naming convention (prefix normalization)

Chuẩn hóa 15/16 skill name sang 3 prefix domain để dễ phân biệt trong catalog `/skill`:

- **`coding-`** (10 skills): implementation + review + diagnose
- **`business-`** (4 skills): spec/design pipeline (fetch, analyze, prepare, validate)
- **`testing-`** (1 skill): test authoring
- **`harness-maintenance`** giữ nguyên (meta skill, không fit 3 nhóm)

#### Rename mapping

| Cũ | Mới |
|---|---|
| `android-feature` | `coding-feature` |
| `android-mvi` | `coding-mvi` |
| `android-compose` | `coding-compose` |
| `android-coroutines` | `coding-coroutines` |
| `android-network` | `coding-network` |
| `android-database` | `coding-database` |
| `android-refactor` | `coding-refactor` |
| `android-diagnose` | `coding-diagnose` |
| `android-code-review` | `coding-review` |
| `android-orchestrator` | `coding-orchestrator` |
| `android-testing` | `testing-android` |
| `input-fetch` | `business-fetch` |
| `input-analyze` | `business-analyze` |
| `input-prepare-feature` | `business-prepare-feature` |
| `input-validate-brief` | `business-validate-brief` |

#### Updated cross-refs

Toàn bộ reference across `AGENTS.md`, `README.md`, `workflows/*.md`, `agents/*.md`, `knowledge/**/*.md`, `skills/**/SKILL.md` được rewrite bằng `scripts/rename-skills.sh` + `scripts/rename-skills-pass2.sh` (longest-first substring replace tránh prefix collision).

#### Tooling

- `scripts/rename-skills.sh` — one-shot folder rename + frontmatter `name:` patch + initial cross-ref sweep
- `scripts/rename-skills-pass2.sh` — second-pass substring replace cho mọi residual (plan filenames, SKILL.md H1 headers, string references trong harness-maintenance examples)

#### Rationale

User không phân biệt được skill `android-*` nào là code vs test vs orchestration khi quét catalog `/skill`. Prefix domain-based giúp agent + user route nhanh: `coding-*` = implementation lane, `business-*` = requirement/design lane, `testing-*` = quality lane. Rename không đổi behavior, chỉ đổi identifier.

## [0.18.0] — 2026-10-19

### Changed — Skill consolidation (20 → 16)

Gộp skill phase-level thành dispatcher skills để giảm catalog noise + unify tool chain cho overlap thật, giữ nguyên invocation lẻ qua flag `--source|--phase|--mode`.

#### Merged

- **`skills/input-fetch/SKILL.md`** (new) — merge `input-fetch-confluence` + `input-fetch-figma`. Dispatcher `--source confluence|figma`. Cùng output contract (snapshot vào `assets/sources/` + record origin/sha256 trong `brief.yaml.sources[]`), khác MCP adapter + extraction procedure.
- **`skills/input-analyze/SKILL.md`** (new) — merge `input-analyze-spec` + `input-analyze-design` + `input-reconcile`. Dispatcher `--phase spec|design|reconcile|all`. Mỗi phase vẫn callable độc lập cho refresh section.
- **`skills/android-diagnose/SKILL.md`** (new) — merge `android-debug` + `android-performance`. Dispatcher `--mode bug|perf`. Bug mode reactive (reproduce → isolate → prove → fix); perf mode measurement-driven loop (measure → hypothesize → optimize → re-measure). Common tool chain preserved.

#### Removed

- `skills/input-fetch-confluence/`
- `skills/input-fetch-figma/`
- `skills/input-analyze-spec/`
- `skills/input-analyze-design/`
- `skills/input-reconcile/`
- `skills/android-debug/`
- `skills/android-performance/`

#### Updated cross-refs

`AGENTS.md`, `README.md`, `workflows/prepare-feature-brief.md`, `workflows/fix-bug.md`, `agents/input-analyst.md`, `agents/design-analyst.md`, `knowledge/auto-fix/essentials.md`, `knowledge/performance/essentials.md`, `knowledge/input-analysis/*.md` — route sang skill mới + flag syntax.

#### Tooling

- `scripts/activate-claude-skills.sh` (new, from v0.17.1 dev) — symlink skills vào `~/.claude/skills/` để expose cho Claude Code `/skill`. Commands: `install|uninstall|status`, flags `--from|--target|--prefix|--force|--dry-run`.

#### Rationale

Input pipeline over-decomposed theo phase: 7 skill cho 1 orchestrator (`input-prepare-feature`). Phase chỉ chạy trong pipeline hiếm khi gọi lẻ ngoài orchestrator — chuyển thành phase flag giảm catalog slot + description noise cho Claude Code `/skill` discovery, không mất khả năng refresh section. Android debug vs performance có trigger overlap (ANR, jank, memory, recomposition) + dùng chung Profiler/Perfetto/logcat → gộp thành diagnose dispatcher.

Total: 20 → 16 skills (11 android + 4 input + 1 maintenance). Giữ nguyên: `input-prepare-feature`, `input-validate-brief`, 10 `android-*` còn lại, `harness-maintenance`.

## [0.17.0] — 2026-10-16

### Added — Custom APK Driver Pattern

Pattern cho custom APK driver — hiệu suất cao (~30-100ms/call) cho E2E test volume lớn (200+ cases/round) hoặc yêu cầu Unicode input chuẩn (dấu tiếng Việt). Thay thế ARTEMIS MCP (~1-2s/call) khi scale vượt threshold.

**Harness không ship binary APK.** Document pattern + architecture + protocol spec để downstream product build APK driver riêng, hoặc tham khảo implementation có sẵn (learn-app-plugin private repo).

#### Knowledge (1)

- **`knowledge/e2e-runtime/custom-apk-driver.md`** (~500 LoC):
  - Decision matrix khi nào cần APK driver (volume threshold, latency, Unicode)
  - Architecture overview: host runner ↔ ADB forward ↔ instrumentation HTTP server trên device
  - HTTP protocol spec: `/ping /tree /shot /tap /settext` + extensions `/swipe /long_press /launch /shell /broadcast`
  - UiAutomation API cheat sheet (getWindows, walk tree, injectInputEvent, ACTION_SET_TEXT, takeScreenshot)
  - Project structure (Android library module với instrumentation entry)
  - Unicode input strategies: clipboard vs accessibility setText
  - Element locator priority (resource id → test-tag → content-description → text → regex → fallback)
  - Jetpack Compose semantics considerations
  - Build + sign + install workflow
  - CI integration example (GitHub Actions pipeline)
  - Testing driver reliability (self-test suite + metrics endpoint)
  - **3 acquisition options**: build riêng (recommended, 2-3 tuần), fork learn-app (nhanh nhất với access), vendor binary APK (temporary PoC)
  - Integration mapping APK endpoints → 10 methods driver contract
  - 7 anti-patterns

### Changed

- `knowledge/e2e-runtime/device-driver-contract.md`: thêm section "Implementation paths" với bảng so sánh 5 paths (ARTEMIS / Maestro / Appium / Custom APK / ADB+vision), cross-reference tới `custom-apk-driver.md`.
- `AGENTS.md`: file index add `custom-apk-driver.md`.

### Rationale

User explicit chọn APK custom path cho downstream product scale 200+ cases/round. ARTEMIS MCP (~1.5s × 30 steps × 200 cases = 2.5 giờ/round) không scale được. APK driver (~30ms × 30 × 200 = 3 phút/round) giảm 50x.

Scope decisions:
- **Pattern-only, không ship binary**: giữ harness repo nature (markdown + minimal Python/Bash). Downstream build APK trong project riêng theo doc.
- **HTTP over ADB forward**: protocol đã chứng minh work bởi learn-app-plugin, simpler hơn broadcast intent / content provider.
- **Persistent UiAutomation**: key insight cho performance — 1 instrumentation process giữ connection suốt run, không spawn mới mỗi call.
- **Accessibility setText cho Unicode**: avoid `adb shell input text` limitations với dấu tiếng Việt.
- **3 acquisition options**: user có flexibility (build riêng cho long-term, fork learn-app cho nhanh, vendor binary cho PoC).

Learn-app-plugin DriverInstrumentation.java inspected (public API scope):
- Port 7912 default
- ServerSocket bind 127.0.0.1 only
- Endpoints `/ping /config /tree /shot /tap /settext`
- UiAutomation flags: FLAG_RETRIEVE_INTERACTIVE_WINDOWS + FLAG_INCLUDE_NOT_IMPORTANT_VIEWS + FLAG_REPORT_VIEW_IDS
- Guarded tap với ad detection built-in

Harness doc tổng quát hóa, không copy ad detection product-specific.

### Migration from 0.16.0

Zero breaking change. Pure documentation addition.

### Scope boundaries

- **IN scope v0.17.0**: Documentation pattern + protocol spec + acquisition options
- **OUT scope**: Shipping binary APK, Android project trong harness repo, auto-install workflow
- **OUT scope (future Wave 3)**: `tools/harness-device-driver/` scaffold, APK CI build pipeline, driver marketplace

### Not implemented in Wave

- No actual APK built (downstream responsibility)
- No install script (downstream orchestrator)
- No example product repo demonstrating Option A build (future)

## [0.16.0] — 2026-10-16

### Added — Learn-plugin E2E Pattern Port (Wave 1)

Port **cốt lõi E2E patterns** từ `hung-apero/learn-app-plugin` sang harness dưới dạng **pattern + schema + agent template**, zero runtime code. Downstream product build runner theo pattern khi cần.

#### Agents (3)

- **`agents/ui-judge.md`** — Visual compare screenshot vs Figma + ui-spec, verdict chặn (critical) vs nên sửa (minor). Read-only, record qua state CLI hoặc result file. Generic cho mọi Android app.
- **`agents/e2e-author.md`** — Write runner-neutral JSON step files. Enforce 4 forbidden ops (force-stop $APP_ID, pm clear, hardcode packageId, raw locale change). Alternative patterns provided.
- **`agents/lesson-miner.md`** — Distill tester bugs từ Jira/GitHub/Linear thành structured lessons (symptom + cause + rule + how_to_test + affected_files). PR cho dev review, không auto-merge.

#### Blueprints (2)

- **`blueprints/e2e-step-contract/`** — Runner-neutral JSON step file schema:
  - `README.md` — Design rationale, action types, placeholders, metadata flags
  - `step-file.json.template` — Reference template
  - `step-file.schema.json` — JSON Schema Draft 2020-12 với forbidden ops regex enforce
  - `forbidden-ops.md` — FORBID-001..004 chi tiết (force-stop, pm clear, hardcode AppID, raw locale)
- **`blueprints/ui-spec/`** — Per-node UI contract (screen/popup/sheet/dialog/state):
  - `README.md` — Sections (Reach + Door + Elements + Tokens + Copy + Assets)
  - `node-spec.md.template` — Template per node
  - `nodes-manifest.json.template` — Index manifest `_nodes.json` schema

#### Knowledge (5)

- **`knowledge/e2e-runtime/device-driver-contract.md`** — Abstract driver interface 10 methods (fetchHierarchy, tap, type, swipe, wait, assert, screenshot, shell, launch, hook). Performance targets. Portability requirements. ARTEMIS adapter example.
- **`knowledge/e2e-runtime/guard-round-pattern.md`** — Full round vs verify round orchestration. State machine. Early-stop logic (3 cases same fingerprint). APK cache + round pin. Streaming bug coordination. Resumption after crash.
- **`knowledge/e2e-runtime/interruption-patterns.md`** — Ad popup / permission dialog / system dialog / in-app modal detection + dismiss. Watch mode cho rewarded ads. Max consecutive = 3 fail. Fixture `adsOffRemoteConfig` flag.
- **`knowledge/e2e-runtime/runner-neutral-step.md`** — Design principles declarative, node slug vs view id, JSON over YAML, placeholder resolution, forbidden ops schema-level, metadata flags. So sánh với Maestro / Appium / Espresso / Detox.
- **`knowledge/visual-compare/figma-vs-screenshot.md`** — Perceptual hash (phash default) + SSIM optional. Thresholds (0-5 near-identical, 6-10 minor, 11-20 significant, 21+ very different). Pre-processing (resize, crop system UI, mask dynamic). Per-node override.

#### Workflows (2)

- **`workflows/guard-round.md`** — E2E runtime round orchestration pattern. 5 stages: Open → Build → Install → Run (streaming) → Close. Full vs verify matrix. Rollback strategy. Agent roles mapping.
- **`workflows/mine-lessons.md`** — Bug tracker → structured lessons pipeline. 5 stages: Fetch → Classify → Distill → Merge → PR. Dev review required. Integration với plan-reviewer / test-writer / architect / Guardian.

#### Verification extension

- **`verification/e2e/scripts/stage-5-ui-visual.sh`** — Optional stage 5 cho visual UI compare. Skip gracefully nếu missing deps hoặc rules file.
- **`verification/e2e/validators/validate_ui_visual.py`** — Pillow + imagehash validator. Pre-process (resize + crop + mask). Perceptual hash default + SSIM optional per node. Classification 4 tiers.

### Changed

- `AGENTS.md`: task routing +6 rows (ui-judge, e2e-author, lesson-miner, visual compare, guard-round, mine-lessons), workflows +2, agent roles +3, file index refresh.

### Rationale

`hung-apero/learn-app-plugin` là **product-specific orchestrator** (dòng Learn app) với full runtime E2E stack (90+ test files, built-in APK driver, Firebase/Discord integration). Harness generic không nên copy product-specific infrastructure, nhưng **pattern + schema + agent template** là valuable universally.

Wave 1 port:
- **Portable (DO port)**: UI judge pattern, E2E step schema, device driver contract, guard round orchestration, interruption handling, lesson mining, visual compare technique
- **Product-specific (DO NOT port)**: Built-in APK driver, Feature Store catalog, Firebase Remote Config hook, Discord bot, Google Play compliance, Learn SDK vendored

Key design decisions:
- **Zero runtime code**: harness ship pattern + schema + agent markdown. Downstream build runner adapter khi cần (ARTEMIS MCP, Appium, Maestro, custom APK).
- **Agent template approach**: ui-judge/e2e-author/lesson-miner là generic role prompts, không tie với state CLI implementation của learn-app-plugin.
- **Schema enforcement**: step file forbidden ops ở JSON Schema regex level, 4 defense layers (schema + author lint + driver pre-exec scan + report trace).
- **Visual compare pre-filter**: perceptual hash fast + deterministic, call ui-judge LLM chỉ khi distance >= 6 (giảm cost + latency).
- **Dev-review gate cho lessons**: lesson-miner không auto-publish; PR cho dev approve → next run consume.
- **Mapping Learn 9-step → harness workflows**: không copy state machine (`spec → scout → ask → clear → update-spec → planning → coding → testing → notify`); map từng step vào existing workflows (feature-development, verify-e2e, guard-round).

### Scope boundaries

- **IN scope v0.16.0**: Agent templates, blueprints, knowledge, workflows, visual compare validator (ui-visual stage 5)
- **OUT scope (Wave 2+)**: ARTEMIS MCP adapter wrap, real device driver implementation, state CLI tool, autopilot hooks, pool emulator parallel coordination, journey schema

### Smoke test

- Pillow + imagehash installed cục bộ, validator chạy với synthetic fixture (perceptual_distance=0 cho identical placeholders).
- JSON schema step-file validated syntax OK.
- Stage 5 shell script executable, skip gracefully khi fixture không có `expected/ui/visual.rules.yaml`.

### Migration from 0.15.0

Zero breaking change. Pure addition.

**Usage examples**:

```bash
# Visual compare (nếu fixture có screenshots thật + Figma reference)
./verification/e2e/scripts/stage-5-ui-visual.sh verification/e2e/fixtures/book-detail /tmp/results.yaml

# ui-judge agent (invoke manual qua Claude Code):
# Prompt: "ui-judge grade node book-detail-content với
#   Figma: expected/ui/figma/book-detail-content.png
#   Shot: actual/ui/screenshots/book-detail-content.png
#   Spec: ui-spec/book-detail-content.md"

# e2e-author (invoke manual):
# Prompt: "e2e-author write step file cho test case TC-001 với
#   UI spec: ui-spec/*.md, output briefs/<slug>/actual/e2e/TC-001.json"

# lesson-miner (require tracker MCP):
# Prompt: "lesson-miner mine bugs cho app ABC từ Jira project ABC since 2026-07-01"
```

### Not implemented in Wave 1

- No actual runner (downstream build theo pattern)
- No state CLI (dùng existing task-contract blueprint khi cần)
- No ARTEMIS adapter wrap (Wave 2 nếu team có real device test need)
- No streaming bug coordination infrastructure
- No pool emulator parallel runner

## [0.15.0] — 2026-10-16

### Added — E2E Verification Suite

Full pipeline regression test cho harness. Chạy fixtures qua 5 stages (brief → plan → code → gates → report) và so sánh output với golden snapshots + semantic rules.

#### Workflow

- **`workflows/verify-e2e.md`** — 5-stage pipeline với fix loop, rollback, agent role, report format.

#### Scripts (bash orchestrator)

- **`verification/e2e/scripts/run-e2e.sh`** — entry point với options `--all`, `--stages`, `--update-golden`, `--verbose`.
- **`verification/e2e/scripts/stage-1-brief.sh`** — validate brief: schema + semantic + golden diff.
- **`verification/e2e/scripts/stage-2-plan.sh`** — validate plan artifact (optional).
- **`verification/e2e/scripts/stage-3-code.sh`** — dry Konsist check (optional, static).
- **`verification/e2e/scripts/stage-4-gates.sh`** — cross-reference gates: file existence, link resolution, orphan check.

#### Validators (Python)

- **`verification/e2e/validators/validate_brief.py`** — JSON schema + semantic rules enforcement (min_confirmed_requirements, max_blocker_issues, all_ac_bind_confirmed, components_ambiguous_resolved).
- **`verification/e2e/validators/validate_plan.py`** — task-contract schema + expected structure.
- **`verification/e2e/validators/validate_code_structure.py`** — dry Konsist static check: expected files, forbidden/required regex patterns.
- **`verification/e2e/validators/diff_golden.py`** — snapshot comparator, ignore noise fields (timestamps, checksums).
- **`verification/e2e/validators/report_builder.py`** — consolidate markdown report với stage breakdown.

#### Fixture

- **`verification/e2e/fixtures/book-detail/`** — pilot fixture với intentional conflicts:
  - `config.yaml` — fixture metadata
  - `input/spec.md` + `input/screenshots/` — source
  - `expected/brief.golden.yaml` — golden snapshot
  - `expected/brief.semantics.yaml` — semantic rules
  - `expected/plan.structure.yaml` — plan expected structure
  - `expected/code.konsist.expected.yaml` — code rules dry check

Fixture intentional issues:
- SOURCE_CONFLICT (button label spec vs screenshot)
- MISSING_DESIGN (offline state không có screenshot)
- AMBIGUOUS_COMPONENT (top-right icon candidates)
- MISSING_BEHAVIOR (OI-01 cellular behavior)
- UNRESOLVED_NAVIGATION (OI-02 inline vs full player)

#### Documentation

- **`verification/e2e/README.md`** — layout + hybrid validation strategy + fixture design.
- **`verification/e2e/runbook.md`** — detailed how-to-run, exit codes, troubleshoot, CI integration preview.

### Changed

- `AGENTS.md`: task routing +1 row (verify-e2e), workflows +1 row, file index refresh với 5 e2e paths.

### Rationale

Trước v0.15: harness không có integration test. Khi update skill/schema/workflow, maintainer phải chạy manual check qua product repo thật để confirm không regression. Risk cao: không catch được output format drift, không catch được semantic quality degrade.

v0.15 bridge gap:
- **Automated regression detect**: khi harness thay đổi, chạy `./run-e2e.sh --all` → confirm fixtures vẫn PASS.
- **Hybrid validation**: golden snapshot catch structural drift (schema, field layout), semantic assertion catch content quality degrade (REQ coverage, AC verifiability).
- **No agent dependency**: validators chạy static trên artifacts, không spawn Claude Code/Codex → deterministic, CI-friendly.
- **Fixture ownership**: `book-detail` pilot là canonical example cho downstream team onboard.

Key design decisions:
- **Bash + Python stack**: match install.sh convention (bash orchestrator, Python validator). Zero extra dependency vì jsonschema + pyyaml đã có trong Guardian dependency.
- **Static code check**: Stage 3 không spawn Gradle/Konsist thật (require Android project). Static regex + file list enough cho harness-level e2e.
- **Golden ignore noise**: timestamps + checksums là noise (variable mỗi run). diff_golden strip trước khi compare.
- **Golden update require human**: `--update-golden` không chạy auto trong CI. Golden regenerate luôn qua maintainer review.
- **Stage skip gracefully**: Stage 2 (plan) + 3 (code) skip nếu artifact missing. Fixture không bắt buộc có đủ 5 stages.
- **Smoke test passed trên dev machine**: pilot fixture book-detail chạy end-to-end với mock actual = golden, confirm pipeline logic.

### Migration from 0.14.1

Zero breaking change. E2e là tool mới, additive. Existing workflows không bị impact.

**Usage**:

```bash
# Install deps (one-time)
pip3 install pyyaml jsonschema

# Run single fixture
./verification/e2e/scripts/run-e2e.sh book-detail

# Run all fixtures
./verification/e2e/scripts/run-e2e.sh --all

# Debug stage specific
./verification/e2e/scripts/run-e2e.sh book-detail --stages 1,4 --verbose

# Update golden sau intentional harness change
./verification/e2e/scripts/run-e2e.sh book-detail --update-golden
```

### Integration với Guardian

Guardian workflow `harness-maintenance.md` có thể trigger e2e trong `audit mode` để confirm fixtures stable trước khi propose change. E2e fail → Guardian document regression, không merge. E2e pass → regenerate golden nếu intentional, commit vào PR.

### Scope boundaries

- **IN scope v0.15.0**: Bash orchestrator, Python validators, book-detail pilot fixture, 5 stages, hybrid validation.
- **OUT scope (Wave 2+)**: Agent spawn integration (auto-run Claude Code CLI để produce actual output), multi-fixture parallel run, GitHub Actions CI workflow, benchmark mode (token cost, execution time per skill).

### Smoke test verification

Pilot fixture book-detail chạy local trên dev machine:
- Deps installed: pyyaml 6.x, jsonschema 4.x
- `actual/brief.yaml = expected/brief.golden.yaml` (identity test) → PASS all stages
- Report format đẹp, markdown parse OK
- Exit code 0 với overall PARTIAL (vì Stage 2+3 skip do fixture không có plan/code artifact)

## [0.14.1] — 2026-10-15

### Added

- `README.md`: section **"Update to latest"** consolidate update workflow cho downstream product consume harness. Cover 6-step workflow symlink mode, submodule mode variant, rollback procedure, breaking change check, pin strategy cho development vs CI vs multi-product org.

### Changed

- `README.md` table of contents: thêm entry "Update to latest" (section 2), renumber các section sau.

### Rationale

Trước v0.14.1: workflow update rải trên 3 chỗ trong README (Install, CLI reference, Best practices "Khi update harness" — section này thực chất là checklist cho harness maintainer release version mới, không phải user downstream). User downstream phải tự ghép commands từ `mehcli self-update` + `mehcli update` + git submodule docs. Rollback + pin strategy chưa document.

Zero code change. Pure documentation consolidation.

## [0.14.0] — 2026-10-15

### Added — Confluence + Figma MCP Adapters

Mở rộng input layer với 2 remote source adapters qua MCP. Spec có thể fetch từ Confluence, design có thể fetch từ Figma với node tree + variables + image export. Vẫn tuân thủ "adapter fetch-only" principle: không analyze business logic trong fetch layer.

#### Skills (2)

- **`skills/input-fetch-confluence/SKILL.md`** — Fetch Confluence page + children + attachments + inline images + comments qua `mcp-atlassian`. Normalize sang markdown + binary vào `assets/sources/`. Hỗ trợ URL/page_id/CQL input, `--include-children`, `--include-comments`, `--design-source: confluence-attachments` route images sang screenshots.
- **`skills/input-fetch-figma/SKILL.md`** — Fetch Figma file + node tree + variables + styles + PNG screenshots + SVG icons qua `framelink-figma` (primary) hoặc `TalkToFigma` (fallback live canvas). Build structured `screen-contracts.json` cho downstream analyze. Hỗ trợ `--mode: fetch|live`, `--include-variables`, variants auto-export.

#### Knowledge (2)

- **`knowledge/input-analysis/confluence-fetch-rules.md`** — CONF-RULE-001..012 (permission check, snapshot immutable, preserve revision, markdown normalize, attachment handling, multi-page spec, flag open items). 7 anti-patterns. Edge cases (empty page, large attachment, Cloud vs Server, WIP labels, PDF/DOCX attachments).
- **`knowledge/input-analysis/figma-fetch-rules.md`** — FIG-RULE-001..008 (snapshot, record version, explicit node selection, variables = authoritative token, component instance resolution, image export quality, variants export, preserve constraints + auto-layout). 8 anti-patterns. Edge cases (no variables, remote library, prototyping conditions, nested depth).

#### Design rule overrides khi có Figma

Khi design source là Figma với variables available, DESIGN-RULE override:
- **DESIGN-RULE-OVERRIDE-001**: color từ variable → confirmed (không estimate)
- **DESIGN-RULE-OVERRIDE-005**: dimension fixed → confirmed
- **DESIGN-RULE-OVERRIDE-007**: layout mode auto-layout → confirmed

Vẫn giữ không override: DESIGN-RULE-002 (không infer navigation), DESIGN-RULE-003 (chỉ states có variant), DESIGN-RULE-004 (ambiguous → candidates).

### Changed

- `skills/input-prepare-feature/SKILL.md` Phase P1 — route theo source type (local/confluence/figma) với adapter routing matrix.
- `skills/input-analyze-design/SKILL.md` — thêm Figma mode procedure (Step F1..F5): load structured contract trước, PNG cho visual confirm.
- `workflows/prepare-feature-brief.md` Phase P1 — entry conditions + input artifacts + adapter routing matrix + fetch notes documentation.
- `knowledge/input-analysis/screenshot-reading-rules.md` — section "Priority khi design source = Figma" nêu override rules.
- `verification/brief-schema/brief.schema.json` — thêm `fetch_notes` field (confluence_open_items, suspicious_content, remote_components), thêm `origin_metadata` field cho sourceEntry với page_id/version/file_key/has_variables/mcp_adapter.
- `AGENTS.md` — task routing +2 rows (Confluence, Figma fetch), file index refresh.

### Rationale

Trước v0.14: brief chỉ accept local markdown + screenshots. Team dùng Confluence cho spec + Figma cho design phải export manual rồi copy vào product repo → extra step, lose metadata (version, author, variables).

v0.14 bridge gap:
- **Metadata preservation**: Confluence version + author + Figma variables không mất khi fetch, cho downstream phân tích chính xác hơn (color confirmed từ variable thay vì estimate).
- **Deterministic re-fetch**: origin URI (`confluence://.../#v12`, `figma://file/key?node=1-2&version=ts`) + checksum → detect source drift automatic.
- **Permission guard**: Confluence read restriction check trước fetch, không bypass access control.
- **Instruction injection safe**: spec remote có thể chứa prompt injection; adapter flag suspicious pattern, không execute.

Key design decisions:
- **Adapter fetch-only**: không mix analyze + fetch; analyze thuộc Phase P2/P3. Thay source type (Confluence → Google Docs) không ảnh hưởng analysis logic.
- **MCP qua existing servers**: dùng `mcp-atlassian`, `framelink-figma`, `TalkToFigma` sẵn có. Không build custom integration.
- **Structured over image**: Figma có variables + node tree → authoritative. PNG chỉ fallback visual confirm.
- **Variables unlock confirmed**: design token từ Figma variable upgrade confidence `inferred` → `confirmed` thông qua override rules.
- **Live mode fallback**: Figma plugin workflow (TalkToFigma) chỉ khi file chưa publish version hoặc private.

### Migration from 0.13.0

Zero breaking change. v0.14 additive:
- Existing briefs với local source vẫn work.
- v0.13 brief không có `fetch_notes`, `origin_metadata` → vẫn validate pass (optional fields).
- Khi muốn dùng Confluence/Figma: specify source type trong input `input-prepare-feature`, orchestrator route tới adapter skill tương ứng.

**Usage examples**:

```
# Confluence spec + local design
Prompt: "Prepare feature brief cho book-detail từ confluence URL https://.../pages/123456/Book+Detail và local designs/book-detail/"

# Figma design + local spec
Prompt: "Prepare brief cho payment-flow với spec docs/specs/payment.md và Figma https://www.figma.com/design/<key>/?node-id=1-2"

# Confluence spec với attachments làm design
Prompt: "Prepare brief từ Confluence page 123456 với --design-source confluence-attachments --include-comments"

# Full remote
Prompt: "Prepare brief từ Confluence URL ... + Figma URL ..., include children + variables"
```

### Scope boundaries

- **IN scope v0.14**: Confluence (`mcp-atlassian`), Figma (`framelink-figma` + `TalkToFigma`), markdown normalization, image/variable export.
- **OUT scope (Wave 4+)**: Google Docs, Jira, PDF, OpenAPI adapters. Figma Code Connect. Multi-team profiles. TypeScript CLI.

## [0.13.0] — 2026-10-15

### Added — Input Layer (Markdown + Screenshot MVP)

Lớp chuẩn hóa spec + design nguồn thành Feature Brief package trước khi handoff vào `feature-development`. Upstream của mọi workflow build feature.

#### Skills (5)

- **`skills/input-prepare-feature/SKILL.md`** — orchestrator 5-phase pipeline (fetch → analyze spec → analyze design → reconcile → validate). Entry point duy nhất user gọi.
- **`skills/input-analyze-spec/SKILL.md`** — extract requirement + AC từ spec markdown, phân loại evidence_status (confirmed/inferred/unresolved).
- **`skills/input-analyze-design/SKILL.md`** — extract screen contract từ screenshots: components, states confirmed/missing, ambiguity, assets.
- **`skills/input-reconcile/SKILL.md`** — cross-reference spec + design, classify severity, resolve bằng project default hoặc tạo blocker.
- **`skills/input-validate-brief/SKILL.md`** — 12 quality gates (INPUT/SPEC/DESIGN/RECON/CONTRACT/HANDOFF), mark brief READY/BLOCKED/FAILED.

#### Agents (2)

- **`agents/input-analyst.md`** — role phân tích spec, extract requirement + AC, không viết code, không design UI chi tiết.
- **`agents/design-analyst.md`** — role đọc screenshot, extract screen contract, không claim design token exact, không infer navigation.

#### Workflow

- **`workflows/prepare-feature-brief.md`** — 5-phase pipeline với parallel P2+P3, blocker gate P4, 12-gate validation P5.

#### Blueprint

- **`blueprints/feature-brief/`** — package specification với README + 5 template files (brief.yaml, requirements.md, design.md, acceptance-criteria.md, issues.md).

#### Knowledge

- **`knowledge/input-analysis/requirement-extraction-rules.md`** — REQ-RULE-001..006, 8 anti-patterns, extraction procedure.
- **`knowledge/input-analysis/screenshot-reading-rules.md`** — DESIGN-RULE-001..012, 10 anti-patterns, reading procedure, edge cases.
- **`knowledge/input-analysis/reconciliation-matrix.md`** — issue type matrix, severity decision tree, 5 ví dụ resolution.

#### Verification

- **`verification/brief-schema/brief.schema.json`** — JSON Schema Draft 2020-12 validate brief.yaml. Conditional constraint: evidence_status=confirmed → source_references BẮT BUỘC non-empty với quote.
- **`verification/brief-schema/README.md`** — usage với jsonschema + check-jsonschema.

#### Output location

- **`briefs/`** — output directory. Mỗi feature 1 subfolder `briefs/<slug>/` chứa brief package + assets snapshot. Tách biệt với `plans/` (implementation plan).

### Changed

- `AGENTS.md`: task routing table thêm 5 rows cho input layer; workflows table thêm `prepare-feature-brief.md`; agent roles list thêm `input-analyst` + `design-analyst`; file index refresh.

### Rationale

Trước v0.13: downstream workflow (`feature-development`) đọc spec thô + screenshot adhoc, agent phải guess structure mỗi feature. Spec + design conflict không detect systematic → scope drift, missing requirement silent.

Input layer giải quyết:
- **Contract giữa input và execution**: `briefs/<slug>/brief.yaml` schema-validated, downstream biết chính xác input format.
- **Confidence tagging**: `evidence_status: confirmed/inferred/unresolved` → downstream biết tin cậy đến đâu, không treat suy luận như confirmed.
- **Blocker gating**: `issues[severity=blocker]` chặn implement start cho đến khi human review.
- **Traceability**: mọi requirement có source quote + checksum snapshot → detect spec drift.
- **Reusability**: 1 brief có thể feed nhiều downstream workflow (feature-dev, extract-sdk, parallel-features).

Key design decisions:
- **Pure markdown, không TypeScript CLI**: KISS, consistent với harness hiện tại. CLI chỉ cần khi Wave 3 có multi-source adapters (Confluence/Figma/Jira API).
- **Tích hợp vào harness, không tách repo**: 1 nguồn tiêu chuẩn, dễ discover. Tách repo chỉ khi cross-platform (iOS/BE) có pain point rõ.
- **Brief ≠ Plan**: tách `briefs/` (immutable input contract) khỏi `plans/` (mutable implementation strategy). Brief = what/why, Plan = how.
- **Phase P2 + P3 parallel-ready**: multi-agent spawn độc lập, merge P4.
- **Blocker gate strict**: không auto-pass qua blocker; `--force-handoff` require explicit user rationale.

### Migration from 0.12.0

Zero breaking change. Input layer là addition purely:
- Existing feature-development workflow vẫn work với spec adhoc (brief là optional).
- Khi muốn dùng brief: gọi `input-prepare-feature` trước, downstream Stage 1 Inspect đọc `briefs/<slug>/` thay cho spec gốc.

**Usage**:

```
Prompt: "Prepare feature brief cho book-detail từ docs/specs/book-detail.md + designs/book-detail/"
→ Skill input-prepare-feature orchestrate 5-phase → briefs/book-detail/
```

### Scope boundaries (MVP)

- **IN scope**: Markdown spec + Screenshot design
- **OUT scope (Wave 2)**: Multi-team profiles, JSON schema validation script
- **OUT scope (Wave 3)**: Confluence/Figma/Jira/PDF adapters, TypeScript CLI, Feature Store registry

## [0.12.0] — 2026-10-15

### Added — Harness Guardian (meta-agent)

Agent chuyên maintain + evolve chính harness. Khác với 5 roles khác (dùng harness để develop product), Guardian **phát triển harness itself**.

#### Agent role
- **`agents/harness-guardian.md`** — meta-agent với 3 modes (audit / maintain / evolve), 6 capability areas (knowledge audit, policy audit, skill maintenance, blueprint maintenance, evaluation, release management). Permission levels L0-L3 governance.

#### Skill
- **`skills/harness-maintenance/SKILL.md`** — 7-step lifecycle procedure cho harness maintenance với 3 modes execution.

#### Workflow
- **`workflows/harness-maintenance.md`** — 7-stage change lifecycle: signal → triage → impact → draft → validate → review → release.

#### Knowledge
- **`knowledge/harness-governance/essentials.md`** — permission levels L0-L3 + Protected Baseline (12 ADR cốt lõi) + infrastructure enforcement patterns.

### Changed
- `AGENTS.md`: task routing + workflows + agent roles + file index refresh cho Guardian additions.

### Rationale

ChatGPT "Harness Guardian" model (2026-10-15) đề xuất dedicated meta-agent maintain harness. Harness evolve liên tục (Kotlin/Android/Compose version bump, rule drift, skill improvement từ feedback) → cần Guardian dedicated prevent degrade.

Key design decisions:
- **Protected Baseline**: 12 ADR cốt lõi không được Guardian tự modify (require user approve L3)
- **No self-approve**: Guardian không approve own PR; independent reviewer required L2+
- **Infrastructure enforcement**: GitHub branch protection + CODEOWNERS + token scope, không chỉ prompt
- **Consolidated skill start**: 1 skill cover 6 capability areas; split khi evidence

### Migration from 0.11.0

Zero migration. Guardian là addition purely, không change existing rule/skill.

**Usage**: invoke explicit via prompt, không auto-trigger giữa product development.

```
Prompt: "Harness Guardian, audit mode: review knowledge/coroutines/essentials.md"
Prompt: "Harness Guardian, maintain mode: fix broken links"
Prompt: "Harness Guardian, evolve mode: propose rule cho pattern X"
```

## [0.11.0] — 2026-10-15

### Changed
- **ARCH-004** viết lại: Repository impl không kế thừa base class; API service trả `ApiResult<Dto>` qua `ApiResultCallAdapterFactory` (Retrofit), `ApiResultConverterFactory` (Ktorfit) hoặc `HttpClient.safeRequest` / `safeCall` (Ktor thuần). Rubric giữ severity HIGH.
- **CORO-002**: network suspend call không bọc `withContext(ioDispatcher)`; chỉ IO blocking thật (file, query DB đồng bộ) chuyển dispatcher tại local source.
- Knowledge, skills (`android-network`, `android-database`, `android-feature`, `android-coroutines`, `android-code-review`, `android-testing`), blueprints, agents, workflows cập nhật theo contract mới; bỏ hết hướng dẫn `BaseRepository` / `apiCall`.
- `evaluations/templates/e05-test-quality-audit.md`: expected rewrite chấm theo contract mới (Repository không nhận dispatcher, fake API trả `ApiResult`).

### Added
- `knowledge/data/network.md §ApiResult contract`: định nghĩa `ApiResult` + extension `map` / `flatMap` / `onSuccess` / `getOrNull`, `ErrorMapper` dùng chung (bảng mapping Ktor + Retrofit, timeout match trước `IOException`), snippet adapter/converter/helper kèm đăng ký builder, `CancellationException` luôn rethrow.
- `knowledge/data/network.md §Migration từ BaseRepository` + ranh giới lỗi local DB.
- Konsist template: `ARCH-004 repository impl does not extend base repository`, `ARCH-004 remote api suspend functions return ApiResult`.

**Breaking** (minor): product đang theo pattern `BaseRepository` + `apiCall` sẽ fail Konsist ARCH-004 sau khi update. Fix: làm theo `§Migration từ BaseRepository`, hoặc tạm disable ARCH-004 qua `rule_overrides` (kèm rationale).

### Rationale
Kế thừa base class chỉ để dùng chung error mapping gây coupling, và mỗi method phải tự bọc `apiCall` — quên bọc là exception thô lọt ra. Retrofit và Ktorfit có cơ chế chính thức để trả `ApiResult` ngay tầng network, nên mapping lỗi chỉ cần viết một lần.

## [0.10.2] — 2026-10-14

### Added
- **CONTRIBUTING.md** — guidelines cho external contributors: scope boundary (in/out upstream), dev setup, PR process, rule/skill contribution checklist, commit convention.

### Rationale
Public repo thiếu CONTRIBUTING → external contributor không rõ workflow. Add template giảm friction + align contribution style.

## [0.10.1] — 2026-10-14

### Added
- **LICENSE** — MIT License, clarify commercial + private use allowed.
- README license section updated.

### Rationale
Public repo without LICENSE file ambiguous về quyền sử dụng. MIT là standard cho tooling + lowest friction cho adopter.

## [0.10.0] — 2026-10-14

### Added — Factory stack pack (R1-R5)

Addresses ChatGPT "Android AI Development Factory" model: task contract chuẩn, multi-level build, auto-fix limit, failure classifier, model tier.

#### R-01 Task YAML contract
- **`blueprints/task-contract/template.yaml`** + **`README.md`** — standardized task schema v1 với fields: id, type, priority, scope, acceptance_criteria, execution (max_parallel_agents, max_fix_attempts, orchestration_mode), verification (4 levels), model_tier, delivery, dependencies, risks, open_questions.
- **`mehcli task validate --plan <path>`** subcommand: validate YAML schema (required fields, enum values, warn on runaway configs). Support YAML frontmatter trong markdown.

#### R-02 Multi-level build strategy
- **`knowledge/build-strategy/essentials.md`** — 4 levels: Fast checks (seconds), Targeted tests (minutes), APK + smoke (5-10 min), Regression (20+ min). Level selection decision tree, Gradle optimizations baseline, device lock pattern.

#### R-03 Auto-fix loop với fingerprint
- **`knowledge/auto-fix/essentials.md`** — Failure fingerprint (hash normalized stack), attempt tracking (`plans/<date>/fix-attempts.yaml`), progress detection, escalation path. Cap default 3, max 5 per task.
- **`workflows/fix-bug.md`** — new "Auto-fix loop" section với rules + escalation output template.
- **`agents/orchestrator.md`** — enforce `max_fix_attempts` + fingerprint check + classification routing.

#### R-04 Failure classifier
- **`skills/android-debug/SKILL.md`** — new "Failure classifier" section với 6 categories (build/code/test/device/infra/env), routing matrix per category, classification procedure với examples. Device/infra/env auto-escalate (user responsibility, not code fix).

#### R-05 Model tier routing
- **`knowledge/agent-orchestration/model-tier.md`** — 3 tiers (lite/balanced/deep), default routing per role, decision criteria, config override, cost estimation per task, multi-provider mapping (Claude/OpenAI/Google/local).

### Changed

- `overlay.schema.yaml`: thêm `orchestration.auto_fix.*` + `orchestration.model_tier.*` sections với inline guidance.
- `install.sh`: new `task` dispatcher subcommand với `validate` operation. Python-based schema validator.
- `AGENTS.md`: file index refresh for 5 new knowledge/blueprint files.

### Rationale

ChatGPT "Factory" model proposes 4 layers (content/orchestration/verification/infrastructure). Harness v0.9 cover ~60% core (content + orchestration). v0.10 fills gap trong orchestration (task contract, auto-fix limit) + verification (multi-level build) + runtime (model tier). Infrastructure layer (Maestro/device/VPS) remains out of harness scope — user integrates via CI tool chuyên.

### Migration from 0.9.0

Zero manual migration. New fields optional, backward compat preserved.

**New capability**: User có thể migrate plan.md free-form sang YAML contract gradually. Agent sẽ consume cả 2 format (YAML frontmatter trong markdown recommended cho hybrid).

### Usage examples

```bash
# Validate task before start
mehcli task validate --plan plans/FEAT-104.yaml

# Example output on invalid:
# ❌ Validation FAILED:
#   - ERROR: Missing REQUIRED field: acceptance_criteria
#   - ERROR: type 'xyz' invalid. Options: feature | bugfix | refactor | release | spike
```

## [0.9.0] — 2026-10-14

### Added — Agent orchestration pack

Harness switch cho 4 orchestration modes giải quyết use case "chạy 3-5 features song song từ spec":

#### Config
- **`overlay.yaml.orchestration.*`** fields: `mode` (single/team/parallel-features/auto), `parallel.max_concurrent`, `parallel.isolation`, `parallel.shared_file_strategy`, `auto_threshold.*`, `handoff.report_dir`.
- Install validates `orchestration.mode` enum.

#### Knowledge
- **`knowledge/agent-orchestration/essentials.md`** — comprehensive guide:
  - Mode comparison table (cost multiplier, latency, risk per mode)
  - Mode decision tree
  - Each mode's workflow + handoff doc protocol
  - Claude Code Task tool spawn patterns + tool subset per role
  - Parallel-features: isolation strategy, shared-file coordinator pattern
  - Cost/latency trade-off table
  - When NOT to use parallel-features

#### Skill
- **`skills/android-orchestrator/SKILL.md`** — procedure cho:
  - Mode resolution (Step 1-2)
  - Team mode sequential spawn (Step 3)
  - Parallel-features: spec decomposition + isolation check + batch spawn + aggregate + review (Step 4-9)
  - Parallel feature prompt template cho Task() tool
  - Tool subset table per role
  - Aggregator serial pattern cho shared files (DI/Nav/resources/analytics)

#### Workflow
- **`workflows/parallel-feature-development.md`** — 6-stage orchestration:
  1. Decompose (architect subagent)
  2. Isolation check (orchestrator)
  3. Spawn parallel (orchestrator + N implementer)
  4. Aggregate shared (orchestrator serial)
  5. Review (reviewer subagent với tool subset Read+Grep)
  6. Verify (gates)
  - Final report template với timing + cost + verdict

#### Agent roles
- **`agents/orchestrator.md`** — new role: mindset, scope, workflow, decision guides (team↔single escalation, retry policy), handoff validation rules, anti-patterns.
- **`agents/architect.md`** — add "Spec decomposition" section cho parallel-features mode: feature boundary heuristics, plan template, isolation-check.yaml spec.

### Changed
- `install.sh`: validate `orchestration.mode` + render 5 new placeholders.
- `AGENTS.md`: task routing + workflows table + agent roles section + file index refresh cho orchestration additions.
- `TemplateArchitectureRulesTest.kt`: no change (orchestration là meta-pattern, không ảnh hưởng rule check).

### Rationale

User case: build app mới cần 3-5 features từ spec cùng lúc. Single-threaded orchestration = slow wall-clock. Parallel orchestration = 2x speedup wall-clock với 3x token cost — ROI justified cho new product bootstrap.

Key design decision: **coordinator pattern** cho shared files. Subagent không edit shared file direct (race condition risk); emit merge instructions vào handoff doc, orchestrator aggregate serial. Pattern safe cho parallel + preserve architecture compliance.

### Migration from 0.8.0

**Zero manual migration**. Default `orchestration.mode: auto` — harness tự quyết dựa trên task size + feature count. Overlay cũ không có `orchestration` section vẫn work (fallback single/team).

### Usage example

```yaml
# overlay.yaml
orchestration:
  mode: parallel-features           # Explicit mode
  parallel:
    max_concurrent: 3
    isolation: feature-package
    shared_file_strategy: coordinator
```

Agent prompt: "Build features login + signup + forgot-password song song từ docs/specs/auth.md". Harness tự decompose → isolation check → spawn 3 Task subagent parallel → aggregate → review → verify.

## [0.8.0] — 2026-10-14

### Added — Flexibility pack (A + B + C)

#### A. Architecture profiles

- **`overlay.yaml` field `architecture.profile`** với 3 options:
  - `cmp` (Compose Multiplatform — default) — shared UI + logic qua expect/actual
  - `kmp` (Kotlin Multiplatform) — shared logic, native UI (SwiftUI iOS + Compose Android)
  - `android-only` (Jetpack Compose Android) — single platform
- **`knowledge/architecture/architecture-profiles.md`** — profile comparison, module layouts, migration paths, trade-offs.
- **Konsist test template** profile-aware: rule `ARCH-010` (platform SDK boundary) auto-skip khi `android-only` profile.

#### B. Rule overrides với rationale requirement

- **`overlay.yaml` field `rule_overrides`** — list rule override entries:
  ```yaml
  rule_overrides:
    - rule: ARCH-008
      severity: SHOULD        # downgrade từ MUST
      rationale: "..."         # REQUIRED ≥ 50 chars
    - rule: ARCH-007
      disabled: true
      rationale: "..."
  ```
- **Install-time validation**: `install.sh` reject overlay với rationale < 50 chars.
- **Konsist test** respect overrides via `disabledRules` set rendered từ overlay.
- Governance: human review rationale 1-2 lần đầu, AI trust sau (per user instruction).

#### C. Enforcement mode (strict / advisory)

- **`overlay.yaml` field `enforcement.mode`** — `strict` (default, fail CI) hoặc `advisory` (warn only).
- **`verify.sh`** respect mode: advisory → exit 0 với warning khi violation, không block CI.
- Use case advisory: new product migrate, evaluation phase, không ready enforce ngay.

### Changed

- `overlay.schema.yaml`: thêm `architecture.*`, `rule_overrides`, `enforcement.mode` sections với inline guidance.
- `install.sh`: validate 3 fields mới + render Konsist test + verify.sh với placeholders tương ứng. Propagate exit code từ Python validation.
- `TemplateArchitectureRulesTest.kt`: thêm `architectureProfile`, `disabledRules`, `appliesToProfile()`, `shouldRun()` helpers. Mỗi test method guard bằng `shouldRun("RULE-ID")`.
- `verify.sh.template`: thêm header show profile + enforcement mode + override count; conditional exit theo mode.
- `AGENTS.md`: file index thêm `architecture-profiles.md`.
- AudioBookApp overlay: thêm `architecture.profile: cmp` + `enforcement.mode: strict`.

### Rationale

Harness v0.7 CMP-centric nhưng rigid cho use case khác school (KMP native UI, Android-only). Flexibility pack cho phép:
1. Multi-profile support (3 archaeology schools) via `architecture.profile`
2. Rule deviation có governance (rationale required ≥ 50 chars)
3. Phased adoption (advisory mode cho migration period)

Flexibility hẹp + strict governance (rationale) = balance giữa rigid (safety) + freestyle (over-flexible defeat purpose).

### Migration from 0.7.0

**Zero manual migration** cho CMP products — default `architecture.profile: cmp` preserve current behavior. Overlay cũ không có field vẫn work.

**Breaking** (minor): overlay có `rule_overrides` nhưng rationale < 50 chars → install fail. Fix: expand rationale hoặc remove override.

## [0.7.0] — 2026-10-14

### Added — Multi-stack data layer support

Harness tách rõ data layer options theo target platform:

#### Networking
- **Retrofit** (Android-only) — full section trong `knowledge/data/network.md §Option 2`: setup, service interface annotation, OkHttp interceptor, auth + token refresh với `Authenticator`, error mapping `HttpException`, MockWebServer testing.
- **Ktor Client** (KMP/CMP) — section cũ renamed thành `§Option 1`.
- **Ktorfit** (KMP + annotation) — new section `§Option 3`: Retrofit-style interface + KMP support, Ktorfit builder, DX comparison.
- Decision guide: Android-only → Retrofit; KMP + annotation → Ktorfit; KMP manual → Ktor.
- Side-by-side comparison table.

#### Database
- **SQLDelight** (KMP + Android) — existing section.
- **Room** (Android native + KMP 2.7+) — new section trong `knowledge/data/persistence.md §Room patterns`: `@Entity`, `@Dao`, `@Database`, AutoMigration + manual Migration, `BundledSQLiteDriver` cho KMP, `@ConstructedBy` KMP generator.
- Decision guide: KMP → SQLDelight (mature); Android-only new → Room (Jetpack convention); existing Android migrate CMP → Room 2.7+.

### Changed

- `overlay.schema.yaml`: `stack.network` options rõ (`ktor` / `ktorfit` / `retrofit`); `stack.database` options rõ (`sqldelight` / `room` / `datastore` / `none`) với inline guidance comment.
- `skills/android-network/SKILL.md`: thêm "Lib selection" section; Step 2 "Define API service" tách variant A/B/C per lib.
- `skills/android-database/SKILL.md`: thêm "Lib selection" section; Step 1 "Design schema" tách variant A (SQLDelight) + B (Room).
- `README.md`: thêm "Stack options" table trong `Phạm vi áp dụng` section.

### Rationale

Harness ban đầu CMP-centric (Ktor + SQLDelight). User cần support cả Android-only (Retrofit + Room) + KMP (choice Ktor/Ktorfit, SQLDelight/Room). Expansion không duplicate — knowledge detail trong 1 file, skills cross-reference. Agent chọn snippet đúng dựa trên `stack.network` + `stack.database` trong `overlay.yaml`.

## [0.6.0] — 2026-10-14

### Added — P2 reference blueprint completion

#### Skills (3 more)
- **`skills/android-refactor/SKILL.md`** — Preserve-behavior refactor patterns: P-01 extract function, P-02 extract class, P-03 inline, P-04 move cross-layer, P-05 rename, P-06 split file, P-07 extract feature module. Pair với `workflows/refactor-module.md`.
- **`skills/android-debug/SKILL.md`** — Diagnose Android bugs: D-01 reproduce deterministic, D-02 isolate scope, D-03 logging/breakpoint, D-04 prove root cause, D-05 platform-specific (adb/Xcode), D-06 common bug patterns, D-07 coroutine debug, D-08 Compose recomposition debug.
- **`skills/android-performance/SKILL.md`** — Measure-first optimization: P-01 startup (baseline profile, lazy init), P-02 Compose recomposition, P-03 lazy list, P-04 memory, P-05 network, P-06 DB query, P-07 battery. SLO baseline table.

#### Blueprints (3 more)
- **`blueprints/compose-screen/README.md`** — standalone Compose screen pattern (route stateful + content stateless). Dùng khi feature đơn giản không warrant full feature stack.
- **`blueprints/repository/README.md`** — standalone Repository (domain interface + data impl với remote + local source + sync).
- **`blueprints/usecase/README.md`** — standalone UseCase (orchestrate multi-source, validation+action, Flow transformation). Decision tree "khi nào cần UseCase".

#### Knowledge (3 more domains)
- **`knowledge/patterns/common-patterns.md`** — Design patterns thực dùng trong Kotlin/Android (Factory, Builder DSL, Singleton via DI, Adapter, Facade, Decorator, Strategy, Observer via Flow, State sealed, Command via Intent, Chain of Responsibility). Patterns to AVOID. Rule: pattern chỉ áp dụng khi có problem cụ thể.
- **`knowledge/security/essentials.md`** — Threat model baseline + 10 security sections (SEC-01..10): secret storage (KeyStore/Keychain), network (TLS, cert pinning), PII, platform integrity, input validation, dependency security, WebView, backup, build config, analytics.
- **`knowledge/performance/essentials.md`** — SLO targets table + startup/Compose/memory/lazy list/network/DB/battery optimization patterns. Profiling workflow: measure → hypothesize → optimize → re-measure.

#### Evaluations (2 subfolders)
- **`evaluations/rubrics/README.md`** — Shared scoring rubric: score scale (90-100 → <40), dimension weights (default), severity classification per rule. Baseline vs harness comparison format.
- **`evaluations/regression/README.md`** — Trend tracking across harness versions + model variants. YAML record format, alert thresholds, model matrix.

#### Verification (1 subfolder)
- **`verification/lint/README.md`** — Android Lint setup + custom rule roadmap. Scaffold `lint.xml`, baseline strategy, Compose Lint rules, custom rule example skeleton. Hoãn custom rule tới khi evidence.

### Changed
- `AGENTS.md`: task routing + 3 new skills; file index refreshed cho tất cả P2 additions.

### Rationale
P2 completes the reference blueprint structural match: 11 skills (match reference), 5 blueprints (match reference), 5 workflows (match reference), knowledge covering all 7 reference domains (architecture + presentation gộp vào mvi/compose + coroutines + data + patterns + security + performance), full verification 3-tool stack (Konsist + Detekt + Lint), evaluations 3-subfolder (templates + rubrics + regression).

Harness upstream v0.6.0 ≈ 100% reference blueprint coverage. Chuyển sang evidence-driven refinement.

## [0.5.0] — 2026-10-14

### Added — P1 content catch-up

#### Skills
- **`skills/android-network/SKILL.md`** — Ktor Client integration: DTO + API service + mapper + Repository impl + MockEngine test. HttpClient config checklist, auth strategies, error mapping, retry policy.
- **`skills/android-database/SKILL.md`** — SQLDelight: schema design, DAO, migration, Flow queries, offline-first pattern, in-memory test driver.

#### Workflows
- **`workflows/refactor-module.md`** — 5-stage preserve-behavior refactor (baseline → plan → refactor → compare → verify). Golden rule: no observable behavior change.
- **`workflows/release-validation.md`** — 6-stage release candidate validation (preflight → build → smoke → artifact → regression → sign-off). Android APK + iOS XCFramework coverage.

#### Knowledge
- **`knowledge/data/repository-pattern.md`** — Interface in domain, impl in data; `ApiResult` return; offline-first; data source split; testing with Fake.
- **`knowledge/data/network.md`** — Ktor config essentials, JSON tolerant setup, auth strategies, error type mapping, platform engine via expect/actual.
- **`knowledge/data/persistence.md`** — SQLDelight / DataStore / filesystem / SecureStorage decision guide. Thread safety, lifecycle, testing.
- **`knowledge/data/caching.md`** — L1-L4 cache tier strategy, invalidation patterns, TTL guidance, size limits, common use cases.

#### Blueprints
- **`blueprints/network-service/README.md`** — standalone Ktor service pattern (`CatalogApi`): DTO, API, Mapper, Repository impl, DI binding, MockEngine tests. Dùng khi cần API cho feature không warrant full feature blueprint.

#### Verification
- **`verification/detekt/README.md`** — Detekt setup guide + custom rule roadmap. Enforces KOT (Kotlin conventions) + CORO (concurrency) rules.
- **`verification/detekt/detekt-config-template.yml`** — baseline config: `UnsafeCallOnNullableType`, `SwallowedException`, `GlobalCoroutineUsage`, `InjectDispatcher`, `LargeClass`, naming, complexity thresholds. Compose-friendly exclusions.

### Changed

- `AGENTS.md`: task routing + 2 new skills; workflows table + 2 new; file index refreshed.

### Rationale

P1 catches high-ROI gaps vs reference blueprint — add 2 skills covering API/DB (nearly every feature touches these), 2 workflows covering refactor + release (lifecycle gaps), knowledge/data (4 topics missing), and verification/detekt (second enforcement layer besides Konsist).

Still deferred (P2): 3 skills (`refactor`, `debug`, `performance`), additional blueprint splits, deep knowledge expansion (patterns, security, performance subfolders), evaluations/rubrics folder.

## [0.4.0] — 2026-10-14

### Added

- **`constitution/kotlin-conventions.md`** — 12 KOT rules (naming, null safety, immutability, visibility, sealed types, extensions, scope functions, exception handling, collection ops, resources, documentation).
- **`skills/android-coroutines/SKILL.md`** — dedicated procedure cho async/Flow/cancellation work; previously only knowledge/essentials.
- **`workflows/fix-bug.md`** — 5-stage: reproduce → isolate → cause → fix → verify. Cause-level fix discipline, không mask symptom.
- **`workflows/review-pull-request.md`** — PR audit workflow với 10 dimensions + evidence-based findings + severity levels.
- **`agents/`** folder — role prompts cho multi-agent orchestration:
  - `architect.md` — Plan + inspect, no code
  - `implementer.md` — Execute theo plan, minimal scope
  - `reviewer.md` — Independent audit, evidence-based
  - `test-engineer.md` — Behavior coverage, deterministic test

### Changed

- `AGENTS.md`: task routing table thêm `android-coroutines`; thêm "Workflows" + "Agent roles" sections; file index updated.

### Rationale

Fill P0 gap vs reference blueprint theo evidence-driven priority. Skip P1/P2 (6 skills khác, 20+ knowledge split files, 4 blueprints khác) để tránh YAGNI + context bloat.

## [0.3.0] — 2026-10-14

### Added

- **`bootstrap.sh`** — one-liner curl-pipe installer:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/huypqapero/mobile-engineering-harness/main/bootstrap.sh | bash
  ```
  Clones upstream vào `~/.mobile-engineering-harness/` + symlinks CLI thành `mehcli` ở `~/.local/bin/`.
  Supports: idempotent re-run, PATH check, pass-through subcommand (`bash -s init --project .`).
- **`self-update` subcommand**: `mehcli self-update` git pulls latest từ installed location.
- **`version` subcommand**: `mehcli version` prints tag + commit + upstream path.
- **Env vars** cho bootstrap: `MEH_INSTALL_DIR`, `MEH_BIN_DIR`, `MEH_REF` (pin specific tag).

### Changed

- README quickstart dùng one-liner install thay vì manual clone + symlink.
- Install script branding thành `mehcli` (giữ filename `install.sh` cho backward compat).

## [0.2.0] — 2026-10-14

### Added

- **`install.sh` CLI với 4 subcommands**: `init`, `install`, `update`, `uninstall`.
- **`init --project <path>`**: scaffold `.harness-overlay/` + copy schema template + create upstream symlink.
- **`uninstall --overlay <path>`**: remove rendered files (preserve `overlay.yaml`, `constitution/`, `blueprints/`, upstream symlink).
- **`uninstall --purge`**: nuke entire overlay directory with double confirm.
- **`update --overlay <path>`**: idempotent re-render alias cho `install`.
- **Flag `--dry-run`**: preview actions không execute.
- **Flag `--yes` / `-y`**: skip confirmation prompts cho CI.
- **Manifest tracking**: `.manifest.yaml` ghi rendered files + upstream commit + install time.
- **Auto-generated overlay `README.md`** liệt kê commands + agent resolution order.

### Changed

- `install.sh` refactor từ single-flow sang subcommand dispatcher.
- `install` command bây giờ ghi manifest + render thêm `README.md` cho overlay.

### Fixed

- Help text không leak `set -euo pipefail` ở cuối output (macOS BSD awk compat).

### Migration from 0.1.0

Overlay cũ không có `.manifest.yaml`. Chạy lại `install` sẽ auto-tạo manifest từ hardcoded list — không mất gì. `uninstall` fallback hardcoded list khi manifest missing.

## [0.1.0] — 2026-10-14

### Added

- Initial 2-layer harness.
- `constitution/` — 14 ARCH rules + 10 CORO rules + engineering principles + DoD.
- `knowledge/` — Clean+MVI, Compose, MVI, Coroutines essentials.
- `skills/` — 5 procedures (`android-feature`, `android-compose`, `android-mvi`, `android-code-review`, `android-testing`).
- `blueprints/reference-feature/` — generic `ItemCatalog` golden sample.
- `workflows/feature-development.md` — 5-stage orchestration.
- `verification/` — Konsist test template + `verify.sh` template.
- `evaluations/templates/` — 5 scenario templates.
- `install.sh` — simple render script với placeholder substitution.
