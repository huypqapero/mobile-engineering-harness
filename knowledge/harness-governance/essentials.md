# Harness Governance — Essentials

Rule + process cho **Harness Guardian** maintain harness. Governance layer khác với product rule (ARCH-*, CORO-*, KOT-*) — governance quyết **who can change what**.

## Permission levels

4 levels dựa trên blast radius:

| Level | Change type | Auto allowed? | Review | Approval |
|---|---|---|---|---|
| **L0** | Typo, broken link, formatting, index refresh | Yes (auto-commit) | None | None |
| **L1** | Docs update, add example, non-behavior change | PR + CI pass → auto-merge | Optional | None |
| **L2** | Skill procedure, workflow stage, Konsist rule, verification config | PR + CI pass → wait review | **Independent reviewer required** | None |
| **L3** | Constitution rule, ADR, architecture policy change | PR + CI pass + wait approval | Independent reviewer | **User approval mandatory** |

### Decision tree

```
Change scope?
├─ Typo / fix link / rename file → L0
├─ Doc clarification / add example / warning note → L1
├─ Skill procedure change / new workflow stage / Konsist test rule → L2
├─ New rule MUST / modify ADR / change architecture dependency → L3
└─ Delete rule / remove skill → L3 (require evidence rule dead + user approve)
```

### Examples

| Change | Level |
|---|---|
| Fix typo "coroutne" → "coroutine" | L0 |
| Update link to Compose 1.9 docs | L0 |
| Add example to `knowledge/coroutines/essentials.md` | L1 |
| Clarify ARCH-003 rule wording (same meaning) | L1 |
| Modify Step 2 trong `skills/coding-feature/SKILL.md` | L2 |
| Add new Konsist test cho `ARCH-015` | L2 |
| Change Detekt default severity | L2 |
| Add new rule `ARCH-015 Compose state hoisting pattern` | L3 |
| Modify ADR-007 MVI pattern definition | L3 |
| Remove rule `CORO-010` (declare dead) | L3 |
| Change `architecture.profile` enum options | L3 |

## Protected Baseline

**12 ADR cốt lõi** — Guardian **không được** modify tự ý:

- `ADR-001` (hoặc tương đương) ... → Core architecture decisions
- Chi tiết list trong `constitution/architecture-rules.md`

Guardian có thể:
- **Propose** modification via L3 process
- **Research** evidence support change
- **Benchmark** compare old vs proposed

Guardian **không được**:
- Direct edit ADR file
- Self-approve ADR change
- Merge ADR change without user explicit sign-off

### Protected files

Enforce via GitHub CODEOWNERS:

```
# .github/CODEOWNERS
/constitution/architecture-rules.md  @user
/constitution/concurrency-rules.md   @user
/constitution/kotlin-conventions.md  @user
/constitution/engineering-principles.md @user
/agents/orchestrator.md              @user
/agents/harness-guardian.md          @user
```

CODEOWNERS enforce require review before merge. Guardian token must respect.

## Enforcement — Infrastructure, not just prompt

Governance rules **không** depend AI reading prompt. Phải enforce layer infrastructure:

### GitHub level

- **Branch protection** `main`:
  - Require PR reviews (1+ for L2, user for L3)
  - Require status checks (CI, validation script)
  - Prevent force push
  - Prevent direct push

- **CODEOWNERS** cho protected files
- **Required reviewers** per path
- **Required status check** cho release validation

### Repository level

- Guardian token (if dedicated) **không có** `admin` scope
- Guardian token **không có** `delete_branch` permission
- Secret scanning enabled → prevent accidental secret commit

### CI level

- Validate script chạy pre-merge
- Konsist/Detekt baseline check
- Eval regression check (nếu applicable)
- CHANGELOG update required (for L2/L3 changes)

## Review requirements

### Independent reviewer

L2+ change require **independent reviewer**:
- Different agent/human than proposer
- Guardian **không được self-approve**
- Nếu Guardian propose → human reviewer OR separate agent (ví dụ Codex) approve

### Approval workflow

```
L1 → Guardian propose → CI pass → auto-merge
L2 → Guardian propose → CI pass → wait independent review → merge
L3 → Guardian propose → CI pass → wait independent review → wait user approve → merge
```

### Reviewer tool subset

Reviewer agent (nếu AI):
- Tool subset Read + Grep only (giống product code review)
- Không có Edit → flag issues, không fix

## Scope boundaries

Guardian maintain **upstream harness** only:

- IN scope: `constitution/`, `knowledge/`, `skills/`, `blueprints/`, `workflows/`, `agents/`, `verification/`, `evaluations/`, `overlay.schema.yaml`, `install.sh`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `LICENSE`, `CONTRIBUTING.md`

- OUT of scope:
  - Product overlay content (consumer side)
  - Product-specific code (consumer business logic)
  - CI/CD config (user owns)
  - Infrastructure (VPS, device farm, dashboard)

Guardian confused scope → stop, escalate user.

## Signal filtering

Not all signals actionable. Guardian must filter:

| Signal type | Action |
|---|---|
| Agent feedback report (3+ similar) | Investigate, likely actionable |
| Agent feedback (single) | Note, wait for pattern |
| Official doc change (verified source) | Impact analysis mandatory |
| Benchmark regression (consistent) | Investigate |
| Benchmark regression (flaky) | Rerun before action |
| User complaint "feels wrong" | Request evidence, không auto-action |
| Random internet article "best practice" | Dismiss unless authoritative source |

**Rule**: không "just add rule because found article". Evidence must be:
- Official doc (Google/JetBrains/library maintainer)
- Verified pattern (3+ independent reports)
- Measured benchmark improvement

## Change proposal format

Standard proposal structure (chi tiết `workflows/harness-maintenance.md §Stage 4`):

```yaml
---
id: PROPOSAL-NNN
type: knowledge-update | skill-change | rule-add | rule-revise | adr-new
level: L0 | L1 | L2 | L3
author: harness-guardian
date: YYYY-MM-DD
signal_source: <url hoặc internal ref>
---

# Rationale (evidence-based)
# Proposed change (before/after)
# Impact (consumers affected)
# Risks + mitigations
# Validation plan
# Rollback plan
# Approval required
```

Store tại `plans/proposals/PROPOSAL-NNN.md`.

## Audit routines

Scheduled routines produce reports → Guardian maintain mode consume:

| Routine | Cadence | Output |
|---|---|---|
| Health check | Daily | Broken link + orphan + metadata issues |
| Knowledge audit | Weekly | External doc change tracking |
| Harness evaluation | Monthly | Benchmark regression analysis |
| PR validation | Every PR | Affected rules + schema + reference check |

Setup via GitHub Actions (user config). Harness document pattern, không impl runtime.

## Idempotency + reproducibility

- Guardian action **idempotent**: rerun same proposal = same result
- Rollback point mandatory for L2+ changes
- Versioning strict semver — breaking L3 = major bump

## Anti-patterns

| Anti-pattern | Why bad |
|---|---|
| Modify ADR không user approve | Architecture drift, không reproducible |
| Self-approve PR | Governance bypass |
| Modify eval fixture to pass benchmark | Fake metric |
| Preventive rule add không user story | Harness bloat |
| Delete rule không evidence dead | Remove load-bearing |
| Direct push main | Bypass review |
| Scope creep L1 → L3 | Risky change outside scope |
| Trust single-source feedback | Confirmation bias |
| Guardian spawn Guardian | Recursion risk |
| Modify protected file | Governance violation |

## Guardian token scope (if dedicated)

Nếu setup dedicated token cho Guardian:

**Required**:
- `contents: read + write` cho non-protected files
- `pull_requests: write` cho draft PR
- `issues: write` cho report issue (optional)

**Prohibited**:
- `admin` scope
- `delete_branch` permission
- Push `main` direct
- Modify branch protection rules
- Modify CODEOWNERS

Store secret trong GitHub Actions secrets, không hardcode.

## References

- `agents/harness-guardian.md` — role mindset
- `skills/harness-maintenance/SKILL.md` — procedure
- `workflows/harness-maintenance.md` — change lifecycle
- ChatGPT reference: "Harness Guardian" model (2026-10-15)
- GitHub Branch Protection: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches
- GitHub CODEOWNERS: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
