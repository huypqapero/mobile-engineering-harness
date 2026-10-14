# Workflow: Fix Bug

Reproduce → isolate root cause → fix cause (không mask symptom) → regression test → verify.

## Entry conditions

- Bug report có đủ: trigger steps, expected vs actual, env (device/OS/version).
- Nếu thiếu → stage 1 request thêm từ user, không guess.

## Input artifacts

- Bug report / crash log / Firebase Crashlytics URL
- Related spec file nếu feature đã document
- Reference: `constitution/architecture-rules.md`, skill liên quan

## Stages

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 1. REPRODUCE │───▶│  2. ISOLATE  │───▶│  3. CAUSE    │───▶│   4. FIX     │───▶│  5. VERIFY   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

## Stage 1 — Reproduce

### Actions

1. Read bug report + logs
2. Reproduce locally: same device/emulator profile, same input
3. Capture minimal repro steps (3-5 steps max)
4. Confirm expected behavior qua spec hoặc user

### Completion criteria

- Repro steps < 10 interactions
- Deterministic (ít nhất 2/3 lần repro)
- Capture state snapshot: screenshot, log, stack trace

### Blocker conditions

- Không repro được → stop, request thêm info từ user hoặc flaky test tracking
- Env-dependent (chỉ 1 device model) → document limitation + propose workaround

## Stage 2 — Isolate

### Actions

1. Narrow scope: feature nào? Layer nào (UI / ViewModel / Repository / DataSource)?
2. Git bisect nếu có working baseline
3. Comment out code để shrink surface
4. Identify changed-what-caused-bug (recent PR?)

### Completion criteria

- File + line range cụ thể suspect
- Confirmed bug KHÔNG do environment (clean build, cache clear vẫn repro)

### Blocker conditions

- Bug cross-module quá rộng → raise architecture concern trước fix
- Phụ thuộc 3rd-party library bug → document + propose workaround

## Stage 3 — Cause

### Actions

1. Prove root cause bằng evidence:
   - Logging ở trace path
   - Debugger breakpoint
   - Unit test fail reproducing bug (bug-first test)
2. Classify cause:
   - **Logic**: wrong state transition, missing branch
   - **Concurrency**: race, cancellation leak, zombie coroutine
   - **State**: lost on config change, incorrect SavedStateHandle
   - **Compose**: recomposition skip, unstable param
   - **Data**: null leak, mapper bug, DTO shape change
   - **Platform**: lifecycle event ordering, permission edge
3. Document hypothesis + evidence trong plan

### Completion criteria

- Root cause stated 1-2 sentence
- Có evidence (log excerpt / test fail output / stack)
- Classification rõ

### Blocker conditions

- Chỉ có symptom, không prove được cause → stop, không fix mù
- Multi-cause suspect → tách thành multiple bugs

## Stage 4 — Fix

### Actions

1. Fix tại **cause**, không tại symptom
   - Ví dụ: UI crash do null → sửa data layer bảo đảm non-null contract, không chỉ null-check UI
2. Minimal change scope — không gộp refactor
3. Preserve public API trừ khi bug chính là API
4. Add bug-first test → verify fix makes it pass
5. Add regression test cho edge case liên quan

### Required policies

- ARCH-001..014 (nếu bug cross-layer)
- CORO-001..010 (nếu bug concurrency)
- KOT-002 null safety
- Không `@Ignore` test cũ, không "temporary fix" không issue link

### Completion criteria

- Bug-first test PASS sau fix
- Toàn bộ test suite PASS (không regression)
- Diff scope minimal (< 50 lines ưu tiên)

### Blocker conditions

- Fix tại cause gây breaking change ngoài scope → raise với user, propose refactor plan trước fix
- Fix impact feature khác → document trong report

## Stage 5 — Verify

### Required gates

```bash
./gradlew :{{MODULE_DOMAIN}}:test :{{MODULE_PRESENTER}}:test :{{MODULE_DATA}}:test
./gradlew konsistTest
./gradlew detekt
./gradlew :{{MODULE_APP}}:assembleDebug
```

Chạy đủ 4 gates. iOS build nếu env support.

### Manual verify

- Re-run repro steps từ Stage 1 → expected behavior
- Run related features để check không regression
- Dark mode + large font nếu bug UI-related

### Completion criteria

- 4 gates PASS
- Repro steps không còn repro bug
- Related features không bị regression

## Report format

```
Status: VERIFIED | VERIFIED_WITH_LIMITATIONS | BLOCKED | FAILED

Bug summary:
<1-2 câu, outcome>

Root cause:
<classified: logic/concurrency/state/compose/data/platform>
<evidence summary>

Fix:
- File changed: X, Y, Z
- Approach: cause-level fix, not symptom
- Breaking change: none / minor / major
- Regression test added: yes (file path)

Verification:
- Repro steps: no longer reproduce
- Unit tests: PASS (N new)
- Konsist: PASS
- Detekt: PASS
- Build: PASS
- Manual QA: PASS

Limitations:
- iOS build chưa test (env)
- Edge case Y chưa cover (reason)

Follow-up:
- (optional) refactor suggestion ở area X
- (optional) related bug Y vẫn open
```

## Auto-fix loop (R-03)

Khi gate fail trong Stage 5 (Verify), agent có thể auto-fix với **limit**:

```
Loop:
  1. Compute failure fingerprint (xem knowledge/auto-fix/essentials.md)
  2. Classify failure (xem skills/android-debug §Failure classifier)
  3. Check attempts tracked in plans/<date>/fix-attempts.yaml
     - If fingerprint lặp without progress → ESCALATE (stop loop)
     - If current_attempts >= max_fix_attempts (default 3) → ESCALATE
  4. If classification routes to USER (device/infra/env) → ESCALATE không retry
  5. Else apply fix per routing
  6. Rerun gate
  7. If PASS → EXIT; else back to step 1
```

### Rules

- **MUST** compute fingerprint before each attempt
- **MUST** cap attempts (default 3, max 5 per task contract)
- **MUST** classify trước retry — không retry mù
- **FORBIDDEN** modify test assertion để "make it pass" (test fail → review correctness)
- **FORBIDDEN** `@Ignore` test → fake pass
- **FORBIDDEN** retry device/infra/env failures (escalate ngay)

### Escalation output

```yaml
# plans/reports/escalation-<date>-<task-id>.md
Status: ESCALATED
Reason: fingerprint_loop | attempts_exceeded | classification_route_to_user
Classification: build | code | test | device | infra | env
Last error: ...
Attempts history: ...
Suggested next step: ...
```

User (hoặc orchestrator) decide: continue manually, change scope, abort task.

## Anti-patterns bị cấm

- "Fix" bằng try/catch nuốt exception
- Null-check UI khi contract data layer phải non-null
- Disable test đang fail cùng với fix
- `@Ignore` không link issue
- Workaround cho library bug mà không ghi comment giải thích
- Fix multiple bugs trong 1 PR (reviewer khó verify)
- Add TODO không link issue sau fix
- Gộp refactor vào bugfix PR

## Agent roles

- **Debugger** (Stage 1-3): prove cause
- **Implementer** (Stage 4): minimal fix
- **Test Engineer** (Stage 4-5): regression coverage
- **Reviewer** (Stage 5): verify cause-level fix, không mask

Xem `agents/*.md` cho mindset mỗi role.
