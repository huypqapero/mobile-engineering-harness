---
name: coding-brainstorm
description: Trade-off analysis + outcome lock trước implementation. So sánh 2-3 approach với pros/cons, chốt outcome contract (desired outcome, constraints, non-goals, acceptance criteria) trước khi touch code. Trigger khi task có nhiều hướng viable, decision cao risk, hoặc trước khi start coding-feature cho feature mới.
priority: P1
---

# Skill: coding-brainstorm

Gate skill trước implementation. Không viết code — chốt scope + so sánh approach + ghi outcome contract. Giảm rework do mis-aligned expectation.

## Trigger

- Start feature mới chưa rõ approach ("add offline-first cho library screen")
- 2+ hướng giải quyết cùng viable (ví dụ Flow vs Suspend, Room vs SQLDelight, VM state vs Flow state)
- High-stakes decision: architecture change, library swap, API contract break
- Trước `coding-feature`/`coding-refactor` cho task scope > 1 module
- User hỏi "nên làm cách nào", "có hướng khác không", "có risk gì"
- Debug diagnose xong có >1 fix path (xem `coding-diagnose §Fix tại cause hay symptom`)

## NOT trigger

- Task scope rõ, có plan sẵn, chỉ cần implement → skip brainstorm, invoke `coding-feature` trực tiếp
- Bug fix có root cause + 1 fix path duy nhất → invoke `coding-diagnose --mode bug` trực tiếp
- Refactor rename đơn giản → `coding-refactor` trực tiếp

Brainstorm là gate chọn lọc, không phải reflex.

## Inputs

Bắt buộc:
- Problem statement từ user (1-3 câu)
- Current state (nếu refactor/extend) — path hoặc scout output

Optional:
- Constraint hints: timeline, backward compat, performance target
- Non-goals khai báo trước (giảm scope creep)

## Prerequisites

1. `knowledge/coding/clean-arch/clean-mvi.md` — Clean Arch invariant + MVI integration
2. `knowledge/coding/mvi/essentials.md` — state/intent pattern
3. `knowledge/coding/coroutines/essentials.md` — concurrency primitives
4. Related `knowledge/*/essentials.md` theo domain task
5. `constitution/engineering-principles.md` — team principles (KISS/DRY/YAGNI)

Nếu task touches unknown area → invoke `coding-scout` trước để có context thực.

## Execution procedure

### Step 1 — Capture outcome contract

Chốt 4 field trước khi liệt kê approach. Nếu user không cung cấp → ask (max 2 question).

```markdown
## Outcome Contract

**Desired outcome:** <1 sentence — user-observable result>
**Constraints:** <timeline, backward compat, perf budget, team skill — list bullet>
**Non-goals:** <explicit list — không làm trong task này>
**Acceptance criteria:**
- [ ] <measurable statement 1>
- [ ] <measurable statement 2>
```

**Rule:** không skip field. Non-goals bỏ qua = scope creep sau này.

### Step 2 — Enumerate approaches

List 2-3 approach viable. KHÔNG > 3 (nhiều hơn thì user bối rối, agent dilute analysis).

Mỗi approach:
- **Tên** (ngắn, descriptive)
- **Mô tả** (3-5 câu, high-level)
- **Fit layer nào** (data/domain/presenter/app)
- **Thư viện/pattern đã có vs cần add**

### Step 3 — Trade-off matrix

Compare các approach qua 6 dimension:

| Dimension | A | B | C |
|---|---|---|---|
| Complexity (LoC estimate + file touch count) | ... | ... | ... |
| Test effort (unit/UI/integration) | ... | ... | ... |
| Performance (startup/memory/network) | ... | ... | ... |
| Maintainability (team familiarity) | ... | ... | ... |
| Risk (regression, API break, platform divergence) | ... | ... | ... |
| Reversibility (easy to swap sau?) | ... | ... | ... |

Mỗi cell concise (1-3 từ hoặc số). Dimension khớp constraint từ Step 1 ưu tiên hiển thị.

### Step 4 — Red team mỗi approach

Cho mỗi approach, 1 câu "khi nào approach này FAIL":

- A fails khi: data source thực sự realtime (Room polling tốn battery)
- B fails khi: migration schema > 100k rows (SQLDelight slow init)
- C fails khi: iOS target cần parity (Flow operator không map 1-1)

Red team catch assumption chưa verify.

### Step 5 — Recommend

Chọn 1 approach primary + 1 fallback. Format:

```markdown
## Recommendation

**Primary:** Approach B
**Why:** <2-3 câu — reference matrix cell quyết định>
**Fallback:** Approach A nếu <trigger condition>

**Caveats:**
- <assumption cần verify trước implement>
- <known risk + mitigation>
```

### Step 6 — Handoff hint

Suggest skill tiếp theo + required inputs:

```markdown
## Next step

→ `coding-feature --approach B --brief <path/to/brief>` nếu scope cross-module
→ `coding-mvi` trước, rồi `coding-compose` nếu chỉ presenter layer
→ Loop back `coding-scout` nếu assumption trong caveats cần verify

Required inputs cho skill tiếp theo:
- Outcome contract (section Step 1)
- Approach chosen (B) với rationale
- Non-goals list (prevent scope creep)
```

## Required policies

- KISS: ưu tiên approach ít moving parts hơn khi matrix tie
- YAGNI (nếu user flag `--yagni` trong request): cut non-essential dimension/approach
- Clean Arch invariant: approach vi phạm layer boundary → auto drop khỏi list

## Output contract

Deliverable (markdown inline hoặc save vào `plans/<slug>/brainstorm.md`):

- Outcome contract (4 field)
- 2-3 approach với trade-off matrix
- Red team per approach
- Recommendation primary + fallback
- Caveats + next skill handoff

## Validation

- [ ] Non-goals list ≥ 1 item (nếu empty → re-ask user)
- [ ] Acceptance criteria measurable (không "tốt", "mượt", "clean")
- [ ] Trade-off matrix mỗi cell có content (không bỏ trống)
- [ ] Red team mỗi approach có failure condition cụ thể
- [ ] Recommendation reference ≥ 1 matrix cell làm lý do

## Failure / recovery

- User không trả outcome question → BLOCKED, không bịa outcome
- Chỉ 1 approach viable → không phải brainstorm case, suggest `coding-feature` trực tiếp
- 4+ approach cần so sánh → scope quá rộng, split thành 2 brainstorm nhỏ

## Anti-patterns

- **AP-001 — Skip outcome contract**: Nhảy vào approach list ngay → mất anchor. Outcome FIRST.
- **AP-002 — Enumerate >3 approach**: Dilute analysis. 3 hard cap.
- **AP-003 — Pros/cons chung chung**: "Dễ maintain", "flexible". KHÔNG. Phải reference dimension cụ thể (test effort, LoC, reversibility).
- **AP-004 — Skip red team**: Approach không có failure condition = chưa đủ hiểu. MUST list.
- **AP-005 — Recommend không reason**: "Approach B tốt hơn" không matrix cell reference → không actionable.
- **AP-006 — Implement trong brainstorm**: Brainstorm = decide. Code = `coding-feature`. Không mix.
- **AP-007 — Scope creep lặng**: User hỏi feature X, brainstorm propose cả Y + Z liên quan → raise suggestion, không auto include.

## Handoff

Brainstorm complete → caller skill:
- `coding-feature` với approach chosen + brief
- `coding-refactor` nếu primary = restructure
- `coding-diagnose` nếu brainstorm trong fix-bug flow có >1 fix path
- `plans/<slug>/` persist cho long-running track

## Compare với skill khác

- `coding-review`: review existing code quality. Brainstorm = pre-implementation decision. Khác thời điểm.
- `coding-scout`: discover current state (what IS). Brainstorm = future state (what COULD BE). Scout feeds brainstorm.
- `ak-brainstorm` (external): heavier HTML/wiki publish mode. Harness brainstorm = inline markdown, lightweight gate.

## Future

- Persona debate mode (như `ak-predict`) — 5 personas challenge recommendation
- Historical decision lookup — grep prior brainstorm docs cùng domain
- Confidence scoring per recommendation

---

## Harness context

- Workflow: `workflows/feature-development.md (Stage 2 Plan)`
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`


## Overlay gate (D-full)

Trước Step 1, verify `.harness-overlay/overlay.yaml` tồn tại. Nếu không, abort với status `BLOCKED` và chỉ dẫn user:

> Chưa có overlay. Chạy skill `harness-init` để scaffold trước, sau đó quay lại skill này.

Khi gặp placeholder `{{X}}` trong procedure/code example, resolve bằng mapping ở `AGENTS.md §Placeholder resolution` (Read overlay 1 lần đầu session, cache qua context).
