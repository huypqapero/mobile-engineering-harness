---
name: android-orchestrator
description: Route task vào orchestration mode (single/team/parallel-features) + coordinate subagent spawning + aggregate merge-instructions. Trigger khi task multi-feature (spec có 2+ feature), task cross-module risky, hoặc user explicitly request team mode.
priority: P0
---

# Skill: android-orchestrator

## Trigger

- User request "build nhiều feature từ spec cùng lúc"
- Spec có ≥ 2 feature độc lập (parallel candidate)
- Task cross-module risk cao → cần independent reviewer
- `orchestration.mode: team | parallel-features | auto` trong overlay.yaml
- Task size > threshold trong `auto_threshold`
- Request kèm link Confluence/Figma và `spec_sources` bật → Step 0 chạy `android-spec-ingest` trước

## Prerequisites

1. `.harness/knowledge/agent-orchestration/essentials.md` — modes + patterns
2. `.harness/overlay.schema.yaml §orchestration` — config fields
3. Claude Code `Task` tool available
4. `agents/architect.md`, `agents/implementer.md`, `agents/reviewer.md`, `agents/test-engineer.md`, `agents/orchestrator.md`
5. `skills/android-spec-ingest/SKILL.md` — chỉ khi user đưa link Confluence/Figma (Step 0)

## Execution procedure

### Step 0 — Spec intake (optional ingest)

Chạy trước Step 1.

```
INPUT: request của user + overlay.yaml.spec_sources + docs/specs/
├─ Không có link
│   ├─ Spec liên quan có frontmatter generated_by VÀ status: draft
│   │     → dừng, hỏi các OQ Blocking: yes (re-entry android-spec-ingest Step 8) → status: ready → Step 1
│   └─ Còn lại (kể cả spec cũ không có frontmatter)  → Step 1 (flow cũ)
├─ Có link, nguồn tương ứng không bật / không có block spec_sources
│     → in ngay: "spec_sources.<nguồn>.enabled=false → bỏ qua ingest; bật trong overlay để dùng"
│     → Step 1 (flow cũ)
└─ Có link, nguồn bật → chạy android-spec-ingest (skill quyết định với spec đã tồn tại, Step 1.4)
      ├─ SKIPPED                         → Step 1 (flow cũ)
      ├─ DONE (spec status: ready)       → Step 1 với spec docs/specs/<feature>.md
      └─ BLOCKED (status: draft, thiếu MCP/env, hoặc user cần chọn ghi đè)
            → dừng, hỏi user. User trả lời OQ → cập nhật dòng OQ trong spec
              (Trả lời, Blocking: no), status: ready → Step 1
```

Gate `status: draft` chỉ áp dụng cho spec có field `generated_by` (format `blueprints/feature-spec`); spec cũ không có
frontmatter này giữ nguyên hành vi. Step 0 chỉ tạo/cập nhật file spec. Từ Step 1 trở đi mọi subagent đọc
`docs/specs/<feature>.md`, không gọi lại Confluence/Figma.

### Step 1 — Resolve mode

Read `overlay.yaml.orchestration.mode`:

- `single` → skip orchestration, follow `android-feature` skill thẳng
- `team` → sequential subagent spawn (procedure Step 3)
- `parallel-features` → multi-feature spawn (procedure Step 4-7)
- `auto` → decision tree Step 2

### Step 2 — Auto decision

```
INPUT: task description + spec (docs/specs/<feature>.md — viết tay hoặc sinh từ Step 0)
├─ feature_count > 1 AND features_independent → parallel-features
├─ loc_changed > 300 → team
├─ cross_module touched → team
├─ risk_tier == high → team
└─ ELSE → single
```

Threshold từ `orchestration.auto_threshold.*`. Report chosen mode + rationale.

### Step 3 — Team mode (sequential)

```
Phase A — Architect subagent:
  Spawn Task(subagent_type: "architect-mindset", prompt: "...") 
  → plans/<date>/plan.md
  
Phase B — Implementer subagent:
  Spawn Task(subagent_type: "implementer-mindset", prompt: "Read plan.md + implement")
  → code changes + handoff/implementer.md
  
Phase C — Test Engineer subagent:
  Spawn Task(subagent_type: "test-engineer-mindset", prompt: "...")
  → test files
  
Phase D — Reviewer subagent:
  Spawn Task(subagent_type: "reviewer-mindset", prompt: "Review diff...")
  → review-report.md
  
Phase E — Final aggregate:
  Main agent read all handoff → write final report
```

**Rule**: mỗi Task() wait complete trước phase sau. Không spawn parallel trong team mode.

### Step 4 — Parallel-features mode: Spec decomposition

Spawn **1 architect subagent** đọc toàn spec → produce N feature plans:

```
Task(subagent_type: "architect-mindset", prompt: """
  Read spec at docs/specs/<feature-set>.md
  Decompose into N independent feature plans.
  If spec has "## Sources" / "## Open questions" (blueprints/feature-spec), copy the
  Sources rows and the OQ rows relevant to each feature into that feature plan.
  Several specs → qualify OQ ids as <feature>#OQ-n to avoid collisions.
  
  Each feature plan must have:
  - Scope boundary (packages owned)
  - Shared files touched (DI/Nav/resources) — declare for coordinator
  - Dependencies on other features (if any) → block parallel if cross-dep
  - File list new/modified
  
  Output: plans/<date>/plans/<feature-name>.md per feature
  Also: plans/<date>/isolation-check.yaml declaring overlap analysis
""")
```

### Step 5 — Isolation check

Read `plans/<date>/isolation-check.yaml`:

```yaml
features:
  feature-login:
    owned_packages: ["presenter/.../feature/login/", "domain/.../auth/", "data/.../auth/"]
    shared_files: [NavRoute.kt, PresenterModule.kt, DomainModule.kt, strings.xml]
  feature-signup:
    owned_packages: ["presenter/.../feature/signup/", "domain/.../auth/"]
    shared_files: [NavRoute.kt, PresenterModule.kt, DomainModule.kt, strings.xml]

conflicts:
  owned_overlap: []                   # Must be empty
  cross_dep: [[feature-login, feature-signup]]   # If any, those pairs sequential
```

**Rules**:
- `owned_overlap` không empty → **BLOCK** parallel, fallback team mode
- `cross_dep` không empty → chạy sequential cho dependency chain, parallel cho khác
- Shared files overlap OK — handled bởi coordinator pattern

### Step 6 — Spawn parallel subagents

Dựa trên `max_concurrent` (default 3):

```python
# Pseudo-code
features_batch_1 = features[:max_concurrent]   # First 3
features_batch_2 = features[max_concurrent:]    # Next batch

# Spawn batch 1 parallel
tasks = [
    Task(subagent_type="general-purpose",
         description=f"Implement feature {f.name}",
         prompt=parallel_feature_prompt(f))
    for f in features_batch_1
]
# wait all done

# If more, spawn batch 2
```

### Parallel feature prompt template

```
You are implementing feature `{feature.name}` as part of parallel multi-feature build.

OVERLAY: .harness-overlay/overlay.yaml
PLAN: plans/<date>/plans/{feature.name}.md
HANDOFF OUTPUT: plans/handoff/{feature.name}.md

SCOPE BOUNDARY (strict):
- OWN packages: {feature.owned_packages}
- SHARED FILES (DO NOT EDIT directly):
  - NavRoute.kt, AppNavHost.kt
  - *Module.kt (DI)
  - strings.xml, colors.xml
  → DECLARE merge instructions trong handoff doc, orchestrator sẽ apply

FOLLOW:
- android-feature skill (upstream/skills/android-feature/SKILL.md)
- parallel-feature-development workflow Step 3

DELIVERABLES:
1. Code in owned packages (test + implementation)
2. plans/handoff/{feature.name}.md theo template
3. Unit tests passing

Report: Status (DONE/BLOCKED), files changed, test count, open questions.
```

### Step 7 — Aggregator (serial)

Sau khi tất cả parallel subagents done, main agent (orchestrator role):

1. **Read all** `plans/handoff/<feature>.md`
2. **Validate** mỗi handoff theo template (status, merge instructions present)
3. **Aggregate shared files**:
   - **DI bindings**: open `*Module.kt`, append binding snippets từ mỗi handoff
   - **Nav routes**: open `NavRoute.kt`, add sealed subclass; open `AppNavHost.kt`, add composable
   - **Resources**: open `strings.xml`, add key/value per feature
   - **Analytics**: register event names trong `AnalyticsEvent.kt` hoặc analytics registry
4. **Verify** no duplicate key, no name conflict
5. **Commit** aggregate changes as single commit

### Step 8 — Review

Spawn `Task(reviewer)` với full diff (owned + aggregated):

```
Task(subagent_type: "reviewer-mindset", prompt: """
  Review parallel feature build:
  - Features: {feature-list}
  - Diff: git diff <base>..HEAD
  - Isolation check: plans/<date>/isolation-check.yaml
  - Each handoff: plans/handoff/*.md
  
  Audit:
  - Each feature package self-contained? ARCH-006
  - Shared file aggregation correct? No duplicate/conflict
  - Each feature compile + test pass?
  - Overall architecture compliance?
  
  Follow skills/android-code-review/SKILL.md 10 dimensions.
  Output: plans/reports/review-parallel-<date>.md
""")
```

### Step 9 — Verify + report

```bash
./verify.sh                             # konsistTest + detekt + tests + build
```

Final report at `plans/reports/orchestration-<date>.md`:

```markdown
# Orchestration Report — <date>

## Mode: parallel-features
Features built: 3 (login, signup, forgot-password)
Max concurrent: 3

## Timing
- Decomposition: 2 min
- Parallel implementation: 15 min wall-clock (vs ~45 min sequential)
- Aggregation: 3 min
- Review: 5 min
- Verify: 2 min
Total: 27 min (vs ~55 min single-threaded)

## Status
- feature-login: VERIFIED (12 tests pass)
- feature-signup: VERIFIED (10 tests pass)
- feature-forgot-password: VERIFIED (8 tests pass)

## Aggregation
- DI bindings added: 6 (2 per feature)
- Nav routes added: 3
- Resources added: 15 strings
- Analytics events registered: 12

## Review
- Findings: 2 MEDIUM, 1 LOW
- Verdict: APPROVE_WITH_CHANGES

## Quality gates
- compile: PASS
- konsist: PASS
- detekt: PASS
- tests: PASS (30 new tests)
- build: PASS

## Cost
- Agents spawned: 5 (1 architect + 3 impl + 1 reviewer)
- Estimated tokens: ~45k (vs ~15k single-threaded) — 3x cost, 2x wall-clock speedup
```

## Required policies

- `agents/orchestrator.md` mindset
- `knowledge/agent-orchestration/essentials.md` patterns
- Isolation strategy enforced (`feature-package` default)
- Shared-file coordinator pattern — no parallel direct edit

## Common mistakes

| Mistake | Fix |
|---|---|
| Spawn parallel feature touching same package | Isolation check Step 5 catch; fallback team |
| Subagent edit shared file direct | Explicit prompt forbid; coordinator aggregate instead |
| Max concurrent quá cao → rate limit | Default 3; cap at 5 for most providers |
| Skip isolation check → race condition | Mandatory Step 5 trước Step 6 |
| Handoff doc incomplete → aggregator fail | Validate template, request subagent fix |
| Reviewer có Edit tool → fix instead of flag | Tool subset: Read + Grep only |
| Parallel chạy nhiều lần duplicate feature | Idempotency check: skip feature nếu plan + handoff đã complete |
| Spawn subagent khi spec ingest còn `status: draft` | Step 0: dừng hỏi user, chỉ đi tiếp khi `status: ready` |
| Subagent tự đọc lại Confluence/Figma | Chỉ đọc `docs/specs/<feature>.md`; nguồn ngoài chỉ dùng ở Step 0 |

## Output contract

- Spec intake result (Step 0): skipped + lý do, hoặc spec path + status
- Mode decision + rationale (in orchestration report)
- Plans per feature (parallel-features mode)
- Isolation check YAML
- Handoff doc per feature
- Aggregate shared-file commit
- Review report
- Final orchestration report với cost + timing

## Anti-patterns bị cấm

- Spawn parallel khi features có cross-dependency
- Subagent fork rule MUST không rationale
- Aggregate shared file có duplicate key
- Reviewer với tool edit (bias risk)
- Max concurrent > 5 (rate limit)
- Skip verify gate sau aggregate
