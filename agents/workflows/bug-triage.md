# Workflow: Bug Triage

Flow điều hướng khi QA phát hiện bug sau Coder done (Stage 8 của `feature-full-flow.md`) hoặc fast-path fail. Tech Lead phân loại 3 nhánh: code / design / spec.

## Trigger

- QA report FAIL (Scope A per-screen hoặc Scope B full-flow)
- QA detect regression trong existing flow khi test feature mới
- Monitoring/user report sau release

## Diagram

```
                   qa-report.json
                        │
                        ▼
                   tech-lead  ──── triage
                        │
          ┌─────────────┼─────────────┐
          │             │             │
      Code bug     Design bug     Spec bug
          │             │             │
          ▼             ▼             ▼
        coder       architect   product-analyst
          │             │             │
          ▼             ▼             ▼
       fix code    revise plan    update PRD
          │             │             │
          ▼             ▼             ▼
         qa         architect     product-analyst
          │             │             ▼
          │             ▼        designer (nếu UI impact)
          │          tech-lead        │
          │             │             ▼
          │             ▼        tech-lead
          │          coder            │
          │             │             ▼
          │             ▼          architect
          │            qa             │
          │             │             ▼ (full re-plan cho feature impacted)
          └──────┬──────┘             │
                 ▼                    │
            Re-verify ◄───────────────┘
                 │
          ┌──────┴──────┐
          │             │
         PASS          FAIL
          │             │
          ▼             ▼
       close       retry < 3?  ──YES──► loop lại triage
                       │
                       ▼ NO
                 escalate PM
```

## Phân loại 3 nhánh

### Code bug — delegate Coder

**Signal**:
- Logic sai so với plan.md (plan nói X, code làm Y)
- Race condition / memory leak / coroutine scope sai
- UI binding sai (field map wrong)
- Null handling miss
- Error branch không cover

**Rule**: Coder fix mà **không được thay đổi** domain contract, repository signature, module boundary. Nếu phát hiện cần đổi → raise Tech Lead → re-classify sang design bug.

**Flow**: QA → Tech Lead triage → Coder fix → QA re-verify

**Timebox**: Mỗi retry < 4h. Max 3 retry cùng failure signature.

---

### Design bug — delegate Architect

**Signal**:
- Plan.md thiếu state (ví dụ không có offline state, không có error handling cho API 429)
- Contract không cover edge case (sealed state không enumerate)
- Nav flow conflict (A → B → A loop vô hạn)
- Dependency graph sai (ViewModel inject repo mà nên qua UseCase)
- Performance issue root cause ở architecture (query N+1, over-emit Flow)

**Rule**: Architect revise plan → Tech Lead review (bắt buộc, không fast-path) → Coder re-implement phần ảnh hưởng.

**Flow**: QA → Tech Lead → Architect revise → Tech Lead review → Coder re-impl → QA re-verify

**Timebox**: Mỗi revise < 1 ngày. Max 2 revise rồi escalate PM.

---

### Spec bug — escalate Product Analyst (+ PM)

**Signal**:
- PRD mâu thuẫn (section A nói X, section B nói Y)
- Acceptance criteria thiếu (bug này không được define trong AC)
- User flow trong wireframe không match PRD text
- Business rule không cover case này (user ask ngoài scope)
- Design state không có trong PRD

**Rule**: Product Analyst update PRD → PM đánh giá impact deadline → nếu scope expand → Designer re-design (nếu UI change) → Tech Lead → Architect re-plan phần ảnh hưởng.

**Flow**: QA → Tech Lead → Product Analyst + PM → (Designer) → Tech Lead → Architect → Coder → QA

**Timebox**: Spec resolve < 2 ngày. Rồi quay cascade downstream.

**Impact**: Spec bug thường là cost cao nhất vì cascade impact. Nếu detect sớm (QA Scope A) thì cost nhỏ; detect muộn (release gate) thì cost lớn.

## Tech Lead triage checklist

Khi nhận QA bug report, chạy checklist này **theo thứ tự** để classify:

1. **Compare với PRD**: bug behavior có mâu thuẫn PRD/AC không?
   - YES → **Spec bug**
   - NO → tiếp 2

2. **Compare với plan.md**: plan có cover case này không?
   - NO (plan thiếu state/branch) → **Design bug**
   - YES → tiếp 3

3. **Compare code vs plan**: code có follow plan không?
   - NO (code deviate plan) → **Code bug**
   - YES → tiếp 4

4. **Deep analysis**: Code follow plan + plan cover case + behavior sai → thường là **Design bug ẩn** (plan sai nhưng không rõ rang). Escalate Architect inspect.

## Max retry escalation

### Retry 1 cùng failure signature
Classify + delegate theo nhánh phù hợp.

### Retry 2
Vẫn fail → re-triage. Nếu classify lần đầu "code bug" nhưng fix 2 lần không PASS → có thể design bug ẩn. Chuyển nhánh.

### Retry 3
Vẫn fail → auto escalate PM. PM quyết:
- Dời deadline để Architect redesign toàn phần
- Cắt scope feature (remove sub-feature chứa bug)
- Revert code, defer feature sang sprint sau

## Output

### QA bug report format

`briefs/<slug>/qa-report.json`:

```json
{
  "feature_id": "FEATURE-023",
  "bugs": [
    {
      "id": "BUG-001",
      "symptom": "Tap read-now khi offline → crash",
      "repro_steps": ["Open book-detail", "Enable airplane mode", "Tap read-now"],
      "expected": "Show offline toast + disable button",
      "actual": "ArithmeticException in BookDetailViewModel.onReadNow",
      "evidence": ["screenshot/bug-001.png", "logcat/bug-001.txt"],
      "severity": "BLOCKER | HIGH | MEDIUM | LOW",
      "scope": "A | B",
      "retry_count": 1
    }
  ]
}
```

### Tech Lead triage record

`plans/reports/bug-triage-<id>.md`:

```markdown
# Bug Triage: <bug id>

## Report
- From: QA
- Symptom: <...>

## Classification
- Type: code | design | spec
- Rationale: <evidence from plan/PRD/code>

## Delegation
- Target agent: coder | architect | product-analyst
- Expected action: <...>
- Retry count: 1/3

## Previous attempts (nếu retry > 1)
- Attempt 1: <classification + outcome>
- Re-classification rationale: <...>
```

## Anti-patterns

- Tech Lead delegate Coder fix mà không classify (default "code bug" không đọc plan + PRD)
- Coder tự re-architect khi fix bug (thay đổi contract không raise)
- QA close bug mà không re-verify independent (dùng cùng test case Coder viết)
- Retry 5 lần không escalate PM
- Spec bug fix trực tiếp bằng code workaround (không update PRD → bug tái diễn)
- "Won't fix" bug không log vào `lesson-miner` → không học được

## Lesson feedback

Mọi bug close đều feed vào `lesson-miner`:
- Code bug class recurring → update coding-review rule
- Design bug class recurring → update architect checklist
- Spec bug class recurring → update product-analyst requirement extraction rules

## Pair với workflow khác

- `feature-full-flow.md` Stage 8 — nguồn bug Scope A/B
- `bugfix-fast-path.md` — nguồn bug fast-path fail
- `release-gate.md` — bug critical phát hiện gần release
