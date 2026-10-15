---
name: input-reconcile
description: Cross-reference spec analysis + design analysis, phát hiện conflict/gap, classify severity, resolve bằng project default hoặc tạo blocker. Consolidate issues.md. Phase P4 của prepare-feature pipeline.
priority: P1
---

# Skill: input-reconcile

## Trigger

- Phase P4 của `input-prepare-feature`
- "Reconcile spec + design cho brief <slug>"
- "Resolve conflict trong brief <slug>"

## Inputs

Bắt buộc:
- Brief slug với spec + design analysis complete
- `briefs/<slug>/requirements.md` + `brief.yaml.requirements[]`
- `briefs/<slug>/design.md` + `brief.yaml.screens[]`

Optional:
- Project `constitution/` cho project convention
- Project `knowledge/compose/essentials.md` cho default pattern

## Prerequisites

Trước khi reconcile:

1. `knowledge/input-analysis/reconciliation-matrix.md` — matrix + priority rules
2. `agents/input-analyst.md` + `agents/design-analyst.md` co-authorship
3. `blueprints/feature-brief/issues.md.template`

## Execution procedure

### Phase R1 — Collect

- Load spec analysis: `requirements[]`, `acceptance_criteria[]`, spec-only issues
- Load design analysis: `screens[]`, design-only issues
- Load spec-only + design-only issues từ earlier phases

### Phase R2 — Cross-reference pass

#### R2a — Spec → Design

Cho mỗi requirement có UI implication:

- Có screenshot support? → confirm, add screenshot vào source_references
- Không có screenshot (state spec yêu cầu) → issue `MISSING_DESIGN`
- Screenshot có nhưng component không match → issue `SOURCE_CONFLICT`

#### R2b — Design → Spec

Cho mỗi component có action semantic:

- Spec mô tả action? → gán `action_ref: REQ-XXX` confirmed
- Spec không mô tả → issue `MISSING_BEHAVIOR`
- Spec mô tả khác → issue `SOURCE_CONFLICT`

#### R2c — Direct conflict

Scan spec + design cho label/flow/order mismatch:

- Button label mismatch (spec vs screenshot) → `SOURCE_CONFLICT`
- Flow order mismatch (spec flow A→B→C, design flow A→C→B) → `SOURCE_CONFLICT`
- Field order mismatch → `SOURCE_CONFLICT` info

### Phase R3 — Classify severity

Apply decision tree từ `reconciliation-matrix.md`:

```
Phát hiện conflict/gap
      ↓
Có ảnh hưởng behavior không?
      ├─ YES → severity: blocker
      │          ↓
      │     Có project default resolve được?
      │          ├─ YES → downgrade high
      │          └─ NO → blocker, human review
      │
      └─ NO → severity: high (visual) / info (annotation)
```

Severity rules:

- Button label conflict → blocker
- Nav target conflict → blocker
- Missing loading state → high (project default)
- Missing offline (spec yêu cầu offline-first) → blocker
- Missing offline (spec không yêu cầu) → high
- Icon style diff → info
- Spacing diff → info
- Font family diff → info

### Phase R4 — Project default lookup

Cho mỗi issue có default resolve:

- Loading/error/empty component → `knowledge/compose/essentials.md` (nếu có)
- Offline strategy → constitution rule hoặc `knowledge/data/essentials.md`
- Error mapping → `knowledge/data/network.md`
- Animation → project motion token

Document default vào `assumptions[]`:

```yaml
assumptions:
  - id: ASSUME-001
    description: Loading dùng LinearProgressIndicator fullscreen.
    rationale: knowledge/compose/essentials.md pattern.
    issue_resolved: ISSUE-002
```

Update issue `status: resolved` + `resolved_by_assumption: ASSUME-XXX`.

### Phase R5 — Blocker gate

Count `issues[].severity: blocker, status: open`:

| Count | Brief status | Handoff |
|---|---|---|
| 0 | `READY` | OK |
| > 0 | `BLOCKED` | NO (trừ `--force-handoff`) |
| > 0 + override | `READY_WITH_OVERRIDE` | OK với rationale |

### Phase R6 — Consolidate issues.md

Vào `briefs/<slug>/issues.md` theo template:

- Section Severity + Types reference
- Mỗi issue 1 subsection với:
  - Type, severity, status
  - Description
  - Affected requirements
  - Resolution hint
  - Status (open/resolved/accepted) + resolver nếu có
- Resolution tracking table cuối file
- Blocker count summary

### Phase R7 — Bind YAML final

Update `briefs/<slug>/brief.yaml`:

- `issues[]` consolidated (spec + design + reconciliation)
- `assumptions[]` complete
- `validation.status: pending` (chờ Phase P5 `input-validate-brief`)

## Required policies

- Full `knowledge/input-analysis/reconciliation-matrix.md`
- REQ-RULE-005 (AC chỉ confirmed) — nếu AC bind inferred, raise blocker
- DESIGN-RULE-002 (không infer nav) — raise MISSING_BEHAVIOR nếu detect

## Output contract

Deliverable gồm:

- `briefs/<slug>/issues.md` (consolidated)
- `briefs/<slug>/brief.yaml` final issues + assumptions
- Count summary: B blocker, H high, I info
- Brief status: READY / BLOCKED / READY_WITH_OVERRIDE

## Validation

Trước khi handoff:

- [ ] Mọi conflict/gap có issue entry (không silent resolve)
- [ ] Mọi issue có severity + status
- [ ] Mọi issue resolved có `resolved_by_assumption` hoặc rationale
- [ ] Blocker count accurately computed
- [ ] Assumptions document đầy đủ cho mọi default resolve
- [ ] AC không bind inferred REQ (nếu có → raise blocker)

## Failure / recovery

- Spec analysis incomplete → BLOCKED, request re-run `input-analyze-spec`
- Design analysis incomplete → BLOCKED, request re-run `input-analyze-design`
- Project constitution unreachable → warning, không áp project default, raise issue manual

## Anti-patterns bị cấm

Xem `reconciliation-matrix.md`:
- AP-001 silent resolve
- AP-002 over-blocker (mọi mismatch mark blocker)
- AP-003 under-blocker (label conflict mark info)
- AP-004 auto-generate missing design
- AP-005 skip assumption documentation

## Handoff

→ `input-validate-brief` (Phase P5) với consolidated issues + assumptions
