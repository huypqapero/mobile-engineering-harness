---
name: harness-handoff
description: Tạo portable continuation contract (markdown) cho fresh agent/session resume task đang dở. Capture outcome, decisions, verification state, blockers, next step. Trigger khi end session, switch model (opus→sonnet), context budget cạn, long task spanning multiple sessions, hoặc handoff cho human teammate.
priority: P1
---

# Skill: harness-handoff

Portable session continuation contract. Markdown self-contained — successor agent (hoặc human) đọc file này đủ để resume task safely mà không cần replay history.

## Trigger

- End of session với task chưa complete
- Switch model (opus → sonnet → haiku) giữa task
- Context budget cạn (> 75% full) — hand off thay vì compaction
- Long task spanning sessions (feature cross-module, migration lớn)
- Handoff human teammate (reviewer, oncall, next-shift)
- Trước khi `/clear` nếu muốn resume sau
- Multi-worktree parallel work — sync state giữa worktrees

## NOT trigger

- Task complete + merged → `coding-sumup` hoặc `harness-journal` thay vì handoff
- Trong-session continuation (chưa cần switch) → không cần handoff
- Simple one-shot query không có state → handoff over-engineer

## Inputs

Bắt buộc:
- Task identifier: issue URL, feature slug, hoặc brief slug
- Current state description (1-2 câu)

Optional:
- `--target: agent|human` (default: agent — concise format; `human` — add context explanation)
- `--out <path>` (default: `plans/<date>/handoff-<slug>.md`)
- `--redact` — strip secrets/tokens từ captured context

## Prerequisites

- Access to current work: branch name, modified files, test state
- `plans/<slug>/` nếu task có plan running

## Execution procedure

### Step 1 — Capture task identity

```markdown
# Handoff: <task slug>

**Captured at:** <ISO 8601 với timezone>
**By:** <agent model + runtime>
**Branch:** <current git branch>
**Target:** agent | human
```

### Step 2 — Capture outcome contract

Snapshot từ brainstorm/plan (nếu có) hoặc user prompt gốc:

```markdown
## Outcome Contract

**Desired outcome:** <reproduce từ brainstorm/plan>
**Constraints:** <list>
**Non-goals:** <list — critical để successor không scope creep>
**Acceptance criteria:**
- [ ] <item> (status: pending|in-progress|done|skipped)
- [ ] <item>
```

### Step 3 — Capture decisions made

List tất cả quyết định quan trọng đã chốt trong session hiện tại:

```markdown
## Decisions

1. **<Decision 1>** (at step X): <what + why>
   - Reference: `plans/<slug>/brainstorm.md §N` hoặc git commit SHA
2. **<Decision 2>**: ...
```

Decision = chọn approach, chọn library, chọn pattern, reject alternative. Không list mọi edit nhỏ.

### Step 4 — Capture current state

```markdown
## Current state

**Branch state:** <modified files count, staged?, pushed?>
**Last successful step:** <step name từ plan>
**In-progress step:** <current step + partial progress>
**Verification state:**
- [ ] Unit test touched: pass | fail | not-run
- [ ] Konsist: pass | fail | not-run
- [ ] Detekt: pass | fail | not-run
- [ ] Lint: pass | fail | not-run
- [ ] Build: pass | fail | not-run
```

### Step 5 — Capture blockers

```markdown
## Blockers

### B1 — <short name>
- **What:** <symptom>
- **Attempted:** <N attempts, approaches tried>
- **Hypothesis:** <current theory>
- **Next step:** <concrete action successor should take>
- **References:** <log file paths, stack trace excerpts, related knowledge/*.md>

### B2 — ...
```

Blocker không có "attempted" + "next step" = useless cho successor.

### Step 6 — Capture file inventory

List file đã touch trong session + classification:

```markdown
## Files modified

| Path | Status | Reason |
|---|---|---|
| path/to/File1.kt | staged | <reason, 1 line> |
| path/to/File2.kt | modified-unstaged | <reason> |
| path/to/NewFile.kt | new-untracked | <reason> |

## Files to touch next

| Path | Expected change |
|---|---|
| path/to/NextFile.kt | <what> |
```

### Step 7 — Capture environment state

```markdown
## Environment

**MCP servers used:** <list — mcp-atlassian, framelink-figma, artemis>
**MCP credentials status:** <configured, OK | missing, action needed>
**Device state** (nếu Android testing active): <serial, booted?, locked?>
**Build cache:** <clean | warm | stale>
```

### Step 8 — Explicit next step

Last section, prominent:

```markdown
## Next action for successor

**Immediate:** <1 command/skill to invoke>
**Example:**
\`\`\`
/skill coding-feature --resume --handoff plans/<date>/handoff-<slug>.md
\`\`\`

**Then:** <subsequent 1-3 bullets high-level>

**Verify before shipping:**
- <checklist item>
```

### Step 9 — Redact (nếu `--redact`)

Scan output cho pattern:
- API keys (sk-*, api_key, token)
- Credentials (password, bearer)
- Email trong non-public context
- Internal URLs (localhost, 10.*, 192.168.*)

Replace với `[REDACTED-<type>]` + note trong metadata section.

### Step 10 — Save + report

Save vào `--out` path (default: `plans/<date>/handoff-<slug>.md`).

Output summary cho user:

```
Handoff written: <path>
- Decisions captured: <N>
- Blockers: <N>
- Verification state: <passing>/<total> gates
- Suggested next skill: <skill name>
- Context budget estimate for successor: ~<N> tokens
```

## Required policies

- Verification state MUST explicit (pass/fail/not-run) — không guess
- Blocker MUST có attempted + next step — không chỉ "stuck"
- Redact mode MUST strip trước khi file persist nếu user flag

## Output contract

Deliverable: 1 markdown file với 8 section:
1. Metadata (date, model, branch, target)
2. Outcome contract
3. Decisions
4. Current state + verification
5. Blockers
6. Files modified + to touch
7. Environment state
8. Next action explicit

File self-contained, successor không cần chat history.

## Validation

- [ ] Mọi section có content hoặc explicit "N/A"
- [ ] Outcome contract có ≥1 acceptance criterion checkbox
- [ ] Verification state 5 gates đủ status
- [ ] Blocker (nếu có) đủ attempted + next step
- [ ] Next action immediate = command executable
- [ ] Nếu `--redact`: 0 secret pattern remain

## Failure / recovery

- Task chưa có outcome contract (user chưa brainstorm) → add placeholder + flag `WARN: outcome not formalized`
- Verification gates không chạy được → mark `not-run` + document reason
- Branch dirty + conflict → capture state as-is, flag `WARN: unmerged changes`

## Anti-patterns

- **AP-001 — Narrative dump**: Viết văn kể lại session. KHÔNG. Successor cần structured facts, không story.
- **AP-002 — Skip verification state**: "Should work" không enough. Explicit pass/fail/not-run per gate.
- **AP-003 — Blocker không actionable**: "Stuck on X" không có next step → successor stuck lại. MUST hypothesis + action.
- **AP-004 — Non-goals optional**: Non-goals = scope guard. Empty → successor scope creep.
- **AP-005 — Full chat log include**: Handoff ≠ transcript. Chỉ decisions + state + blockers.
- **AP-006 — Secret leak**: Token/password/internal URL trong handoff file persist = security risk. Default redact nếu doubt.
- **AP-007 — Decision list empty**: Session đã work ≥ 5 min phải có ≥1 decision. Empty = chưa capture đủ.

## Handoff (meta — handoff của handoff)

File handoff → successor:
- Fresh Claude Code session: user mở file, successor read first turn
- Different runtime (Codex, Cursor): file portable markdown, readable universal
- Human teammate: `--target human` thêm context explanation section

Successor skill routing:
- Resume feature: `coding-feature --resume --handoff <path>`
- Resume bug fix: `coding-diagnose --mode bug --resume --handoff <path>`
- Resume review: `coding-review --resume --handoff <path>`

## Compare với skill khác

- `coding-sumup`: post-completion recap. Handoff = mid-task, task chưa xong.
- `harness-watzup`: end-of-session report cross-task (xem gì đang in-flight). Handoff = single task deep.
- `harness-journal`: chronological log. Handoff = snapshot current state cho resume.
- `ak-handoff`: tương tự nhưng có `--dispatch` để spawn remote runtime. Harness handoff = file-only, không dispatch.

## Future

- Auto-detect handoff trigger (context > 75% → prompt save handoff)
- `--dispatch` option spawn new session với handoff loaded
- Handoff validation gate — successor refuse resume nếu file thiếu section
- Diff tool handoff-to-handoff cho multi-session tracking

---

## Harness context

- Workflow: `(standalone; không gắn pipeline cố định)`
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`


## Overlay gate (D-full)

Trước Step 1, verify `.harness-overlay/overlay.yaml` tồn tại. Nếu không, abort với status `BLOCKED` và chỉ dẫn user:

> Chưa có overlay. Chạy skill `harness-init` để scaffold trước, sau đó quay lại skill này.

Khi gặp placeholder `{{X}}` trong procedure/code example, resolve bằng mapping ở `AGENTS.md §Placeholder resolution` (Read overlay 1 lần đầu session, cache qua context).
