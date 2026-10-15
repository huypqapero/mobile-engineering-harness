# Requirement Extraction Rules

Rules trích xuất requirement từ spec markdown + design screenshot thành entries trong `brief.yaml`. Áp dụng cho skill `input-analyze-spec` và `input-reconcile`.

## Mục đích

Prevent agent **tự generate requirement** không có trong nguồn, hoặc đánh dấu `confirmed` cho suy luận. Mỗi requirement phải trace về source cụ thể.

## Hard rules

### REQ-RULE-001 — Mọi requirement phải có source reference

- `requirements[].source_references` MUST không rỗng cho `evidence_status: confirmed` hoặc `inferred`.
- Format: `{path, locator, quote?, note?}`.
- `path` phải trong `assets/sources/` của brief, không phải path gốc trong product repo.
- `locator`: line number (`L23`), range (`L23-L28`), hoặc `full-image` cho screenshot.

### REQ-RULE-002 — Phân biệt evidence status đúng

| Status | Điều kiện |
|---|---|
| `confirmed` | Có **quote cụ thể** từ spec HOẶC có spec quote + visible trong screenshot |
| `inferred` | Suy từ screenshot alone, hoặc từ pattern app, không có spec quote |
| `unresolved` | Nguồn silent, cần stakeholder clarify |

**Cấm:** gán `confirmed` cho requirement derive từ screenshot alone, kể cả khi screenshot "rõ ràng".

### REQ-RULE-003 — Mỗi requirement có 1 responsibility

- Nếu description chứa "và" cross-cutting (ví dụ "user tap play **và** show toast **và** track analytics") → tách thành ≥2 requirements.
- Exception: multi-step của cùng 1 action (ví dụ "tap play → loading → playback") giữ 1 requirement, mô tả flow.

### REQ-RULE-004 — Requirement type enum

Dùng đúng 1 trong 5:

- `functional` — business behavior (tap, submit, calculate)
- `non-functional` — performance, security, accessibility, i18n
- `navigation` — routing giữa screens
- `validation` — input constraint (format, length, required)
- `ui` — visual state, layout, component

Không tự tạo type mới. Nếu không fit → chọn gần nhất + note trong description.

### REQ-RULE-005 — AC chỉ reference confirmed requirements

- `acceptance_criteria[].requirement_ids` chỉ chứa requirement có `evidence_status: confirmed`.
- Nếu AC derive từ `inferred` requirement → tạo issue blocking resolve requirement trước.
- Rationale: AC là contract test; không được test behavior inferred.

### REQ-RULE-006 — Non-functional requirements default từ project

- Performance, accessibility, i18n: nếu spec không nói, dùng project default (`docs/design-guidelines.md`).
- Source reference: `path: project-default`, `locator: docs/design-guidelines.md`.
- `evidence_status: confirmed` (project default là authoritative).

## Soft rules

### REQ-RULE-010 — Prefer precise quotes

- Quote chính xác từ spec thay vì paraphrase.
- Quote dài > 3 câu → trim, mark `...` ở giữa.

### REQ-RULE-011 — Group related requirements

- UI requirements của cùng screen → list cạnh nhau trong `requirements.md`.
- Order: confirmed → inferred → unresolved → non-functional.

### REQ-RULE-012 — ID convention

- `REQ-001`, `REQ-002`, ... cho functional/ui/validation/navigation
- `NFR-001`, `NFR-002`, ... cho non-functional
- `AC-001`, `AC-002`, ... cho acceptance criteria
- Gap trong numbering OK (ví dụ REQ-001 → REQ-010 cho inferred) để group semantic.

## Anti-patterns (CẤM)

### AP-001 — Tự generate business rule

**Sai:**
```yaml
- id: REQ-005
  description: Audio preview giới hạn 3 lần/ngày để tránh abuse.
  evidence_status: confirmed
```
→ Nếu spec không nói "3 lần/ngày" thì CẤM confirmed. Nếu không có trong nguồn → không tạo requirement này.

**Đúng:** không tạo requirement này. Nếu cần, hỏi PM.

### AP-002 — Confirmed từ screenshot alone

**Sai:**
```yaml
- id: REQ-006
  description: Button "Add to Cart" lưu book vào wishlist.
  evidence_status: confirmed
  source_references:
    - path: assets/sources/screenshots/detail.png
```
→ Screenshot cho thấy button nhưng không chứng minh behavior.

**Đúng:**
```yaml
- id: REQ-006
  description: Tap button "Add to Cart" lưu book vào wishlist.
  evidence_status: inferred    # cần confirm
```
+ tạo ISSUE `MISSING_BEHAVIOR`.

### AP-003 — Merge functional và ui

**Sai:**
```yaml
- id: REQ-007
  description: Play button màu primary + tap → playback trong 500ms + analytics event.
```
→ Mix 3 concerns.

**Đúng:** tách REQ-007 (functional play), REQ-008 (ui style), REQ-009 (analytics), REQ-010 (performance NFR).

### AP-004 — Vague acceptance criteria

**Sai:**
```yaml
- id: AC-010
  description: App chạy mượt.
  verifiable: true
```
→ Không measurable.

**Đúng:**
```yaml
- id: AC-010
  description: Scroll Book Detail giữ 60fps p90 trên device baseline Pixel 6.
  verifiable: true
  test_hint: FrameTiming test với Compose benchmark
```

### AP-005 — Infer navigation

**Sai:** gán `type: navigation` cho suy luận "tap item → detail screen" không có spec confirm.

**Đúng:** nếu nav không rõ → tạo issue `MISSING_BEHAVIOR` severity `high`.

## Extraction procedure

1. **Đọc spec full** trước khi extract (không stream line-by-line).
2. **List candidates** — mỗi câu/section potential requirement, chưa gán ID.
3. **Classify** candidate:
   - Có action verb từ user? → `functional`
   - Có constraint/validation? → `validation`
   - Mô tả visual? → `ui`
   - Nav giữa screens? → `navigation`
   - Performance/a11y/i18n? → `non-functional`
4. **Dedupe** — merge candidate trùng (DUPLICATE_REQUIREMENT issue).
5. **Match với screenshot** — cho mỗi requirement có UI, check screenshot có support không.
   - Match → add screenshot vào source_references
   - Mismatch → tạo SOURCE_CONFLICT issue
   - Spec có, screenshot không có → OK (behavior-only)
   - Screenshot có, spec không có → tạo inferred requirement + MISSING_BEHAVIOR issue
6. **Assign ID** theo convention REQ-001.
7. **Write prose** vào `requirements.md`, bind YAML vào `brief.yaml`.
8. **Validate** — gọi `input-validate-brief` skill check REQ-RULE-001..006.

## Required policies

- Reference `blueprints/feature-brief/README.md` cho format
- Reference `screenshot-reading-rules.md` khi screen requirement
- Reference `reconciliation-matrix.md` khi conflict phát hiện
