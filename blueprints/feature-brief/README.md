# Blueprint: Feature Brief

Standardized package của **input layer** cho mọi feature đưa vào harness. Khác với `task-contract` (plan contract — how to build), `feature-brief` là **input contract — what to build + why**, được derive từ spec + design nguồn.

## Why

- **Single input surface**: downstream workflow (`feature-development`, `extract-feature-to-sdk`, `parallel-feature-development`) consume cùng format, không phải mỗi lần đọc lại spec thô.
- **Confidence tagging**: mỗi requirement có `evidence_status` (confirmed / inferred / unresolved) → agent downstream biết tin cậy đến đâu.
- **Blocker gating**: `issues[severity=blocker]` chặn implement start cho đến khi human review.
- **Traceability**: mỗi requirement + screen có `source_references` link về artifact gốc.
- **Checksum provenance**: detect spec drift giữa brief và implementation.

## Khác biệt với task-contract

| | feature-brief (input) | task-contract (plan) |
|---|---|---|
| Nguồn | Spec + design nguồn | Human/orchestrator quyết định |
| Mục đích | Capture **what to build** | Capture **how to build** |
| Timing | Trước Stage 1 Inspect | Trong Stage 2 Plan |
| Mutability | Immutable sau validate | Mutable khi scope evolve |
| Output location | `briefs/<slug>/` | `plans/<date>-<slug>/` |

**Flow:**

```
input nguồn               input layer                   execution layer
──────────                ──────────                    ──────────
spec.md + screenshots  →  prepare-feature-brief  →  briefs/<slug>/      → feature-development → plans/<date>-<slug>/ → code
```

## Package layout

```text
briefs/<feature-slug>/
├── brief.yaml                 ← manifest (machine-readable, single source of truth)
├── requirements.md            ← functional + non-functional requirements prose
├── design.md                  ← screen contracts, components, states
├── acceptance-criteria.md     ← verifiable AC list
├── issues.md                  ← conflicts, assumptions, blockers
└── assets/
    ├── sources/               ← snapshot spec + screenshots gốc (immutable copy)
    │   ├── spec.md
    │   └── screenshots/
    └── analysis/              ← derived (optional diagrams, flow charts)
```

### Vai trò từng file

| File | Format | Role |
|---|---|---|
| `brief.yaml` | YAML (schema-validated) | Machine contract — orchestrator parse, downstream workflow consume |
| `requirements.md` | Markdown | Prose chi tiết, 1 section per requirement, source quotes |
| `design.md` | Markdown | Screen-by-screen contract: layout, components, states, assets |
| `acceptance-criteria.md` | Markdown | Verifiable AC, mỗi item map tới ≥1 requirement |
| `issues.md` | Markdown | Conflicts/assumptions/blockers, severity + resolution hint |
| `assets/sources/` | Binary + MD | Snapshot để downstream verify checksum khi implement |

## Usage

### Tạo brief từ MVP (Markdown + Screenshot)

```bash
# 1. Chuẩn bị input
mkdir -p input/book-detail/screenshots
cp docs/specs/book-detail.md input/book-detail/spec.md
cp designs/book-detail/*.png input/book-detail/screenshots/

# 2. Gọi skill
# Prompt agent: "Prepare feature brief cho book-detail từ input/book-detail/"
# → Skill `input-prepare-feature` orchestrate 5 phase

# 3. Output
ls briefs/book-detail/
# brief.yaml  requirements.md  design.md  acceptance-criteria.md  issues.md  assets/
```

### Validation

```bash
# Agent gọi `input-validate-brief` skill, hoặc manual:
# - brief.yaml khớp schema verification/brief-schema/brief.schema.json
# - mọi source_reference tồn tại trong assets/sources/
# - mọi requirement id unique
# - mọi AC map tới requirement id tồn tại
# - không còn issue[severity=blocker] chưa resolve
```

### Downstream consume

Workflow `feature-development` Stage 1 Inspect **phải**:

1. Đọc `briefs/<slug>/brief.yaml`
2. Kiểm `issues.md` còn blocker không → nếu còn, không start
3. Dùng `requirements.md` + `design.md` làm authoritative input (không re-read spec gốc trừ khi debug)
4. Reference AC ids trong plan + test

## Field reference (brief.yaml)

Xem `brief.yaml.template` — mỗi field có inline comment.

### Required fields

- `id` — kebab-case feature slug, unique
- `title` — human-readable title
- `goal` — 1-2 câu outcome
- `sources` — tối thiểu 1 spec source
- `requirements` — tối thiểu 1 confirmed requirement
- `acceptance_criteria` — tối thiểu 1 AC

### Evidence status enum

- `confirmed` — có source reference rõ ràng (quote spec hoặc screenshot với context)
- `inferred` — derive từ screenshot/pattern, cần human review
- `unresolved` — không đủ info, cần hỏi stakeholder

### Issue severity enum

- `blocker` — chặn implement (conflict giữa spec và design ảnh hưởng behavior)
- `high` — cần resolve trong implement nhưng không block start
- `info` — assumption đã document, không cần action

## Rules

- **MUST** validate brief qua `input-validate-brief` skill trước khi handoff
- **MUST** không có `evidence_status: inferred` ở AC (AC phải confirmed từ spec)
- **MUST** mỗi `source_reference` point tới file trong `assets/sources/` + line number
- **MUST** checksum ở `sources` match file thật trong `assets/sources/`
- **SHOULD** issue `blocker` resolve trước handoff; nếu không resolve được, user approve pass qua
- **FORBIDDEN** tự generate requirement không có trong spec hoặc visible trong screenshot
- **FORBIDDEN** gán `confirmed` cho requirement derive từ screenshot alone (phải có spec quote)

## Anti-patterns

- Infer navigation từ screenshot (tap X → screen Y) → tạo issue `inferred`, không confirmed
- Infer design token (color, spacing) exact value → list ước lượng với confidence
- Generate loading/error state khi screenshot chỉ có content → list vào `states_missing`
- Merge spec requirement và design requirement thành 1 item → tách để source reference rõ
- Skip `assets/sources/` snapshot → mất khả năng detect drift

## Reference

- `verification/brief-schema/brief.schema.json` — JSON schema validate brief.yaml
- `knowledge/product/input-analysis/requirement-extraction-rules.md` — rules trích xuất requirement
- `knowledge/product/input-analysis/screenshot-reading-rules.md` — rules đọc screenshot
- `knowledge/product/input-analysis/reconciliation-matrix.md` — conflict handling matrix
- `skills/input-prepare-feature/SKILL.md` — orchestrator skill
- `workflows/prepare-feature-brief.md` — 5-phase pipeline
