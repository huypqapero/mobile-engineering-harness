---
name: feature-store-new
description: Tạo Feature Store artifact mới (KMP/Android library có UI + business flow, 2-module topology core + ui, Runtime Config pattern cho adapter). Trigger khi user yêu cầu "tạo feature store X dùng chung cho A/B/C", "design kit UI/flow dùng chung nhiều app" (paywall, chatbot, onboarding, kyc). Spawn feature-store-architect agent dẫn pipeline FS-mindset-first (Phase 0 Brainstorm → Capability Contract → API + Theme + Flow → 2-module layout → testFixtures → Publish).
priority: P1
---

# Skill: feature-store-new

## Trigger

- "Tạo feature store X dùng chung cho A/B/C"
- "Design kit UI dùng chung nhiều app" (paywall, chatbot, onboarding, KYC, review-prompt)
- "Build shared flow Y publish Maven cho N consumer"
- "Design khung feature-store để tôi review"

**Không trigger khi**:
- **Không có UI** (headless infrastructure, API facade) → dùng `/library-new` (SDK pure)
- **Không có business flow** (chỉ UI component thuần) → dùng shared-ui-component (hiếm, considerconsider SDK UI lib)
- **< 5 consumer** (real + straw-man) → BLOCKED, downgrade feature thường trong app
- Chỉ 1 app ("sẽ có app thứ 2 sau") → BLOCKED, giữ trong app presenter
- Extract code từ product → dùng `/feature-store-extract` (TBD)

## Inputs

Bắt buộc:
- Tên FS (artifact id, kebab-case, không chứa tên product)
- Danh sách consumer: ≥ 2 real + straw-man persona lấp đủ ≥ 5 total
- Responsibility 1 câu (không "và")
- Capability sơ bộ: D?, U?, F?, S?, E?, L? (dùng decision tree `capability-contract.md §FS-CAP-002`)
- Platform scope: KMP common / androidMain / cần iosMain?
- **Design system consumer**: chung Material 3 hay mỗi app brand khác? (ảnh hưởng Theme Contract scope)
- **Backend consumer**: chung backend hay mix (Firebase, REST, GraphQL)? (ảnh hưởng D1/D2/D3)
- Publishing target: Maven Central / internal Nexus / GitHub Packages

Optional:
- Design reference nếu FS có API shape mong muốn
- Deadline
- Steward (owner FS dài hạn)

## Prerequisites

Đọc trước khi start (bắt buộc đầy đủ, không skim):

1. `knowledge/coding-feature-store/mindset.md [KB → team/arch-coding-feature-store, kb_search "coding feature store mindset"]` — ADR FS-001..007, foundation
2. `knowledge/coding-feature-store/capability-contract.md [KB → team/arch-coding-feature-store, kb_search "coding feature store capability contract"]` — 6-trục YAML + decision tree
3. `knowledge/coding-feature-store/module-topology.md [KB → team/arch-coding-feature-store, kb_search "coding feature store module topology"]` — 2-module template
4. `knowledge/coding-feature-store/data-port-runtime-config.md [KB → team/arch-coding-feature-store, kb_search "coding feature store data port runtime config"]` — Runtime Config pattern + compileOnly + classpath guard
5. `knowledge/coding-feature-store/theme-adapter.md [KB → team/arch-coding-feature-store, kb_search "coding feature store theme adapter"]` — Theme Contract (nếu U ≥ U1)
6. `knowledge/coding-feature-store/testing-kit.md [KB → team/arch-coding-feature-store, kb_search "coding feature store testing kit"]` — testFixtures mandatory
7. `knowledge/coding-feature-store/essentials.md [KB → team/arch-coding-feature-store, kb_search "coding feature store essentials"]` — checklist rule cứng
8. `knowledge/coding-sdk/sdk-mindset.md [KB → team/arch-coding-sdk, kb_search "coding sdk sdk mindset"]` — rule BCV/deprecation chung
9. `knowledge/coding-sdk/brainstorm-process.md [KB → team/arch-coding-sdk, kb_search "coding sdk brainstorm process"]` — 10-step Phase 0 (dùng chung)
10. `agents/feature-store-architect.md` — role mindset

Skip prerequisite → bias feature-first drift, mất 4 guarantee FS.

## Execution procedure

### Step 0 — Scope lock

Verify 3 câu hỏi trước khi spawn agent:
1. FS có UI Compose không? → nếu không, dùng `/library-new` thay vì skill này
2. Có business flow / state nghiệp vụ không? → nếu không, considerconsider shared-ui-component
3. ≥ 5 consumer (real + straw-man) không? → nếu không, BLOCKED, downgrade feature thường

Trả lời bất kỳ "không" → **STOP**, báo user chọn skill phù hợp.

### Step 1 — Phase 0 Brainstorm (Feature Store Architect)

Spawn `feature-store-architect` agent chạy 10-step top-down theo `knowledge/coding-sdk/brainstorm-process.md [KB → team/arch-coding-sdk, kb_search "coding sdk brainstorm process"] §BRAIN-002` + extend FS:

1. Mission statement (1 câu không "và")
2. Non-goals (≥ 5 item có lý do)
3. Consumer personas (≥ 5 real + straw-man)
4-5. Use case inventory + matrix 3-axis (≥ 15 use case)
5.5. **Capability tuple candidate** `(D?, U?, F?, S?, E?, L?)` — quyết định sớm
6. Intersection audit + Cross-cutting lens
7. Scope decision (FS vs SDK vs feature thường)
8. **Backend diversity audit** (D1/D2/D3)
9. **Design system diversity audit** (theme contract scope)
10. Backward compat

Output tại `plans/<date>-<slug>/`:
- `brainstorm.md`
- `use-case-matrix.md`
- `straw-man-personas.md`

**Gate**: thiếu 1/3 artifact → BLOCK Stage 2.

### Step 2 — Capability tuple decision

Agent lock tuple `(D?, U?, F?, S?, E?, L?)` qua decision tree. Document reasoning trong `brainstorm.md`.

### Step 3 — Capability Contract (FS-CONTRACT.md)

Agent draft `FS-CONTRACT.md` theo template `capability-contract.md §FS-CAP-003`:
- YAML frontmatter đầy đủ 6-trục
- `modules`, `supported_adapters`, `optional_deps`
- `override_points`, `flow_steps`, `breaking_policy`
- Owner (steward) + status (draft/preview/ga)

Review với stakeholders (ít nhất 2 consumer app lead) trước Stage 4.

### Step 4 — Public API draft

Agent draft public API cho 2 module:

**`:core`**:
- Port interface `FsDataSource` + port khác (nếu nhiều)
- `FsConfig` class + helper functions (`firebaseSource`, `restSource`, `customSource`)
- Facade `*Kit.create(block: FsConfig.() -> Unit): FsClient`
- `FsViewModel` + `FsState` + `FsIntent` + `FsEffect` (nếu U ≥ U3)
- Flow step types + `FsStepInterceptor` (nếu F ≥ F2)

**`:ui`** (nếu U ≥ U1):
- `FsTheme` interface + `LocalFsTheme` CompositionLocal
- `Material3FsAdapter` composable
- Public screen composable (slot API nếu U ≥ U2)
- Nav graph extension (nếu L2)

Document trong `plans/<date>-<slug>/public-api-draft.md`.

### Step 5 — Module layout + Gradle

Agent produce:
- `settings.gradle.kts` include `:core`, `:ui`
- `:core/build.gradle.kts` với `java-test-fixtures` + BCV + `compileOnly` adapter deps
- `:ui/build.gradle.kts` với Compose BOM + `api(project(":core"))`
- Package convention `com.<org>.<fs>.{api,data,internal}` + `com.<org>.<fs>.ui.{theme,components,screens,navigation,preview}`
- Konsist rules file (6 rule, xem `module-topology.md §FS-TOPO-005`)
- `.gitignore` + CI config outline

Document `plans/<date>-<slug>/module-layout.md`.

### Step 6 — testFixtures spec

Agent spec:
- Fake port list + behavior (`FakeFsDataSource`, `FakeAnalytics`, `FakeClock`, `FakeAuth`, `FakeNav`)
- TestDriver interface (nếu F ≥ F2): `FsTestDriver`
- Assertion helper list
- PreviewProvider cho mỗi screen (nếu U ≥ U1): `FsStatePreviewProvider`
- Screenshot test target: Paparazzi (ưu tiên JVM) hoặc Roborazzi, coverage ≥ 8 snapshot/screen (4 state × 2 light-dark)

Document `plans/<date>-<slug>/testing-kit-spec.md`.

### Step 7 — Handoff to Coder

Agent produce handoff doc `plans/handoff/<fs>/fs-architect-to-coder.md`:

```markdown
# Handoff: <fs-name> (Feature Store Architect → Coder)

## Meta
From: feature-store-architect | To: coder | Status: ready

## Deliverables
- FS-CONTRACT.md: <path>
- Public API draft: <path>
- Module layout: <path>
- Konsist rules: <path>
- testFixtures spec: <path>

## Capability tuple
D: ... | U: ... | F: ... | S: ... | E: ... | L: ...

## Acceptance criteria
- [ ] 2 module `:core` + `:ui`, Gradle setup đúng template
- [ ] Public API match draft, BCV `apiDump` committed
- [ ] `explicitApi()` enabled
- [ ] Konsist 6 rule pass
- [ ] `compileOnly` adapter deps + `requireClasspath()` guard
- [ ] Theme interface + Material3 default adapter (nếu U ≥ U1)
- [ ] testFixtures implement đầy đủ fake + driver + assertion
- [ ] PreviewProvider ship + screenshot test ≥ 8/screen pass CI
- [ ] README + CHANGELOG + FS-CONTRACT.md root artifact

## Open questions
- <list>
```

### Step 8 — Coder implement

Coder dùng handoff + load knowledge:
- `knowledge/coding-feature-store/*` (nếu cần tra rule)
- `knowledge/coding/clean-arch/*` (nếu FS expose domain concept)
- `knowledge/coding/compose/*` (nếu U ≥ U1)
- `knowledge/coding/mvi/*` (nếu U ≥ U3 expose VM)

Impl:
1. Gradle setup 2 module
2. Public API skeleton
3. Adapter trong `:core/data/<name>/`
4. Theme + default adapter (nếu có UI)
5. Default screens (nếu có UI)
6. testFixtures (fake + driver + assertion + PreviewProvider)
7. Konsist rules
8. BCV apiDump

### Step 9 — Reviewer + QA

- Reviewer: API diff review (`:core/api/*.api`, `:ui/api/*.api`), Konsist violation, breaking change scan
- QA: testFixtures coverage, screenshot test diff, consumer scenario smoke (A/B/C/D xem `module-topology.md §FS-TOPO-004`)

### Step 10 — Release 0.1.0-alpha

Validation checklist `knowledge/coding-feature-store/essentials.md [KB → team/arch-coding-feature-store, kb_search "coding feature store essentials"] §Validation checklist`:
- [ ] FS-CONTRACT.md đầy đủ
- [ ] 2-module topology
- [ ] BCV API dump
- [ ] `explicitApi()` enabled
- [ ] `compileOnly` adapter deps + classpath guard
- [ ] Konsist 6 rule pass
- [ ] Theme Contract (nếu U ≥ U1) + dark mode
- [ ] testFixtures đầy đủ
- [ ] PreviewProvider + screenshot test CI gate pass
- [ ] README + CHANGELOG + migration guide
- [ ] Steward documented

Pass tất cả → tag `0.1.0-alpha`, publish Nexus/Maven. Consumer integrate thử 1 app.

### Step 11 — Iterate preview → GA

Theo feedback consumer:
- `0.x-preview` ≥ 2 consumer integrate OK
- Breaking tự do trong `0.x`, mỗi lần có CHANGELOG + migration note
- `1.0.0` sau khi ít nhất 3/5 consumer sign-off API freeze

## Agent spawning

Spawn `feature-store-architect` subagent với prompt:

```
Role: feature-store-architect
Task: /feature-store-new cho <fs-name>
Working directory: <absolute path>
Inputs: <đầy đủ từ user>
Load knowledge:
- knowledge/coding-feature-store/*
- knowledge/coding-sdk/sdk-mindset.md [KB → team/arch-coding-sdk, kb_search "coding sdk sdk mindset"] + brainstorm-process.md + essentials.md
Rules: ~/.claude/rules/development-rules.md + review-audit-self-decision.md
Report path: plans/reports/
Plan dir: plans/<date>-<slug>/
Language: vi
```

## Quality gate (bắt buộc trước tuyên bố skill DONE)

1. 3 artifact Phase 0 Brainstorm trong `plans/<date>-<slug>/`
2. `FS-CONTRACT.md` draft với 6-trục đầy đủ
3. Public API draft `:core` + `:ui`
4. Module layout spec + Konsist rules
5. testFixtures spec
6. Handoff doc `plans/handoff/<fs>/fs-architect-to-coder.md`

Thiếu 1 → không DONE.

## Report format

Cuối pipeline, tạo `plans/reports/feature-store-new-<date>-<slug>.md`:

```markdown
# Feature Store: <name>

## Outcome
<capability tuple + modules + status>

## Deliverables
- FS-CONTRACT.md: <path>
- Brainstorm: <path>
- Public API draft: <path>
- Module layout: <path>
- Testing kit spec: <path>
- Handoff: <path>

## Decisions locked
- D: ... (lý do)
- U: ... (lý do)
- F: ... (lý do)
- Backend adapter: [...]
- Theme contract: [...]

## Next step
- Coder impl (handoff ready)
- Target 0.1.0-alpha: <date>

## Unresolved questions
- <list>
```

## Rules

- Luôn chạy Scope lock Stage 0 trước spawn agent. Fail → block.
- Luôn chạy Phase 0 Brainstorm trước Capability Contract.
- Luôn verify 2-module topology, không chấp nhận 3+ module trừ RFC đặc biệt.
- Luôn verify `compileOnly` adapter deps.
- Theme Contract mandatory nếu U ≥ U1.
- testFixtures mandatory trước release 1.0.
- Breaking change `:core` yêu cầu RFC + sign-off ≥ 3/5.

## Reference

- Agent: `agents/feature-store-architect.md`
- Knowledge: `knowledge/coding-feature-store/` (6 file)
- Shared SDK knowledge: `knowledge/coding-sdk/` (BCV, brainstorm process, essentials chung)
- Sibling skill: `skills/library-new/SKILL.md` (SDK pure infra, không UI)
