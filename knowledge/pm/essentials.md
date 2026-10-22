# Project Management knowledge — essentials

Knowledge nền cho `project-manager` agent. Feasibility scoring, deadline buffer, scope decision, release window, bug-triage decision tree.

## 1. Feasibility scoring rubric

### 4 dimension × 1-3 scale

| Dim | 1 (low) | 2 (medium) | 3 (high) |
|---|---|---|---|
| **Business value** | Nice-to-have, không impact metric cụ thể | Retention lever (reduce churn 1-5%) | Revenue/growth lever (new revenue stream, +10%+ metric) |
| **Urgency** | Can wait quarter / nothing-will-break-if-defer | This sprint (user ask tích lũy, SLA soft) | Now (blocker, compliance, platform policy deadline, security) |
| **Confidence spec** | Fuzzy, chỉ idea | Spec draft, chưa validated | Spec frozen + validated (BA pass, stakeholder sign-off) |
| **Feasibility tech** | Unknown (chưa Tech Lead estimate) | Known hard (có estimate + risk list) | Known easy (có precedent, pattern tương tự đã làm) |

### Score → Priority

| Total | Priority | Action |
|---|---|---|
| 11-12 | **P0** | Current sprint, override backlog nếu cần |
| 8-10 | **P1** | Next sprint, backlog top |
| 6-7 | **P2** | Backlog, revisit quarterly |
| < 6 | **Defer** | Reject hoặc "icebox", notify stakeholder |

### Rule
- Score < 6 → KHÔNG đưa vào sprint, kể cả stakeholder push
- Score 11+ cần user override nếu scope cut 30%+ ảnh hưởng commitment đã công bố

## 2. Deadline buffer rule

### Breakdown

```
Target deadline = Hard commitment to stakeholder
Buffer = 20% of estimated effort
Working deadline = Target - Buffer

Ví dụ:
- Stakeholder commitment: 2026-11-15
- Estimated effort: 10 ngày work
- Buffer: 2 ngày
- Working deadline giao Tech Lead: 2026-11-13
```

### Rule
- Buffer 20% MẶC ĐỊNH, không cho = 0
- Nếu scope frozen + estimate confident → có thể giảm 15%
- Nếu scope negotiable + estimate uncertain → tăng 25-30%
- Vượt buffer → escalate stakeholder, không cắt test/review

## 3. Scope decision matrix

Khi Tech Lead escalate deadline conflict (estimation > deadline), PM quyết 3 option:

### Option A: Cắt scope (preferred nếu có low-value sub-feature)

Khi dùng:
- Release window có business trigger (marketing campaign, platform deadline)
- Scope có sub-feature value < 20% total

Cách:
- Rank sub-feature theo value
- Cắt bottom N sub-feature đến khi fit deadline
- Log scope decision record

### Option B: Dời deadline

Khi dùng:
- Scope đã minimal, không còn gì cắt
- Release không có hard trigger (sprint cadence flexible)
- Dời < 1 tuần không impact downstream

Cách:
- Negotiate stakeholder, communicate new date
- Max 2 tuần dời (vượt → re-score backlog)

### Option C: Add resource (parallel mode)

Khi dùng:
- Deadline hard + scope frozen
- Có team capacity dư
- Feature có isolation OK (ít share code)

Cách:
- Request Tech Lead chạy `parallel-features` workflow
- Verify isolation-check.yaml SAFE
- Monitor token budget 1.3-1.5× sequential

### Red flags
- "Just push harder" — không option, phải chọn A/B/C
- Cắt test/review để fit deadline — tech debt accumulation
- Add resource mà không check isolation — merge conflict chaos

## 4. Release window planning

### Checklist pre-release

Business side (PM owns):
- [ ] AC toàn PRD đạt
- [ ] Scope frozen, no CR pending
- [ ] Release window match marketing/platform policy
- [ ] Rollout strategy defined (% staged: 10 → 50 → 100)
- [ ] Rollback plan + trigger rõ (crash rate > 0.5%, ANR > 0.2%)
- [ ] Marketing material ready
- [ ] Support team briefed (FAQ, known issue, user-facing changelog)
- [ ] Analytics tracking verified staging
- [ ] Legal/compliance OK (privacy policy update nếu touch user data)
- [ ] Localization strings đủ ngôn ngữ target
- [ ] Platform policy OK (review guideline, age rating, permission)

### Staged rollout matrix

| Release type | Rollout plan |
|---|---|
| Minor feature (low risk) | 24h: 10% → 50% → 100% |
| Major feature (medium risk) | Day 1: 10%, Day 3: 50%, Day 7: 100% |
| Infrastructure change | Day 1: 1%, Day 3: 10%, Day 7: 50%, Day 14: 100% |
| Hotfix critical | 100% ngay sau co-sign |

### Rollback trigger (default)

- Crash rate > baseline + 0.3%
- ANR rate > baseline + 0.1%
- Critical bug escalated to BLOCKER
- Metric key (adoption, revenue) drop > 10% vs forecast

## 5. Bug-triage decision tree (từ góc nhìn PM)

Khi Tech Lead escalate bug không fix được:

```
QA fail retry 3 lần?
├─ YES → Classification cũ sai, re-triage với Tech Lead
│         ├─ Spec bug confirm → PM quyết: update PRD + accept delay | descope
│         ├─ Design bug confirm → PM quyết: Architect re-plan (có buffer?) | descope
│         └─ Code bug confirm (hiếm) → add resource (senior Coder)
└─ NO → tiếp tục bug-triage flow bình thường
```

### Rule PM
- Max 2 re-triage cùng feature → escalate stakeholder (defer feature)
- Spec bug cascade impact deadline > 2 tuần → re-score backlog
- 3+ critical bug trong 1 feature → consider revert, defer sang sprint sau

## 6. Progress tracking

### Daily audit
Đọc `plans/handoff/*.md` → agent nào stuck > 2 ngày?

### Weekly audit
- Check `plans/reports/*.md` → có BLOCKER chưa resolve
- Burndown vs plan: deviation > 20% → flag
- Build/test state → regression tích lũy

### Red flags
- Handoff stuck > 2 ngày cùng stage → agent misalign hoặc bị block
- 3+ CR cho cùng feature → spec quality kém, request BA refresh
- QA retry pattern tăng → quality downstream xuống, add review gate

## 7. Scope creep management

### Signal
- CR expand scope > 10% effort
- Mid-sprint request add feature mới ngoài plan
- Coder "while I'm here, let me also..."

### Response
1. Document CR impact (effort delta + deadline delta)
2. PM decide: accept + log Scope Decision Record | reject | defer
3. Nếu accept + impact deadline → notify stakeholder trong 24h
4. Nếu reject → log reason + add vào backlog nếu có value

## 8. Anti-patterns

- Ép Tech Lead "estimate lại cho đúng deadline" khi evidence rõ không khả thi
- Approve release với BLOCKER open ("hotfix sau")
- Tự cắt scope kỹ thuật (bỏ test, bỏ validation) để fit deadline
- Prioritize backlog bằng loudest-stakeholder, không bằng score
- Skip milestone exit criteria vì "gần xong rồi"
- Micromanagement: hỏi Coder tiến độ hàng giờ, review plan Architect line-by-line
- Scope creep approval không log Scope Decision Record
- Approve parallel-features khi 2 feature share domain contract

## 9. Dependency

- `agents/project-manager.md` — role spec
- `agents/workflows/feature-full-flow.md` — Stage 2 Planning + Stage 9 Release Gate
- `agents/workflows/bug-triage.md` — escalation path
- `agents/workflows/release-gate.md` — co-sign flow
- `agents/workflows/parallel-features.md` — Option C scope decision
- `knowledge/meta/agent-orchestration/essentials.md` — handoff state tracking

## 10. Last updated

- Date: 2026-10-22
- Dependency version: harness v0.21.0
- Review trigger: khi backlog tooling đổi (Linear → Jira) hoặc stakeholder structure thay đổi
