---
name: bug
description: Xử lý bug end-to-end. Dispatcher theo --mode fix|triage (+ cờ --parallel). fix (default) = bugfix-fast-path pipeline, Tech Lead triage check 4 fast-path conditions → fast-path (1-4h) / mini-plan / full-flow. fix --parallel = batch N bug từ Jira/list, cluster theo root cause, scout 1 lần/batch, lane song song giữa cluster, verify matrix + evidence validator deterministic, state bền vững resume được. triage = classify bug không rõ loại (code/design/spec), route Coder/Architect/Product Analyst, escalate PM. Dành cho bug report từ user, QA, monitoring, lesson-miner.
priority: P0
---

# Skill: bug

Dispatcher xử lý bug. **File này chỉ chọn mode.** Sau khi chọn, **đọc đúng file reference và theo procedure trong đó**:

| Mode | Khi nào | Reference thực thi |
|---|---|---|
| `--mode fix` (default) | 1 bug có evidence, chưa classify — mặc định thử fast-path trước | `references/mode-fix.md` |
| `--mode fix --parallel` | **Batch N bug** (Jira/list), fix cùng lúc — cluster + scout 1 lần + lane song song + evidence validator | `references/mode-fix-parallel.md` |
| `--mode triage` | Bug đã fail fast-path, hoặc đã biết không phải code bug (design/spec) — classify + route đúng agent | `references/mode-triage.md` |

Hai mode là 2 câu hỏi khác nhau: `fix` hỏi *fix lớn cỡ nào* (fast-path/mini/full), `triage` hỏi *bug loại gì* (code/design/spec → ai sửa gốc). `--parallel` là biến thể batch của `fix`.

## Mode selection

1. User nêu rõ `--mode` → theo đó.
2. Không nêu → **default `fix`** (bug mới luôn thử fast-path trước).
3. `--parallel` **chỉ khi gọi tường minh** (có `--jql` hoặc danh sách ≥ 2 bug ID). KHÔNG auto-suy ra từ "fix bug X" đơn lẻ — single bug luôn route `mode-fix`. Dùng khi ≥ 3 bug chia được ≥ 2 cluster độc lập file.
4. Chuyển `fix → triage` tự động khi: fast-path fail 2 retry (nghi design bug ẩn), hoặc triage ban đầu đã biết là spec/design bug.

## Trigger

**`--mode fix`**: "Fix bug X" · "Fix crash Y" · "Sửa bug / khắc phục lỗi Z" · bug report có evidence (repro + log/screenshot) · hotfix request.

**`--mode triage`**: "Triage bug X" · "Phân loại bug Y" · QA report FAIL ở Stage 8 feature-full-flow · fast-path của `--mode fix` fail cần re-classify · bug tái diễn > 3 lần dù đã fix.

## Inputs

- **`--mode fix`**: bug description (symptom + repro) + evidence. Optional `--id`, `--severity`, `--affected-screen`.
- **`--mode triage`**: QA bug report path/text + context artifact (PRD / plan.md / code diff). Optional `--retry-count`, `--previous-attempt`.

Chi tiết: xem đầu file reference tương ứng.

## Shared behavior (cả hai mode)

- Step 1 luôn là **Tech Lead triage** (`agents/tech-lead.md §Step 7`).
- Kết thúc luôn **QA re-verify**; PASS → close, FAIL → retry (max theo reference từng mode: single `fix` = 3, `fix --parallel` lane = 2) → escalate.
- Mọi bug close feed `lesson-miner` (code bug → `coding-review` rule; design → architect checklist; spec → requirement-extraction rules).
- Pre-flight check, procedure chi tiết, timing: **trong file reference từng mode**.

## Harness context

- Workflow: `agents/workflows/bugfix-fast-path.md` (fix) + `agents/workflows/bug-triage.md` (triage) + `agents/workflows/parallel-features.md` (pattern lane isolation cho `--parallel`)
- Script: `scripts/validate_evidence.py` (evidence validator deterministic cho `--parallel`), schema `schemas/evidence.schema.json`
- Agent: `agents/tech-lead.md` (triage owner), `agents/coder.md`, `agents/architect.md`, `agents/product-analyst.md`, `agents/qa.md`
- Pair: `/feature` (khi scope vượt fast-path/mini-plan hoặc spec bug cascade rộng), `coding-diagnose` (low-level root cause), `coding-review` (review diff trước commit)
- Guardrails: `~/.claude/rules/development-rules.md`, `review-audit-self-decision.md`, `orchestration-protocol.md`
