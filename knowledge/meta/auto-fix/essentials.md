# Auto-fix Loop — Essentials

AI agent **không retry infinite**. Mỗi failure có fingerprint; attempt limit cap; escalation path rõ. Prevent cost explosion + loop zombie.

## Core rule

- **MUST**: `max_fix_attempts` default **3**, cap **5**
- **MUST**: compute failure fingerprint để detect same error loop
- **MUST**: nếu fingerprint lặp 2x without progress → **escalate**, không retry
- **FORBIDDEN**: retry infinite "cho đến khi pass"
- **FORBIDDEN**: Disable test / modify assertion để pipeline xanh

## Failure fingerprint

Hash of stable signature → detect "same error repeated".

```python
def compute_fingerprint(failure):
    stack = normalize_stack_trace(failure.stack_trace)
    task = failure.task_id        # Gradle task name
    error_type = failure.exception_class
    return sha1(f"{task}:{error_type}:{stack[:3_frames]}")
```

**Normalize** để tolerant line number drift:
- Strip line numbers trong stack trace
- Keep class/method names
- Keep first 3 frames (ngăn hash drift do stack sâu)

## Attempt tracking

Mỗi task maintain `plans/<date>/fix-attempts.yaml`:

```yaml
task: FEAT-104
attempts:
  - timestamp: 2026-10-14T10:30:00Z
    fingerprint: a1b2c3d4
    classification: build
    change_summary: "Fixed import"
    outcome: FAIL
    progress: true          # New error signature → different problem
  - timestamp: 2026-10-14T10:35:00Z
    fingerprint: e5f6g7h8
    classification: test
    change_summary: "Updated assertion"
    outcome: PASS

max_fix_attempts: 3
current_attempts: 2
```

## Decision loop

```
LOOP:
  1. Agent apply fix (code change)
  2. Run verification gate
  3. If PASS → EXIT success
  4. If FAIL:
     a. Compute fingerprint
     b. Load fix-attempts.yaml
     c. If fingerprint == previous AND no progress → ESCALATE
     d. If current_attempts >= max_fix_attempts → ESCALATE
     e. Append attempt entry → GOTO 1
```

## Progress detection

"Progress" = new error signature khác fix trước. "No progress" = same fingerprint lặp.

| Scenario | Progress? | Action |
|---|---|---|
| Fingerprint A → fix → Fingerprint B | Yes | Continue (new error, moving forward) |
| Fingerprint A → fix → Fingerprint A | No | Escalate (stuck) |
| Fingerprint A → fix → PASS | Done | Exit success |
| Fingerprint A × 3 attempts | — | Escalate (cap reached) |

## Escalation path

Khi escalate:

```yaml
# plans/reports/escalation-<date>-<task-id>.md
Status: ESCALATED
Reason: fingerprint_loop | attempts_exceeded | classification_route

Fingerprint: a1b2c3d4
Classification: build | code | test | device | infra | env

Last error:
  stack: <...>
  summary: <...>

Attempts history:
  - attempt 1: ... → FAIL
  - attempt 2: ... → FAIL (same fingerprint)
  - escalate at attempt 3

Suggested route:
  - If build/code → investigate root cause, likely spec/architecture issue
  - If test → review assertion correctness (not just make it pass)
  - If device → infrastructure recovery (user)
  - If infra → VPS/CI resource (user)
  - If env → version mismatch (user)
```

Agent **không tự route**; report + wait user hoặc orchestrator decide.

## Failure classification routing

| Classification | Who fixes | Fix strategy |
|---|---|---|
| **build** (compile, dep conflict, Gradle) | Coder agent | Fix code / dependency |
| **code** (logic bug, null, race) | Coder + QA | Fix cause, add test |
| **test** (flaky, wrong assertion) | QA + Reviewer | Review assertion correctness FIRST |
| **device** (ADB offline, emulator timeout) | **User** (infra) | ADB restart, device reconnect |
| **infra** (OOM, disk, network) | **User** (infra) | Scale VPS, clean disk, check net |
| **env** (JDK/Kotlin version, SDK missing) | **User** (setup) | Update toolchain |

**MUST** classify trước retry. Classification wrong → retry wrong fix.

Chi tiết classifier: xem `skills/coding-diagnose/SKILL.md §Failure classifier`.

## Special cases — stop immediately

Không retry, surface ngay:

- **OOM / disk full** → infra, không code
- **ADB offline** → device recovery
- **Network timeout CI** → infra
- **Git conflict** → merge human
- **Test assertion wrong** → QA/Reviewer evaluate correctness, **không auto-fix** để pass
- **Dependency version conflict** → ADR decision needed
- **Breaking API change ngoài scope** → outside task scope

## Fix strategies

### For build failures

```
Attempt 1: Resolve immediate error (import, type, syntax)
Attempt 2: Check surrounding context (interface change, migration incomplete)
Attempt 3: Classification review — if same fingerprint → spec/architecture issue
```

### For test failures

```
Attempt 1: Analyze expected vs actual
Attempt 2: Check if assertion correct (not "fix test to pass")
Attempt 3: Escalate — maybe spec unclear
```

### For runtime crash

```
Attempt 1: Fix at cause (not symptom)
Attempt 2: Add defensive handling + regression test
Attempt 3: Escalate — root cause unclear
```

## Anti-patterns bị cấm

- Retry infinite "cho đến khi xanh"
- Disable `@Ignore` test đang fail → fake pass
- Modify assertion value → fake pass
- Catch exception silence → mask bug
- Change rule to "accept violation" → defeat purpose
- Fix one error → spawn 10 others, lặp again
- Ignore classification route, retry mọi loại giống nhau
- Fingerprint tracking disabled → không detect loop

## Orchestrator integration

Orchestrator agent enforce limit:

```python
# Pseudo-code trong orchestrator subagent
def spawn_fix_attempt(task, failure):
    attempts = load_attempts(task)
    if attempts.current >= task.max_fix_attempts:
        escalate(task, "attempts_exceeded")
        return
    
    fingerprint = compute_fingerprint(failure)
    if attempts.last_fingerprint == fingerprint and not attempts.last_progress:
        escalate(task, "fingerprint_loop")
        return
    
    Task(subagent_type="implementer", prompt=fix_prompt(task, failure))
    attempts.append(fingerprint, outcome=TBD)
```

## Monitoring

Dashboard track (Phase 3 — ngoài harness):
- Avg attempts per task
- Fingerprint distribution (top looping errors)
- Escalation rate per classification
- Agent time wasted on retry loop

## Common mistakes

| Mistake | Fix |
|---|---|
| `max_fix_attempts: 10` → runaway cost | Cap 3, max 5 |
| No fingerprint → không detect loop | Mandatory fingerprint compute |
| Classify every error as "code" → wrong fix | Classifier matrix mandatory |
| Retry test failure without reviewing assertion | Review → fix cause or fix test (correct one) |
| Escalate quá sớm (attempt 1) → không productive | Allow 2-3 attempts progress legitimately |
| Fingerprint quá sensitive (hash full stack) | Normalize + top 3 frames only |

## Config

Overlay task contract:

```yaml
execution:
  max_fix_attempts: 3        # Default 3, cap 5
```

Overlay default (optional):

```yaml
# overlay.yaml
orchestration:
  auto_fix:
    default_max_attempts: 3
    fingerprint_normalize: true
    escalate_on_classification: [device, infra, env]   # Auto-escalate these
```

## References

- `skills/coding-diagnose/SKILL.md §Failure classifier`
- `workflows/fix-bug.md §Auto-fix section`
- `agents/orchestrator.md §Fast failure`
- `blueprints/task-contract/template.yaml §execution.max_fix_attempts`
