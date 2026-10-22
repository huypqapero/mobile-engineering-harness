# Agent Workflows — Routing & Handoff

Index các workflow điều hướng giữa 14 agent trong `/agents/`. Orchestrator là LLM agent runtime coordinator, đọc workflow phù hợp để decide spawn + handoff.

## 14 agent — vị trí trong pipeline

```
Product lifecycle layer                 Engineering layer                   Meta
─────────────────────────                ──────────────────                  ─────
product-analyst  (BA)                    tech-lead                          orchestrator
project-manager  (PM)                    architect                          lesson-miner
designer         (UI)                    coder                              harness-guardian
design-analyst   (reverse)               reviewer
                                         qa
                                         ├─ e2e-author (subagent)
                                         └─ ui-judge   (subagent)
```

Tổng: **12 role-based agent** (product/engineering) + **2 subagent QA** + **3 meta agent** = 14 file trong `/agents/`. Orchestrator coordinate 11 còn lại.

## 5 workflow điều hướng

| Workflow | Khi nào dùng | Entry | Exit |
|---|---|---|---|
| `feature-full-flow.md` | Feature mới, scope ≥ 1 screen | Product Analyst | Release Gate |
| `bugfix-fast-path.md` | Bugfix nhỏ (match 4 điều kiện fast-path) | Tech Lead (triage) | QA signoff |
| `bug-triage.md` | QA phát hiện bug sau implement | QA report | Coder (code bug) / Architect (design bug) / Product Analyst (spec bug) |
| `release-gate.md` | Feature xong, chuẩn bị release | Tech Lead + PM co-sign request | Release approved |
| `parallel-features.md` | Nhiều feature độc lập cùng sprint | PM request Tech Lead | Multiple features converge |

## Nguyên tắc chung điều hướng

### 1. Linear với gate — không skip stage

Mặc định: Product Analyst → PM → Designer → Tech Lead → Architect → Coder → QA → Release. Mỗi stage có gate (artifact + verification). Thiếu artifact → không chuyển stage.

### 2. Artifact ownership — một owner, một người duyệt

| Artifact | Owner | Người duyệt |
|---|---|---|
| `market-research.md` | Product Analyst | PM |
| `requirements.md`, `wireframe.json` | Product Analyst | PM / Designer |
| `design.md`, `design-spec.json` | Designer | Product Analyst (nghiệp vụ) |
| `project-plan.yaml` | PM | user |
| `tech-brief.md` | Tech Lead | — |
| `plan.md` (architecture) | Architect | Tech Lead |
| Production code | Coder | Reviewer + Tech Lead |
| `qa-report.json` | QA | QA self-verify qua evidence |
| `release-readiness-<v>.md` | Tech Lead | PM co-sign |

Agent khác có thể comment, không được tự ý sửa artifact đã approved. Phải tạo ChangeRequest.

### 3. ChangeRequest flow

Khi downstream agent phát hiện gap upstream (ví dụ Designer thấy PRD thiếu state):

1. Tạo `briefs/<slug>/change-requests/CR-<id>.md`
2. Notify owner artifact gốc
3. Owner update artifact
4. PM đánh giá impact deadline nếu CR expand scope
5. Orchestrator mark downstream artifact "needs re-validate"

### 4. Fast-path trigger

Tech Lead là gate quyết định fast-path. Thỏa 4 điều kiện (xem `bugfix-fast-path.md`) → Architect → Coder thẳng, skip Tech Lead review.

### 5. Max retry + escalation

- **Review loop** (Tech Lead ↔ Architect): max 2 revise rồi auto ESCALATE_TO_PM
- **Bug fix loop** (QA ↔ Coder): cùng failure signature max 3 retry rồi auto escalate Tech Lead triage lại
- **Spec/design gap**: không có max retry, phải quay owner artifact resolve

### 6. Handoff doc format bắt buộc

Mỗi handoff tạo file `plans/handoff/<feature>/<from>-to-<to>.md`:

```markdown
# Handoff: <feature>

## Meta
- From: <agent>
- To: <agent>
- Date: YYYY-MM-DD HH:MM
- Status: ready | blocked | needs-context

## Artifact delivered
- Path: <file>
- Version: <n>

## Acceptance criteria met
- [x] <criteria>

## Open questions
- <list>

## Blocking issues
- <list>
```

Orchestrator chỉ chuyển tiếp khi file này tồn tại, status = ready, acceptance criteria check hết.

## Orchestrator routing responsibility

Orchestrator đọc:
1. User task → classify (feature mới / bugfix / scope decision / release / refactor)
2. Chọn workflow phù hợp trong folder này
3. Spawn agent theo workflow step
4. Validate handoff doc sau mỗi step
5. Trigger ChangeRequest flow khi downstream raise gap
6. Escalate user khi max retry hoặc blocker không resolve

Không có workflow phù hợp → orchestrator ask user, không tự chế workflow.

## Xem thêm

- `orchestrator.md` — orchestrator agent spec
- `tech-lead.md` — gate decision + fast-path rule
- `../../workflows/` — root workflows (legacy, overlap với folder này sẽ migrate dần)
