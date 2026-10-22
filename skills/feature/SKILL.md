---
name: feature
description: Kick off feature-full-flow pipeline cho feature mới. Spawn Orchestrator điều phối chain Product Analyst → PM → Designer → Tech Lead → Architect → Tech Lead review gate → Coder → Reviewer + QA → Release Gate (8 stage). Entry point chuẩn cho mọi feature request.
priority: P0
---

# Skill: feature

Thin wrapper invoke pipeline đầy đủ qua Orchestrator agent + `feature-full-flow` workflow.

## Trigger

- "Implement feature X" / "Add feature X" / "Build feature X"
- "Làm tính năng X" / "Thêm tính năng X"
- Feature request mới chưa có plan.md
- Có PRD/spec nhưng chưa qua pipeline

## Inputs

Bắt buộc:
- **Feature description**: 1-3 câu outcome
- **Feature slug** (optional, auto-generate từ description nếu không có): kebab-case

Optional:
- `--deadline <YYYY-MM-DD>`: target release date (PM lock)
- `--priority <P0|P1|P2>`: default P1
- `--spec <path>`: path spec có sẵn → skip Stage 1
- `--design <path>`: path design có sẵn → skip Stage 3
- `--plan <path>`: path plan.md có sẵn → skip tới Stage 7

## Procedure

### Step 1 — Classify entry stage

Dựa vào input artifact có sẵn:

| Có sẵn | Entry stage | Entry agent |
|---|---|---|
| Chỉ description | Stage 1 Discovery | product-analyst |
| description + spec | Stage 2 Planning | project-manager |
| spec + design | Stage 4 Tech Brief | tech-lead |
| spec + design + plan.md | Stage 7 Implementation | coder (fast-path check trước) |

### Step 2 — Announce workflow

Trước khi spawn, log 1 dòng:
```
Pipeline: feature-full-flow
Entry stage: <N>
Entry agent: <name>
Skip stage: <list nếu có>
```

### Step 3 — Delegate Orchestrator

Spawn Task tool với prompt:

```
Role = Orchestrator. Đọc:
- agents/orchestrator.md
- agents/workflows/feature-full-flow.md
- agents/workflows/README.md (artifact ownership + handoff rules)

Feature:
- Description: {{feature-description}}
- Slug: {{slug}}
- Deadline: {{deadline nếu có}}
- Priority: {{priority}}

Input artifact available:
- {{spec: path | design: path | plan: path | none}}

Task:
1. Entry stage: {{N}}, entry agent: {{name}}
2. Spawn subagent chain theo workflow 8-stage, SKIP các stage đã có artifact
3. Validate handoff doc sau mỗi stage (plans/handoff/{{slug}}/*.md)
4. Escalate PM khi BLOCKER hoặc max retry
5. Report sau mỗi stage completion
```

### Step 4 — Monitor + aggregate

- Theo dõi handoff doc tạo tại `plans/handoff/<slug>/`
- Nếu subagent raise BLOCKER → surface user ngay, không continue
- Pipeline done → aggregate final report tại `plans/reports/feature-{{slug}}-summary.md`

## Pre-flight check

Trước khi kick off, verify:

- [ ] Repo clean hoặc đã commit WIP
- [ ] Branch đúng (feature branch, không main)
- [ ] `./gradlew` wrapper OK (cho stage 7+)
- [ ] Nếu feature có UI → device/emulator ready (cho QA stage)
- [ ] `agents/orchestrator.md` + `agents/workflows/feature-full-flow.md` tồn tại

Thiếu check → surface user, không spawn.

## Output

- `plans/reports/feature-<slug>-summary.md` — aggregate report cuối pipeline
- Chain handoff doc tại `plans/handoff/<slug>/`
- Code changes trong feature branch
- Release Readiness report nếu đi tới Stage 9

## Pair với skill khác

- `bugfix` — khi task là fix bug, không phải feature mới
- `parallel-features` — khi có nhiều feature chạy cùng sprint
- `release` — sau khi feature done, trigger release gate
- `coding-orchestrator` — low-level orchestration cho sub-tasks
- `business-prepare-feature` — nếu chỉ cần làm input layer (brief) chưa muốn full pipeline

## Khi NÀO không dùng skill này

- Task là bugfix nhỏ → dùng `bugfix` thay thế
- Chỉ cần review PR → dùng reviewer agent standalone
- Chỉ cần QA regression → dùng qa agent standalone
- Chỉ cần plan không impl → dùng architect agent standalone
