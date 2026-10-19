---
name: coding-vibe
description: One-shot pipeline từ task intake → PR ready cho Android/KMP feature hoặc bug fix. Chain `coding-brainstorm → coding-scout → coding-feature|coding-diagnose → testing-android → coding-review` với explicit gates. Trigger khi user muốn "ship feature X", "fix bug Y end-to-end", hoặc có GitHub issue/request cần delivery hoàn chỉnh.
priority: P0
---

# Skill: coding-vibe

End-to-end delivery orchestrator. Chain existing coding-/testing- skills với explicit quality gate giữa mỗi step. Không re-implement procedure — chỉ orchestrate + enforce gate.

## Trigger

- "Ship feature X từ issue #123"
- "Fix bug Y, chạy đủ test + review + PR"
- "Làm từ đầu đến cuối cho tôi feature Z"
- GitHub issue URL + yêu cầu delivery
- Request có từ "end-to-end", "full pipeline", "từ brainstorm đến ship"

## NOT trigger

- Scope rõ 1 skill (chỉ compose UI, chỉ add DAO) → invoke skill lẻ, không cần vibe
- User muốn kiểm soát từng step → không auto-chain, suggest từng skill thủ công
- Task read-only (review, scout, explain) → không shipping pipeline

Vibe = heavyweight. Chỉ dùng khi scope đáng.

## Inputs

Bắt buộc:
- Task source: GitHub issue URL, feature request text, hoặc bug description
- Branch intent: new feature branch | existing branch resume

Optional:
- `--skip-brainstorm` nếu outcome contract đã lock sẵn (plan có)
- `--mode: feature|fix|refactor` (default: auto-detect từ task text)
- `--no-ship` dừng trước PR creation, chỉ chuẩn bị commit
- `--advice` spawn kongming advisory ở decision point (từ ak pattern)
- `--yagni` cut scope không cần cho outcome stated

## Prerequisites

Tools cần available:
- `gh` CLI (nếu task là issue URL hoặc tạo PR)
- `git` + clean working tree hoặc rõ branch state
- `./gradlew` + Konsist/Detekt/Lint config
- Device/emulator nếu task touches UI test

Skills cần installed:
- `coding-brainstorm`, `coding-scout`
- `coding-feature` HOẶC `coding-diagnose` (theo mode)
- `testing-android`
- `coding-review`

Nếu skill thiếu → BLOCKED, raise cho user install.

## Pipeline stages

```
┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐
│ Intake  │─▶│Brainstorm│─▶│  Scout  │─▶│ Implement│─▶│   Test   │─▶│  Review  │─▶│  Ship   │
└─────────┘  └──────────┘  └─────────┘  └──────────┘  └──────────┘  └──────────┘  └─────────┘
                  │             │            │             │             │            │
                  ▼             ▼            ▼             ▼             ▼            ▼
              outcome       touch map    code done    tests pass    findings     PR created
              locked        + risks      + verif      Konsist+DT    addressed
```

Mỗi stage có **gate**: không pass → stop pipeline, raise cho user. Không auto-override.

### Stage 1 — Intake

1. Parse task source:
   - URL GitHub → `gh issue view <N>` để fetch title + body + labels
   - Text direct → use as-is
2. Classify mode (nếu không `--mode` explicit):
   - Labels `bug`, `crash`, `anr` hoặc body có "bug/fix/crash" → `fix`
   - Labels `feature`, `enhancement` hoặc body có "add/new/implement" → `feature`
   - Body có "refactor/cleanup/split" → `refactor`
   - Ambiguous → ask user
3. Create plan dir `plans/<date>-<slug>/` nếu chưa có
4. Create feature branch `feat/<slug>` hoặc `fix/<slug>` nếu chưa có

**Gate G1:** task identifier + mode + branch resolved. Fail → BLOCKED.

### Stage 2 — Brainstorm

Nếu `--skip-brainstorm` → skip, use existing `plans/<slug>/brainstorm.md` làm outcome contract.

Else: invoke `coding-brainstorm` với task + mode.

**Output expected:** `plans/<slug>/brainstorm.md` với outcome contract + chosen approach.

**Gate G2:** outcome contract có 4 field (desired/constraints/non-goals/AC) + approach chosen + ≥1 AC measurable. Fail → re-run brainstorm với user clarification.

**Advice hook** (`--advice`): spawn `kongming` cho second opinion về approach chosen trước khi scout.

### Stage 3 — Scout

Invoke `coding-scout` với:
- Target = feature slug hoặc symbol từ bug report
- Scope = module hint từ brainstorm (data/presenter/app)
- `--depth shallow` cho overview, auto-promote `--depth full` nếu touches >5 files

**Output expected:** file inventory + blast radius + suggested files to touch/avoid.

**Gate G3:** scout trả về ≥1 relevant file HOẶC confirm "greenfield area" explicitly. Empty + unclear → re-scout với broader scope.

### Stage 4 — Implement

Route theo mode:

| Mode | Skill | Inputs |
|---|---|---|
| `feature` | `coding-feature` | brainstorm.md + scout output |
| `fix` | `coding-diagnose --mode bug` | bug description + scout output + brainstorm (nếu có) |
| `refactor` | `coding-refactor` | scout output + outcome contract |

**Sub-skills coding-feature có thể invoke:** coding-mvi, coding-compose, coding-coroutines, coding-network, coding-database theo layer touched.

**Gate G4:** 
- Compile pass (`./gradlew compileDebugKotlin`)
- Files touched match scout plan (deviation → log + continue, không block)
- Không violate layer boundary (domain không import Android/Firebase)

Fail → `coding-diagnose --mode bug` loop (max 3 attempts, pattern từ `knowledge/auto-fix/essentials.md`).

### Stage 5 — Test

Invoke `testing-android` với:
- Scope = files touched trong Stage 4
- Level = unit + integration (UI test optional, flag per feature)

**Gate G5:**
- Unit test touched: pass
- Konsist: pass
- Detekt: no new warning
- Lint: no new error
- Build full: pass

Fail → classify theo `coding-diagnose §Failure classifier`:
- `test` category → fix assertion/setup, re-run
- `build` category → fix import/type, re-run
- `code` category → loop back Stage 4 với findings
- `device/infra/env` → ESCALATE user, không retry

Max 3 attempts total trong Stage 5.

### Stage 6 — Review

Invoke `coding-review` với diff từ branch:
- Scope: Clean Arch + SOLID + MVI + Compose lifecycle + concurrency + test quality
- Output: findings với severity (blocker/high/info)

**Gate G6:**
- 0 blocker finding
- High findings: auto-address nếu actionable, hoặc flag + ask user accept
- Info findings: log, không block

Fail blocker → loop back Stage 4 với finding list. Max 2 re-review cycle.

### Stage 7 — Ship

Chỉ chạy nếu không `--no-ship`.

1. Stage files touched (không `git add -A` — risk commit untracked)
2. Compose commit message theo conventional format từ brainstorm outcome:
   ```
   <type>(<scope>): <desired outcome 1 line>
   
   <body — reference brainstorm decisions + non-goals>
   
   Closes #<issue> (nếu task từ issue)
   ```
3. Commit (local, chưa push)
4. Push branch tới remote
5. Create PR qua `gh pr create` với:
   - Title từ commit subject
   - Body từ `plans/<slug>/brainstorm.md §Outcome Contract` + `review.md §Findings addressed`
   - Labels theo mode (`type:feature|type:fix|type:refactor`)
   - Reviewer suggestion (nếu có CODEOWNERS)

**Gate G7:** PR URL returned + CI đã trigger. Fail → raise error, không retry auto.

### Stage 8 — Report

Final summary cho user:

```markdown
## Vibe Complete: <task slug>

**PR:** <URL>
**Branch:** <name>
**Mode:** feature|fix|refactor
**Duration:** <session time>

### Pipeline stages
- [x] Intake — mode detected, branch created
- [x] Brainstorm — approach <A|B|C> chosen (`plans/<slug>/brainstorm.md`)
- [x] Scout — N files touched, M callers
- [x] Implement — <stats: LoC added/removed, files touched>
- [x] Test — Konsist/Detekt/Lint/unit all pass
- [x] Review — <N> findings addressed
- [x] Ship — PR created

### Acceptance criteria status
- [x] AC-1: <criterion>
- [x] AC-2: <criterion>

### Follow-up (optional)
- <item 1>: <why defer>
- <item 2>
```

## Error handling

**Any gate fail > max retry** → STOP pipeline, invoke `harness-handoff` auto với state snapshot. User resume sau khi fix root cause.

**User interrupt** (Ctrl+C hoặc "stop"): save state + auto handoff.

**Context budget cạn** (> 75%): pause + handoff + suggest resume ở session mới.

## Required policies

- Mỗi gate explicit — không "best effort" pass
- Rollback-friendly: không force push, không rewrite history, không skip hooks
- Non-goals từ brainstorm MUST honor — scope creep = AP violation
- Max retry per stage: documented trong Stage 4 (3), Stage 5 (3), Stage 6 (2)

## Output contract

- 1 PR created (nếu `--no-ship`: branch pushed với changes, không PR)
- `plans/<slug>/` directory với brainstorm.md + scout-notes.md + review.md
- Branch với commit theo conventional format
- Verification artifacts: Konsist/Detekt/Lint report attached (comment PR hoặc gist)
- Final report (section Stage 8)

## Validation

- [ ] 7 gate (G1-G7) explicit pass/fail logged
- [ ] Non-goals không violated (compare final diff vs non-goals list)
- [ ] AC coverage: mọi confirmed AC có evidence (test/screenshot/log)
- [ ] PR body reference plan + brainstorm + review
- [ ] CI triggered (nếu team có CI)

## Failure / recovery

- Gate G2 fail (brainstorm empty) → BLOCKED, không skip tới scout
- Gate G4 fail retry exceed → `harness-handoff` auto + ESCALATE
- Gate G6 blocker findings loop infinite → cap 2 cycle + ESCALATE
- Gate G7 push rejected (branch protection) → báo user config, không force
- MCP server disconnect giữa stage → pause + handoff, không continue blind

## Anti-patterns

- **AP-001 — Skip gate silently**: Mỗi gate fail must raise, không auto bypass.
- **AP-002 — Scope creep từ scout findings**: Scout tìm thấy issue khác → log, không auto fix trong vibe này.
- **AP-003 — Mix feature + refactor**: 1 vibe = 1 mode. User muốn cả 2 → 2 vibe runs.
- **AP-004 — Force push to clean history**: Không bao giờ. Mỗi retry = commit mới.
- **AP-005 — Skip test to ship faster**: Gate G5 MUST pass. `--no-test` không support.
- **AP-006 — PR không reference plan**: PR body phải link brainstorm + review. Transparency cho reviewer.
- **AP-007 — Retry infinite**: Max cap mỗi stage. Vượt cap → handoff, không loop.
- **AP-008 — Advice without act**: `--advice` spawn kongming → MUST act on advice hoặc document reject reason.

## Compare với skill khác

- `coding-feature`: single-feature implementation, không chain test/review/ship. Vibe = feature + full pipeline.
- `coding-orchestrator`: multi-feature parallel. Vibe = single-feature end-to-end.
- `ak-vibe`: tương tự pattern nhưng chain React/Next skills. Harness vibe = Android/KMP chain.
- Manual chain: user tự invoke từng skill. Vibe = auto + gate enforce.

## Dispatch mode (future, không auto)

Khi `--dispatch <runtime>`:
- Save vibe plan → handoff file
- Spawn remote runtime (Codex, Cursor) với handoff
- Monitor progress qua webhook/polling

**Hiện tại không support** — chạy local only.

## Handoff

Vibe complete → không handoff (task closed via PR).
Vibe interrupted → auto `harness-handoff` với state.
Vibe partial (`--no-ship`) → return control user với branch state.

## Future

- `--dispatch` cho multi-runtime orchestration
- Auto rollback branch nếu CI fail sau PR
- Metrics: track vibe duration + success rate per stage
- Preset modes: `--preset critical-fix` (skip brainstorm, fast-track test) | `--preset experimental` (relax review threshold)

---

## Harness context

- Workflow: `workflows/feature-development.md, fix-bug.md, review-pull-request.md`
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`


## Overlay gate (D-full)

Trước Step 1, verify `.harness-overlay/overlay.yaml` tồn tại. Nếu không, abort với status `BLOCKED` và chỉ dẫn user:

> Chưa có overlay. Chạy skill `harness-init` để scaffold trước, sau đó quay lại skill này.

Khi gặp placeholder `{{X}}` trong procedure/code example, resolve bằng mapping ở `AGENTS.md §Placeholder resolution` (Read overlay 1 lần đầu session, cache qua context).
