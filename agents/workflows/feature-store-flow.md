# Workflow: Feature Store Flow

Pipeline tạo & vận hành Feature Store artifact ở **repo riêng + publish artifact**, 2-module (`:core` + `:ui`), có UI + business flow, consume được bởi N product cùng harness.

## Mode

Workflow có 2 mode, chọn theo trigger:

- **Greenfield**: FS mới, chưa có code tồn tại (dùng skill `/feature-store-new`)
- **Extract**: tách feature từ product repo thành FS riêng (dùng skill `/feature-store-extract`)

## Trigger

Greenfield:
- User request "tạo feature store X dùng chung cho A/B/C"
- Harness Guardian đề xuất FS khi phát hiện pattern UI + flow duplicate giữa product
- Pilot điển hình: paywall-kit, chatbot-kit, onboarding-kit, kyc-kit, review-prompt-kit

Extract:
- User request "tách feature Y ở product A thành feature store riêng"
- Product B/C/D cần dùng lại UI + flow từ product A
- Feature đã ổn định ≥ 6 tháng, UI pattern stable

## Trigger check (bắt buộc, dừng nếu fail)

1. **FS có UI Compose consumer dùng được không?** Nếu không → downgrade SDK (dùng `library-flow`)
2. **Có business flow / state nghiệp vụ không?** Nếu không → consider shared-ui-component (hiếm)
3. **≥ 5 consumer** (real + straw-man persona). Dưới 5 → BLOCKED, downgrade feature thường trong app. Extract lift-and-shift có thể giãn xuống ≥ 2 real với justification scope hẹp.
4. Responsibility 1 câu không có "và"
5. (Extract) Boundary feature ổn định ≥ 6 tháng (UI/flow không bay)
6. **FS mindset acknowledged**: Feature Store Architect confirm đã đọc `knowledge/coding-feature-store/mindset.md [KB → team/arch-coding-feature-store, kb_search "coding feature store mindset"]` + commit tới 4 guarantee (Stability, Configurability, **Overridability**, Testability)

Fail bất kỳ → status BLOCKED, note lý do, không spawn pipeline.

## Diagram (greenfield)

```
user request
     │
     ▼
feature-store-architect  ──trigger check (3 Q + ≥ 5 consumer)──  (fail → BLOCKED/downgrade)
     │ pass
     ▼
Phase 0 — Brainstorm (10-step top-down + 2 FS extend)
  • brainstorm.md
  • use-case-matrix.md (3-axis, ≥ 15 use case)
  • straw-man-personas.md (≥ 5 persona)
  • backend-diversity-audit.md     (new vs library-flow)
  • design-system-diversity-audit.md (new vs library-flow)
  Gate: mental test 5 persona ≥ 4/5 GREEN + capability tuple locked
     │ pass
     ▼
Capability tuple decision (D?, U?, F?, S?, E?, L?)
     │
     ▼
FS-CONTRACT.md (6-trục YAML + override points + flow steps + breaking policy)
     + public-api-draft.md
     │
     ▼
API Freeze :core (interface + sealed + VM contract, BCV API dump commit)
     │
     ▼
Theme Freeze :ui (interface + CompositionLocal + Material3 adapter, BCV tolerant dump)
     │ (chỉ nếu U ≥ U1)
     ▼
architect  ──2-module layout + Konsist 6 rule──  module-layout.md
     │
     ▼
coder  ──implement core + ui──  code + unit test + testFixtures (fake + driver + previews)
     │
     ▼
reviewer (code quality)   feature-store-architect (API diff BCV + Konsist + override surface)
     │                           │
     └────────┬──────────────────┘
              ▼
         qa  ──scenario A-D matrix + screenshot test──  pass/fail
              │
              ▼
    publish pipeline (CI tag → sign → Maven, :core + :ui + :core-test-fixtures classifier)
              │
              ▼
    consumer product repo integrate (1 scenario A/B/C/D pilot)
```

## Diagram (extract)

```
user request + source product repo
     │
     ▼
feature-store-architect  ──trigger check──  (fail → BLOCKED)
     │ pass
     ▼
coding-scout  ──map coupling: UI theme, flow, data, resource──  scout-report.md
     │
     ▼
feature-store-architect  ──strategy decide──
     │
     ├─► lift-and-shift ─► copy UI + VM + rename theme bind + extract port
     │
     └─► clean-slate ───► Phase 0 Brainstorm full → rewrite theme + flow + API
     │
     ▼
extract-risk.md (UI theme coupling, flow coupling, resource prefix) + CR flow source product
     │
     ▼
architect → coder → reviewer + feature-store-architect → qa → publish
     │
     ▼
source product repo migrate (consume FS qua public API, drop old impl)
     │
     ▼
remove old internal feature module (sau 1 release safe)
```

## 12 stage + gate

### Stage 1 — Trigger validation (Feature Store Architect)

**Input**: user request + consumer list + capability sơ bộ

**Activity**:
1. Verify 3 Q scope lock: có UI? có flow? ≥ 5 consumer?
2. Verify responsibility 1 câu không "và"
3. (Extract) verify boundary ổn định ≥ 6 tháng
4. Confirm FS mindset acknowledged (`mindset.md` loaded, 4 guarantee commit)

**Output**: pass → tiếp Stage 1b; fail → BLOCKED note (hoặc downgrade sang SDK/feature thường)

**Gate**: không skip. Fail = dừng pipeline. Dưới 5 consumer = downgrade feature thường trong app.

---

### Stage 1b — Phase 0 Brainstorm (Feature Store Architect)

**Owner**: `feature-store-architect`

**Activity**: Chạy 10-step top-down theo `knowledge/coding-sdk/brainstorm-process.md [KB → team/arch-coding-sdk, kb_search "coding sdk brainstorm process"] §BRAIN-002` + extend FS:

1. Mission statement (1 câu không "và")
2. Non-goals (≥ 5)
3. Consumer personas (≥ 5, real + straw-man)
4-5. Use case inventory + matrix 3-axis (≥ 15 use case)
5.5. **Capability tuple candidate** `(D?, U?, F?, S?, E?, L?)` — decide sớm
6. Intersection audit + Cross-cutting lens
7. Scope decision (FS vs SDK vs feature thường)
8. **Backend diversity audit** (D1/D2/D3) — consumer backend đồng nhất Firebase hay mix REST/GraphQL?
9. **Design system diversity audit** (theme scope) — consumer chung Material 3 hay mỗi app brand?
10. Backward compat strategy

**Output** (tại `plans/<date>-<slug>/`):
- `brainstorm.md`
- `use-case-matrix.md`
- `straw-man-personas.md`
- `backend-diversity-audit.md`
- `design-system-diversity-audit.md`

**Gate**:
- [ ] Mission 1 câu không "và"
- [ ] Non-goals ≥ 5 có lý do
- [ ] Consumer persona ≥ 5
- [ ] Use case matrix ≥ 15 row, mỗi row tag đủ 3 trục
- [ ] Capability tuple candidate locked
- [ ] Backend diversity audit → D-level chọn rõ (D1/D2/D3)
- [ ] Design system audit → Theme Contract scope rõ
- [ ] Mental test 5 persona ≥ 4/5 GREEN

Fail bất kỳ → BLOCK Stage 3.

---

### Stage 2 — Coupling scout (chỉ extract mode)

**Owner**: `feature-store-architect` delegate `coding-scout`

**Input**: product repo nguồn + path feature tách

**Activity**: map
- Symbol phụ thuộc product concept
- Resource reference có namespace product (`R.string.product_a_*`, `R.drawable.product_a_*`)
- **Theme coupling**: Compose composable dùng `MaterialTheme.*` direct → sẽ convert sang Theme Contract
- **Flow coupling**: ViewModel + state machine có phụ thuộc product-specific logic → identify override step
- **Data coupling**: Repository/UseCase phụ thuộc backend endpoint cụ thể → chuyển sang port
- DI binding
- Analytics event name có prefix product → tách analytics port
- expect/actual bridge nếu KMP

**Output**: `plans/<date>-<slug>/scout-report.md` liệt kê:
- 100% public symbol feature tách + độ phụ thuộc
- Theme binding points (chỗ screen dùng `MaterialTheme` direct)
- Flow override candidate (step cần interceptor)
- Data port candidate (backend endpoint cần abstract)
- Resource namespace cần rename
- Anti-pattern từ `mindset.md §Anti-pattern`

**Gate**: scout cover 100% public symbol của feature tách + liệt kê đủ 4 coupling type (UI, flow, data, resource).

---

### Stage 3 — Capability Contract design (Feature Store Architect)

**Owner**: `feature-store-architect`

**Input**:
- Greenfield: requirement + Phase 0 artifact
- Extract: scout-report.md + source code + Phase 0 (clean-slate) hoặc minimal spec (lift-and-shift)

**Activity**:
1. Lock capability tuple `(D?, U?, F?, S?, E?, L?)` từ Phase 0
2. Draft `FS-CONTRACT.md` theo template `capability-contract.md §FS-CAP-003`:
   - YAML frontmatter 6-trục
   - `modules`: `[:core, :ui]`
   - `supported_adapters`: list adapter built-in
   - `optional_deps`: Gradle coordinate adapter deps
   - `override_points`: data_source, ui_slots, ui_full (VM expose), flow_interceptor, skip_step, theme_tokens
   - `flow_steps` (nếu F ≥ F1): id + skippable + anchor
   - `breaking_policy`: strict (core) / tolerant (ui) / semi-strict (theme)
3. Draft `public-api-draft.md`:
   - Port interface list
   - `FsConfig` class + helper functions (`firebaseSource`, `restSource`, `customSource`)
   - Facade `*Kit.create()`
   - VM + State + Intent + Effect (nếu U ≥ U3)
   - Flow step types + Interceptor (nếu F ≥ F2)
4. Draft `theme-contract.md` (nếu U ≥ U1):
   - `FsTheme` interface + sub-interface (Colors, Typography, Shapes)
   - CompositionLocal name
   - Material3 default adapter mapping
   - Token list + versioning policy
5. Draft `data-port.md`:
   - Port interface signature
   - Built-in adapter list + factory shape (`firebaseSource(...)`, `restSource(...)`)
   - compileOnly deps + classpath guard FQCN
6. Draft `flow-override.md` (nếu F ≥ F2):
   - Step list + skippable/anchor
   - Interceptor signature
   - State machine extensibility (nếu F3)
7. Extract: `extract-risk.md` + strategy (lift-and-shift / clean-slate)

**Output**:
- `plans/<date>-<slug>/fs-contract.md` (format giống `FS-CONTRACT.md` sẽ ship)
- `plans/<date>-<slug>/public-api-draft.md`
- `plans/<date>-<slug>/theme-contract.md` (nếu U ≥ U1)
- `plans/<date>-<slug>/data-port.md`
- `plans/<date>-<slug>/flow-override.md` (nếu F ≥ F2)
- `plans/<date>-<slug>/extract-risk.md` (extract mode)

**Gate** (Contract ready):
- [ ] Capability tuple 6-trục declare đủ
- [ ] Responsibility 1 câu
- [ ] Modules = 2 (`:core`, `:ui`), không hơn (hoặc justify RFC)
- [ ] Supported adapters ≥ 1
- [ ] Optional deps khớp `compileOnly` plan
- [ ] Override points đầy đủ cho tuple declared
- [ ] Flow steps có anchor (nếu F3)
- [ ] Breaking policy chốt per surface
- [ ] 4 guarantee check (Stability/Configurability/**Overridability**/Testability)
- [ ] Theme Contract có token list + Material3 adapter mapping (U ≥ U1)
- [ ] Dark mode mandatory (`isDark: Boolean`)

---

### Stage 3b — API Freeze :core (Feature Store Architect + Coder)

**Owner**: `feature-store-architect` lead, `coder` impl

**Activity**:
1. Code **chỉ** interface Port + sealed hierarchy + data class public + VM contract
2. **KHÔNG impl** nội dung (empty body hoặc `TODO()` placeholder)
3. Setup `binary-compatibility-validator` plugin trên `:core`
4. Chạy `./gradlew :core:apiDump`, commit `core/api/core.api`
5. Review mental 5 persona (từ `straw-man-personas.md`): persona N có plug được qua port + customSource/firebaseSource/restSource không?
6. Nếu persona N không plug được → quay lại Stage 3 refactor API

**Output**: Core API skeleton committed + `core/api/core.api`

**Gate**:
- [ ] `./gradlew :core:apiCheck` PASS
- [ ] API dump reflects contract
- [ ] Mental test 5 persona ≥ 4/5 GREEN
- [ ] Konsist Rule 1 (core không import Compose) PASS
- [ ] Konsist Rule 2 (core/data/* package convention) PASS

Fail → quay lại Stage 3.

---

### Stage 3c — Theme Freeze :ui (Feature Store Architect + Coder)

**Owner**: `feature-store-architect` lead, `coder` impl

**Chỉ chạy khi U ≥ U1.** Nếu U0 headless → skip stage này.

**Activity**:
1. Code `FsTheme` interface + sub-interface (Colors, Typography, Shapes) + `isDark` field
2. Code `LocalFsTheme: ProvidableCompositionLocal<FsTheme>`
3. Code `Material3FsAdapter` composable (default adapter, Material → FsTheme mapping)
4. Setup BCV `:ui` với tolerant policy (deprecation 1 minor)
5. `./gradlew :ui:apiDump`, commit `ui/api/ui.api`
6. Draft slot composable signature (nếu U ≥ U2):
   - Mỗi slot = `@Composable` param với default fallback
   - Document trong `theme-contract.md`

**Output**: Theme skeleton + `ui/api/ui.api`

**Gate**:
- [ ] `FsTheme.isDark` field present
- [ ] Light + Dark token value đầy đủ trong `Material3FsAdapter`
- [ ] Slot composable có default fallback
- [ ] `./gradlew :ui:apiCheck` PASS
- [ ] Konsist Rule 4 (screen không dùng `MaterialTheme.*` direct) PASS

Fail → quay lại Stage 3c refactor Theme.

---

### Stage 4 — CR flow với source product (chỉ extract mode)

**Owner**: `feature-store-architect` + `tech-lead` của source product

**Activity**:
1. Tạo CR tại source product `briefs/<slug>/change-requests/CR-fs-extract-<id>.md`
2. Impact assessment:
   - File nào trong product sẽ migrate (list)
   - Theme consumer app phải viết adapter mới
   - Resource rename plan (prefix `R.string.<fs>_*`)
   - Deadline migration
3. Source product owner (Tech Lead + PM) sign-off

**Output**: CR approved hoặc rejected (dừng extract)

**Gate**: không extract nếu source product không sign-off migration cost.

---

### Stage 5 — Module layout + impl plan (Architect)

**Owner**: `architect`

**Input**: `fs-contract.md` + API skeleton Stage 3b + Theme skeleton Stage 3c (+ scout-report nếu extract)

**Activity**:
1. Design Gradle 2 module theo `module-topology.md §FS-TOPO-001`:
   - `:core` (KMP hoặc Android lib tùy platform scope)
   - `:ui` (Android lib + Compose)
2. KMP sourceSet layout (commonMain / androidMain / iosMain) nếu KMP
3. Package convention:
   - `:core/api/`, `:core/data/<adapter>/`, `:core/internal/`
   - `:ui/theme/`, `:ui/components/`, `:ui/screens/`, `:ui/navigation/`, `:ui/preview/`
4. **Konsist rule setup** (6 rule, xem `module-topology.md §FS-TOPO-005`):
   - Rule 1: core không import Compose
   - Rule 2: core/data/* package convention
   - Rule 3: public class chỉ ở `api/` hoặc `data/<name>/`
   - Rule 4: ui screen không dùng `MaterialTheme.*` direct
   - Rule 5: ui không import core/internal
   - Rule 6: core không có Service Locator / global singleton object (chỉ Facade `*Kit`)
5. **Convention plugin** cho 2 module: `explicitApi` + BCV + Konsist + `java-test-fixtures` auto-apply
6. Compose version pin (BOM) ở `:ui`
7. Chọn impl pattern khớp capability tuple (ví dụ F3 → state machine extensible)
8. Test strategy:
   - `:core` unit test (JVM/common)
   - `:ui` screenshot test (Paparazzi/Roborazzi)
   - testFixtures setup

**Output**: `plans/<date>-<slug>/module-layout.md`

**Gate**:
- [ ] Module split = 2 (`:core`, `:ui`)
- [ ] Konsist 6 rule file list
- [ ] Mỗi public API trong Contract map tới impl file
- [ ] Test plan per module
- [ ] testFixtures source set scaffolded (`core/src/testFixtures/kotlin/`)
- [ ] Compose BOM version pin documented

---

### Stage 6 — Implementation (Coder)

**Owner**: `coder`

**Input**: `module-layout.md` + `fs-contract.md` + API skeleton + Theme skeleton

**Activity**:
1. Scaffold Gradle 2 module nếu FS mới (greenfield)
2. Setup `binary-compatibility-validator` + `java-test-fixtures` + Konsist plugin
3. Impl `:core`:
   - Public API theo contract (Config, Facade, VM, State)
   - Built-in adapter trong `data/<name>/`
   - `compileOnly` adapter SDK deps + `requireClasspath()` guard trong mỗi factory
   - Default no-op cho side-effect port (NoopAnalytics, etc.)
   - Flow state machine (nếu F ≥ F1), interceptor hook (F2), extensible state (F3)
   - Unit test cho mỗi public API path (happy + edge ≥ 2) + flow state transition
4. Impl `:ui` (nếu U ≥ U1):
   - `FsTheme` interface + `Material3FsAdapter`
   - Default screen composable
   - Slot composable (U2) + VM expose (U3)
   - Nav graph extension (nếu L2)
   - `@Preview` cho mỗi screen (≥ Light + Dark + 4 state)
5. Impl `testFixtures` trong `:core/src/testFixtures/kotlin/`:
   - FakeFsDataSource, FakeAnalytics, FakeClock, FakeAuth, FakeNav
   - FsTestDriver (nếu F ≥ F2)
   - Assertion helper
   - FsStatePreviewProvider (cho `:ui` import)
6. Setup Maven publish plugin + signing (greenfield)
7. Setup Paparazzi/Roborazzi cho `:ui` screenshot test

**Gate**:
- [ ] `./gradlew build` PASS
- [ ] `./gradlew :core:apiCheck` + `:ui:apiCheck` PASS
- [ ] Unit test PASS cho `:core`
- [ ] Screenshot test PASS cho `:ui`, coverage ≥ 8 snapshot/screen (4 state × 2 light-dark)
- [ ] Konsist 6 rule PASS
- [ ] Detekt PASS
- [ ] API dump file committed (`core/api/*.api`, `ui/api/*.api`)
- [ ] testFixtures artifact publish được qua Gradle (test local `./gradlew publishToMavenLocal`)

**Constraint**: Coder không được expand public API ngoài contract. Nếu cần → raise Feature Store Architect, không tự quyết.

---

### Stage 7 — Dual review (Reviewer + Feature Store Architect parallel)

**Owner**: `reviewer` + `feature-store-architect` chạy song song

**Reviewer (code quality)**:
- Code quality dòng-theo-dòng
- Error handling, null safety
- Test coverage touched code
- Hardcoded value, magic number
- Performance obvious

**Feature Store Architect (contract compliance)**:
- API diff (`:core/api/*.api` + `:ui/api/*.api`) match contract
- Konsist 6 rule PASS
- `compileOnly` adapter deps đúng
- Classpath guard mỗi factory
- Theme Contract không `MaterialTheme.*` leak vào screen
- Override surface đầy đủ (slot, VM, interceptor)
- testFixtures coverage đủ port
- Breaking change (nếu có) có RFC

**Output**: 2 review verdict (APPROVE / APPROVE_WITH_CHANGES / REQUEST_CHANGES)

**Gate**: cả 2 role APPROVE (hoặc APPROVE_WITH_CHANGES resolved) → tiếp Stage 8.

---

### Stage 8 — QA matrix (QA)

**Owner**: `qa`

**Activity**: Chạy 4 consumer scenario theo `module-topology.md §FS-TOPO-004`:

| Scenario | Modules | Backend | UI |
|---|---|---|---|
| A | core + ui + firebase dep | Firebase | Default |
| B | core + firebase dep | Firebase | Custom (từ VM) |
| C | core + ui | Custom port | Default |
| D | core | Custom port | Custom |

Mỗi scenario:
- Build smoke
- Integration test minimal (happy path)
- Screenshot verify (A, C)
- API usage verify (B, D consume VM đúng)

Thêm:
- testFixtures smoke test (import `testImplementation(testFixtures(...))` ở consumer sample)
- Theme adapter test (default `Material3FsAdapter` + 1 consumer custom)
- Flow interceptor test (nếu F ≥ F2)
- Anchor step test (nếu F3)

**Output**: `plans/<date>-<slug>/qa-report.md` matrix 4 scenario × test type

**Gate**:
- [ ] 4 scenario build PASS
- [ ] Screenshot diff ≤ threshold
- [ ] testFixtures smoke PASS
- [ ] Theme adapter test PASS
- [ ] Flow test PASS (nếu applicable)

---

### Stage 9 — Publish pipeline

**Owner**: `tech-lead` + CI

**Activity**:
1. Tag git `v0.1.0-alpha` (greenfield đầu) hoặc version theo SemVer
2. CI chạy:
   - Build release 2 module
   - Konsist + Detekt + BCV
   - Screenshot test
   - Sign artifact (GPG hoặc internal key)
   - Publish Maven: `:core`, `:ui`, `:core:test-fixtures` (classifier)
3. Verify published artifact ở internal Nexus hoặc Maven Central
4. Update CHANGELOG + README

**Gate**:
- [ ] CI pipeline PASS end-to-end
- [ ] Artifact pulled thành công ở consumer sample
- [ ] CHANGELOG entry đầy đủ (Added/Changed/Deprecated/Removed/Breaking)
- [ ] README root có capability tuple + modules + quick start 4 scenario

---

### Stage 10 — Consumer integration (pilot)

**Owner**: `coder` ở consumer product + `feature-store-architect` support

**Activity**:
1. Chọn 1 consumer scenario (A/B/C/D) làm pilot integrate
2. Add dep theo scenario
3. Wire `FsConfig` (source, theme, analytics, nav)
4. Verify screen render + flow run OK
5. Report back feedback → Feature Store Architect

**Gate**:
- [ ] Consumer app build + run OK
- [ ] Screen render đúng theme
- [ ] Flow happy path PASS
- [ ] Feedback captured

---

### Stage 11 — Source product migration (chỉ extract mode)

**Owner**: `coder` ở source product + `tech-lead` source product

**Activity**:
1. Source product consume FS artifact qua public API
2. Remove old internal feature module (hoặc giữ 1 release safe trước khi remove)
3. Migration guide document ở source product repo
4. Regression test source product PASS

**Gate**:
- [ ] Source product dùng FS artifact
- [ ] Old module removed (hoặc marked deprecated)
- [ ] Source product regression PASS

---

### Stage 12 — Iterate preview → GA

**Owner**: `feature-store-architect`

**Activity**:
1. Monitor consumer feedback trong `0.x-preview`
2. Breaking change tự do trong `0.x` nếu cần, mỗi lần CHANGELOG + migration note
3. Khi ≥ 3 consumer (hoặc đủ 3/5) sign-off API freeze → tag `1.0.0`
4. Sau `1.0.0`: breaking `:core` yêu cầu RFC + sign-off ≥ 3/5

**Gate release 1.0.0**:
- [ ] ≥ 3 consumer integrate OK ở production
- [ ] Validation checklist `essentials.md §Validation checklist` PASS
- [ ] Steward documented
- [ ] Deprecation policy published
- [ ] Governance channel setup (RFC repo, Slack/Discord, bug tracker)

---

## Artifact ownership

| Artifact | Owner primary | Reviewer |
|---|---|---|
| `brainstorm.md`, `use-case-matrix.md`, `straw-man-personas.md` | Feature Store Architect | Tech Lead (source product nếu extract) |
| `fs-contract.md` | Feature Store Architect | Consumer app lead ≥ 2 |
| `public-api-draft.md`, `theme-contract.md`, `data-port.md`, `flow-override.md` | Feature Store Architect | Reviewer |
| `module-layout.md` | Architect | Feature Store Architect |
| `scout-report.md` (extract) | coding-scout agent | Feature Store Architect |
| `extract-risk.md` (extract) | Feature Store Architect | Source product Tech Lead |
| `qa-report.md` | QA | Feature Store Architect |
| `FS-CONTRACT.md` (publish artifact root) | Feature Store Architect | Reviewer |
| README + CHANGELOG | Feature Store Architect | Tech Lead |

## Handoff rule

Mỗi stage sang stage sau phải có handoff doc tại `plans/handoff/<fs>/<from>-to-<to>.md`:

```markdown
# Handoff: <fs>
## Meta
From: <role> | To: <role> | Date: YYYY-MM-DD | Status: ready|blocked|needs-context
## Artifact delivered
- Path: <file> | Version: <n>
## Acceptance criteria met
- [x] <criteria>
## Open questions / Blocking issues
- <list>
```

Orchestrator chỉ cho tiếp stage sau khi handoff status = ready, acceptance check hết.

## Max retry + escalation

| Loop | Max retry | Escalate |
|---|---|---|
| Phase 0 Brainstorm (Stage 1b) ↔ Capability Contract (Stage 3) | 2 vòng | Tech Lead → cut scope hoặc downgrade |
| API Freeze (Stage 3b) ↔ Contract (Stage 3) | 2 vòng | Feature Store Architect raise user |
| Theme Freeze (Stage 3c) ↔ Theme Contract (Stage 3) | 2 vòng | Designer + Feature Store Architect co-design |
| Coder ↔ QA Scenario fail | 3 lần | Feature Store Architect re-plan |
| CR flow source product (Stage 4) | 2 vòng | PM nếu scope ảnh hưởng deadline source |
| Consumer sign-off (Stage 12 → 1.0) | — | Feature Store Architect + PM negotiate |

Vượt max → auto escalate, không retry thêm.

## Fast-path (không áp dụng cho FS)

Fast-path không áp dụng vì FS luôn multi-module + public API cross-consumer. Mọi FS task phải chạy đủ 12 stage (greenfield) hoặc 12 stage với Stage 2 + 4 + 11 extra (extract).

## Reference knowledge

- `knowledge/coding-feature-store/mindset.md [KB → team/arch-coding-feature-store, kb_search "coding feature store mindset"]` — ADR FS-001..007
- `knowledge/coding-feature-store/capability-contract.md [KB → team/arch-coding-feature-store, kb_search "coding feature store capability contract"]` — 6-trục YAML
- `knowledge/coding-feature-store/module-topology.md [KB → team/arch-coding-feature-store, kb_search "coding feature store module topology"]` — 2-module template + Konsist 6 rule
- `knowledge/coding-feature-store/data-port-runtime-config.md [KB → team/arch-coding-feature-store, kb_search "coding feature store data port runtime config"]` — Runtime Config pattern
- `knowledge/coding-feature-store/theme-adapter.md [KB → team/arch-coding-feature-store, kb_search "coding feature store theme adapter"]` — Theme Contract
- `knowledge/coding-feature-store/testing-kit.md [KB → team/arch-coding-feature-store, kb_search "coding feature store testing kit"]` — testFixtures
- `knowledge/coding-feature-store/essentials.md [KB → team/arch-coding-feature-store, kb_search "coding feature store essentials"]` — checklist rule cứng
- `knowledge/coding-sdk/brainstorm-process.md [KB → team/arch-coding-sdk, kb_search "coding sdk brainstorm process"]` — 10-step Phase 0 (dùng chung)
- `knowledge/coding-sdk/essentials.md [KB → team/arch-coding-sdk, kb_search "coding sdk essentials"]` — rule shared với SDK (BCV, deprecation, explicit API)

## Reference agent/skill

- `agents/feature-store-architect.md` — role lead pipeline
- `skills/feature-store-new/SKILL.md` — entry greenfield
- `skills/feature-store-extract/SKILL.md` — entry extract
- `agents/workflows/library-flow.md` — workflow sibling cho SDK pure (không UI)
