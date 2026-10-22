# Workflow: Harness Maintenance

Change lifecycle cho **chính harness** — không phải product. Dùng bởi Harness Guardian agent.

**Golden rule**: Guardian **improve** harness, **không được** tùy ý thay đổi architecture foundation đã chốt. 12 ADR cốt lõi là Protected Baseline — require user approval để modify.

## Entry conditions

- Guardian invoke với mode (audit / maintain / evolve)
- Signal nguồn rõ (official doc, feedback, benchmark, user request)
- Harness repo access với governance config

## Stages

```
┌────────┐   ┌────────┐   ┌─────────┐   ┌───────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐
│ Signal │──▶│ Triage │──▶│ Impact  │──▶│ Draft │──▶│ Validate │──▶│  Review  │──▶│ Release │
└────────┘   └────────┘   └─────────┘   └───────┘   └──────────┘   └──────────┘   └─────────┘
```

## Stage 1 — Signal intake

### Sources

| Source | Signal |
|---|---|
| External docs | Android Studio/Kotlin/Compose release notes |
| Framework update | AGP bump, Konsist/Detekt new version |
| Coding agent feedback | Recurring rule violation report |
| Benchmark regression | Eval score drop vs baseline |
| User request | "Add rule for X" |
| CI failure classify | Rule outdated / verification broken |
| PR comment | Reviewer flag harness issue |

### Collect

Store signal tại `plans/signals/<date>-<source>.md`:
```markdown
Signal source: Kotlin 2.1 release notes
Date: 2026-10-15
Content: Flow.flowOn(Dispatchers.Unconfined) deprecated in test context
Reference: https://kotlinlang.org/releases/2.1.0.html
Impact estimate: medium (knowledge/coding/coroutines/essentials.md section Dispatcher)
```

## Stage 2 — Triage

### Classify root cause

- **Harness bug**: rule/skill/knowledge outdated hoặc wrong
- **Coding agent bug**: agent misinterpret correct rule → prompt improvement, không rule change
- **External change**: framework update → harness adapt
- **False positive**: agent feedback incorrect, dismiss với reasoning

### Deduplicate

- Check existing proposals `plans/proposals/`
- Check closed signals `plans/signals/` archive
- Nếu already addressed → close signal

### Decision

- Actionable → proceed Stage 3
- Not actionable (coding agent interpretation issue) → document, không change harness
- Dismiss false positive → archive signal với rationale

## Stage 3 — Impact analysis

### Via registry (if available)

```yaml
# registry/rule-registry.yaml
- id: CORO-002
  knowledge: [coroutines/essentials.md]
  skills: [coding-coroutines, coding-feature]
  blueprints: [reference-feature]
```

Query: "CORO-002 affects which?" → list consumers.

### Via grep (manual)

```bash
# Rule references
grep -rln "CORO-002" constitution/ knowledge/ skills/ blueprints/ workflows/ agents/

# Knowledge consumers
grep -rln "coroutines/essentials.md" skills/ blueprints/ agents/
```

### Impact map output

```yaml
# plans/impact-<proposal-id>.yaml
rules_affected:
  - CORO-002 (dispatcher inject)
  - CORO-010 (test coroutines)
knowledge_affected:
  - coroutines/essentials.md §Dispatcher
skills_affected:
  - coding-coroutines §Step 2 Dispatcher selection
blueprints_affected: []
agents_affected: []
evals_affected:
  - E03 (concurrency search debounce)
```

Impact scope → classification level:
- 0 affected downstream → L0/L1
- 2-3 skills affected → L2
- Constitution rule → L3

## Stage 4 — Draft change proposal

Produce `plans/proposals/PROPOSAL-<id>.md`:

```markdown
# Proposal PROPOSAL-NNN

## Metadata
- ID: PROPOSAL-042
- Type: knowledge-update | skill-change | rule-add | rule-revise | adr-new
- Level: L0 | L1 | L2 | L3
- Author: harness-guardian
- Date: 2026-10-15
- Signal source: <ref>

## Rationale
<evidence>

## Proposed change

### Before
<excerpt current text/code>

### After
<excerpt new text/code>

## Impact (from Stage 3)
<impact map YAML>

## Risks + mitigations
<list>

## Validation plan
- Schema check: ...
- Reference check: ...
- Konsist regenerate test (if applicable): ...
- Benchmark run: ...

## Rollback plan
`git revert <sha>` + CHANGELOG rollback entry

## Approval
Level required: L1 | L2 | L3

Reviewers:
- @independent-reviewer (L2)
- @user (L3)
```

## Stage 5 — Validate

### Pre-merge gate

| Gate | Required for | Tool |
|---|---|---|
| Schema valid | L0-L3 | yaml-lint, markdown-lint |
| Reference intact | L0-L3 | grep script |
| Konsist template compile | L2-L3 (if touched) | gradle konsistTest render check |
| Benchmark regression | L2-L3 | eval scenario run compare baseline |
| Impact map accurate | L2-L3 | manual + registry |

### Rule tuyệt đối

**Guardian không được**:
- Modify eval fixture để pass benchmark do chính mình broke
- Modify rule để lower threshold → pass validation
- Delete test → avoid regression report
- Soften severity → pass audit

Nếu validate fail → **fix harness code**, không modify test.

### Fail path

- Validation fail → revise proposal, không merge
- Max 3 revision attempts (align auto-fix principle)
- 3 attempts fail → escalate (human expert decide)

## Stage 6 — Review + merge

### Permission matrix

| Level | Review | Merge path |
|---|---|---|
| L0 | None | Auto-commit Guardian token |
| L1 | CI pass | Auto-merge PR |
| L2 | Independent reviewer approve | Merge after approve |
| L3 | User approve | Merge after user sign-off |

### Independent reviewer rule

- L2 require review from **different agent/human** than proposer
- Guardian **không được** self-approve
- CODEOWNERS enforce: `constitution/` + `agents/` + protected files require human

### Governance enforcement (infrastructure)

Enforce beyond prompt:
- GitHub branch protection: require review `main`
- CODEOWNERS: `/constitution/*` owner required
- Guardian token: no direct push `main`
- CI gate: proposal file mandatory for L2/L3 changes

## Stage 7 — Release

Nếu change ship-worthy:

```bash
# CHANGELOG update
vim CHANGELOG.md
# Add entry under new version

# Semver decision
# Major: breaking rule change
# Minor: new skill/workflow/knowledge
# Patch: doc/typo/example

# Commit + tag
git add -A
git commit -m "chore(release): vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags

# GitHub Release
gh release create vX.Y.Z \
  --title "vX.Y.Z — <summary>" \
  --notes-file plans/release-notes-vX.Y.Z.md
```

### Release notes mandatory

- Added / Changed / Deprecated / Removed sections
- Migration path (if breaking)
- Rollback instruction

### Notify

- Discord webhook (if configured) auto-fire
- Internal team Slack (user config)
- Email changelog subscribers (user config)

## Scheduled routines

Config via GitHub Actions (user setup, ngoài harness):

| Cadence | Routine | Scope | Trigger |
|---|---|---|---|
| Daily (2AM) | Health check | Broken links, orphans, registry | Lightweight audit |
| Weekly (Mon 3AM) | Knowledge audit | External doc change check | Create signal nếu tracked doc update |
| Monthly (1st 4AM) | Harness evaluation | Run E01-E05 benchmark | Create signal nếu regression |
| On PR | Change validation | Affected rules, schema, refs | Automated reviewer |

Routine output: signal files → Guardian maintain mode next invoke.

## Anti-patterns bị cấm

- Skip classification level → wrong permission path
- Modify ADR without user approve (L3) → architectural drift
- Self-approve L2/L3 PR
- Modify eval fixture để pass benchmark do mới broke
- Add preventive rule không user story
- Delete load-bearing rule without evidence dead
- Direct push `main` branch
- Scope creep: L0 fix → L2 refactor
- Benchmark skip "để nhanh"
- Trust single agent feedback as truth

## Rollback

Nếu release ship wrong:

1. **Identify breaking commit**: `git log` + release notes
2. **Revert path**:
   - Last tag commit still exist → `git revert <sha>` + tag patch version
   - Rollback point marked trong release notes
3. **Communicate**: GitHub Release note update với "⚠ Known issue, use vX.Y.Z-1"
4. **Fix forward**: patch release với fix

## Agent roles

- **Harness Guardian** — primary (xem `agents/harness-guardian.md`)
- **Independent reviewer** — L2/L3 approval (có thể là Codex, hoặc human reviewer)
- **User** — L3 final approval cho ADR/constitution changes

## Example end-to-end

**Scenario**: Kotlin 2.1 release có breaking change trong Flow

```
Stage 1: Signal — ChatGPT scraper detect release notes
Stage 2: Triage — classify "external change", harness need adapt
Stage 3: Impact — affects CORO-002, knowledge/coding/coroutines/essentials.md
Stage 4: Draft — PROPOSAL-042 Level L1 (knowledge update, non-behavior)
Stage 5: Validate — markdown lint PASS, reference check PASS, no eval regression
Stage 6: Review — CI pass, auto-merge
Stage 7: Release — v0.11.1 patch, CHANGELOG entry, GitHub Release
```

Total time: ~30 min với Guardian audit mode + maintain mode.

## References

- `agents/harness-guardian.md` — role mindset
- `skills/harness-maintenance/SKILL.md` — procedure chi tiết
- `knowledge/meta/harness-governance/essentials.md` — permission levels + protected baseline
