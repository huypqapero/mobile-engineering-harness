# Agent Orchestration — Essentials

Harness support 4 orchestration modes qua `orchestration.mode`. Chọn dựa trên task size + risk + feature count + budget.

## Modes

| Mode | Khi dùng | Cost multiplier | Latency | Risk |
|---|---|---|---|---|
| `single` | Task < 300 LOC, 1 feature, không cross-module | 1x | Nhanh nhất | Self-review bias |
| `team` | Task medium, 1 feature nhưng risk cao | 2-3x | Trung bình | Handoff drift |
| `parallel-features` | **Build nhiều feature từ spec (3-5 features cùng lúc)** | 3-5x | **Nhanh total** nhờ parallel | Shared-file conflict |
| `auto` | Mặc định — harness quyết | Varies | Varies | — |

## Mode decision tree

```
task.feature_count > 1 → parallel-features
                            ↓ else
task.loc_changed > 300 → team
task.cross_module → team
task.risk_tier == high → team
                            ↓ else
single
```

## Mode: `single`

1 agent chạy toàn task. Chuyển mindset qua các role (xem `agents/*.md`):

- Phase inspect → mindset `architect`
- Phase implement → mindset `implementer`
- Phase test → mindset `test-engineer`
- Phase verify → mindset `reviewer`

**Pros**: nhanh, cost thấp, context thống nhất.
**Cons**: self-review bias (reviewer là chính mình), context có thể drift giữa phase dài.

## Mode: `team`

Sequential subagent spawn qua Claude Code `Task` tool. Mỗi role dedicated subagent với context riêng + tool subset.

### Flow

```
1. Main agent spawn Task(architect) → plan.md
   ↓ (wait complete)
2. Main agent spawn Task(implementer) với plan.md context → code changes
   ↓ (wait complete)
3. Main agent spawn Task(reviewer) với diff → findings report
   ↓ (wait complete)
4. Main agent aggregate → final report
```

### Handoff doc protocol

Mỗi subagent write handoff tại `{{ORCHESTRATION_HANDOFF_DIR}}/<role>.md`:

```markdown
# handoff/architect.md

## Scope
<task summary>

## Decisions
- UseCase needed: yes (orchestrate X + Y repos)
- State pattern: data class with 5 branches
- ...

## File list (new / modified)
- domain/model/book/BookDetail.kt (new, ~50 LOC)
- data/repository/BookRepositoryImpl.kt (modify, +15 LOC)
- ...

## Risks + mitigations
- ...

## Open questions
- ...

## Handoff to Implementer
Read `plans/<date>/plan.md` + follow `coding-feature` skill.
```

**Pros**: independent reviewer catch bias, specialization deep per role.
**Cons**: cost 2-3x, latency 3-4 phases serial.

## Mode: `parallel-features` (critical cho spec-driven build)

Spawn N subagent cùng lúc, mỗi subagent 1 feature. Dùng khi spec có **nhiều feature độc lập**.

### Prerequisite: isolation strategy

**`feature-package` isolation** (default, khuyến nghị):

Mỗi feature có package riêng (`presenter/.../feature/login/`, `presenter/.../feature/signup/`). Subagent chỉ edit trong package của feature mình.

**Shared files** (DI binding, Nav route, resources) — subagent **không touch**. Thay vào đó emit "merge instructions" vào handoff.

### Flow

```
1. Architect agent reads spec → produces N feature plans
   plans/<date>/plans/{feature-A,feature-B,feature-C}.md

2. Orchestrator agent verify isolation:
   - Mỗi plan touch package khác nhau? ✓
   - Mỗi plan touch Gradle module khác nhau? OK
   - Shared files declared trong plans? OK

3. Spawn N parallel Task() subagent:
   - Task(impl-A): implement feature-A
   - Task(impl-B): implement feature-B
   - Task(impl-C): implement feature-C
   Each writes:
     - Code trong feature package (safe)
     - Merge instructions to handoff/<feature>.md
         - DI bindings
         - Nav routes
         - Resources (strings/colors)
         - Analytics events

4. Wait tất cả done (parallel barrier)

5. Orchestrator aggregator (SERIAL):
   - Read all handoff/<feature>.md
   - Apply DI bindings to DomainModule.kt + DataModule.kt + PresenterModule.kt
   - Apply Nav routes to NavRoute.kt + AppNavHost.kt
   - Apply resources to strings.xml
   - Commit single consolidated diff

6. Reviewer audit aggregate diff → findings

7. Verify: konsistTest + detekt + tests
```

### Isolation check (bắt buộc trước spawn)

```yaml
# Trước spawn, orchestrator verify:
feature_a:
  packages: [presenter/.../feature/login/]
  shared_files_touched: [NavRoute.kt, PresenterModule.kt]  # merge via handoff
feature_b:
  packages: [presenter/.../feature/signup/]
  shared_files_touched: [NavRoute.kt, PresenterModule.kt]  # merge via handoff
# Conflict check: no package overlap. Shared files handoff OK.
```

Nếu feature A + B touch cùng package (ví dụ cross-feature refactor) → fallback `team` mode, không parallel.

### Handoff format cho parallel

```markdown
# handoff/feature-login.md

## Status
DONE | BLOCKED | FAILED

## Scope
Feature login — email/password + OAuth Google

## Files owned (feature package)
- presenter/.../feature/login/LoginApi.kt (new)
- presenter/.../feature/login/LoginScreen.kt (new)
- presenter/.../feature/login/LoginViewModel.kt (new)
- presenter/.../feature/login/LoginContract.kt (new)
- domain/model/auth/LoginRequest.kt (new)
- domain/usecase/auth/LoginUseCase.kt (new)
- data/dto/LoginDto.kt (new)
- data/remote/AuthApi.kt (modify: +loginEndpoint)
- data/repository/AuthRepositoryImpl.kt (modify: +login method)

## Merge instructions (orchestrator applies)
### DI bindings
- Module: DomainModule
  Code: `factory { LoginUseCase(get()) }`
- Module: PresenterModule
  Code: `viewModel { LoginViewModel(get()) }`

### Nav routes
- Route sealed: `@Serializable data object Login : NavRoute()`
- Composable:
  ```kotlin
  composable<NavRoute.Login> {
      LoginRoute(onBack = { navController.popBackStack() }, onNavigate = ...)
  }
  ```

### Resources
- strings/login_title=Login
- strings/login_email_hint=Email
- strings/login_submit=Sign In

### Analytics events (register)
- login_viewed
- login_submit_tapped
- login_success
- login_failed

## Open questions
- None

## Tests
- LoginViewModelTest.kt (6 tests, all pass)
- LoginUseCaseTest.kt (3 tests, all pass)
```

### Cost / latency trade-off

| Metric | Single | Team | Parallel-features (3 feat) |
|---|---|---|---|
| Total token | 1x | 2-3x | 3-4x |
| Latency wall-clock | 1x | 3x | **1.2-1.5x** (parallel speedup) |
| Agent-hours | 1h | 3h | 3-4h parallel ≈ 1-1.5h wall |

Parallel-features **tối ưu wall-clock time** cho multi-feature build từ spec — critical cho new product bootstrapping.

### Risk mitigation

| Risk | Mitigation |
|---|---|
| Parallel edit same file | Isolation strategy + feature-package default |
| Shared-file race condition | Coordinator pattern — subagent emit instructions, orchestrator apply serial |
| Context drift giữa subagents | Shared plan.md + handoff format strict |
| Subagent fail → block entire run | `max_concurrent` + retry failed slot; không block other feature |
| Cost explosion | `max_concurrent` cap + feature size review trước spawn |

## Mode: `auto`

Harness decision tree:

```python
if spec.feature_count > 1 and features_independent:
    return "parallel-features"
if task.loc_changed > 300 or task.cross_module:
    return "team"
if task.risk_tier == "high":
    return "team"
return "single"
```

Threshold config qua `orchestration.auto_threshold.*`.

## Claude Code Task tool patterns

Spawn subagent:

```python
# Pseudo-code — AI agent dùng Task tool
Task(
    subagent_type="general-purpose",
    description="Implement feature login",
    prompt="""
    You are implementing feature `login` as part of parallel multi-feature build.
    
    Context:
    - Plan file: plans/<date>/plans/feature-login.md
    - Overlay: .harness-overlay/overlay.yaml
    - Follow coding-feature skill in .harness-overlay/upstream/skills/coding-feature/SKILL.md
    - Follow parallel-feature-development workflow
    
    Scope boundary:
    - You own package: presenter/.../feature/login/, domain/.../auth/, data/.../auth/
    - DO NOT edit shared files directly: NavRoute.kt, AppNavHost.kt, *Module.kt, strings.xml
    - DO emit merge instructions to plans/handoff/feature-login.md
    
    Deliverable:
    - Code in owned packages
    - Handoff doc at plans/handoff/feature-login.md with merge instructions
    - Unit tests passing
    
    Report status when done.
    """,
)
```

### Tool subset per role

| Role | Allowed tools |
|---|---|
| architect | Read, Grep, Write (plan only) |
| implementer | Read, Edit, Write, Grep, Bash |
| reviewer | Read, Grep, Bash (test commands) — **no Edit** |
| test-engineer | Read, Edit (test files only), Bash |
| orchestrator | All tools + Task spawn |

Enforce qua Claude Code `subagent_type` + prompt instruction. Harness document patterns; actual enforcement platform-dependent.

## When NOT to use parallel-features

- Features **không độc lập** (feature A depend feature B output)
- Spec có **shared architecture change** (cross-feature refactor)
- Budget cứng, không afford 3-4x cost
- Debug phase — single easier trace
- Team quá small, review bandwidth không đủ

## Common mistakes

| Mistake | Fix |
|---|---|
| Parallel feature touching cùng package | Fallback team mode, không parallel |
| Subagent edit shared file direct → conflict | Isolation rule + handoff merge |
| Max concurrent > 5 → model rate limit | Cap `max_concurrent: 3-5` conservatively |
| Handoff doc missing instructions → orchestrator fail aggregate | Template strict, validate before accept |
| Reviewer spawn với full tool → bias (fix instead of flag) | Tool subset: Read + Grep only |
| Auto mode threshold quá loose → over-spawn | Tune threshold, start conservative |

## References

- `.harness/skills/coding-orchestrator/SKILL.md` — procedure
- `.harness/workflows/parallel-feature-development.md` — workflow
- `.harness/agents/orchestrator.md` — role
- `.harness/agents/*.md` — individual role mindsets
- Claude Code docs — Task tool (external)
