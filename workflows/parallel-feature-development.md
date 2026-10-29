# Workflow: Parallel Feature Development

Orchestrate build **N feature độc lập song song** từ spec. Dùng khi project mới bootstrapping, cần ship nhiều feature cùng lúc, hoặc user explicitly request team mode.

**Golden rule**: parallel chỉ safe khi feature **isolated** (package riêng, không cross-dependency, shared files handled via coordinator).

## Entry conditions

- Spec có ≥ 2 feature declarable
- `orchestration.mode: parallel-features | auto` trong overlay.yaml
- Claude Code (hoặc runtime support Task tool spawn)
- Budget cho 2-4x cost per feature

## Input artifacts

- Spec file(s) trong `docs/specs/` hoặc user prompt
- Overlay config
- Access to `.harness-overlay/upstream/` skills + agents

## Stages

```
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ 1. DECOMPOSE  │──▶│ 2. ISOLATION  │──▶│ 3. SPAWN      │──▶│ 4. AGGREGATE │──▶│  5. REVIEW   │──▶│  6. VERIFY   │
│   (architect) │   │   CHECK       │   │ PARALLEL      │   │   SHARED     │   │ (reviewer)   │   │              │
└───────────────┘   └───────────────┘   └───────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

## Stage 1 — Decompose spec

### Agent role: `architect`

Spawn 1 subagent với role mindset `architect` + `orchestrator` (combined cho stage này).

### Actions

1. Read spec file(s) + user prompt
2. Identify feature boundary — ranh giới feature nằm ở đâu?
3. For each feature:
   - Define scope (what UI, what data, what business logic)
   - Identify owned packages (presenter + domain + data per feature)
   - Identify shared files touched (DI, Nav, resources, analytics registry)
   - Identify dependencies on other features (if any)
4. Write `plans/<date>/plans/<feature-name>.md` per feature
5. Write `plans/<date>/isolation-check.yaml` tổng hợp

### Completion criteria

- 1 plan file per feature
- Isolation YAML listing owned packages + shared files + dependencies
- Each plan < 200 lines

### Blocker conditions

- Features có cross-dependency chain → sequential subset, parallel subset khác
- Features touch cùng package → không parallel được, fallback team mode

## Stage 2 — Isolation check

### Agent role: `orchestrator`

Main agent (hoặc dedicated subagent) verify parallel safety.

### Actions

1. Parse `plans/<date>/isolation-check.yaml`
2. Compute conflicts:
   - **Owned overlap**: 2+ features cùng own 1 package → BLOCK parallel
   - **Cross-dep**: feature A depend feature B output → chạy sequential cho chain đó
3. Decide batching:
   - Independent features → batch cùng lúc (up to `max_concurrent`)
   - Dependent features → sequential sau independent batch done
4. Report plan to user:
   ```
   Parallel safe: 3 features (login, signup, forgot-password)
   Sequential after: 1 feature (profile — depends on login)
   ```

### Completion criteria

- 0 owned-package overlap
- Dependency chain documented
- User approval nếu `auto` mode (optional confirm trước spawn)

### Blocker conditions

- Owned overlap không giải quyết được → fallback team mode cho overlap features
- Spec quá vague → re-run Stage 1 architect với clarification

## Stage 3 — Spawn parallel

### Agent role: `orchestrator`

### Actions

1. For each feature trong current batch:
   ```python
   Task(
       subagent_type="general-purpose",
       description=f"Implement feature {feature.name}",
       prompt=parallel_feature_prompt(feature),
   )
   ```
2. Prompt template (xem `skills/coding-orchestrator/SKILL.md §Parallel feature prompt`)
3. Wait all tasks in batch complete
4. Collect handoff reports từ `plans/handoff/<feature>.md`

### Completion criteria

- Mỗi feature có handoff doc với status
- Status DONE: compile pass + unit test pass + merge instructions complete
- Status BLOCKED/FAILED: logged, orchestrator decide retry hoặc skip

### Blocker conditions

- 1+ feature BLOCKED → orchestrator investigate, có thể retry hoặc proceed với partial batch
- All feature FAILED → stop, surface error to user

### Rules per subagent

- **MUST** operate strictly trong owned packages
- **FORBIDDEN** edit shared files (NavRoute, Module, strings) direct
- **MUST** write merge instructions trong handoff doc
- **MUST** run unit test local (gradle module test) trước claim DONE

## Stage 4 — Aggregate shared files

### Agent role: `orchestrator`

Main agent (serial) apply shared-file changes từ handoff merge instructions.

### Actions

1. Read all `plans/handoff/*.md`
2. Validate template compliance (status + merge instructions present)
3. **DI bindings**:
   - Open `data/di/DataModule.kt`, `domain/di/DomainModule.kt`, `presenter/di/PresenterModule.kt`
   - Append bindings từ each handoff
   - Verify no duplicate class name
4. **Nav routes**:
   - Open `presenter/navigation/NavRoute.kt`
   - Add `@Serializable` sealed subclass per feature
   - Open `presenter/navigation/AppNavHost.kt`
   - Add composable per route
5. **Resources**:
   - Open `presenter/commonMain/composeResources/values/strings.xml` (+ locale variants)
   - Add keys per feature (`feature_<name>_*` namespace)
   - Verify no duplicate key
6. **Analytics**:
   - Open `domain/analytics/AnalyticsEvent.kt` (hoặc registry)
   - Register event names per feature
7. **Remote config** (nếu có):
   - Update `docs/specs/remote-config-registry.md`

### Completion criteria

- All shared files updated với contributions từ all features
- 0 duplicate / conflict
- Single commit "aggregate: feature-A + feature-B + feature-C"

### Blocker conditions

- Duplicate key (ví dụ 2 feature cùng declare `strings/common_submit`) → request subagent fix, không auto-override
- Conflict composable name → rename theo convention + update handoff

## Stage 5 — Review aggregate

### Agent role: `reviewer`

Spawn independent subagent reviewer với full diff.

### Actions

1. `git diff <base>..HEAD` → full aggregate diff
2. Read all `plans/handoff/*.md` + `isolation-check.yaml`
3. Audit theo 10 dimensions `skills/coding-review/SKILL.md`:
   - Architecture (ARCH-001..014)
   - SOLID
   - MVI
   - Compose
   - Coroutines
   - Kotlin
   - Error handling
   - Security
   - Testing
   - Maintainability
4. Plus parallel-specific checks:
   - Each feature package self-contained? (ARCH-006)
   - No cross-feature import ngang hàng?
   - Shared file aggregation correct?
   - Nav routes type-safe?
   - Resource keys namespaced?
5. Write `plans/reports/review-parallel-<date>.md`

### Completion criteria

- 0 BLOCKER findings
- HIGH findings có fix path
- Verdict: APPROVE | APPROVE_WITH_CHANGES | REQUEST_CHANGES

### Blocker conditions

- ≥ 1 BLOCKER → request fix từ owner subagent (re-spawn)
- Multiple HIGH same feature → degrade to team mode retry

### Tool subset (critical)

Reviewer subagent **chỉ Read + Grep + Bash**, **không Edit**. Prevent bias "fix thay vì flag".

## Stage 6 — Verify

### Required gates

```bash
./.harness-overlay/verification/scripts/verify.sh
```

Chạy đủ:
- compile (`./gradlew assemble`)
- unit tests all modules
- Konsist (`./gradlew konsistTest`)
- Detekt
- Build smoke

### iOS gate (optional)

Nếu `architecture.profile: cmp` + có iOS target → `./gradlew :composeApp:iosX64MainKlibrary`.

### Completion criteria

- All required gates PASS
- Advisory gates skip ok (document trong report)

## Final report

```markdown
# Parallel Feature Build Report — <date>

## Features built
- feature-login (12 tests, 450 LOC)
- feature-signup (10 tests, 380 LOC)
- feature-forgot-password (8 tests, 290 LOC)
Total: 3 features, 30 tests, 1120 LOC

## Timing
- Decomposition (Stage 1): 2 min
- Isolation check (Stage 2): 1 min
- Parallel spawn + impl (Stage 3): 15 min wall-clock
  - 3 subagent concurrent
- Aggregate (Stage 4): 3 min
- Review (Stage 5): 5 min
- Verify (Stage 6): 2 min
Total wall-clock: 28 min

Comparison vs sequential single-agent: ~55 min
Speedup: 2x

## Cost
- Agents spawned: 5 (1 architect + 3 impl + 1 reviewer)
- Estimated tokens: ~45k (vs ~15k single) — 3x cost
- ROI: 2x wall-clock speedup justified for new product bootstrap

## Verification
- compile: PASS
- konsist: PASS (10 rules, 0 violation)
- detekt: PASS (baseline shrunk by 2)
- unit_tests: PASS (30 new, 0 fail)
- build: PASS
- ios_build: SKIP (no macOS runner)

## Review findings
- 2 MEDIUM, 1 LOW
- Verdict: APPROVE_WITH_CHANGES

## Shared files aggregated
- DI bindings: 6 added
- Nav routes: 3 added
- Resources: 15 strings
- Analytics events: 12 registered

## Follow-up
- MEDIUM: feature-signup missing offline state render — fix in next PR
- LOW: naming inconsistency "forgot_password" vs "forgotPassword" → stick with snake_case strings
```

## Agent roles summary

| Stage | Role | Tool subset |
|---|---|---|
| 1 Decompose | architect | Read, Grep, Write (plan only) |
| 2 Isolation | orchestrator | Read, Grep, Write |
| 3 Parallel spawn | orchestrator + N implementer | implementer: Read, Edit, Write, Grep, Bash |
| 4 Aggregate | orchestrator | Read, Edit, Write |
| 5 Review | reviewer | **Read, Grep, Bash** (no Edit) |
| 6 Verify | orchestrator | Bash |

## When NOT to use parallel-features

- Features có cross-dependency
- Spec có cross-feature refactor
- Budget cứng, không afford 3x cost
- Feature count = 1 (dùng `coding-feature` + single mode)
- Debug phase cần single-thread trace

## Anti-patterns bị cấm

- Spawn parallel với features overlap packages
- Subagent edit shared file direct (phá coordinator pattern)
- Reviewer tool subset có Edit (bias)
- Max concurrent > 5 (rate limit)
- Skip isolation check Stage 2
- Skip review Stage 5 "để nhanh"
- Aggregate không single commit (lộn xộn history)
- Features overlap scope rồi vẫn force parallel

## Reference

- `skills/coding-orchestrator/SKILL.md` — procedure chi tiết
- `knowledge/meta/agent-orchestration/essentials.md [KB → team/arch-meta-orchestration, kb_search "agent orchestration essentials"]` — modes + patterns
- `agents/orchestrator.md`, `agents/architect.md`, `agents/coder.md`, `agents/reviewer.md`
