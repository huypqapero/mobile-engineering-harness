---
name: coding-review
description: Review PR, diff, module theo chuẩn {{PRODUCT_NAME}}. Scan Clean Architecture violation, SOLID, MVI, Compose lifecycle, concurrency safety, test quality. Output findings với severity, location, evidence.
priority: P0
---

# Skill: coding-review

## Trigger

- "Review PR #123"
- "Review diff này"
- "Audit module presenter/feature/<x>"
- Trước khi merge feature branch

## Inputs

- PR number / branch / commit range / diff content
- Scope: full diff hoặc file-list cụ thể

## Prerequisites

1. `constitution/architecture-rules.md [KB → develop/constitution, kb_search "architecture rules"]` — 14 ARCH + 3 MOD
2. `constitution/concurrency-rules.md [KB → develop/constitution, kb_search "concurrency rules"]` — CORO-001..010
3. `constitution/engineering-principles.md [KB → develop/constitution, kb_search "engineering principles"]`
4. Project `CLAUDE.md`

## Execution procedure

### Step 1 — Scope + gather diff

```bash
gh pr diff <N>                        # PR diff
git diff <base>..<head>               # Branch diff
git log <base>..<head> --oneline      # Commit list
```

Identify files touched và nhóm theo module (composeApp / presenter / domain / data).

### Step 2 — Review theo dimensions

Checklist bắt buộc, theo thứ tự ưu tiên:

#### A. Architecture (BLOCKER-level)

- [ ] ARCH-001: domain imports không chứa Android/iOS/Firebase?
- [ ] ARCH-002: presenter imports không chứa `{{PACKAGE_ROOT}}.data.*`?
- [ ] ARCH-003: ViewModel field type là UseCase hoặc Repository interface (không `*Impl`)?
- [ ] ARCH-005: Mapper là `object` với extension functions?
- [ ] ARCH-006: Feature package self-contained? Không import cross-feature?
- [ ] ARCH-010: Platform SDK chỉ ở `data/{androidMain,iosMain}/`?
- [ ] ARCH-013: Null-safe mapping, không `!!` trong mapper?

#### B. SOLID

- [ ] SRP: ViewModel không chứa business logic (chỉ orchestrate)?
- [ ] SRP: UseCase chỉ 1 operation?
- [ ] DIP: Dependency theo domain interface, không concrete impl?
- [ ] ISP: Interface không "god" rộng?
- [ ] Composition over inheritance?

#### C. MVI (BLOCKER)

- [ ] ARCH-007: ViewModel extend `BaseViewModel`?
- [ ] State immutable, không `MutableStateFlow` public?
- [ ] Effect dùng `Channel` + `receiveAsFlow()`, không `SharedFlow` cho 1-time event?
- [ ] Navigation là Effect, không State?
- [ ] ARCH-008: 5 UI states coverage?

#### D. Compose

- [ ] `collectAsStateWithLifecycle()` thay vì `collectAsState()`?
- [ ] `items(list, key = { ... })` cho lazy list dynamic?
- [ ] Design token (`{{THEME_CLASS}}.*`), không hardcode color/spacing?
- [ ] Stateless composable hoisted state?
- [ ] Preview ≥ 2 state critical?
- [ ] Accessibility: `contentDescription`, min touch target?

#### E. Coroutines (BLOCKER)

- [ ] CORO-001: Scope rõ (viewModelScope / inject), không GlobalScope?
- [ ] CORO-002: Dispatcher inject qua interface, không hardcode?
- [ ] CORO-003: `supervisorScope` khi tác vụ con độc lập, `coroutineScope` khi phải đồng bộ?
- [ ] CORO-004: `CancellationException` re-throw?
- [ ] CORO-005: StateFlow / Channel / Flow đúng chỗ?
- [ ] CORO-007: `stateIn(WhileSubscribed(5000))` cho shared Flow?

#### F. Error handling

- [ ] `ApiResult` / `DomainError` dùng, không throw raw?
- [ ] Error mapping ở `ErrorMapper` qua CallAdapter / Converter / `safeRequest`; Repository impl không kế thừa base class (ARCH-004)?
- [ ] UI phân biệt 4 error class: network / server / client / unknown?

#### G. Security

- [ ] Không hardcode secret, API key, token?
- [ ] Token lưu `KeyStore` (Android) / Keychain (iOS)?
- [ ] Log không chứa PII, token?

#### H. Testing

- [ ] Unit test cho behavior mới?
- [ ] Test chạy xanh?
- [ ] Không `@Ignore`, không assertion weak (`assertTrue(result != null)` vô nghĩa)?
- [ ] Edge case: null, empty, error, cancellation?
- [ ] `runTest` + inject dispatcher cho coroutine test?

#### I. API compatibility

- [ ] Public API thay đổi có intentional?
- [ ] Nếu có SDK future-ready: `internal` default, `public` qua `<Feature>Api.kt`?

#### J. Maintainability

- [ ] File < 400 dòng?
- [ ] Hàm < 50 dòng?
- [ ] Comment chỉ cho WHY non-obvious?
- [ ] Không TODO không link issue?

### Step 3 — Output findings

Mỗi finding format:

```
### [BLOCKER] ARCH-010 Platform SDK in commonMain
File: presenter/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/presenter/player/MiniPlayerBar.kt:45
Observed:
    import androidx.media3.exoplayer.ExoPlayer
Why it's a problem:
    ExoPlayer là Android-specific. Rule ARCH-010 cấm platform SDK trong commonMain.
    Compile sẽ fail trên iOS target.
Recommended fix:
    Expose qua expect/actual: `expect class AudioPlayer` ở data/commonMain,
    actual implementation ở data/androidMain dùng ExoPlayer.
Verification:
    ./gradlew :presenter:iosX64MainKlibrary (phải pass sau fix)
```

Severity levels:
- **BLOCKER**: vi phạm MUST rule, chặn merge
- **HIGH**: SHOULD vi phạm có risk thực tế
- **MEDIUM**: improvement đáng làm nhưng không chặn
- **LOW**: nitpick, style, naming

### Step 4 — Summary report

```
# PR #42 Review — <feature name>

## Verdict
APPROVE_WITH_CHANGES | REQUEST_CHANGES | APPROVE

## Stats
- Files changed: 12
- Findings: 2 BLOCKER, 3 HIGH, 5 MEDIUM, 2 LOW

## Blockers (must fix)
<list>

## High-priority
<list>

## Suggestions
<list>

## Rules verified PASS
- ARCH-001, ARCH-003, ARCH-007, CORO-001, CORO-004 ...
```

## Review discipline

### Chỉ raise finding với evidence

Mỗi finding phải có:
- File + line number cụ thể
- Observed code snippet
- Rule ID vi phạm (hoặc principle)
- Fix cụ thể, không "làm theo best practice"

### Không review vượt scope

- PR về feature A → không raise finding cho code không touch
- Nếu phát hiện bug cũ nghiêm trọng ngoài scope → ghi "out of scope but noted"

### Verified vs assumed

- Rule nào Konsist/Detekt verify tự động → ghi "verified by Konsist"
- Rule manual review → ghi "manual verification"
- Không claim pass khi chưa thực đọc

## Output contract

Review report theo format Step 4, saved tại:
`plans/reports/code-review-<date>-pr<N>.md`

## Validation checklist cuối

- [ ] Mọi file touched đã scan
- [ ] 10 dimensions (A..J) đã check
- [ ] Finding có severity + evidence + fix cụ thể
- [ ] Konsist / Detekt pass đã verify (hoặc gọi ra là chưa verify)
- [ ] Verdict rõ: APPROVE / APPROVE_WITH_CHANGES / REQUEST_CHANGES

## Anti-patterns reviewer

- "Có thể improve ở đây" không nói cách
- "Follow best practice" vague
- Finding không có file + line
- Approve khi test fail
- Nitpick quá nhiều LOW làm chìm BLOCKER
- Không đọc test → bỏ qua test weak

---

## Harness context

- Workflow: `workflows/review-pull-request.md`
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`


## Overlay gate (D-full)

Trước Step 1, verify `.harness-overlay/overlay.yaml` tồn tại. Nếu không, abort với status `BLOCKED` và chỉ dẫn user:

> Chưa có overlay. Chạy skill `harness-init` để scaffold trước, sau đó quay lại skill này.

Khi gặp placeholder `{{X}}` trong procedure/code example, resolve bằng mapping ở `AGENTS.md §Placeholder resolution` (Read overlay 1 lần đầu session, cache qua context).
