---
name: feature-store-extract
description: Tách feature đã tồn tại trong 1 product (có UI + flow + business logic) thành Feature Store artifact riêng, 2-module topology (core + ui), publish ở repo riêng cho ≥ 5 consumer. Trigger khi feature đã ổn định ≥ 6 tháng ở 1 product repo và cần dùng chung ở ≥ 2 product khác. Scout coupling (UI theme, flow, data, resource) → chọn strategy lift-and-shift vs clean-slate → extract + migrate source product.
priority: P1
---

# Skill: feature-store-extract

## Trigger

- "Tách feature Y ở product A thành feature store riêng"
- "Product B/C/D cần dùng lại UI + flow của feature Y, extract thành shared"
- "Move <feature-with-UI-and-flow> sang shared feature store"

**Không trigger khi**:
- Feature **không có UI** (headless, chỉ data/logic) → dùng `/library-extract` (SDK pure)
- Feature **không có business flow** (chỉ UI component thuần) → consider shared-ui-component
- Chỉ 1 consumer sử dụng → giữ ở product
- Boundary feature chưa ổn định (< 6 tháng, UI/flow đang bay) → chờ settle
- Feature tạo mới chưa có code trong product → dùng `/feature-store-new`

## Inputs

Bắt buộc:
- Product repo nguồn + path feature sẽ extract (ví dụ `product-a/presenter/paywall/`)
- Danh sách ≥ 2 consumer thật cam kết migrate + lấp đủ ≥ 5 total với straw-man
- Lý do extract (business + technical)
- Target repo FS (đã có hay cần tạo mới)
- **Design system diversity**: consumer đã dùng Material 3 chung hay mỗi app brand khác? (ảnh hưởng Theme Contract scope)
- **Backend diversity**: consumer chung backend với source product hay backend khác? (ảnh hưởng D1/D2/D3)

Optional:
- Deadline migration source product
- Steward FS dài hạn

## Prerequisites

Đọc trước khi start (FS knowledge set — bắt buộc đầy đủ, không skim):

1. `knowledge/coding-feature-store/mindset.md [KB → develop/feature-store, kb_search "coding feature store mindset"]` — ADR FS-001..007
2. `knowledge/coding-feature-store/capability-contract.md [KB → develop/feature-store, kb_search "coding feature store capability contract"]` — 6-trục + decision tree
3. `knowledge/coding-feature-store/module-topology.md [KB → develop/feature-store, kb_search "coding feature store module topology"]` — 2-module template (classify code hiện tại fit layer nào)
4. `knowledge/coding-feature-store/data-port-runtime-config.md [KB → develop/feature-store, kb_search "coding feature store data port runtime config"]` — Runtime Config pattern (identify adapter candidate)
5. `knowledge/coding-feature-store/theme-adapter.md [KB → develop/feature-store, kb_search "coding feature store theme adapter"]` — Theme Contract (identify UI theme coupling cần chuyển)
6. `knowledge/coding-feature-store/testing-kit.md [KB → develop/feature-store, kb_search "coding feature store testing kit"]` — testFixtures
7. `knowledge/coding-feature-store/essentials.md [KB → develop/feature-store, kb_search "coding feature store essentials"]`
8. `knowledge/coding-sdk/brainstorm-process.md [KB → develop/sdk, kb_search "coding sdk brainstorm process"]` — Phase 0 nếu clean-slate
9. `knowledge/coding-sdk/sdk-mindset.md [KB → develop/sdk, kb_search "coding sdk sdk mindset"]` — rule BCV chung
10. `agents/feature-store-architect.md` — role lead
11. `agents/workflows/feature-store-flow.md` — pipeline 12 stage
12. `skills/coding-scout/SKILL.md` — dùng cho map coupling

Skip prerequisite → bias feature-first drift, mất 4 guarantee FS.

## Execution procedure

### Step 1 — Scope lock + Trigger validation

Verify 6 gate:

1. **FS có UI Compose consumer dùng được không?** Nếu không → downgrade dùng `/library-extract`
2. **Có business flow / state nghiệp vụ không?** Nếu không → consider shared-ui-component
3. **≥ 5 consumer** (real + straw-man) cho **clean-slate mode**, hoặc **≥ 2 real consumer** cho **lift-and-shift mode** với justification scope hẹp
4. Boundary feature ổn định ≥ 6 tháng (UI pattern không bay, flow stable, không có refactor lớn gần đây)
5. Responsibility 1 câu không "và"
6. FS mindset acknowledged (`mindset.md` loaded, 4 guarantee commit)

Fail bất kỳ → **STOP**, báo user chọn skill phù hợp.

### Step 2 — Scout coupling + classify (coding-scout)

Delegate `coding-scout` tại product repo nguồn. Scan 5 nhóm coupling:

#### 2.1 UI theme coupling
- Composable dùng `MaterialTheme.*` direct (candidate convert sang Theme Contract)
- Composable dùng `colorResource(R.color.product_a_*)` (candidate rename hoặc port)
- Icon/illustration bind product resource (candidate slot override)
- Hardcoded color/font/dimension trong Compose (candidate extract token)

#### 2.2 Flow coupling
- ViewModel + state machine có logic product-specific (candidate interceptor)
- Navigation route hardcode product name (candidate rename hoặc deep link param)
- Step order có assume product business rule (candidate anchor + skip whitelist)

#### 2.3 Data coupling
- Repository/UseCase bind backend endpoint cụ thể (candidate port)
- Firebase/REST client config bind product account (candidate adapter helper)
- Analytics event prefix product (candidate rename hoặc analytics port)

#### 2.4 Resource coupling
- `R.string.product_a_*` namespace (candidate rename `R.string.<fs>_*`)
- `R.drawable.product_a_*` namespace
- `R.raw.*` audio/video asset

#### 2.5 Dependency coupling
- DI binding sang Koin/Hilt module product
- expect/actual bridge nếu KMP
- Transitive dep qua product shared util

**Classify theo capability tuple** (FS target):

- Data layer code hiện tại → D1 (owned backend) hay D3 (headless, port)?
- UI layer code → U1 (chỉ theme) hay U2 (có slot) hay U3 (expose VM)?
- Flow layer → F0 (single screen), F1 (fixed), F2 (interceptor + skip), hay F3 (extensible)?
- State → S0/S1/S2/S3?
- Lifecycle → L0/L1/L2/L3?

**Output**: `plans/<date>-<slug>/scout-report.md` liệt kê:
- 100% public symbol feature tách + độ phụ thuộc
- 5 coupling nhóm với file + LOC + severity (low/med/high)
- Capability tuple suggest cho FS target
- Theme binding points (chỗ `MaterialTheme.*` direct)
- Flow override candidate (step cần interceptor)
- Data port candidate (endpoint cần abstract)
- Resource namespace cần rename
- Anti-pattern cần refactor (từ `mindset.md §Anti-pattern cấm cứng`)

### Step 3 — Decide extract strategy

Spawn `feature-store-architect` recommend strategy:

**Lift-and-shift** nếu:
- 2 real consumer, UI pattern hiện tại acceptable cho cả 2
- Cần ship < 3 tuần
- Coupling cắt được bằng rename resource + extract 1 port (data)
- Design system 2 consumer **giống nhau** (cùng Material 3 token chuẩn)
- Backend 2 consumer **giống nhau** (chung Firebase hoặc chung REST endpoint)
- Không cần override flow step (F0 hoặc F1 fit)

**Clean-slate** nếu:
- ≥ 3 real consumer (hoặc đủ 5 total với straw-man)
- UI theme bind product-specific nặng → cần Theme Contract đầy đủ
- Backend consumer khác nhau → cần D3 port + ≥ 2 adapter built-in
- Flow consumer khác nhau → cần F2 interceptor + skip hoặc F3 extensible
- Code hiện tại có inheritance extension / God Config / Singleton object → refactor nặng
- FS sẽ phục vụ > 5 consumer roadmap

User confirm strategy trước Step 4.

Lift-and-shift chọn → chấp nhận FS không có Theme Contract đầy đủ (chỉ default Material3 adapter), chỉ 1 built-in adapter data, không có flow interceptor. Nhưng vẫn phải có:
- 2-module topology (`:core` + `:ui`)
- `FsTheme` interface tối thiểu (dù chỉ map Material3 1:1)
- `FsDataSource` port (dù chỉ 1 adapter)
- testFixtures mandatory

### Step 4 — Phase 0 Brainstorm (chỉ clean-slate)

Spawn `feature-store-architect` chạy Phase 0 đầy đủ như `/feature-store-new` Step 1:

1-10. Full 10-step + 2 FS extend (backend-diversity + design-system-diversity audit)

Output tại `plans/<date>-<slug>/`:
- `brainstorm.md`
- `use-case-matrix.md`
- `straw-man-personas.md`
- `backend-diversity-audit.md`
- `design-system-diversity-audit.md`

Gate Phase 0 pass trước Step 5.

**Lift-and-shift skip** Phase 0 full, chỉ cần:
- Non-goals explicit ≥ 3
- Capability tuple suggest từ scout report
- 2 consumer sign-off capability tuple

### Step 5 — Draft Capability Contract + Extract Risk

Agent produce:

**Capability Contract** (`fs-contract.md`) theo `capability-contract.md §FS-CAP-003`:
- 6-trục YAML đầy đủ
- Modules `[:core, :ui]`
- Supported adapters list
- Override points, flow steps, breaking policy

**Public API draft** (`public-api-draft.md`):
- Port interface từ scout coupling data
- Config helper (`firebaseSource`, `restSource`, `customSource`)
- VM expose nếu U ≥ U3
- Flow interceptor nếu F ≥ F2

**Theme Contract** (`theme-contract.md`) nếu U ≥ U1:
- `FsTheme` interface + sub-interface
- Material3 default adapter mapping (từ pattern Material3 hiện tại trong product)
- Token list extract từ scout UI theme coupling

**Data Port** (`data-port.md`):
- Port interface signature từ Repository hiện tại
- Built-in adapter list (ít nhất lift source product backend adapter)
- compileOnly deps + classpath guard FQCN

**Flow Override** (`flow-override.md`) nếu F ≥ F2:
- Step list từ ViewModel hiện tại
- Interceptor signature
- Skip whitelist
- Anchor step (F3)

**Extract Risk** (`extract-risk.md`):
- UI theme coupling cần cắt + migration cost
- Flow coupling cần cắt
- Data port abstraction cost
- Resource rename plan (`R.string.product_a_*` → `R.string.<fs>_*`)
- Anti-pattern refactor list (Singleton → Facade, God Config → split, inheritance → SPI)
- Migration cost source product (LOC estimate, deadline)

Gate: contract pass, risk assessed, Phase 0 gate pass (clean-slate).

### Step 6 — CR flow với source product

Tạo CR tại source product repo:
- `briefs/<slug>/change-requests/CR-fs-extract-<id>.md`

Nội dung CR:
- Feature extract scope
- File source product sẽ migrate (list từ scout)
- Resource rename plan
- Theme adapter consumer app phải viết (nếu brand khác source product theme)
- Breaking change source product (nếu có, document migration path)
- Migration cost estimate (LOC + deadline)

Source product owner (Tech Lead + PM) sign-off:
- Chấp nhận migration cost
- Deadline migrate OK
- Không có concern breaking workflow source product

Gate: không extract nếu source product không sign-off.

### Step 7 — Module layout (Architect)

Spawn `architect` theo pipeline Stage 5 trong `agents/workflows/feature-store-flow.md`:
- 2-module `:core` + `:ui`
- Konsist 6 rule
- Gradle convention plugin (BCV + `java-test-fixtures` + explicitApi + Konsist)
- Compose BOM pin ở `:ui`
- Package convention

Output: `module-layout.md`.

### Step 8 — Implementation (Coder)

Spawn `coder` theo Stage 6:

**Lift-and-shift flow**:
1. Copy source code từ product → `:core/internal/` (impl) + `:ui/screens/` (UI)
2. Rename package `com.product-a.feature.X.*` → `com.<org>.<fs>.*`
3. Rename resource `R.string.product_a_*` → `R.string.<fs>_*`
4. Extract 1 Port (data) từ Repository hiện tại
5. Build `FsConfig` + Facade `*Kit.create()` wrapper
6. Convert `MaterialTheme.*` direct → `FsTheme` interface + Material3 1:1 adapter
7. Impl testFixtures tối thiểu (fake data port + preview provider)
8. BCV apiDump

**Clean-slate flow**:
1. Scaffold Gradle 2 module từ đầu
2. Impl API theo contract (không copy nguyên source product)
3. Impl adapter built-in trong `data/<name>/` (compileOnly deps + classpath guard)
4. Impl Theme Contract + Material3 default adapter + consumer adapter guide
5. Impl flow state machine với interceptor hook (F2) hoặc extensible (F3)
6. Impl default UI từ zero (lấy inspiration từ source product nhưng không copy direct)
7. Impl testFixtures đầy đủ (fake + driver + assertion + preview)
8. BCV apiDump cả `:core` + `:ui`

Gate: như Stage 6 trong `feature-store-flow.md`.

### Step 9 — Dual review + QA matrix

Theo Stage 7 + 8 trong `feature-store-flow.md`:
- Reviewer (code quality) + Feature Store Architect (contract compliance) parallel
- QA matrix 4 scenario (A/B/C/D) + screenshot test ≥ 8 snapshot/screen

### Step 10 — Publish + Source product migration

Publish FS artifact theo Stage 9. Rồi migrate source product theo Stage 11:
1. Source product consume FS artifact qua public API
2. Remove old internal module (hoặc deprecated 1 release safe)
3. Migration guide ở source product repo
4. Regression test source product PASS

Gate: source product build + run OK với FS artifact. Old module removed hoặc marked deprecated.

### Step 11 — Iterate preview → GA

Theo Stage 12 trong `feature-store-flow.md`:
- `0.x-preview` ≥ 2 consumer integrate
- Breaking tự do trong `0.x`
- `1.0.0` khi ≥ 3/5 consumer sign-off

## Agent spawning

Spawn `feature-store-architect` subagent với prompt:

```
Role: feature-store-architect (extract mode)
Task: /feature-store-extract từ <source-product-path> → <fs-name>
Working directory: <absolute path>
Inputs:
  - Source product repo: <path>
  - Feature path: <path>
  - Consumer list: <≥ 2 real + straw-man ≥ 5>
  - Design system diversity: <same|different>
  - Backend diversity: <same|different>
  - Strategy preference: <lift-and-shift|clean-slate|auto-recommend>
Load knowledge:
  - knowledge/coding-feature-store/* (7 file)
  - knowledge/coding-sdk/sdk-mindset.md [KB → develop/sdk, kb_search "coding sdk sdk mindset"] + brainstorm-process.md + essentials.md
Rules: ~/.claude/rules/development-rules.md + review-audit-self-decision.md
Report path: plans/reports/
Plan dir: plans/<date>-<slug>/
Language: vi
```

## Quality gate (bắt buộc trước tuyên bố skill DONE)

1. `scout-report.md` cover 5 coupling nhóm, 100% public symbol
2. Strategy decision (lift-and-shift / clean-slate) với justification
3. Phase 0 artifacts (clean-slate) hoặc minimal spec (lift-and-shift)
4. `fs-contract.md` với 6-trục đầy đủ
5. `public-api-draft.md`, `theme-contract.md` (nếu U ≥ U1), `data-port.md`
6. `extract-risk.md` + CR source product approved
7. `module-layout.md`
8. Handoff doc `plans/handoff/<fs>/fs-architect-to-coder.md`

Thiếu 1 → không DONE.

## Report format

Cuối pipeline, tạo `plans/reports/feature-store-extract-<date>-<slug>.md`:

```markdown
# Feature Store Extract: <name>

## Source
Source product: <repo + path>
Extract strategy: <lift-and-shift | clean-slate>
Justification: <lý do>

## Outcome
Capability tuple: D? U? F? S? E? L?
Modules: :core + :ui
Status: 0.1.0-alpha publish OK | source product migrated

## Deliverables
- Scout report: <path>
- Phase 0 (nếu clean-slate): <paths>
- FS-CONTRACT.md: <path>
- Public API draft: <path>
- Theme contract: <path>
- Data port: <path>
- Extract risk: <path>
- Module layout: <path>
- CR source product: <id + status>

## Migration summary
- Source product LOC migrated: <N>
- Resource rename: <count>
- Theme adapter consumer apps need: <list>
- Breaking source product: <yes/no + migration path>

## Decisions locked
- D: ... (lý do)
- U: ... (lý do)
- F: ... (lý do)
- Backend adapter: [...]
- Theme contract: [...]

## Next step
- Coder impl (handoff ready)
- Target 0.1.0-alpha: <date>
- Source product migrate deadline: <date>

## Unresolved questions
- <list>
```

## Rules

- Luôn chạy Scope lock Step 1 trước. Fail → block.
- Luôn chạy Scout Step 2 với 5 coupling nhóm trước strategy decide.
- Clean-slate luôn chạy Phase 0 full. Lift-and-shift skip Phase 0 nhưng vẫn phải có capability tuple.
- CR source product mandatory, không extract nếu không sign-off.
- 2-module topology mandatory. Không chấp nhận 3+ module trừ RFC đặc biệt.
- `compileOnly` adapter deps mandatory nếu có adapter built-in.
- Theme Contract mandatory nếu U ≥ U1 (dù lift-and-shift chỉ map Material3 1:1).
- testFixtures mandatory trước release 1.0.
- Breaking change source product (hiếm) phải có migration guide + deadline.

## Reference

- Agent: `agents/feature-store-architect.md`
- Workflow pipeline: `agents/workflows/feature-store-flow.md` (12 stage)
- Knowledge: `knowledge/coding-feature-store/` (7 file)
- Shared SDK knowledge: `knowledge/coding-sdk/` (BCV, brainstorm, essentials chung)
- Sibling skill: `skills/feature-store-new/SKILL.md` (greenfield)
- Sibling skill: `skills/library-extract/SKILL.md` (SDK pure headless extract)
