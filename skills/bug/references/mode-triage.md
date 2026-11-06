# bug — `--mode triage`

Bug classification + delegate đúng agent sửa gốc. Tech Lead classify 3 nhánh: code bug → Coder, design bug → Architect, spec bug → Product Analyst. Max 3 retry rồi escalate PM.

> Dùng mode này khi: bug đã fail fast-path của `--mode fix`, hoặc đã biết không phải code bug (vd QA report + plan review thấy plan thiếu state). Bug mới chưa classify → `--mode fix` (xem `mode-fix.md`), mặc định thử fast-path trước.

## Inputs

Bắt buộc:
- **QA bug report path**: `briefs/<slug>/qa-report.json` HOẶC description text
- **Context artifact**: paths tới PRD / plan.md / code diff đã apply

Optional:
- `--retry-count <N>`: lần triage thứ mấy (nếu N ≥ 2, Tech Lead sẽ re-classify)
- `--previous-attempt <path>`: triage trước đã classify sang nhánh nào

## Procedure

### Step 1 — Tech Lead classify theo checklist

Spawn Task:

```
Role = Tech Lead. Đọc:
- agents/tech-lead.md (Step 7 Bug triage)
- agents/workflows/bug-triage.md (classification rules + decision tree)

Bug report: {{report path/text}}
PRD: {{path}}
Plan.md: {{path nếu có}}
Code diff: {{path nếu có}}
Retry count: {{N}}

Task classify theo 4-step decision tree:
1. Compare với PRD → bug behavior có mâu thuẫn PRD/AC không?
   - YES → SPEC BUG
   - NO → tiếp 2
2. Compare với plan.md → plan có cover case này không?
   - NO (plan thiếu state/branch) → DESIGN BUG
   - YES → tiếp 3
3. Compare code vs plan → code có follow plan không?
   - NO (code deviate plan) → CODE BUG
   - YES → tiếp 4
4. Deep analysis → thường là DESIGN BUG ẩn, escalate Architect inspect

Nếu retry ≥ 2: re-classify (nghi ngờ phân loại lần trước sai). Nếu retry = 3: auto-escalate PM.

Output: plans/reports/bug-triage-{{id}}.md với classification + rationale (phải cite evidence từ PRD/plan/code).
```

### Step 2 — Delegate theo nhánh

#### Nhánh A: Code bug → Coder

```
Role = Coder. Đọc agents/coder.md + triage report.

Task: Fix theo nhánh code bug.
Rule cứng:
- KHÔNG được thay đổi domain contract, repository signature, module boundary
- Nếu phát hiện cần đổi → raise Tech Lead → re-classify sang design bug
- Add regression test
- Timebox < 4h per retry

Max 3 retry cùng signature rồi auto escalate Tech Lead triage lại.
```

#### Nhánh B: Design bug → Architect

```
Role = Architect. Đọc agents/architect.md + triage report.

Task: Revise plan.md cover state/branch thiếu.
- Save new plan.md version tại plans/<date>-<slug>/plan-v<N>.md
- Note delta vs plan trước (section nào thêm/sửa)
- Handoff Tech Lead review (BẮT BUỘC full review, không fast-path)

Sau Tech Lead approve → Coder re-implement phần ảnh hưởng.

Max 2 revise rồi auto escalate PM.
```

#### Nhánh C: Spec bug → Product Analyst (+ PM)

```
Role = Product Analyst. Đọc agents/product-analyst.md + triage report.

Task: Update PRD cover case missing.
- Save PRD version mới tại briefs/<slug>/requirements-v<N>.md
- Note delta
- PM đánh giá impact deadline → có thể expand scope → re-score backlog

Sau PRD approved → cascade downstream:
- Designer re-design nếu UI impact
- Tech Lead → Architect re-plan phần ảnh hưởng
- Coder → QA re-verify
```

### Step 3 — Re-verify

Sau khi fix theo nhánh, spawn QA re-verify. PASS → close; FAIL → increment retry, quay Step 1.

### Step 4 — Lesson feedback

Mọi bug close đều feed `lesson-miner`:
- Code bug class recurring → update `skills/coding-review/` rule
- Design bug class recurring → update `agents/architect.md` checklist
- Spec bug class recurring → update `knowledge/product/input-analysis/requirement-extraction-rules.md [KB → product/input-analysis, kb_search "input analysis requirement extraction rules"]`

## Pre-flight check

- [ ] QA bug report có evidence (repro + log/screenshot)
- [ ] PRD file reference được
- [ ] plan.md reference được (nếu feature đã qua pipeline)
- [ ] Code diff reference được

Thiếu PRD hoặc plan → classify sẽ guess, không reliable.

## Khi NÀO không dùng mode này

- Bug 100% code bug đơn giản → `--mode fix` fast-path nhanh hơn
- Chưa có QA report → chạy QA agent trước để có evidence
- Chỉ muốn thảo luận "feature này nên design lại không" → architect brainstorm, không phải triage
- Nếu spec bug cascade quá rộng → có thể cần full re-plan qua `/feature`
