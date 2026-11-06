---
name: feature
description: Entry point chuẩn cho mọi feature request. Dispatcher theo scope. Default (1 feature) = feature-full-flow pipeline, spawn Orchestrator chain Product Analyst → PM → Designer → Tech Lead → Architect → review gate → Coder → Reviewer + QA → Release Gate (8 stage). --parallel (N feature độc lập cùng sprint) = Tech Lead feasibility + Architect isolation-check + Orchestrator spawn N lane song song + shared-file aggregation + release bundle gate.
priority: P0
---

# Skill: feature

Dispatcher cho feature delivery. **File này chỉ chọn scope.** Sau khi chọn, **đọc đúng file reference và theo procedure trong đó**:

| Scope | Khi nào | Reference thực thi |
|---|---|---|
| single (default) | 1 feature mới | `references/single.md` |
| `--parallel` | ≥ 2 feature độc lập cần ship cùng sprint (mỗi feature đã qua Stage 1-6, có plan.md approved) | `references/parallel.md` |

## Scope selection

1. User truyền `--parallel` + feature list ≥ 2 → parallel.
2. Mặc định (1 feature, hoặc không có cờ) → single.
3. Parallel nhưng isolation-check fail / N = 1 → fallback single sequential cho từng feature.

Rule of thumb: `--parallel` chỉ worth khi N ≥ 3 và các feature SAFE isolation; N = 2 thường sequential rẻ hơn + ít rủi ro.

## Trigger

**single**: "Implement / Add / Build feature X" · "Làm / Thêm tính năng X" · feature request mới chưa có plan.md · có PRD/spec nhưng chưa qua pipeline.

**`--parallel`**: "Chạy parallel feature X, Y, Z" · "Ship cả 3 feature này cùng sprint" · PM thấy deadline conflict không cắt được scope · backlog N feature đã qua Stage 1-6 độc lập.

## Inputs

- **single**: feature description (1-3 câu outcome) + optional slug. Optional `--deadline`, `--priority`, `--spec`, `--design`, `--plan` (skip stage tương ứng).
- **`--parallel`**: feature list ≥ 2 slug (mỗi slug có plan.md approved) + target release. Optional `--mode safe|unsafe-force`, `--max-concurrent`.

Chi tiết: xem đầu file reference tương ứng.

## Shared behavior

- Cả hai đều spawn **Orchestrator** (`agents/orchestrator.md`) điều phối subagent chain.
- Handoff doc tạo tại `plans/handoff/<slug>/` sau mỗi stage; BLOCKER → surface user ngay, không continue.
- Pre-flight check (repo clean, branch đúng, gradlew OK, device ready nếu UI), output report, rollback: **trong file reference từng scope**.

## Harness context

- Workflow: `agents/workflows/feature-full-flow.md` (single) + `agents/workflows/parallel-features.md` (parallel)
- Agent: `agents/orchestrator.md` (điều phối), chain 8-stage product → engineering → release
- Pair: `/bug` (khi task là fix bug, không phải feature mới), `release` (sau khi feature done → release gate), `coding-orchestrator` (low-level orchestration sub-tasks), `business-prepare-feature` (chỉ cần input layer brief)
- Guardrails: `~/.claude/rules/development-rules.md`, `review-audit-self-decision.md`, `orchestration-protocol.md`
