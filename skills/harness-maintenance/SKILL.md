---
name: harness-maintenance
description: Audit + improve + evolve chính harness (rule/skill/knowledge/blueprint/eval). Dùng bởi Harness Guardian agent, không bởi product coding agents. Trigger khi scheduled routine, user invoke audit, hoặc coding agent feedback accumulate.
priority: P1
---

# Skill: harness-maintenance

## Trigger

- User invoke `harness-guardian` role
- Scheduled routine (health check daily, knowledge audit weekly, eval monthly)
- Coding agent feedback accumulate (3+ similar reports)
- Official doc update (Kotlin/Compose/Android version bump)
- Benchmark regression detect
- PR vào harness repo

## Prerequisites

1. `.harness/agents/harness-guardian.md` — role mindset
2. `.harness/knowledge/harness-governance/essentials.md` — permission levels + protected baseline
3. `.harness/workflows/harness-maintenance.md` — change lifecycle
4. GitHub repo access với `gh` CLI
5. (Optional) `registry/*.yaml` cho impact analysis fast

## Modes

### `audit` — Report only, không change

**Scheduled routines**:

| Frequency | Routine | Scope |
|---|---|---|
| Daily | Health check | Broken link, orphan file, registry inconsistency, metadata validity |
| Weekly | Knowledge audit | External doc change (Kotlin/Android/Compose), feedback triage |
| Monthly | Harness evaluation | Benchmark run, regression analysis, improvement proposal |
| On PR | Change validation | Affected rules, schema, cross-reference, review scope |

**Output**: `plans/reports/guardian-audit-<type>-<date>.md`.

### `maintain` — Fix L0-L2 changes

**Trigger**: user invoke OR audit found actionable issue.

Scope limited:
- L0 auto-commit (typo, link, format)
- L1 PR auto-merge (docs, examples)
- L2 PR independent review (skill procedure, workflow stage)

**Not scope**: L3 constitution/ADR change (require user approve).

### `evolve` — Propose L2-L3 changes

**Trigger**: user explicit request.

Guardian research + draft proposal + benchmark:
- New rule candidate (ví dụ "add rule for Compose SharedTransitionLayout")
- ADR revision candidate (ví dụ "revise ADR-007 for Compose 1.9 state hoisting")
- Skill restructure (ví dụ "split android-compose into 3 focused skills")

Produce `plans/proposals/PROPOSAL-NNN.md`. Không auto-apply L3.

## Execution procedure

### Step 1 — Signal + triage

Identify change signal:
- External: official doc change, framework release
- Internal: PR, coding agent feedback, benchmark regression
- Scheduled: audit routine detect anomaly

Triage root cause:
- Harness bug (rule outdated, skill procedure wrong)?
- Coding agent bug (misinterpret rule)?
- External change (framework update)?

Classification wrong → wrong fix.

### Step 2 — Impact analysis

Nếu có `registry/`, query YAML. Else grep + manual trace:

```bash
# Find rule references
grep -rln "ARCH-007" constitution/ knowledge/ skills/ blueprints/ workflows/ agents/ evaluations/

# Find skill consumers
grep -rln "android-mvi" workflows/ agents/ AGENTS.md

# Find knowledge dependents
grep -rln "knowledge/coroutines/essentials.md" skills/ blueprints/
```

Output: impact map
```yaml
affected:
  rules: [ARCH-007, MVI-001]
  knowledge: [mvi/essentials.md, presentation/ui-state.md]
  skills: [android-mvi, android-feature, android-code-review]
  blueprints: [reference-feature]
  evaluations: [E02, E09]
  agents: [architect, implementer, reviewer]
```

### Step 3 — Classify permission level

Dựa trên scope impact:

- Typo / link / index → **L0**
- Doc update, example add, non-behavior change → **L1**
- Skill procedure, workflow stage, Konsist rule → **L2**
- Constitution rule, ADR, architecture policy → **L3** (require user approval)

**Protected Baseline** (12 ADR cốt lõi): Guardian **không được** tự modify. Chỉ propose L3.

Chi tiết: `knowledge/harness-governance/essentials.md`.

### Step 4 — Draft change proposal

Produce `plans/proposals/PROPOSAL-<id>.md`:

```markdown
# Proposal: <title>
ID: PROPOSAL-NNN
Level: L0 | L1 | L2 | L3
Date: YYYY-MM-DD

## Rationale
<evidence-based, not opinion>
Example: Kotlin 2.1 release deprecates `Flow.flowOn(Dispatchers.Unconfined)` behavior.
Current knowledge/coroutines/essentials.md §Dispatcher states "Unconfined OK for test".
Need update.

## Scope
Files touched:
- knowledge/coroutines/essentials.md §Dispatcher table
- Possibly skills/android-coroutines/SKILL.md §Dispatcher selection

## Rules affected
- CORO-002 (dispatcher inject) — no change
- CORO-010 (test coroutines) — minor doc update

## Diff
<unified diff hoặc file list before/after>

## Risks
- Low: doc-only change
- Backward compat: Yes (behavior rule unchanged)

## Validation plan
- Schema check: markdown lint pass
- Reference check: no broken link
- Konsist test: no change (not affected)
- Benchmark: run E03 (concurrency scenario) — expect no delta

## Rollback plan
Git revert commit <sha>

## Approval
L1 → CI pass + auto-merge
```

### Step 5 — Validate change

Pre-merge gate:

- **Schema**: YAML + markdown parse valid
- **Reference**: cross-link intact (`grep` old reference)
- **Konsist template**: compile check nếu touched
- **Eval regression**: run affected scenarios, compare baseline

```bash
# Reference check script
guardian/scripts/check-references.sh  # (if exists)

# Or manual:
grep -r "old-term" . && echo "FAIL: old reference still present"
```

Guardian **tuyệt đối không được** modify eval fixture để pass benchmark do chính mình broke.

### Step 6 — Review + merge

| Level | Review | Merge |
|---|---|---|
| L0 | None | Auto commit (Guardian token) |
| L1 | Optional (CI green = merge) | Guardian or user |
| L2 | Independent reviewer required | After approval |
| L3 | User approval required | After user sign-off |

Independent reviewer = different agent/human than proposer. Guardian không self-approve.

### Step 7 — Release (if release-worthy)

Nếu change ship-worthy → tag + release:

```bash
# Update CHANGELOG
vim CHANGELOG.md

# Bump version if applicable
# Minor: new feature/rule
# Patch: fix/docs

# Commit + tag
git commit -m "chore: release vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags

# GitHub Release
gh release create vX.Y.Z --notes-file ...
```

Rollback point mandatory — note trong release notes.

## Six capability areas (within this skill)

Hiện tại 1 consolidated skill. 6 capability areas handled:

### 1. Knowledge audit

- Track official docs (Android/Kotlin/Compose/Konsist/Detekt)
- Flag outdated reference
- Verify link alive
- Compare harness guidance vs external best practice

### 2. Policy audit

- Rule conflict detect (ví dụ ARCH-X says Y, ARCH-Z says !Y)
- ADR consistency check
- Severity level duplicate (same rule MUST + SHOULD)
- Missing verification (rule không map Konsist/Detekt)

### 3. Skill maintenance

- Skill length check (> 400 lines → split consider)
- Duplication detect across skills
- Procedure gap (trigger không rõ, prerequisite missing)
- Example staleness

### 4. Blueprint maintenance

- Build check (blueprint reference code compile)
- Pattern staleness (framework update → blueprint outdated)
- Alignment với current rule

### 5. Harness evaluation

- Run `evaluations/templates/` scenarios
- Compare baseline → current
- Delta analysis per dimension
- Flag regression

### 6. Release management

- Semver bump decision
- CHANGELOG assembly
- Rollback point document
- GitHub Release creation
- Notify consumers (Discord webhook, etc.)

## Anti-patterns

| Anti-pattern | Risk |
|---|---|
| Modify protected ADR không user approve | Breaking architecture |
| Self-approve L2/L3 PR | Governance circumvent |
| Modify eval fixture để pass benchmark | Fake metric, hide regression |
| Add rule không user story | Preventive theorizing, bloat |
| Delete rule chưa evidence dead | May remove load-bearing rule |
| Direct push `main` | Bypass review |
| Scope creep: 1 fix → refactor nhiều file | Risky L1 → L2/L3 jump |
| Skip impact analysis | Miss affected consumer |
| Trust all agent feedback as truth | Noise/duplicate/false |
| Guardian spawn Guardian recursive | Loop risk |

## Output contract

- Audit mode: report tại `plans/reports/guardian-audit-<type>-<date>.md`
- Maintain mode: PR với proposal doc + diff
- Evolve mode: proposal tại `plans/proposals/PROPOSAL-<id>.md`
- Release mode: tag + GitHub Release + CHANGELOG entry

## Common mistakes

| Mistake | Fix |
|---|---|
| Skip classification level | Mandatory Step 3 trước action |
| Blur boundary với product coding agent | Guardian NEVER touch product overlay code |
| Approve own change | Independent reviewer mandatory L2/L3 |
| Modify ADR bỏ qua user | L3 require user approve, no exception |
| Benchmark break → modify eval | Modify harness code to pass, không modify test |
| Fix 1 skill → cascading edits | Limit scope, L2 cap per PR |

## Scheduled routines

Cron spec (ngoài scope harness, user setup via GitHub Actions):

```yaml
# .github/workflows/guardian-schedule.yml (user config)
on:
  schedule:
    - cron: '0 2 * * *'    # Daily 2AM health check
    - cron: '0 3 * * 1'    # Weekly Monday 3AM knowledge audit
    - cron: '0 4 1 * *'    # Monthly 1st 4AM harness evaluation

jobs:
  guardian-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Invoke Guardian audit
        run: |
          # Trigger Claude Code session với prompt specific
          # Collect report → PR nếu L0/L1 found
```

User tự setup. Harness document pattern, không impl.

## References

- `agents/harness-guardian.md` — role mindset
- `workflows/harness-maintenance.md` — change lifecycle workflow
- `knowledge/harness-governance/essentials.md` — permission levels detail
- ChatGPT reference: "Harness Guardian" model (2026-10-15)
