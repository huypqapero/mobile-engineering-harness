# Workflow: Refactor Module

Preserve behavior → restructure code → compare before/after → verify no regression.

**Golden rule**: refactor **không bao giờ** thay đổi observable behavior. Nếu behavior cần thay đổi → đó là feature work, dùng `feature-development.md`.

## Entry conditions

- Target module/package rõ (ví dụ `presenter/feature/library`, `data/repository`)
- Lý do refactor: SRP violation, file quá dài, duplicate code, future-SDK prep
- Test suite hiện tại pass (baseline xanh)

## Input artifacts

- Target scope: file/package/module
- Rationale: SRP / DRY / modularization / future-SDK extraction
- Reference: constitution + relevant skill

## Stages

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 1. BASELINE  │───▶│  2. PLAN     │───▶│ 3. REFACTOR  │───▶│  4. COMPARE  │───▶│  5. VERIFY   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

## Stage 1 — Baseline

### Actions

1. Chạy test suite hiện tại: `./gradlew test` → ghi lại số test pass + time
2. Chạy Konsist + Detekt → ghi violation hiện tại (nếu có)
3. Chụp cấu trúc current: `tree <module>/` hoặc `find`
4. List public API surface (classes/functions exposed)
5. Identify integration points (DI binding, Nav route, resource reference)

### Completion criteria

- Test baseline xanh (hoặc document test fail cũ, không gộp fix)
- Public API list đầy đủ
- Integration points known

### Blocker conditions

- Test baseline đỏ → fix test trước, không refactor trên code broken
- Public API không rõ → cần `grep` consumers trước

## Stage 2 — Plan

### Actions

1. Choose refactor strategy:
   - **Extract** function/class/package
   - **Inline** redundant abstraction
   - **Rename** cho clarity
   - **Move** between layer/module
   - **Split** large file (file > 400 lines → split per `ARCH-012`)
2. Preserve public API hoặc **document breaking change** nếu intended
3. Draft file list: new / modified / deleted
4. Risk assessment: cross-module impact? Consumer surface?

### Scope boundary rules

- **Không refactor** code ngoài target scope "while I'm here"
- **Không thay đổi** signature public API trừ khi plan state rõ
- **Không gộp** feature work vào refactor PR

### Completion criteria

- Plan < 150 dòng
- File list cụ thể
- Breaking change (nếu có) listed rõ với migration path
- Risk + mitigation stated

## Stage 3 — Refactor

### Execution patterns

#### Pattern A — Extract function

```kotlin
// Before
fun process(data: Data): Result {
    // 30 dòng validation
    // 20 dòng transform
    // 15 dòng save
}

// After
fun process(data: Data): Result {
    val validated = validate(data)
    val transformed = transform(validated)
    return save(transformed)
}

private fun validate(data: Data): Validated = ...
private fun transform(validated: Validated): Transformed = ...
private fun save(transformed: Transformed): Result = ...
```

#### Pattern B — Extract class

Khi 1 class có ≥ 2 unrelated responsibility → tách.

#### Pattern C — Inline abstraction

Khi interface chỉ có 1 impl + không có test fake → inline, bớt indirection.

#### Pattern D — Move cross-layer

Ví dụ: Business logic trong Composable → move sang ViewModel.
Ví dụ: DTO mapping trong Repository → move sang Mapper object.

#### Pattern E — Split file

File > 400 lines → tách theo responsibility. Giữ public API path.

### Rules

- **Mỗi step compile pass** — không commit broken intermediate
- **Mỗi step test pass** — không stack refactor khi test đỏ
- **Small commits** — mỗi commit 1 refactor type (extract, rename, move)
- **Không change behavior** — test suite phải pass identical input/output

### Completion criteria

- Code compile
- Test suite pass identical
- File structure match plan
- Public API preserved (hoặc migration path documented)

## Stage 4 — Compare

### Actions

1. Diff before vs after:
   - File count change
   - Line count change
   - Public API diff
   - Dependency graph diff
2. Verify behavior unchanged:
   - Test suite result identical
   - Manual smoke test (nếu UI touched)
3. Verify metrics improved:
   - File < 400 lines ✓
   - Duplication reduced
   - SRP compliance improved
4. Document trade-offs:
   - Readability improved?
   - Performance impact?
   - Maintenance cost change?

### Completion criteria

- Diff summary report
- Metrics before/after
- Zero behavior change confirmed

## Stage 5 — Verify

### Required gates

```bash
./gradlew :<module>:test                          # test unchanged behavior
./gradlew konsistTest                             # architecture rules
./gradlew detekt                                  # code quality
./gradlew :{{MODULE_APP}}:assembleDebug           # compile
```

### Manual verify

- Run app, exercise refactored feature
- Preview Compose nếu UI refactor
- Smoke test related features (regression)
- Check nav flows nếu touch route

### Completion criteria

- 4 gates PASS
- Zero regression trong related feature
- Konsist/Detekt violation count ≤ baseline (ideally reduced)

## Report format

```
Status: VERIFIED | VERIFIED_WITH_LIMITATIONS | BLOCKED | FAILED

Refactor summary:
<1 câu what + why>

Scope:
- Module/package: <path>
- Rationale: <SRP / file size / future-SDK / ...>

Changes:
- Files: N added, M modified, K deleted
- Lines: +X / -Y (net Z)
- Public API: preserved | changed (list)
- Dependency graph: unchanged | changed (describe)

Behavior preservation:
- Unit tests: N pass, 0 fail (identical to baseline)
- Integration tests: N pass
- Manual smoke: PASS
- Regression check: no related feature broken

Metrics:
- Files > 400 lines: before X → after Y
- Konsist violations: before X → after Y
- Detekt findings: before X → after Y

Verification:
- compile: PASS
- konsist: PASS
- detekt: PASS
- tests: PASS

Breaking changes:
- (if any) list + migration path

Follow-up:
- (optional) further refactor opportunities noted
```

## Anti-patterns bị cấm

- Refactor + feature work gộp 1 PR
- Refactor + bugfix gộp 1 PR
- Change behavior "incidentally" không plan
- Commit broken intermediate state
- Disable test đang fail "temporarily"
- Rename public API không migration path
- Over-refactor: tạo abstraction cho hypothetical reuse
- Scope creep: refactor ngoài target package
- Skip baseline measurement → không biết regression

## Decision guide — Khi nào refactor vs rewrite

**Refactor** khi:
- Public API stable, chỉ internal structure
- Test coverage đủ cover behavior
- Incremental steps feasible

**Rewrite** (= feature work) khi:
- API cần redesign
- Business logic thay đổi
- Test coverage không đủ confidence → viết test trước, rồi mới refactor hoặc rewrite

## Agent roles

- **Architect** (Stage 1-2): define scope + strategy
- **Implementer** (Stage 3): execute steps
- **Reviewer** (Stage 4-5): verify no behavior change

Xem `agents/*.md`.
