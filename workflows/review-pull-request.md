# Workflow: Review Pull Request

Automated PR review với evidence-based findings. Scope: pending changes, PR number, commit hash, hoặc branch diff.

## Entry conditions

- PR URL / number / branch / commit range cụ thể
- Repo có `AGENTS.md` + constitution rules

## Input artifacts

- Diff: `gh pr diff <N>` hoặc `git diff <base>..<head>`
- Spec file liên quan (nếu feature-related)
- Related rule files trong `constitution/`

## Stages

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  1. SCAN     │───▶│  2. ANALYZE  │───▶│ 3. VERIFY    │───▶│  4. REPORT   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

## Stage 1 — Scan

### Actions

1. `gh pr diff <N>` hoặc `git diff <base>..<head>`
2. List files touched, group theo module
3. Read PR description, linked issues, spec references
4. Determine scope: feature / bugfix / refactor / docs / infra

### Completion criteria

- File list grouped theo module
- Scope classified
- Related constitution rules + skill known

## Stage 2 — Analyze

### Dimensions (bắt buộc check theo thứ tự)

Dùng `skills/android-code-review/SKILL.md` làm checklist chi tiết. Shortened:

**A. Architecture (BLOCKER-level)**
- ARCH-001 domain purity (import check)
- ARCH-002 presenter không import data
- ARCH-003 ViewModel deps (không `*Impl`)
- ARCH-005 Mapper object + extension
- ARCH-006 feature package self-contained
- ARCH-010 platform SDK boundary

**B. SOLID + Clean Arch**
- SRP: ViewModel orchestrate only
- DIP: domain interface, không concrete
- UseCase trivial 1-1 không logic → SKIP (YAGNI)

**C. MVI (BLOCKER)**
- ARCH-007 BaseViewModel inheritance
- No `MutableStateFlow` public
- Nav là Effect, không State
- ARCH-008 5 states coverage

**D. Compose**
- `collectAsStateWithLifecycle()`
- `items(list, key = )`
- Design token (`{{THEME_CLASS}}`), không hardcode
- Preview ≥ 2 states

**E. Coroutines (BLOCKER)**
- CORO-001 no GlobalScope
- CORO-002 dispatcher inject
- CORO-003 supervisorScope vs coroutineScope
- CORO-004 cancellation re-throw
- CORO-005 StateFlow/Channel đúng chỗ

**F. Kotlin**
- KOT-002 no `!!` ngoài giải thích
- KOT-003 no mutable collection expose
- KOT-005 sealed vs data class đúng purpose
- KOT-009 exception specificity

**G. Error handling**
- `ApiResult` / `DomainError` dùng, không throw raw
- Error mapping ở `ErrorMapper` (CallAdapter / Converter / `safeRequest`), Repository impl không kế thừa base class

**H. Security**
- No secret hardcoded
- Token qua KeyStore/Keychain
- Log không chứa PII

**I. Testing**
- Unit test cho behavior mới
- Không `@Ignore` không issue link
- Assertion specific
- `runTest` + inject dispatcher cho coroutine test

**J. Maintainability**
- File < 400 dòng
- Function < 50 dòng
- Comment chỉ non-obvious WHY
- Không TODO stale

### Completion criteria

- Mỗi file touched đã scan qua 10 dimensions
- Finding format: Rule ID, severity, file:line, evidence, fix

### Blocker conditions

- Diff > 500 lines → suggest split PR trước khi review
- Spec mismatch → raise với PR author

## Stage 3 — Verify

### Required

- Konsist: `./gradlew konsistTest` → verify rule MUST không violation
- Detekt: `./gradlew detekt` → verify code quality
- Test suite: `./gradlew test` → verify no regression
- Build: `./gradlew :{{MODULE_APP}}:assembleDebug` → verify compile

### Optional

- Run new unit test khi có fixture available
- Visual preview check nếu Compose UI thay đổi
- Instrumented test nếu platform-sensitive change

### Completion criteria

- 4 required gates PASS trên branch PR
- Finding manual verify qua file read

## Stage 4 — Report

### Finding format

```
### [BLOCKER] <RULE-ID> <short description>
File: path/to/File.kt:line
Observed:
    <code snippet>
Why it's a problem:
    <explain impact + rule rationale>
Recommended fix:
    <concrete code / steps>
Verification:
    <command / test to confirm>
```

### Severity levels

| Severity | Scope | Blocking merge? |
|---|---|---|
| **BLOCKER** | MUST rule violation | Yes |
| **HIGH** | SHOULD rule + clear impact | Review required |
| **MEDIUM** | Improvement rõ ràng | Suggest |
| **LOW** | Nitpick, style, naming | Optional |

### Summary report

```markdown
# PR #<N> Review — <feature name>

## Verdict
APPROVE | APPROVE_WITH_CHANGES | REQUEST_CHANGES

## Stats
- Files changed: X
- Lines: +Y / -Z
- Findings: A BLOCKER, B HIGH, C MEDIUM, D LOW

## Blockers (must fix)
<list findings>

## High-priority
<list findings>

## Medium / Low (suggestions)
<list findings>

## Rules verified PASS
- ARCH-001, ARCH-003, ARCH-007, CORO-001, CORO-004, KOT-002, ...
- (Konsist / Detekt run on branch, log attached)

## Verification run
- compile: PASS
- konsist: PASS (X rules)
- detekt: PASS
- unit_tests: PASS (N tests, 0 fail)
- build: PASS

## Suggested next steps
- (optional) Split large file F into F1 + F2
- (optional) Add missing test for edge case E
```

### Save location

`plans/reports/code-review-<date>-pr<N>.md` trong project.

### Post-back to GitHub (optional)

```bash
gh pr review <N> --comment -b "$(cat plans/reports/code-review-....md)"
```

Hoặc:
```bash
gh pr review <N> --request-changes -b "..."
```

## Review discipline

### Chỉ raise finding với evidence

Mỗi finding bắt buộc:
- Rule ID (hoặc principle)
- File + line number cụ thể
- Observed code snippet
- Fix cụ thể, không "follow best practice" vague

### Verified vs assumed

- Rule nào Konsist/Detekt verify tự động → ghi "verified by Konsist"
- Manual review → ghi "manual verification"
- Không claim pass khi chưa thực đọc

### Không review ngoài scope

- PR về feature A → không raise finding cho code không touch
- Nếu phát hiện bug cũ nghiêm trọng → ghi "out of scope but noted", không block merge

### Nitpick budget

- Max 5 LOW findings per PR. Nhiều hơn → gộp "Style suggestions" 1 block, không spam.
- BLOCKER + HIGH ưu tiên; LOW chỉ note nếu đã cover BLOCKER/HIGH.

## Anti-patterns reviewer

- "Có thể improve ở đây" không nói cách
- "Follow best practice" vague
- Finding không file + line
- Approve khi test fail
- Nitpick quá nhiều LOW che BLOCKER
- Không đọc test → bỏ qua test weak
- Comment mang tính judgmental về author ("you should know this...")
- Review 500+ line diff trong 10 phút không chú trọng

## Agent roles

- **Reviewer** (lead): orchestrate dimensions A→J
- **Architect**: dimension A, B
- **Test Engineer**: dimension I
- Dùng 1 agent cho PR < 300 dòng; cân nhắc tách role cho PR > 500 dòng cross-module

Xem `agents/reviewer.md` cho mindset.
