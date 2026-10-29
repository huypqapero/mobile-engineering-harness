# Workflow: Mine Lessons

Convert tester-filed bugs từ bug tracker (Jira, GitHub Issues, Linear) thành structured lessons feed back vào next-run plan checks + review rules + regression tests.

## Entry conditions

- Bug tracker access (API token qua MCP hoặc gh CLI)
- App code / project id configured
- Memory repo (lessons storage) available — optional, nếu không có thì write local

## Input artifacts

- Bug tracker API endpoint + credentials (từ env/MCP config)
- App identifier (project key, repo name)
- Time range filter (`--since YYYY-MM-DD`)
- Existing lessons snapshot (nếu có memory repo)

## Stages

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  P1. FETCH   │───▶│  P2. CLASSIFY│───▶│  P3. DISTILL │───▶│  P4. MERGE   │───▶│  P5. PR      │
│  bugs từ     │    │  fixed vs    │    │  lessons     │    │  với existing│    │  cho dev     │
│  tracker     │    │  open        │    │  from fixed  │    │  lessons     │    │  review      │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

---

## Stage P1 — Fetch bugs

### Actions

1. Resolve tracker config:
   - Type: `jira` | `github` | `linear`
   - Project/repo identifier
   - Auth qua MCP (`mcp-atlassian` cho Jira) hoặc gh CLI
2. Query bugs:
   - Filter: `project = <key> AND (resolved >= since OR status = open) AND type = bug`
   - Order: most recent first
3. Save raw records: `<out>/bug-records/<ticket-id>.json`

### Example queries

**Jira:**
```
project = ABC AND type = Bug AND (resolved >= -90d OR status = Open)
```

**GitHub:**
```bash
gh issue list --repo <owner>/<repo> --label bug --state all --limit 100
```

**Linear:**
```graphql
query { issues(filter: { team: { key: { eq: "ABC" } }, labels: { name: { eq: "bug" } } }) { ... } }
```

### Completion criteria

- Bug records saved
- Record count ≥ 0 (empty OK, workflow succeeds)

### Blocker conditions

- API auth fail → BLOCKED
- Tracker unreachable → BLOCKED

---

## Stage P2 — Classify

### Actions

Cho mỗi bug record:

| Status | Classification | Next action |
|---|---|---|
| `fixed` + có `fix_commit` | Candidate distill | → P3 |
| `fixed` + không fix evidence | Record only | Skip distill |
| `open` | Record only | Skip distill |
| `wontfix` | Record only + note | Skip distill |
| `duplicate` | Link to canonical | Skip distill |

Save classified records với tag.

### Completion criteria

- Mọi bug có classification tag

---

## Stage P3 — Distill lessons

### Actions

Cho mỗi `candidate distill`:

1. Load:
   - Bug description (steps, expected, actual)
   - Fix commit (nếu có repo access) → diff
   - Fix PR comments
2. Extract 5 components của lesson:
   - **Symptom**: user-observable behavior (từ bug description)
   - **Cause**: root cause (từ fix diff analysis)
   - **Rule**: generalized rule (map tới ARCH/CORO/MVI/KOT id nếu possible)
   - **How to test**: regression test case description
   - **Affected files**: list files touched trong fix
3. Draft lesson YAML (`pending-review`):

```yaml
# <out>/lessons/<lesson-id>.yaml
id: LESSON-2026-NNN
app: <app-code>
feature: <feature-name>
severity: critical | high | medium | low

symptom: >
  <user-observable>

cause: >
  <root cause code pattern>

rule: >
  <generalized rule>

how_to_test: >
  <regression test description>

affected_files:
  - <file1>
  - <file2>

related_bugs:
  - <tracker-prefix>: <ticket-id>
  - <tracker-prefix>: <ticket-id>

tags:
  - <ARCH-NNN or CORO-NNN or similar>
  - <feature-area>

created_at: <ISO>
author: lesson-miner-agent
status: pending-review
```

### Completion criteria

- Mỗi fixed bug với evidence → 1 lesson draft
- No empty symptom/cause/rule

---

## Stage P4 — Merge với existing

### Actions

1. Load `Memory:lessons/*.yaml` (existing)
2. Cho mỗi new lesson:
   - Compute similarity key: hash of (tags + feature + rule prefix)
   - Match với existing lesson cùng key?
3. Merge rules:
   - Match → append `related_bugs`, keep latest `how_to_test`, broaden `symptom` nếu more cases
   - No match → new entry
4. Preserve `created_at` + `author` của original lesson khi merge

### Completion criteria

- Unified lesson set (no duplicates)
- Related_bugs appended correctly

### Blocker conditions

- Memory repo unreachable → write local only, warning

---

## Stage P5 — PR cho dev review

### Actions (nếu memory repo có write access)

1. Create branch trong memory repo: `lessons/<app>-<date>`
2. Commit new/updated lessons
3. Push branch
4. Open PR:
   - Title: `lessons: distill <N> bugs từ <app> (<since>)`
   - Body:
     - Summary: counts (new lessons, merged lessons, bug records)
     - Top findings (3-5 critical lessons)
     - Request review
5. Set lesson status `pending-review` (chờ dev approve)

### Nếu không có repo access

- Write lessons locally vào `<out>/lessons/`
- Report cho user: path + instructions manual PR

### Completion criteria

- PR URL (nếu có) hoặc local path + manual instructions
- Lesson status pending-review

### Blocker conditions

- Memory repo write denied → fallback local, warning

---

## Dev review integration

Dev review PR:
- Approve lesson → merge, status → `approved`, next run plan reviewer use
- Reject → close PR, lesson không propagate
- Request changes → agent re-run với feedback

Rules:
- **MUST** dev approve, không auto-merge
- **MUST** rejected lessons kept với status `rejected` cho audit
- **SHOULD** aggregate 3+ lessons cùng rule → propose constitution ADR update (via Harness Guardian)

---

## Report format

Write report tại `plans/reports/mine-lessons-{date}-{app}.md`:

```markdown
# Mine Lessons Report — <app>

Date: <date>
Period: <since> → <now>
Tracker: <type>

## Summary

- Bug records fetched: <N>
- Fixed with evidence: <N>
- Open: <N>
- WontFix: <N>
- Duplicate: <N>

## Lessons distilled

- New: <N>
- Merged with existing: <N>
- Updated related_bugs: <N>

## Top findings

<Top 3-5 critical lessons với severity + feature + rule>

## PR

<URL nếu có, else local path>

## Review required

Dev review PR trước next harness run consume lessons.
```

---

## Rules

- **MUST** fetch chỉ bug type (không feature request / task)
- **MUST** mọi lesson có symptom + cause + rule + how_to_test (không empty)
- **MUST** related_bugs link ngược về tracker ticket
- **MUST** `pending-review` cho dev approve
- **FORBIDDEN** fabricate lesson không có fix evidence
- **FORBIDDEN** auto-merge PR
- **FORBIDDEN** modify tracker (read-only)
- **SHOULD** map rule tới ARCH/CORO/MVI/KOT id khi possible

---

## Anti-patterns

### AP-001 — Fabricate lessons

Distill từ open bugs chưa fix → speculation. Chỉ distill từ fixed bugs với commit evidence.

### AP-002 — Skip bug records

Chỉ save distilled lessons, skip raw records → mất traceability.

### AP-003 — Over-merge

Merge 2 lessons khác feature nhưng cùng rule → confusing. Keep separate, link via tags.

### AP-004 — Store credentials

API token trong lesson YAML → leak. Credentials ở env/MCP config only.

### AP-005 — Auto apply lessons

Pending-review lessons áp dụng vào next run plan check tự động → chưa validated, risk false alarm.

---

## Downstream integration

### `plan-reviewer` / `coding-review` agent

- Khi review code, load approved lessons với `affected_files` match
- Flag violations của lesson rule
- Suggest fix từ `how_to_test`

### `test-writer` / `e2e-author` agent

- Khi write test cases cho feature, load lessons với `feature` match
- Translate `how_to_test` thành test case
- Mark case `regression: LESSON-NNN`

### `architect` / `planner` agent

- Khi plan feature touching files với lessons, include "consider lesson LESSON-NNN" trong plan rationale

### `harness-guardian`

- Aggregate 3+ lessons cùng rule → propose ADR update
- Audit mode: check if lessons being applied correctly across projects

---

## Agent roles

| Phase | Role |
|---|---|
| P1 Fetch | `lesson-miner` agent + tracker MCP |
| P2 Classify | `lesson-miner` |
| P3 Distill | `lesson-miner` |
| P4 Merge | `lesson-miner` + memory repo access |
| P5 PR | `lesson-miner` + gh CLI |

Dev review PR = human, not agent.

---

## Final output schema

```yaml
app: <app-code>
period:
  since: <date>
  until: <date>
tracker: <type>
summary:
  bug_records: <N>
  fixed_with_evidence: <N>
  lessons_new: <N>
  lessons_merged: <N>
pr_url: <url or null>
local_path: <path>
status: pending-review | partial | failed
```

---

## Rollback strategy

Lessons immutable sau approve. "Rollback" = reject hoặc deprecate với reason:

```yaml
status: deprecated
deprecated_at: <ISO>
deprecated_reason: >
  Rule no longer applicable since <ADR-NNN> update.
```

Deprecated lessons stay trong repo (audit), không active check.

---

## Reference

- `agents/lesson-miner.md` — agent role chi tiết
- `agents/harness-guardian.md` — ADR promotion workflow
- `agents/plan-reviewer.md` (nếu có) hoặc `agents/reviewer.md` — consume lessons
- `constitution/engineering-principles.md [KB → team/arch-constitution, kb_search "engineering principles"]` — rule naming convention
- Bug tracker API docs: Jira REST, GitHub Issues API, Linear GraphQL

## Note về generic vs product-specific

Workflow generic cross-tracker. Downstream config tracker type + memory repo riêng. Harness document pattern + schema, không ship Jira integration code — require MCP server hoặc gh CLI.
