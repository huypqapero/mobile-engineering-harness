---
name: library-extract
description: Tách code đang tồn tại trong 1 product thành KMP/Android library riêng + publish artifact. Trigger khi ≥ 2 consumer thật cần dùng chung code đã ổn định ≥ 6 tháng ở 1 product repo. Scout coupling → chọn strategy lift-and-shift vs clean-slate → extract + migrate source product.
priority: P1
---

# Skill: library-extract

## Trigger

- "Tách module Y ở product A thành lib riêng"
- "Product B/C/D cần dùng lại code từ product A, extract thành lib"
- "Move <feature> sang shared library"

**Không trigger khi**:
- Chỉ 1 consumer sử dụng code đó → giữ ở product
- Boundary code chưa ổn định (< 6 tháng, API đang bay) → chờ settle
- Code tạo mới chưa có trong product → dùng `library-new`

## Inputs

Bắt buộc:
- Product repo nguồn + path code sẽ extract (ví dụ `product-a/presenter/analytics/`)
- Danh sách ≥ 2 consumer thật cam kết migrate
- Lý do extract (business + technical)
- Target repo lib (đã có hay cần tạo mới)

Optional:
- Deadline migration source product
- Steward lib dài hạn

## Prerequisites

Đọc trước khi start (SDK knowledge set — bắt buộc đọc toàn bộ, không skim):
1. `knowledge/coding-sdk/sdk-mindset.md [KB → develop/sdk, kb_search "coding sdk sdk mindset"]` — ADR SDK-001..006
2. `knowledge/coding-sdk/pattern-catalog.md [KB → develop/sdk, kb_search "coding sdk pattern catalog"]`
3. `knowledge/coding-sdk/layered-architecture.md [KB → develop/sdk, kb_search "coding sdk layered architecture"]` — classify code hiện tại thuộc layer nào
4. `knowledge/coding-sdk/brainstorm-process.md [KB → develop/sdk, kb_search "coding sdk brainstorm process"]` — Phase 0 nếu clean-slate
5. `knowledge/coding-sdk/testing-kit-rules.md [KB → develop/sdk, kb_search "coding sdk testing kit rules"]` — TestingKit extract/write
6. `knowledge/coding-sdk/essentials.md [KB → develop/sdk, kb_search "coding sdk essentials"]`
7. `agents/library-architect.md`
8. `agents/workflows/library-flow.md`
9. `skills/coding-scout/SKILL.md` (dùng cho map coupling)

## Execution procedure

### Step 1 — Trigger validation

Verify 4 gate:
1. **≥ 5 consumer** (real + straw-man) cho **clean-slate mode**, hoặc ≥ 2 real consumer cho **lift-and-shift mode** với justification scope hẹp
2. Boundary code ổn định ≥ 6 tháng (không có refactor lớn gần đây, API không thay đổi tần suất cao)
3. Responsibility 1 câu không "và"
4. SDK mindset acknowledged (`sdk-mindset.md`)

Fail bất kỳ → BLOCKED, note lý do.

### Step 2 — Scout coupling + Layer classification 🆕

Delegate `coding-scout` tại product repo nguồn. Scan:
- Symbol phụ thuộc product-specific concept (tên feature, enum product)
- Resource reference với namespace product (`R.string.product_a_*`)
- DI binding sang Koin/Hilt module product
- Analytics event name có prefix product
- expect/actual bridge nếu KMP
- Dep gián tiếp qua product shared util
- **Layer classification**: code hiện tại thuộc L0/L1/L2/L3/L4 theo `layered-architecture.md` (có thể cross-layer = feature-first drift)
- **Extension point tiềm năng**: `abstract class` / `open class` / inheritance → chuyển sang SPI (Strategy + Registry / Interceptor / Listener) khi extract
- **Hardcoded dependency**: Logger / Analytics / HttpClient / Clock → convert sang port injection
- **God Config / Singleton object**: → refactor sang Builder + Named Instance

Output: `plans/<date>-<slug>/scout-report.md` liệt kê:
- 100% public symbol của code tách + độ phụ thuộc
- Layer map của code hiện tại
- Extension point candidate list
- Anti-pattern cần refactor (từ `sdk-mindset.md §SDK-004`)

### Step 3 — Draft Library Contract + Extract Risk

Spawn `library-architect`:

**Clean-slate mode**: chạy **Phase 0 Brainstorm đầy đủ** như `library-new` Step 0:
- `brainstorm.md` (10-step)
- `use-case-matrix.md` (≥ 15 use case, 3-axis)
- `straw-man-personas.md` (≥ 5 persona, lấp từ 2 real consumer)
- Gate Phase 0 pass trước khi Contract

**Lift-and-shift mode**: skip Phase 0 full, chỉ cần:
- Non-goals explicit ≥ 3
- Layer classification (từ scout report)

Rồi produce:
- `library-contract.md` với public API minimal + Layer Map + Pattern Catalog mapping + SPI Contract + TestingKit (clean-slate full; lift-and-shift giãn SPI nếu ít consumer)
- `config-matrix.md` cho real consumer
- `extract-risk.md` liệt kê coupling cần cắt + migration cost + anti-pattern refactor list

Gate: contract pass, risk assessed, Phase 0 Gate pass (clean-slate).

### Step 4 — Decide extract strategy

`library-architect` recommend:

**Lift-and-shift** nếu:
- 2 real consumer, API hiện tại acceptable
- Cần ship < 2 tuần
- Code hiện tại không cross-layer (fit 1 layer, không vi phạm SDK-mindset nặng)
- Coupling cắt được bằng rename package + resource prefix

**Clean-slate** nếu:
- ≥ 3 real consumer (hoặc đủ 5 total với straw-man)
- API hiện tại leak concept product
- Code hiện tại cross-layer / có inheritance extension / có hardcoded dep → cần refactor nặng
- Boundary API sẽ expose cho team ngoài / public
- SDK sẽ phục vụ > 5 consumer trong roadmap

User confirm strategy trước Step 5. Lift-and-shift chọn → chấp nhận SDK không layered đầy đủ nhưng vẫn phải có ≥ 2 SPI minimum (Port + Listener).

### Step 5 — CR flow với source product

Tạo CR tại source product repo:
- `briefs/<slug>/change-requests/CR-lib-extract-<id>.md`
- Impact: file nào trong product sẽ migrate qua public API lib, deadline
- Source product `tech-lead` + `project-manager` sign-off

Gate: không extract nếu source product không approve migration cost.

### Step 6 — Setup lib repo

Nếu lib repo chưa tồn tại → delegate `coder` scaffold như trong `library-new` Step 4 (gradle setup, BCV, publish, CI).

Nếu lib repo đã có → skip scaffold, chỉ add module mới.

### Step 7 — Extract impl

#### Lift-and-shift

Coder:
1. Copy code từ product sang lib repo
2. Rename package root sang lib namespace
3. Rename resource prefix `product_a_*` → `lib_<name>_*`
4. Cắt DI binding product → factory function + port
5. Inline / replace util product bằng impl riêng (hoặc dep riêng nếu nhẹ)
6. Public API tối thiểu: mark `internal` tất cả không cần expose
7. **Refactor anti-pattern từ scout** (Step 2): object Singleton → factory, inheritance → SPI, setListener → Flow
8. Add unit test (nếu product test có → migrate; không có → viết happy + edge)
9. **TestingKit** `:lib-testing` artifact: minimal fake + driver (có thể giãn so với clean-slate nhưng không skip)

#### Clean-slate

1. `library-architect` + `architect` draft public API theo contract minimal + Layer Map 5-layer + SPI Contract
2. **SPI Freeze** như `library-new` Step 2b (code chỉ interface + sealed, BCV commit)
3. Coder impl lại từ đầu theo plan Architect, theo đúng 5-layer module split
4. Reference code product chỉ để đọc, không copy
5. Unit test viết mới per layer
6. **TestingKit** `:lib-testing` artifact đầy đủ theo `testing-kit-rules.md`

### Step 8 — Dual review

Parallel:
- `reviewer` — code quality
- `library-architect` — API diff vs contract, verify public API minimal

Gate: Reviewer APPROVE + API match contract.

### Step 9 — QA matrix + source product regression

`qa` scope A:
- Build + test lib trên min + max Kotlin
- Build sample consume lib qua local maven

Thêm **regression source product**:
- Replace code product bằng dep lib (`implementation(libs.myLib)`)
- Build product + chạy existing test suite
- QA smoke feature nào consume code vừa extract

Gate: toàn pass. Nếu product regression fail → fix lib hoặc rollback extract.

### Step 10 — First publish

Lib tech-lead:
- Tag `v0.1.0`
- CI publish
- Verify resolve external

### Step 11 — Migrate source product

Delegate `coder` tại source product repo:
- `implementation(libs.myLib)` vào `libs.versions.toml` + module
- Remove code đã extract
- Giữ `typealias` 1 release safe (`@Deprecated` pointing tới lib type) để downstream của product kịp migrate
- PR qua product review flow

### Step 12 — Report

Theo mẫu DoD + bổ sung:
```
Extract strategy: lift-and-shift | clean-slate
Scout coverage: X public symbols analyzed
Source product impact: Y files changed, Z lines removed, deprecated-typealias in <files>
API diff: NEW LIB (0.1.0 initial)
Consumer migration: source product MIGRATED | PENDING; other consumers PENDING
Publish: VERIFIED
```

## Required policies

- LIB-SCOPE-001..003 (boundary + flavor)
- LIB-API-001..006 (minimality + BCV)
- LIB-CONFIG-001..005 (DI-agnostic)
- LIB-PORT-001..004 (side-effect injection)
- LIB-DEP-001..005 (no transitive leak)
- LIB-RES-001..003 (resource prefix, consumer-rules)
- LIB-PUBLISH-001..005
- LIB-GOV-001..004

Full: `knowledge/coding-sdk/essentials.md [KB → develop/sdk, kb_search "coding sdk essentials"]`.

## Validation

Trước khi tuyên bố DONE:

### Trigger & scout
- [ ] Trigger check pass (consumer count đạt mode tương ứng)
- [ ] SDK mindset acknowledged
- [ ] Scout report cover 100% public symbol + Layer classification + Extension point list + Anti-pattern list

### Contract
- [ ] (Clean-slate) Phase 0 artifacts committed (brainstorm.md + use-case-matrix.md + straw-man-personas.md), Gate pass
- [ ] Extract Risk + CR source product sign-off
- [ ] Strategy explicit (lift-and-shift / clean-slate)
- [ ] Library Contract + Config Matrix committed, có Layer Map + Pattern Catalog mapping + SPI Contract + TestingKit sections
- [ ] (Clean-slate) ≥ 3 SPI; (Lift-and-shift) ≥ 2 SPI minimum
- [ ] Anti-pattern từ scout đã refactor (object → factory, inheritance → SPI, setListener → Flow)

### Code
- [ ] (Clean-slate) 5-layer Gradle module split + Konsist layer rule PASS
- [ ] Lib `./gradlew apiCheck` pass
- [ ] API dump committed cho mọi module
- [ ] Lib unit test pass min + max Kotlin
- [ ] Resource prefix migrated
- [ ] Analytics event name migrated (hoặc giữ name cũ với note)

### TestingKit
- [ ] `:lib-testing` artifact built + tested
- [ ] Fake cho port L0
- [ ] (Clean-slate) Full driver + assertion; (Lift-and-shift) minimal driver

### Source product
- [ ] Source product regression PASS sau khi switch sang lib
- [ ] Source product PR merge với deprecated-typealias

### Release
- [ ] CI publish pipeline PASS cho mọi module (bao gồm `:lib-testing`)

## Failure / recovery

- Scout phát hiện coupling nặng (> 50% file dính product concept) → recommend clean-slate hoặc defer extract
- CR source product reject → BLOCKED, escalate PM product
- Regression source product fail sau migrate → fix lib hoặc rollback switch; không ép-ship
- API dump diff lộ symbol thừa → tighten `internal`, không bump version thừa

## Anti-patterns bị cấm

### Extract process
- Lift-and-shift mà không rename package/resource (conflict với consumer product)
- Impl lib mà không CR source product (owner product không biết sẽ migrate)
- Giữ cả code trong product + lib (duplicate, maintenance kép)
- Remove code product trước khi lib publish stable (chain break)
- Expose nguyên API cũ của product (chưa minimal, leak concept)
- Analytics event rename không coordinate với data team (break dashboard)
- Skip source product regression (bug chỉ phát hiện ở production)

### SDK mindset drift (từ `sdk-mindset.md`)
- Extract thành lib nhưng giữ feature-first API shape (không layered, không SPI)
- Clean-slate mode skip Phase 0 Brainstorm
- Giữ nguyên anti-pattern từ product: `object Singleton`, inheritance extension, `setListener(cb)`, hardcoded Logger/Analytics, God Config
- Clean-slate không có TestingKit → vi phạm `testing-kit-rules.md`
- Không classify layer code hiện tại → không biết feature-first drift ở đâu

### SPI
- Extract code có inheritance mà không chuyển sang Strategy + Registry SPI
- Hardcoded Clock/Logger từ product giữ nguyên trong lib → phải convert sang port

---

## Harness context

- Workflow: `agents/workflows/library-flow.md` §Extract mode
- Agent: `agents/library-architect.md`
- Knowledge: SDK knowledge set đầy đủ trong `knowledge/coding-sdk/`
- Scout: `skills/coding-scout/SKILL.md`
- Guardrails: `~/.claude/rules/development-rules.md`, `review-audit-self-decision.md`, `orchestration-protocol.md`

## Overlay gate

Skill chạy ở **2 repo khác nhau**:
- **Source product repo**: có `.harness-overlay/overlay.yaml` — Step 2 (scout) và Step 11 (migrate) đọc overlay như skill thường
- **Lib repo**: KHÔNG consume overlay — Step 6-10 không đọc placeholder, lib tự quản gradle/package

Agent phải phân biệt rõ context "đang ở repo nào" khi execute step.
