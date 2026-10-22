# Workflow: Feature Full Flow

Pipeline đầy đủ cho feature mới (scope ≥ 1 screen hoặc impact business logic). Chạy qua 8 stage với gate rõ ràng.

## Trigger

- User request feature mới
- Backlog grooming PM: feature P0/P1 approved
- Khôi phục scope đã defer từ sprint trước

## Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  PRODUCT LAYER                                                     │
│  product-analyst  ──PRD + wireframe──►  project-manager            │
│       │                                       │                    │
│       │                                       │ scope + deadline   │
│       │                                       ▼                    │
│       └──wireframe + PRD──►  designer  ──design-spec──►  tech-lead │
│                                                              │     │
│  ENGINEERING LAYER                                           │     │
│                                                              ▼     │
│                                                       tech-brief   │
│                                                              │     │
│                                                              ▼     │
│                                                        architect   │
│                                                              │     │
│                                           plan.md ◄──────────┘     │
│                                              │                     │
│                                              ▼                     │
│                                        tech-lead ─── review ────┐  │
│                                              │                  │  │
│                                     APPROVE  │  REQUEST_CHANGES │  │
│                                              ▼                  │  │
│                                         coder                   │  │
│                                              │                  │  │
│                                              ▼                  │  │
│                                       reviewer + qa             │  │
│                                              │                  │  │
│                                     PASS     │     FAIL         │  │
│                                              ▼                  │  │
│                                     tech-lead + pm              │  │
│                                              │                  │  │
│                                              ▼                  │  │
│                                       Release Gate              │  │
│                                              │                  │  │
│                                              ▼                  │  │
│                                         Released                │  │
└──────────────────────────────────────────────┴──────────────────┴──┘
                                                      ↑
                                                      │ max 2 revise
                                                      │
                                           architect revise ──┘
```

## 8 stage + gate

### Stage 1 — Discovery (Product Analyst)

**Owner**: `product-analyst`

**Input**: User idea / stakeholder brief / existing spec file

**Activity**:
1. Market mode: competitor scan + user pain research (nếu idea mới, chưa validated)
2. Spec mode: extract requirement từ spec nguồn
3. Wireframe mode: produce low-fi functional wireframe

**Output**: `briefs/<slug>/market-research.md` (optional) + `requirements.md` + `acceptance-criteria.md` + `wireframe.json`

**Gate** (Product requirements ready):
- [ ] Confirmed requirement ≥ 80%, inferred < 20%, unresolved = 0 (hoặc explicit defer)
- [ ] Wireframe cover mọi user flow trong PRD
- [ ] Acceptance criteria verifiable

**Handoff**: `plans/handoff/<feature>/product-analyst-to-project-manager.md`

---

### Stage 2 — Planning (Project Manager)

**Owner**: `project-manager`

**Input**: PRD + wireframe từ Stage 1

**Activity**:
1. Score feasibility (business value × urgency × confidence × tech feasibility)
2. Prioritize backlog, assign P0/P1/P2
3. Breakdown milestone, assign deadline
4. Flag cross-feature dep + external dep

**Output**: `plans/project-plan.yaml` updated với feature entry

**Gate** (Scope + milestone chốt):
- [ ] Deadline rõ (target + buffer)
- [ ] Scope frozen (true/false, với lý do)
- [ ] Dependency list đầy đủ

**Handoff** (parallel):
- `plans/handoff/<feature>/project-manager-to-designer.md`
- Nếu feature không có UI (ví dụ background job pure) → skip Designer, nhảy sang Tech Lead

---

### Stage 3 — Design (Designer)

**Owner**: `designer`

**Input**: Wireframe + PRD + deadline

**Activity**:
1. Audit design system project (reuse > create)
2. Draft high-fi screen mockup, 5 states, interaction
3. Dark mode + responsive variant
4. Accessibility pass
5. Export asset

**Output**: `briefs/<slug>/design.md` + `design-spec.json` + `assets/design/`

**Gate** (Design ready):
- [ ] Mọi screen có 5 states (nếu remote-data)
- [ ] Token semantic, no hardcode
- [ ] Contrast WCAG AA
- [ ] Touch target ≥ 48dp
- [ ] Asset export đúng format

**Handoff**: `plans/handoff/<feature>/designer-to-tech-lead.md`

**ChangeRequest trigger**: Nếu Designer phát hiện PRD gap (ví dụ permission denied state không có) → tạo `change-requests/CR-<id>.md` → Product Analyst update PRD → quay lại Stage 1 (chỉ phần gap, không toàn feature)

---

### Stage 4 — Technical Brief (Tech Lead)

**Owner**: `tech-lead`

**Input**: PRD + design + deadline + codebase constraints

**Activity**:
1. Reject nếu thiếu field (outcome / AC / deadline)
2. Extract ADR áp dụng (từ `constitution/`)
3. Flag module touch, platform SDK dep, nav route change
4. Write Tech Brief

**Output**: `plans/<date>-<slug>/tech-brief.md`

**Gate**:
- [ ] ADR list rõ (bắt buộc tuân thủ cho feature này)
- [ ] Module boundary clear
- [ ] Risk + mitigation state

**Handoff**: Spawn `architect` với tech-brief.md path

---

### Stage 5 — Architecture Plan (Architect)

**Owner**: `architect`

**Input**: tech-brief.md

**Activity**: 1-page plan theo `architect.md` spec

**Output**: `plans/<date>-<slug>/plan.md`

**Gate** (Plan ready):
- [ ] File list cụ thể
- [ ] Decision có rationale
- [ ] Risk + verification plan

**Handoff**: Trả về Tech Lead review

---

### Stage 6 — Plan Review Gate (Tech Lead)

**Owner**: `tech-lead`

**Input**: `plan.md`

**Activity**:
1. **Fast-path check**: thỏa 4 điều kiện → skip review, delegate Coder luôn, GOTO Stage 7 với note "fast-path"
2. **Full review** (6 dimensions): ADR / codebase fit / estimation / risk / dependency / verification
3. Verdict: APPROVE / REQUEST_CHANGES / ESCALATE_TO_PM

**Output**: `plans/reports/tech-lead-review-<date>-<slug>.md`

**Gate**:
- APPROVE (0 BLOCKER) → GOTO Stage 7
- REQUEST_CHANGES → Architect revise (max 2 vòng, lần 3 ESCALATE_TO_PM)
- ESCALATE_TO_PM → dừng pipeline, PM quyết scope cut hoặc dời deadline → quay Stage 2

---

### Stage 7 — Implementation (Coder)

**Owner**: `coder`

**Input**: plan.md approved

**Activity**: Execute bottom-up theo `coder.md` workflow

**Output**: Code changes + smoke test pass + compile clean

**Gate**:
- [ ] File list match plan (hoặc delta documented)
- [ ] Smoke test pass
- [ ] Konsist + Detekt pass trên code mới

**Handoff**: Spawn parallel `reviewer` + `qa`

---

### Stage 8 — Verify (Reviewer + QA parallel)

**Owners**: `reviewer` (code audit) + `qa` (behavior verification)

**Reviewer activity**: 10 dimensions review, output verdict APPROVE / APPROVE_WITH_CHANGES / REQUEST_CHANGES

**QA activity**:
- **Scope A** (per-screen) default sau mỗi task: unit + UI logic + visual (`ui-judge`) → report bug nếu fail
- **Scope B** (full-flow E2E) tại milestone/release gate: delegate `e2e-author` + ARTEMIS runner

**Gate**:
- Reviewer APPROVE **AND** QA PASS → GOTO Release Gate
- Reviewer REQUEST_CHANGES → Coder fix → Reviewer re-verify (same loop, không reset)
- QA FAIL → `bug-triage.md` workflow (xem file đó)

---

### Stage 9 — Release Gate (Tech Lead + PM co-sign)

Xem `release-gate.md`.

## Timeline guideline

Mặc định tổng timeline:
- Stage 1-2 (Product + Planning): 10-20% deadline
- Stage 3 (Design): 15-25%
- Stage 4-6 (Tech + Plan + Review): 15-20%
- Stage 7 (Code): 30-40%
- Stage 8 (Verify): 10-15%
- Stage 9 (Release): < 5%

Vượt budget stage → PM audit, decide re-scope hoặc re-estimate.

## Khi nào deviate linear flow

### Skip stage hợp lệ

| Skip | Khi | Thay bằng |
|---|---|---|
| Stage 1 (Product) | Spec stakeholder đã sẵn + validated | Product Analyst chỉ format lại |
| Stage 3 (Design) | Feature non-UI (background job, data migration) | Jump sang Tech Lead |
| Stage 6 (Review) | Fast-path 4 điều kiện | Note "fast-path", Reviewer vẫn chạy ở Stage 8 |

### Không skip được

- Stage 2 (Planning) — luôn cần deadline
- Stage 4-5 (Tech Brief + Plan) — luôn cần
- Stage 7 (Code) — hiển nhiên
- Stage 8 (Verify) — luôn cần

## Handoff doc chuỗi

```
briefs/<slug>/handoff/
├── 01-product-analyst-to-project-manager.md
├── 02-project-manager-to-designer.md
├── 03-designer-to-tech-lead.md
├── 04-tech-lead-to-architect.md
├── 05-architect-to-tech-lead.md
├── 06-tech-lead-to-coder.md
├── 07-coder-to-reviewer.md
├── 07b-coder-to-qa.md
└── 08-tech-lead-pm-release.md
```

## Pair với workflow khác

- `bugfix-fast-path.md` — bỏ qua Stage 1-3-5-6 cho bugfix nhỏ
- `bug-triage.md` — triage khi Stage 8 QA FAIL
- `release-gate.md` — chi tiết Stage 9
- `parallel-features.md` — chạy multiple feature trên cùng sprint
