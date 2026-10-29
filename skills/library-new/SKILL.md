---
name: library-new
description: Tạo SDK publish artifact (KMP/Android lib) mới ở repo riêng. Trigger khi user yêu cầu "tạo lib X dùng chung cho A và B" hoặc "design SDK cho ...". Spawn library-architect agent dẫn pipeline SDK-mindset-first (Phase 0 Brainstorm → Contract → SPI Freeze → Impl → TestingKit → Publish).
priority: P1
---

# Skill: library-new

## Trigger

- "Tạo lib X dùng chung cho A và B"
- "Build shared library / SDK cho ..."
- "Setup repo lib Y publish lên Maven Central"
- "Design SDK cho ..." / "Design khung SDK để tôi review"

**Không trigger khi**:
- **< 5 consumer** (real + straw-man) → BLOCKED, downgrade shared module monorepo
- Chỉ 1 consumer thật ("sẽ có consumer thứ 2 sau") → BLOCKED
- Extract code đang tồn tại từ product → dùng `library-extract`
- Util nhỏ < 200 lines dùng cho 1-2 project → giữ monorepo shared module

## Inputs

Bắt buộc:
- Tên lib (artifact id)
- Danh sách consumer: ≥ 2 real + straw-man persona lấp đủ ≥ 5 total
- Responsibility 1 câu (không có "và")
- Platform scope: KMP common / androidMain / cần iosMain?
- Publishing target: Maven Central / internal Nexus / GitHub Packages

Optional:
- Design reference nếu lib có API shape mong muốn
- Deadline
- Steward (ai sẽ own lib dài hạn)

## Prerequisites

Đọc trước khi start (bắt buộc đầy đủ):
1. `knowledge/coding-sdk/sdk-mindset.md [KB → develop/sdk, kb_search "coding sdk sdk mindset"]` — ADR SDK-001..006, foundation mindset
2. `knowledge/coding-sdk/pattern-catalog.md [KB → develop/sdk, kb_search "coding sdk pattern catalog"]` — pattern canonical mapping
3. `knowledge/coding-sdk/layered-architecture.md [KB → develop/sdk, kb_search "coding sdk layered architecture"]` — 5-layer kernel-plugin
4. `knowledge/coding-sdk/brainstorm-process.md [KB → develop/sdk, kb_search "coding sdk brainstorm process"]` — 10-step Phase 0
5. `knowledge/coding-sdk/testing-kit-rules.md [KB → develop/sdk, kb_search "coding sdk testing kit rules"]` — TestingKit mandatory
6. `knowledge/coding-sdk/essentials.md [KB → develop/sdk, kb_search "coding sdk essentials"]` — rule checklist
7. `agents/library-architect.md`
8. `agents/workflows/library-flow.md`

Skip prerequisite → bias feature-first drift.

## Execution procedure

### Step 0 — Phase 0 Brainstorm (Library Architect) 🆕

Spawn `library-architect` agent chạy 10-step top-down theo `brainstorm-process.md §BRAIN-002`:

1. Mission statement (1 câu không "và")
2. Non-goals (≥ 5 item có lý do)
3. Consumer personas (≥ 5 real + straw-man)
4-5. Use case inventory + matrix 3-axis (≥ 15 use case)
5.5. **Intersection audit + Cross-cutting lens** (bắt buộc, catch unknown unknowns như `suspend-call × rationale-needed`)
6. Scope decision (IN L_N / OUT / CONSUMER-OWN)
7. Layer decomposition
8. L0 Kernel primitive
9. SPI contract design (≥ 3 SPI)
10. Backward compat strategy

**Output**:
- `plans/<date>-<slug>/brainstorm.md` (có section Step 5.5)
- `plans/<date>-<slug>/use-case-matrix.md` (bao gồm UC phát sinh từ audit)
- `plans/<date>-<slug>/straw-man-personas.md`

**Gate** (9 checklist):
- [ ] Mission 1 câu không "và"
- [ ] Non-goals ≥ 5
- [ ] Consumer persona ≥ 5
- [ ] Use case matrix ≥ 15 row, mỗi row tag đủ 3 trục
- [ ] Step 5.5 intersection audit ≥ 2 plane, mọi cell risky có UC đại diện hoặc document skip
- [ ] 10 cross-cutting concern (BRAIN-007) có answer rõ cho mỗi caller-surface (UX host, process death, config change, DI, dispatcher, lifecycle timing, error, cancel, test host, concurrency)
- [ ] L0 primitive ≤ 5 method
- [ ] ≥ 3 SPI với ≥ 2 default impl + ≥ 1 example custom mỗi SPI
- [ ] Mental test 5 persona × 3 lens (SPI plug + UX/lifecycle + error/cancel/concurrency): ≥ 4/5 GREEN mỗi lens

Fail bất kỳ → BLOCK Step 1, không draft Contract.

### Step 1 — Trigger validation (Library Architect)

Verify sau Phase 0:
1. **≥ 5 consumer** (real + straw-man theo `straw-man-personas.md`)
2. Responsibility 1 câu không "và"
3. Platform scope rõ
4. SDK mindset acknowledged

Fail bất kỳ → status BLOCKED, note lý do, dừng.

### Step 2 — Draft Library Contract (Library Architect)

Spawn `library-architect` (nếu solo session, giữ cùng session) produce `library-contract.md` theo template expanded trong `agents/library-architect.md §Output §1`. Bắt buộc có:

- **Layer Map** (5-layer kernel-plugin)
- **Pattern Catalog mapping** (mỗi public component tag pattern từ `pattern-catalog.md`)
- **SPI Contract** (≥ 3 SPI document: TypeResolver, Interceptor, Listener với stability tier + default + example custom)
- **TestingKit section** (fake, driver, assertion, dep policy)
- Public API surface (minimal + stability + pattern tag)
- Config API + side-effect ports
- Versioning + publishing + governance
- `config-matrix.md` cho ≥ 2 real consumer

**Gate** (Contract ready):
- [ ] 11 checklist item trong `library-flow.md §Stage 3 Gate`
- [ ] SDK-002 3 guarantee verify (Stability, Configurability, Extensibility)

### Step 2b — SPI Freeze (Library Architect + Coder) 🆕

Code **chỉ** interface SPI + sealed hierarchy + data class public API, **không impl** nội dung:

1. Scaffold Gradle module per layer: `:core`, `:scheduler`, `:scenario`, `:policy`, `:integration`, `:testing`
2. Apply BCV plugin + explicitApi
3. Code SPI + sealed hierarchy (empty body / `TODO()`)
4. `./gradlew apiDump` + commit `api/<module>.api`
5. Mental test 5 persona lại — persona N không plug được qua SPI → quay lại Step 2

**Gate**:
- [ ] `./gradlew apiCheck` PASS trên SPI module
- [ ] API dump committed
- [ ] Konsist rule L0 không import L1+ setup
- [ ] Mental test ≥ 4/5 GREEN

### Step 3 — Module layout plan (Architect)

Delegate `architect` với Contract đã có + SPI frozen:
- **Gradle module split theo 5-layer** (`:core`, `:scheduler`, `:scenario`, `:policy`, `:integration`, `:testing`, `samples/*`)
- KMP sourceSet layout
- expect/actual boundary
- **Konsist rule file list** (`KonsistLayerRuleTest.kt`)
- **Convention plugin** (`xxx-layer-conventions.gradle.kts`): explicitApi + BCV + Konsist auto-apply + resource prefix
- Build config: BCV plugin, publish plugin, signing
- Test strategy per layer

Output: `plans/<date>-<slug>/plan.md`

### Step 4 — Scaffold repo

Delegate `coder`:
- Init git repo mới cho lib
- Gradle setup theo plan (multi-module 5-layer)
- `gradle.properties` với group/version
- `settings.gradle.kts` với module list đủ layer
- `libs.versions.toml` nội bộ
- `.github/workflows/` CI: build + test + apiCheck + konsistTest + publish-on-tag
- `consumer-rules.pro`
- Convention plugin
- README.md + CHANGELOG.md skeleton

### Step 5 — Implement API theo contract

Coder impl từng public API theo plan + contract. Thứ tự:

1. **L0 Kernel primitive** (interface + default port impl: Logger, Clock, StateStore)
2. **L1 TypeResolver registry** + built-in resolver
3. **L2 Composition** (Scenario, lifecycle state machine)
4. **L3 Policy interceptor chain** + built-in interceptor
5. **L4 Integration adapter** (platform-specific, 3rd-party bridge)
6. Factory function + Facade entry point
7. Unit test per layer (happy + edge ≥ 2 per public API)
8. `samples/minimal/` quickstart ≤ 20 dòng + `samples/full/` dùng cả 5 layer

Coder không được expand public API ngoài contract. Phát hiện cần expand → raise Library Architect.

### Step 6 — TestingKit implementation (Coder) 🆕

Impl `:lib-testing` artifact theo Contract §TestingKit + `testing-kit-rules.md`:

1. Fake impl cho mọi port L0 (`FakeClock`, `InMemoryStateStore`, `RecordingLogger`, `RecordingAnalytics`, `RecordingNotificationPresenter`, `FakePermissionChecker`)
2. Driver cao level (`TestXxxKit`) pre-wire fake
3. Assertion helper
4. Builder helper (default sensible)
5. Self-test (meta-test fake + smoke test driver)
6. `samples/testing-sample/` demo use

**Gate**:
- [ ] `./gradlew :testing:build :testing:test :testing:apiCheck` PASS
- [ ] Sample compile + run
- [ ] Coverage ≥ 80% public symbol SDK có fake/driver

### Step 7 — Dual review

Parallel:
- `reviewer` — code quality 10 dimensions + Konsist layer rule
- `library-architect` — API diff BCV + Contract compliance + Pattern mapping + Layer boundary + TestingKit coverage

Gate:
- Reviewer APPROVE
- API PASS/NEW_SYMBOLS (không BREAKING vì mới)

### Step 8 — QA matrix

`qa` scope A:
- Build + test trên min + max Kotlin
- Konsist test layer rule PASS
- Build sample app consume lib qua local maven, assert resolve + import < 20 dòng
- **TestingKit smoke**: sample app dùng `:lib-testing`, consumer test code chạy được
- **Straw-man test**: impl 1 straw-man persona plugin (vd `LunarCalendarResolver` cho reminder SDK) → verify SPI thực sự extend được

### Step 9 — First publish

Tech-lead lib (hoặc Library Architect kiêm):
- Verify tag `v0.1.0`
- CI pipeline publish **mọi module** (`:core`, `:scheduler`, `:scenario`, `:policy`, `:integration`, `:testing`)
- Verify artifact resolve từ external repo
- Verify `:lib-testing` artifact publish
- Announce consumer

### Step 10 — Report

Theo mẫu `constitution/definition-of-done.md [KB → develop/constitution, kb_search "definition of done"] §Report` + bổ sung:
```
Phase 0 Brainstorm: COMPLETE (brainstorm.md + use-case-matrix.md + straw-man-personas.md)
Consumer count: N real + M straw-man = N+M total (≥ 5)
Layer coverage: L0/L1/L2/L3/L4 populated
SPI count: ≥ 3 (TypeResolver/Interceptor/Listener)
Mental test 5 persona: GREEN/5
Pattern mapping: all public components tagged
API diff: PASS | NEW_SYMBOLS (bump minor) | BREAKING (block)
Config matrix: INITIALIZED
TestingKit: PUBLISHED (:lib-testing)
Consumer onboarding: < 5 dòng gradle, < 20 dòng quickstart
Konsist layer rule: PASS
Publish: VERIFIED | FAILED
```

## Required policies

### SDK-level (bắt buộc)
- SDK-001..006 (xem `sdk-mindset.md`)
- Pattern Catalog mapping (xem `pattern-catalog.md`)
- 5-layer architecture + Konsist rule (xem `layered-architecture.md`)
- BRAIN-001..007 (xem `brainstorm-process.md`, bao gồm Step 5.5 Intersection audit + Cross-cutting concern catalog)
- TEST-001..011 TestingKit (xem `testing-kit-rules.md`)

### Rule-level (từ essentials)
- LIB-SCOPE-001..003 (boundary)
- LIB-API-001..006 (versioning + minimality)
- LIB-CONFIG-001..005 (DI-agnostic config)
- LIB-PORT-001..004 (side-effect injection)
- LIB-DEP-001..005 (dependency hygiene)
- LIB-PATTERN-001..006 (pattern per lib type)
- LIB-PUBLISH-001..005 (publishing pipeline)
- LIB-GOV-001..004 (governance)

## Validation

Trước khi tuyên bố DONE:

### Phase 0 artifacts
- [ ] `brainstorm.md` committed (10 step + Step 5.5 Intersection audit + Cross-cutting lens)
- [ ] `use-case-matrix.md` committed (≥ 15 use case + UC phát sinh từ audit, 3-axis tagged)
- [ ] `straw-man-personas.md` committed (≥ 5 persona)
- [ ] Mental test 5 persona × 3 lens (SPI plug + UX/lifecycle + error/cancel/concurrency) ≥ 4/5 GREEN mỗi lens
- [ ] 10 cross-cutting concern (BRAIN-007) có answer rõ cho mỗi caller-surface, không TBD

### Trigger
- [ ] ≥ 5 consumer (real + straw-man)
- [ ] Responsibility 1 câu không "và"
- [ ] SDK mindset acknowledged

### Contract
- [ ] `library-contract.md` committed có Layer Map + Pattern Catalog + SPI Contract + TestingKit
- [ ] `config-matrix.md` committed (≥ 2 real consumer concrete)
- [ ] Mọi public component map ≥ 1 pattern
- [ ] ≥ 3 SPI với stability tier
- [ ] SDK-002 3 guarantee verified

### Code
- [ ] 5-layer Gradle module split
- [ ] Konsist layer rule PASS
- [ ] BCV `./gradlew apiCheck` PASS
- [ ] API dump `api/<module>.api` committed cho mọi module
- [ ] Unit test pass trên min + max Kotlin
- [ ] `samples/minimal/` + `samples/full/` build pass
- [ ] Resource prefix enforced (Android)
- [ ] `consumer-rules.pro` ship kèm

### TestingKit
- [ ] `:lib-testing` artifact built + tested + apiCheck
- [ ] Fake cho mọi port L0
- [ ] Driver + assertion + builder helper
- [ ] Self-test PASS
- [ ] `samples/testing-sample/` build + run
- [ ] Dep policy TEST-004 (no Mockito/Mockk)

### Straw-man verify
- [ ] ≥ 1 straw-man persona plugin impl thành công (verify SPI extensibility)

### Release
- [ ] CHANGELOG.md có entry `0.1.0`
- [ ] CI publish pipeline PASS cho mọi module
- [ ] Artifact (bao gồm `:lib-testing`) resolve từ external repo

## Failure / recovery

- Trigger check fail (< 5 consumer) → BLOCKED, không tiếp. Gợi ý: downgrade shared module monorepo.
- Phase 0 Gate fail → quay lại Step 0 refactor brainstorm, không skip.
- Mental test persona × lens < 4/5 ở bất kỳ lens nào → quay lại Step 5.5 (nếu lens 2/3 fail do miss cross-cutting) hoặc Step 7-9 (nếu lens 1 fail do SPI gap), không approve Contract.
- Step 5.5 intersection audit phát hiện cell trống không hợp lý → thêm UC vào `use-case-matrix.md`, re-run Step 6 scope decision.
- Cross-cutting concern (BRAIN-007) có answer TBD cho caller-surface S → BLOCK, phải document rõ `COVERED by UC-N` | `OUT with reason` | `CONSUMER-OWN via SPI-X`.
- Contract mâu thuẫn giữa consumer A/B → tạm BLOCKED, tổ chức sync meeting.
- BCV API dump chưa commit → `./gradlew apiDump` + commit.
- Konsist layer rule FAIL → fix import vi phạm, không disable rule.
- Straw-man plugin không impl được qua SPI → quay lại Step 2 refactor SPI.
- CI publish fail → check signing/credential, không retry blindly.
- Resource conflict khi smoke test consumer → bump prefix, không ép consumer rename.
- TestingKit thiếu fake cho port → add fake trước release.

## Anti-patterns bị cấm

### Scope & brainstorm
- Skip Phase 0 Brainstorm, nhảy thẳng Contract
- Skip trigger check "chắc có consumer sau"
- < 5 consumer vẫn approve pipeline
- Skip Step 5.5 Intersection audit, chỉ tag UC theo 1 trục rời rạc (bỏ lọt cell `(axis_X=A) × (axis_Y=B)` risky)
- Mental test chỉ chạy lens 1 (SPI plug), bỏ lens 2 (UX/lifecycle) + lens 3 (error/cancel/concurrency)
- Cross-cutting concern đánh giá "assumed trivial" không document rõ answer

### API & pattern
- Impl trước Contract (sẽ phải refactor API khi contract rõ)
- Impl trước SPI Freeze (Step 2b)
- Public component không map pattern từ catalog
- Expose `data class` public không có versioning plan
- Expose `enum class` cho state machine
- Hardcode Logger/Analytics/HttpClient
- `api(...)` dep không có lý do
- `object SingletonLib` thay vì factory
- `setListener(cb)` callback thay vì `Flow<State>`
- Reflection auto-discovery cho SPI
- Service Locator global static registry
- Inheritance extension (`abstract class BasePlugin`)

### Architecture
- Approve SDK không layered (monolithic module) khi scope > util pure
- L0 kernel import L1+
- L4 Integration gọi thẳng L0 kernel skip L2/L3

### SPI
- SDK không có SPI cho use case có thể mở rộng
- SPI < 3 (thiếu TypeResolver/Interceptor/Listener minimum)
- SPI chỉ expose interface không có default impl

### TestingKit
- Release 1.0 không có `:lib-testing` artifact
- TestingKit fake no-op không mirror semantic production
- TestingKit depend Mockito/Mockk
- TestingKit không có self-test

### Publishing
- Publish version `0.1.0` mà chưa có `samples/` + quickstart
- Publish core module mà không publish `:lib-testing` cùng version
- CI không có BCV gate
- CI không có Konsist gate

---

## Harness context

- Workflow: `agents/workflows/library-flow.md`
- Agent: `agents/library-architect.md`
- Knowledge: full SDK knowledge set trong `knowledge/coding-sdk/`
- Guardrails: `~/.claude/rules/development-rules.md`, `review-audit-self-decision.md`, `orchestration-protocol.md`

## Overlay gate

Skill này **không** đọc `.harness-overlay/overlay.yaml` vì lib ở repo riêng, không consume harness overlay của consumer product. Lib repo tự quản gradle config, package root, module layout — không phụ thuộc placeholder `{{PACKAGE_ROOT}}` etc.
