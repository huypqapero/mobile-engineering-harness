# Changelog

Tất cả thay đổi đáng chú ý của Mobile Engineering Harness.

Format tuân theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) và semver.

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
