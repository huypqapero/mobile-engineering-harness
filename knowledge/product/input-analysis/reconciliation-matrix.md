# Reconciliation Matrix

Matrix xử lý conflict/gap giữa spec và design. Áp dụng cho skill `business-analyze --phase reconcile`.

## Mục đích

Khi spec và design mâu thuẫn hoặc thiếu nhau, agent phải quyết định: tạo issue (severity nào), hay accept assumption, hay block. Matrix này đưa quyết định đó deterministic.

## Priority rules

1. **Business logic** → spec confirmed thắng design
2. **Visual design** → design confirmed thắng spec text
3. **Implementation convention** → project default (từ `constitution/` + `docs/design-guidelines.md`) thắng cả 2
4. **Impact behavior/architecture** → không auto-resolve, tạo blocker

## Issue type matrix

| Type | Phát hiện khi | Default severity | Resolution path |
|---|---|---|---|
| `SOURCE_CONFLICT` | Spec và design mô tả khác nhau | blocker (nếu behavior) / high (nếu visual) | Human review |
| `MISSING_DESIGN` | Spec có state/behavior nhưng không screenshot | high | Project design system default |
| `MISSING_BEHAVIOR` | Design có component nhưng spec không mô tả action | blocker (nếu action required) / info (nếu passive) | Stakeholder clarify |
| `MISSING_API` | Spec cần data nhưng không có API contract | high | Backend contract required |
| `MISSING_ASSET` | Screenshot có asset chưa có file | high | Request designer |
| `DUPLICATE_REQUIREMENT` | Spec có requirement trùng | info | Auto-merge, preserve refs |
| `UNSUPPORTED_INPUT` | Adapter không parse được file | blocker | Fix input hoặc skip |
| `AMBIGUOUS_COMPONENT` | Screenshot có component không rõ semantic | high | Human review candidates |
| `UNRESOLVED_NAVIGATION` | Flow nav giữa 2 screens không confirm | high | Stakeholder clarify |

## Severity decision tree

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

## Reconciliation procedure

### Phase R1 — Collect analysis output

Input:
- `ProductSpecification` từ `business-analyze --phase spec`
- `DesignContract[]` từ `business-analyze --phase design`
- Optional: existing codebase context (nếu agent được provide)

### Phase R2 — Cross-reference pass

Cho mỗi requirement + mỗi screen component:

1. **Spec → Design**: requirement có UI implication → screenshot support? 
   - Yes → confirm, add screenshot vào source_references
   - No → check screenshot thiếu hay state missing → tạo `MISSING_DESIGN`
2. **Design → Spec**: component có action semantic → spec có mô tả?
   - Yes → confirm, link `action_ref`
   - No → tạo `MISSING_BEHAVIOR`
3. **Spec ↔ Design direct conflict**: label, flow, order khác nhau → tạo `SOURCE_CONFLICT`

### Phase R3 — Classify severity

Apply decision tree:

- Button label khác (Buy vs Add to Cart) → **blocker** (ảnh hưởng string resource + analytics + copy legal)
- Icon style khác → **info** (resolve downstream designer handoff)
- Nav target khác → **blocker** (ảnh hưởng routing architecture)
- Spacing khác → **info** (project token thắng)
- Missing loading state → **high** (project default resolve)
- Missing offline behavior → **blocker** nếu spec yêu cầu offline-first, else **high**

### Phase R4 — Project default lookup

Nếu issue có default resolve:

- Loading/error/empty component → `knowledge/coding/compose/essentials.md`
- Offline strategy → `knowledge/coding/data/essentials.md` (nếu có) hoặc constitution rule
- Error mapping → `knowledge/coding/data/network.md`
- Animation → project motion token

Document default vào `assumptions[]`:

```yaml
assumptions:
  - id: ASSUME-001
    description: Loading state dùng project default LinearProgressIndicator fullscreen.
    rationale: knowledge/coding/compose/essentials.md pattern.
    issue_resolved: ISSUE-002
```

### Phase R5 — Blocker gate

Count issues `severity: blocker, status: open`:

- Count > 0 → brief status `BLOCKED`, không handoff
- Count = 0 → brief status `READY`, handoff OK
- User explicit override: `--force-handoff` → brief status `READY_WITH_OVERRIDE`, document trong `validation.notes`

## Conflict resolution examples

### Ví dụ 1 — Label conflict

**Spec L45:** "Nút Buy chuyển sang checkout"
**Screenshot `detail.png`:** Button label "Add to Cart"

**Resolution:**
```yaml
issues:
  - id: ISSUE-001
    type: SOURCE_CONFLICT
    severity: blocker
    description: Button label mismatch.
    affected_requirements: [REQ-005]
    resolution_hint: >
      Hỏi PM confirm label. Nếu "Add to Cart": behavior = add + stay (không checkout).
      Nếu "Buy": behavior = add + nav checkout.
    status: open
```

### Ví dụ 2 — Missing loading state

**Spec L30:** "Loading indicator khi fetch book metadata"
**Screenshots:** chỉ có `detail.png` (content state)

**Resolution:**
```yaml
issues:
  - id: ISSUE-002
    type: MISSING_DESIGN
    severity: high
    description: Loading state không có screenshot.
    affected_requirements: [REQ-001]
    resolution_hint: Dùng project default LinearProgressIndicator fullscreen.
    status: resolved
    resolved_by_assumption: ASSUME-001

assumptions:
  - id: ASSUME-001
    description: Loading dùng LinearProgressIndicator fullscreen.
    rationale: Project pattern từ knowledge/coding/compose/essentials.md.
```

### Ví dụ 3 — Infer behavior block

**Design:** `detail.png` có icon bookmark top-right
**Spec:** không nhắc bookmark

**Resolution:**
```yaml
issues:
  - id: ISSUE-003
    type: MISSING_BEHAVIOR
    severity: blocker
    description: Bookmark icon không có spec; không rõ behavior.
    affected_requirements: []
    resolution_hint: >
      PM confirm feature bookmark. Nếu YES: tạo REQ mới + storage contract.
      Nếu NO: remove icon khỏi design.
    status: open
```

→ Blocker vì có thể cần schema change (storage bookmarked books).

### Ví dụ 4 — Duplicate requirement

**Spec L10:** "User có thể play preview"
**Spec L45:** "Nút Play phát 30 giây audio"

**Resolution:** merge thành REQ-001, preserve source refs cả 2:

```yaml
requirements:
  - id: REQ-001
    description: User tap Play phát 30s audio preview.
    evidence_status: confirmed
    source_references:
      - path: assets/sources/spec.md
        locator: L10
      - path: assets/sources/spec.md
        locator: L45

issues:
  - id: ISSUE-004
    type: DUPLICATE_REQUIREMENT
    severity: info
    description: Spec có 2 mentions của play preview; merged thành REQ-001.
    status: resolved
```

### Ví dụ 5 — Visual mismatch minor

**Spec:** "Cover image 2:3 aspect ratio"
**Screenshot:** cover visual tỉ lệ khoảng 3:4

**Resolution:**
```yaml
issues:
  - id: ISSUE-005
    type: SOURCE_CONFLICT
    severity: info
    description: Cover aspect ratio spec (2:3) vs screenshot (~3:4).
    resolution_hint: Spec thắng (business metadata); design update sau.
    status: resolved
```

→ Info severity vì không ảnh hưởng behavior, project convention: spec thắng cho data constraint.

## Anti-patterns (CẤM)

### AP-001 — Silent resolve

**Sai:** phát hiện conflict, chọn 1 side, không log issue.
**Đúng:** mọi conflict phải có issue (dù severity info).

### AP-002 — Over-blocker

**Sai:** mọi mismatch nhỏ (spacing, color estimate) đều blocker.
**Đúng:** blocker chỉ cho behavior/architecture impact.

### AP-003 — Under-blocker

**Sai:** label conflict mark `info` vì "chỉ là string".
**Đúng:** label conflict → blocker (ảnh hưởng copy, legal, analytics event name).

### AP-004 — Auto-generate missing design

**Sai:** không có error screenshot → agent tự "thiết kế" error layout trong brief.
**Đúng:** `states_missing: [error]` + issue `MISSING_DESIGN` + default pattern reference.

### AP-005 — Skip assumption documentation

**Sai:** resolve issue bằng default, không ghi vào `assumptions[]`.
**Đúng:** mọi default resolve phải có `ASSUME-XXX` link ngược.

## Severity escalation triggers

Downgrade từ `blocker` → `high` chỉ khi:

1. Project default rule exists (reference được)
2. Downstream workflow có safety net (ví dụ `coding-feature` Stage 2 Plan có open-question gate)
3. User explicit accept assumption

Escalate `info` → `high` khi:

1. Conflict xuất hiện ở ≥ 2 nơi trong spec
2. Affect ≥ 1 confirmed requirement AC
3. Project convention conflict với spec

## Required policies

- `blueprints/feature-brief/README.md` — issue schema
- `requirement-extraction-rules.md` — REQ-RULE-005 (AC chỉ confirmed)
- `screenshot-reading-rules.md` — DESIGN-RULE-002 (không infer nav)
- `constitution/` — project rules cho default resolve
