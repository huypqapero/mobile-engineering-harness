---
name: bugfix
description: Kick off bugfix-fast-path pipeline. Tech Lead triage check 4 fast-path conditions, route sang fast-path (3 stage, 1-4h) / mini-plan (4 stage) / full-flow (fallback) tùy scope. Dành cho bug report từ user, QA, monitoring, lesson-miner.
priority: P0
---

# Skill: bugfix

Thin wrapper invoke bugfix pipeline qua Tech Lead triage + `bugfix-fast-path` workflow.

## Trigger

- "Fix bug X" / "Fix crash Y" / "Fix lỗi Z"
- "Sửa bug X" / "Khắc phục crash Y"
- Bug report có evidence (repro steps + log/screenshot)
- Hotfix request

## Inputs

Bắt buộc:
- **Bug description**: symptom + repro steps
- **Evidence**: screenshot / logcat / crash log / Sentry link

Optional:
- `--id <BUG-xxx>`: bug tracker ID (Linear/Jira/GitHub Issue)
- `--severity <BLOCKER|HIGH|MEDIUM|LOW>`: default HIGH
- `--affected-screen <name>`: screen bị impact (giúp Tech Lead scout nhanh)

## Procedure

### Step 1 — Tech Lead triage

Spawn Task:

```
Role = Tech Lead. Đọc:
- agents/tech-lead.md (Step 7 Bug triage)
- agents/workflows/bugfix-fast-path.md
- agents/workflows/bug-triage.md (classification rules)

Bug:
- Description: {{bug-description}}
- Evidence: {{evidence paths/links}}
- ID: {{bug-id}}
- Severity: {{severity}}

Task triage:
1. Reproduce evidence
2. Scout codebase xác định file ảnh hưởng (dùng Grep/Read, hoặc skill coding-scout nếu cần)
3. Chạy 4 điều kiện fast-path:
   - Scope ≤ 1 file presenter
   - Không touch shared file (DI, Nav, strings, Analytics, gradle)
   - Label fit (type:bugfix | type:ui-tweak | scope:single-screen)
   - No new dependency
4. Check forbidden flags: security / ADR-011 high-risk / cross-feature contract / migration
5. Verdict:
   - FAST-PATH APPROVED → Stage 2a
   - MINI-PLAN → Stage 2b (Architect shortform)
   - FULL-FLOW → chuyển qua skill `feature` với spec = bug report

Output: plans/reports/triage-bugfix-{{id}}.md với verdict + rationale + file list ước tính.
```

### Step 2a — Fast-path implement (nếu APPROVED)

Spawn Task Coder:

```
Role = Coder. Fast-path mode. Đọc agents/coder.md + triage report.

Scope cứng ≤ 1 file production code.
Task:
1. Fix root cause (không workaround che symptom)
2. Add regression test cover scenario bug
3. Smoke test local + Konsist + Detekt pre-check
4. STOP + raise nếu phát hiện phải touch file thứ 2 → quay triage mini-plan

Output: diff + regression test + brief handoff doc.
```

### Step 2b — Mini-plan (nếu MINI-PLAN)

Spawn Task Architect shortform:

```
Role = Architect, mini-plan mode. Đọc agents/architect.md + triage report.

Task: Viết mini-plan ≤ 50 lines (root cause + fix approach + files touched + risk + verification), save tại plans/<date>-<slug>/mini-plan.md.

Rồi handoff Tech Lead quick review (ADR compliance + regression coverage).
```

Sau mini-plan approved → spawn Coder theo Step 2a flow.

### Step 3 — QA Scope A verify

Spawn Task QA:

```
Role = QA scope A per-screen. Đọc agents/qa.md.

Task verify:
1. Reproduce bug trên build mới → verify fix PASS
2. Run regression test Coder viết
3. Smoke test adjacent flow để catch side-effect
4. Visual compare qua ui-judge nếu UI change

Verdict:
- PASS → close bug, update lesson-miner feed
- FAIL (retry < 3) → loop lại Coder
- FAIL (retry = 3) → auto-escalate Tech Lead (có thể design bug ẩn, chuyển bug-triage.md)
```

### Step 4 — Close + record

- Signoff tại `plans/reports/bugfix-signoff-{{id}}.md`
- Nếu bug thuộc class recurring → trigger `lesson-miner` ingest

## Pre-flight check

- [ ] Bug report có evidence (không chỉ "nó bị lỗi")
- [ ] Repo clean
- [ ] Branch bugfix riêng (hoặc hotfix branch)
- [ ] Có thể reproduce được local hoặc dev build

## Pair với skill khác

- `feature` — khi scope không fit fast-path/mini-plan
- `bug-triage` — nếu đã biết là design bug hoặc spec bug, skip fast-path check
- `coding-diagnose` — low-level root cause analysis
- `coding-review` — review diff bugfix trước commit

## Timing guide

| Pipeline | Agent | Typical time |
|---|---|---|
| Fast-path (≤ 1 file) | tech-lead + coder + qa | 1-4h |
| Mini-plan (2-3 files) | + architect | 4-8h |
| Full-flow (invoke `feature`) | 7+ agent | days |

## Khi NÀO không dùng skill này

- Feature mới không phải fix → dùng `feature`
- Chỉ triage không fix → dùng tech-lead agent standalone
- Spec gap → chuyển product-analyst update PRD trước
