# Blueprint: Task Contract

Standardized YAML contract cho mọi task deliver qua harness. Thay cho free-form plan.md.

## Why

- **Consistency**: mỗi task format giống nhau, agent không guess structure
- **Validation**: `mehcli task validate` kiểm tra schema trước khi start
- **Machine-readable**: orchestrator parse YAML quyết routing (mode, verification level, model tier)
- **Audit trail**: diff task contract qua git history track scope change

## Usage

### Create task

```bash
# Copy template
cp .harness-overlay/upstream/blueprints/task-contract/template.yaml \
   plans/FEAT-104.yaml

# Edit fields
vim plans/FEAT-104.yaml

# Validate
mehcli task validate --plan plans/FEAT-104.yaml
```

### Validation errors (install-time)

- Missing REQUIRED field → fail
- Invalid enum value (ví dụ `type: xyz`) → fail
- `execution.max_fix_attempts > 10` → warn (likely runaway)
- `verification.*` all `false` → warn (no quality gate)

### Agent consume

Orchestrator agent reads task contract:

```python
# Pseudo-code
task = parse_yaml("plans/FEAT-104.yaml")

# Mode routing
mode = task.execution.orchestration_mode
if mode == "auto":
    mode = decide_mode(task)   # based on scope + feature count

# Verification level
levels = compute_verification_levels(task.verification)
# Level 1 compile, Level 2 unit, ... → chạy đúng gate

# Model tier
model_overrides = task.model_tier or default_tiers()
```

## Field reference

Xem `template.yaml` — mỗi field có inline comment giải thích.

### Required fields

- `id` — unique task identifier
- `type` — feature / bugfix / refactor / release / spike
- `project` — product name
- `goal` — 1-2 câu outcome
- `acceptance_criteria` — checkable items

### Optional với defaults

- `priority: medium`
- `execution.max_parallel_agents: 2`
- `execution.max_fix_attempts: 3`
- `execution.require_review: true`
- `execution.orchestration_mode: auto`
- `verification.compile: true`
- `verification.unit_test: true`

## Example — Feature task

```yaml
id: FEAT-105
type: feature
project: my-app
priority: high

goal: |
  Add email login flow với validation + API integration.

scope:
  modules: [feature/auth, domain, data]

acceptance_criteria:
  - Email + password field với client-side validation
  - API call POST /auth/login với error mapping
  - Save token qua SecureStorage
  - Navigate Home sau success
  - Show error banner cho invalid credentials
  - Loading state khi API call

execution:
  max_parallel_agents: 1
  max_fix_attempts: 3
  orchestration_mode: single       # Single feature, không cần parallel

verification:
  compile: true
  unit_test: true
  lint: true
  apk_smoke: true                  # Flow critical → smoke test
  regression: false
```

## Example — Parallel multi-feature task

```yaml
id: EPIC-AUTH-01
type: feature
project: my-app
priority: high

goal: |
  Build auth module (login + signup + forgot-password) song song.

scope:
  modules: [feature/login, feature/signup, feature/forgot-password, domain/auth, data/auth]

acceptance_criteria:
  - Login flow working
  - Signup flow working với email validation
  - Forgot password flow working với reset token

execution:
  max_parallel_agents: 3
  max_fix_attempts: 3
  orchestration_mode: parallel-features
  isolation: feature-package

verification:
  compile: true
  unit_test: true
  lint: true
  apk_smoke: true
  regression: true                 # Auth critical → full regression

model_tier:
  architect: opus                  # Spec decomposition cần reasoning mạnh
  reviewer: opus                   # Audit cross-feature consistency
```

## Example — Bugfix task

```yaml
id: BUG-42
type: bugfix
project: my-app
priority: critical

goal: |
  Fix crash in BookDetail screen khi offline + rotate.

scope:
  modules: [presenter/feature/bookdetail, data]
  avoid: [feature/payment]

acceptance_criteria:
  - No crash khi offline + rotate device
  - State preserved qua config change
  - Error message hiển thị thay crash
  - Regression test added

execution:
  max_parallel_agents: 1
  max_fix_attempts: 2              # Bugfix thường cause rõ, ít retry
  orchestration_mode: team         # Debugger → Fixer → Reviewer

verification:
  compile: true
  unit_test: true
  lint: true
  apk_smoke: true                  # Verify repro không còn
  regression: false

risks:
  - level: medium
    description: Fix at cause level có thể impact related screen
    mitigation: Run related feature smoke test
```

## Rules

- **MUST** validate task YAML trước khi start implementation
- **MUST** update `open_questions` khi phát hiện ambiguity
- **MUST** không mở rộng scope ngoài `scope.modules`
- **SHOULD** add risk + mitigation khi task touch critical path
- **FORBIDDEN** modify task contract after review approved (tạo task mới)

## Migration từ plan.md free-form

Dự án đã có plan.md markdown:

1. Keep plan.md làm **implementation detail** (section "File list", "Decisions", code sample)
2. Add YAML frontmatter với contract fields:
   ```markdown
   ---
   id: FEAT-104
   type: feature
   # ... other YAML fields
   ---
   
   # Plan: Library screen
   
   ## File list
   ...
   
   ## Architecture decisions
   ...
   ```
3. `mehcli task validate` parse frontmatter — same validation.

## Anti-patterns

- Scope creep: mở rộng `scope.modules` giữa chừng → tạo task mới
- All verification `false` → task không có quality gate
- `max_fix_attempts > 5` → prevent runaway
- Multiple goals trong 1 contract → tách thành multiple tasks

## Reference

- `knowledge/cross-cutting/build-strategy/essentials.md` — multi-level build strategy
- `knowledge/meta/auto-fix/essentials.md` — fix attempt pattern
- `knowledge/meta/agent-orchestration/model-tier.md` — model routing
