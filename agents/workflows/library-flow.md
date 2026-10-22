# Workflow: Library Flow

Pipeline tạo & vận hành KMP/Android library ở **repo riêng + publish artifact**, consume được bởi N product cùng harness.

## Mode

Workflow có 2 mode, chọn theo trigger:

- **Greenfield**: lib mới, chưa có code tồn tại.
- **Extract**: tách code từ product repo thành lib riêng.

## Trigger

Greenfield:
- User request "tạo lib X dùng chung cho A và B"
- Harness Guardian đề xuất lib khi phát hiện pattern duplicate giữa product

Extract:
- User request "tách module Y ở product A thành lib riêng"
- Product B/C/D cần dùng lại code từ product A
- Boundary code đã ổn định ≥ 6 tháng

## Trigger check (bắt buộc, dừng nếu fail)

1. **≥ 5 consumer** (real + straw-man persona). Dưới 5 → BLOCKED, downgrade sang shared module. (Lift-and-shift extract có thể giãn xuống 2 real với justification.)
2. Responsibility 1 câu không có "và"
3. (Extract) Boundary code ổn định ≥ 6 tháng
4. **SDK mindset acknowledged**: Library Architect confirm đã đọc `knowledge/cross-cutting/shared-library/sdk-mindset.md` + commit tới 3 guarantee (Stability, Configurability, Extensibility)

Fail bất kỳ → status BLOCKED, note lý do, không spawn pipeline.

## Diagram (greenfield)

```
user request
     │
     ▼
library-architect  ──trigger check (≥ 5 consumer)──  (fail → BLOCKED)
     │ pass
     ▼
Phase 0 — Brainstorm (10-step top-down)
  • brainstorm.md
  • use-case-matrix.md (3-axis, ≥ 15 use case)
  • straw-man-personas.md (≥ 5 persona)
  Gate: mental test 5 persona ≥ 4/5 GREEN
     │ pass
     ▼
library-contract.md (Layer Map + Pattern Catalog + SPI Contract + TestingKit)
     + config-matrix.md
     │
     ▼
SPI Freeze (code chỉ interface + sealed + data class, BCV API dump commit)
     │
     ▼
architect  ──5-layer module layout + Konsist rule──  plan.md
     │
     ▼
coder  ──implement──  code + unit test + TestingKit (:lib-testing)
     │
     ▼
reviewer (code quality)   library-architect (API diff BCV + layer rule)
     │                           │
     └────────┬──────────────────┘
              ▼
         qa  ──matrix test + TestingKit smoke──  pass/fail
              │
              ▼
    publish pipeline (CI tag → sign → Maven, :core + :layer modules + :testing)
              │
              ▼
    consumer product repo migrate
```

## Diagram (extract)

```
user request + source product repo
     │
     ▼
library-architect  ──trigger check──  (fail → BLOCKED)
     │ pass
     ▼
coding-scout  ──map coupling──  scout-report.md
     │
     ▼
library-architect  ──strategy decide──
     │
     ├─► lift-and-shift ─► copy + rename + minimal API cleanup
     │
     └─► clean-slate ───► contract first → rewrite
     │
     ▼
extract-risk.md + CR flow với source product owner
     │
     ▼
architect → coder → reviewer + library-architect → qa → publish
     │
     ▼
source product repo migrate qua public API
     │
     ▼
remove old internal module (sau 1 release safe)
```

## 11 stage + gate

### Stage 1 — Trigger validation (Library Architect)

**Input**: user request + consumer list

**Activity**:
1. Verify ≥ 5 consumer (real + straw-man)
2. Verify responsibility 1 câu không "và"
3. (Extract) verify boundary ổn định ≥ 6 tháng
4. Confirm SDK mindset acknowledged (`sdk-mindset.md` loaded)

**Output**: pass → tiếp Stage 1b; fail → BLOCKED note

**Gate**: không skip. Fail = dừng toàn pipeline. Dưới 5 consumer = downgrade sang shared module monorepo.

---

### Stage 1b — Phase 0 Brainstorm (Library Architect) 🆕

**Owner**: `library-architect`

**Activity**: Chạy 10-step top-down theo `brainstorm-process.md §BRAIN-002`:
1. Mission statement
2. Non-goals (≥ 5)
3. Consumer personas (≥ 5, real + straw-man)
4-5. Use case inventory + matrix 3-axis (≥ 15 use case)
6. Scope decision (IN L_N / OUT / CONSUMER-OWN)
7. Layer decomposition (verify ratio healthy)
8. L0 Kernel primitive (interface ≤ 5 method)
9. SPI contract design (≥ 3 SPI)
10. Backward compat strategy

**Output**:
- `plans/<date>-<slug>/brainstorm.md`
- `plans/<date>-<slug>/use-case-matrix.md`
- `plans/<date>-<slug>/straw-man-personas.md`

**Gate**:
- [ ] Mission 1 câu không "và"
- [ ] Non-goals ≥ 5 có lý do
- [ ] Consumer persona ≥ 5
- [ ] Use case matrix ≥ 15 row, mỗi row tag đủ 3 trục
- [ ] L0 primitive ≤ 5 method
- [ ] ≥ 3 SPI design với ≥ 2 default impl + ≥ 1 example custom mỗi SPI
- [ ] Mental test 5 persona ≥ 4/5 GREEN

Fail bất kỳ → BLOCK Stage 3.

---

### Stage 2 — Coupling scout (chỉ extract mode)

**Owner**: `library-architect` delegate `coding-scout`

**Input**: product repo nguồn + path code tách

**Activity**: map
- Symbol phụ thuộc product concept
- Resource reference có namespace product
- DI binding
- Analytics event prefix
- expect/actual bridge nếu có

**Output**: `plans/<date>-<slug>/scout-report.md`

**Gate**: scout cover 100% public symbol của code tách

---

### Stage 3 — Contract design (Library Architect)

**Owner**: `library-architect`

**Input**:
- Greenfield: requirement
- Extract: scout-report.md + source code

**Input**: Phase 0 artifacts (`brainstorm.md`, `use-case-matrix.md`, `straw-man-personas.md`) + requirement/scout-report

**Activity**:
1. Decide platform matrix (KMP target)
2. Draft public API surface tối thiểu
3. **Layer Map** (5-layer kernel-plugin, map use case từ matrix vào layer)
4. **Pattern Catalog mapping** (mỗi public component tag pattern từ `pattern-catalog.md`)
5. **SPI Contract** (≥ 3 SPI document: TypeResolver, Interceptor, Listener)
6. Draft config API + side-effect ports
7. Draft dependency policy (api/implementation + catalog)
8. **TestingKit Plan** (`:lib-testing` artifact spec)
9. Draft versioning + publishing + governance
10. Extract: viết `extract-risk.md` + strategy (lift-and-shift / clean-slate)

**Output**:
- `library-contract.md` (expanded template có Layer Map + Pattern Catalog + SPI Contract + TestingKit)
- `config-matrix.md`
- `extract-risk.md` (extract mode)

**Gate** (Contract ready):
- [ ] Responsibility 1 câu
- [ ] Layer Map có đủ 5 layer (hoặc justify skip layer nào)
- [ ] Mỗi public component map ≥ 1 pattern từ `pattern-catalog.md`
- [ ] SPI ≥ 3 với stability tier
- [ ] Public API list đầy đủ với stability tag + pattern tag
- [ ] Config field có default hoặc explicit required-reason
- [ ] Dependency `api` list có justification
- [ ] Resource namespace isolated
- [ ] Versioning + publishing policy chốt
- [ ] TestingKit section complete (fake list, driver, assertion, dep policy, CI gate)
- [ ] SDK-002 3 guarantee check (Stability/Configurability/Extensibility)

---

### Stage 3b — SPI Freeze (Library Architect + Coder) 🆕

**Owner**: `library-architect` lead, `coder` impl

**Activity**:
1. Code **chỉ** interface SPI + sealed hierarchy + data class public API
2. **KHÔNG impl** nội dung (empty body hoặc `TODO()` placeholder)
3. Apply `binary-compatibility-validator` plugin
4. Chạy `./gradlew apiDump`, commit `api/<module>.api` vào git
5. Review mental 5 persona (từ `straw-man-personas.md`) — nếu persona N không plug được qua SPI đã design → quay lại Stage 3

**Output**: SPI contract code committed + API dump file

**Gate**:
- [ ] `./gradlew apiCheck` PASS trên SPI module
- [ ] API dump reflects đúng SPI design
- [ ] Mental test 5 persona ≥ 4/5 GREEN
- [ ] Konsist test L0 không import L1+ setup

Fail → quay lại Stage 3 refactor SPI.

---

### Stage 4 — CR flow với source product (chỉ extract mode)

**Owner**: `library-architect` + `tech-lead` của source product

**Activity**:
1. Tạo CR tại source product `briefs/<slug>/change-requests/CR-lib-<id>.md`
2. Impact assessment: file nào trong product sẽ migrate, deadline migration
3. Source product owner (Tech Lead product + PM) sign-off

**Output**: CR approved hoặc rejected (dừng extract)

**Gate**: không extract nếu source product không sign-off migration cost.

---

### Stage 5 — Module layout + impl plan (Architect)

**Owner**: `architect`

**Input**: `library-contract.md` (có Layer Map) + SPI contract đã freeze (+ scout-report nếu extract)

**Activity**:
1. Design gradle module theo 5-layer: `:core` (L0), `:scheduler` (L1), `:scenario` (L2), `:policy` (L3), `:integration` (L4), `:testing`
2. KMP sourceSet layout (commonMain / androidMain / iosMain)
3. expect/actual boundary nếu có platform-specific
4. **Konsist rule setup**: `L0 không import L1+`, resource prefix, package visibility
5. **Convention plugin** cho multi-module (explicitApi + BCV + Konsist auto-apply)
6. Chọn impl pattern (sealed class vs interface, Builder DSL, etc.) khớp Pattern Catalog
7. Test strategy per layer (xem `layered-architecture.md §LAYER-007`)
8. TestingKit module scaffolding

**Output**: `plans/<date>-<slug>/plan.md`

**Gate**:
- [ ] Module split khớp 5-layer (hoặc justify skip layer)
- [ ] Konsist rule file list
- [ ] Mỗi public API trong Contract map tới impl file
- [ ] Test plan per layer
- [ ] TestingKit module scaffolded

---

### Stage 6 — Implementation (Coder)

**Owner**: `coder`

**Input**: plan.md + library-contract.md

**Activity**:
1. Scaffold gradle module nếu lib mới (greenfield)
2. Setup `binary-compatibility-validator` plugin (Kotlin BCV)
3. Impl public API theo contract
4. Impl default no-op cho side-effect port
5. Unit test cho mỗi public API path (happy + edge ≥ 2)
6. Setup `consumer-rules.pro` (Android R8/ProGuard)
7. Setup Maven publish plugin + signing (greenfield)

**Gate**:
- [ ] `./gradlew build` pass
- [ ] `./gradlew apiCheck` (BCV) pass
- [ ] Unit test pass
- [ ] Konsist/Detekt pass
- [ ] API dump file (`api/<module>.api`) committed

**Constraint**: Coder không được expand public API ngoài contract. Nếu cần → raise Library Architect, không tự quyết.

---

### Stage 7 — Dual review (Reviewer + Library Architect parallel)

**Reviewer activity** (code quality):
- 10 dimensions review như `reviewer.md`
- Chú ý: visibility (`internal` không bị leak), thread-safety, resource prefix

**Library Architect activity** (API diff):
- Diff `api/<module>.api` vs base version
- Verify: không symbol thừa, không binary break (nếu `>= 1.0`)
- Verify config matrix match contract
- Verify CHANGELOG entry

**Output**:
- Reviewer verdict: APPROVE / APPROVE_WITH_CHANGES / REQUEST_CHANGES
- Library Architect API verdict: PASS / NEW_SYMBOLS / BREAKING

**Gate**:
- Reviewer APPROVE **AND** API PASS/NEW_SYMBOLS → next stage
- API BREAKING với `>= 1.0` → BLOCK, require RFC + consumer sign-off trước khi tiếp
- Reviewer REQUEST_CHANGES → Coder fix, re-review

---

### Stage 7b — TestingKit implementation (Coder) 🆕

**Owner**: `coder`

**Input**: Contract §TestingKit + plan.md

**Activity**:
1. Impl fake cho mọi port L0 (`FakeClock`, `InMemoryStateStore`, `RecordingLogger`, `RecordingAnalytics`, `RecordingNotificationPresenter`, `FakePermissionChecker`)
2. Impl driver cao level (`TestXxxKit`) pre-wire fake default
3. Impl assertion helper (`assertFired`, `assertBlocked`, `assertFireOrder`)
4. Impl builder helper (default sensible)
5. Self-test (meta-test cho mọi fake + smoke test cho driver)
6. Sample module `samples/testing-sample/` demo use

**Gate**:
- [ ] `./gradlew :testing:build :testing:test` PASS
- [ ] `./gradlew :testing:apiCheck` PASS (BCV cho testing module)
- [ ] Sample compile + run
- [ ] Coverage ≥ 80% public symbol SDK có fake/driver tương ứng
- [ ] Dependency policy TestingKit tuân `testing-kit-rules.md §TEST-004` (không Mockito/Mockk)

---

### Stage 8 — QA matrix (QA)

**Owner**: `qa` scope A

**Activity**:
- Unit test trên matrix: min Kotlin + max Kotlin version
- Android lib: lint + Robolectric (nếu cần) + instrumentation smoke
- Konsist test: layer rule enforce PASS
- Consumer smoke: build 1 sample app consume lib qua local Maven, assert integrate ok trong < 20 dòng
- **TestingKit smoke**: build sample app dùng `:lib-testing`, verify consumer test code chạy được
- **Straw-man test**: impl 1 straw-man persona plugin (vd `LunarCalendarResolver`) để verify SPI thực sự extend được
- (Extract) regression test product repo nguồn sau khi migrate qua public API

**Output**: QA report

**Gate**: toàn matrix pass. Fail → fix pipeline bugfix, không ship.

---

### Stage 9 — Publish

**Owner**: `tech-lead` của lib repo (hoặc Library Architect kiêm nếu team nhỏ)

**Activity**:
1. Bump version trong `gradle.properties` theo SemVer
2. Update CHANGELOG.md (Keep-a-Changelog format)
3. Tag `vX.Y.Z` push lên remote
4. CI tự: build + sign (GPG hoặc Sigstore nếu Maven Central) + publish
5. Verify artifact đã lên repository
6. Announce consumer: version mới, breaking? migration?

**Gate**:
- [ ] Tag match version trong `gradle.properties`
- [ ] CHANGELOG đã update
- [ ] CI pipeline publish PASS cho **mọi module** (`:core`, `:scheduler`, `:scenario`, `:policy`, `:integration`, `:testing`)
- [ ] Smoke resolve từ repo bên ngoài ok
- [ ] `:lib-testing` artifact publish cùng SDK version

---

### Stage 10 — Consumer migration (sau publish)

**Owner**: mỗi consumer product `tech-lead`

**Activity**:
- Bump version trong `libs.versions.toml`
- Fix deprecation warning (nếu minor release) hoặc migration code (nếu major)
- Regression test consumer app

**Gate**: không block lib release. Mỗi consumer tự plan migration theo sprint của họ.

**Timeline guideline**: consumer migrate ≤ 2 sprint sau lib release stable, trừ breaking lớn → có thể dời.

## Loop & escalation

| Loop | Max retry | Escalate to |
|---|---|---|
| Library Architect ↔ Architect (plan revise) | 2 vòng | PM / lib owner |
| Coder ↔ Reviewer bug fix | 3 lần cùng signature | Library Architect re-evaluate contract |
| QA matrix fail | 1 vòng | Library Architect audit lại scope |
| Breaking change not approved by consumer | — | PM scope cut hoặc dời release |

## Fast-path cấm

Không có fast-path cho lib workflow. Bugfix lib vẫn phải:
- Qua Reviewer + Library Architect dual review
- Bump patch version
- Update CHANGELOG

Lý do: lib ảnh hưởng N consumer, không-review-được-ngay như bugfix 1 screen trong product.

## Scope guard (raise user)

Agent phải raise user, không tự quyết, khi:
- Breaking change `>= 1.0` không có RFC
- Deadline ép compromise API minimality
- Consumer bất đồng với design (ví dụ A muốn flag này, B muốn flag khác)
- Resource namespace conflict với consumer existing
- Dependency có license không tương thích project license consumer

## Pair với workflow khác

- `feature-full-flow.md` — không áp dụng cho lib (lib không có PRD/wireframe/UI design chuẩn)
- `bug-triage.md` — nếu bug ở lib, triage như bình thường nhưng fix phải qua Stage 7-9 lib
- `release-gate.md` — release lib có co-sign Library Architect + lib Tech Lead, không PM product
- `parallel-features.md` — không áp dụng

## Pair với knowledge (bắt buộc đọc)

- `knowledge/cross-cutting/shared-library/sdk-mindset.md` — ADR SDK-001..006
- `knowledge/cross-cutting/shared-library/pattern-catalog.md` — pattern canonical
- `knowledge/cross-cutting/shared-library/layered-architecture.md` — 5-layer model
- `knowledge/cross-cutting/shared-library/brainstorm-process.md` — Phase 0 10-step
- `knowledge/cross-cutting/shared-library/testing-kit-rules.md` — TestingKit mandatory
- `knowledge/cross-cutting/shared-library/essentials.md` — rule checklist
