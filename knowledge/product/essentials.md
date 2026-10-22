# Product knowledge — essentials

Knowledge nền cho `product-analyst` agent (BA): market research, spec extraction, wireframe low-fi functional, acceptance criteria.

## 1. Market research mode

### Mục tiêu
Trước khi viết PRD, verify ý tưởng có value thực tế. Output `market-research.md` cho PM score feasibility.

### Checklist 5 câu
1. **Problem evidence** — user pain cụ thể là gì? Có quote/ticket/survey chứng minh?
2. **Current workaround** — user đang giải quyết thế nào (competitor app / manual / không giải quyết)?
3. **Competitor landscape** — tối thiểu 3 app competitor + feature matrix (ai có / ai thiếu)
4. **Distribution channel** — users phát hiện feature này qua đâu (search, viral, recommendation)?
5. **Success signal** — metric nào chứng minh feature "work" (retention +X%, DAU +Y%, revenue, NPS)?

**Rule**: Thiếu bằng chứng ≥ 2 trong 5 câu → flag "research incomplete", không đẩy xuống PM.

### Anti-patterns
- Market research = "feel like users want this" (không evidence)
- Competitor scan = "app lớn nào cũng có" (không matrix)
- Success signal vague ("improve engagement") — phải measurable

## 2. Spec extraction mode

Full procedure trong `knowledge/input-analysis/requirement-extraction-rules.md` (REQ-RULE-001..006).

### Checklist nhanh
1. Snapshot spec vào `briefs/<slug>/assets/sources/spec.md` (preserve nguồn)
2. Read full spec trước khi extract (không line-by-line)
3. Classify evidence: confirmed (có quote) / inferred (suy từ pattern) / unresolved (gap)
4. Assign ID: REQ-001.., NFR-001.., AC-001..
5. Quote exact source trong `source_references[].quote`

## 3. Wireframe low-fi mode

### Scope wireframe BA sở hữu
BA viết **functional-level**: screen có component gì, user thao tác thế nào, state nghiệp vụ ra sao. KHÔNG design pixel (Designer).

### Component taxonomy (functional)

| Loại | Ví dụ | Khi dùng |
|---|---|---|
| Input | TextField, Checkbox, Radio, Dropdown | User nhập/chọn data |
| Trigger | Button, Link, Tap-area | User action → effect |
| Display | Text, Image, List, Grid | Hiển thị data |
| Feedback | Toast, Snackbar, Dialog, Banner | System → user signal |
| Navigation | Tab, BottomNav, BackButton, Drawer | Chuyển màn |
| Status | ProgressBar, Loading, Error, Empty | State transition |
| Content | Card, Chip, Avatar, Badge | Compose data |

### 5 state nghiệp vụ bắt buộc per màn có remote data

| State | Khi nào | BA ghi gì |
|---|---|---|
| **loading** | Đang fetch | "Hiển thị skeleton 3 line / spinner" |
| **empty** | Fetch success, data = 0 | "Hiển thị message + CTA 'thêm mới'" (hoặc N/A nếu màn luôn có data) |
| **error** | Fetch fail | "Hiển thị ErrorView + Retry button" |
| **offline** | No network | "Banner 'Offline' + cached data (nếu có)" |
| **success** | Fetch success, data > 0 | "Hiển thị full layout" |

Thiếu bất kỳ state → wireframe incomplete, Designer sẽ reject.

### Wireframe format output

```json
{
  "screen_id": "book-detail",
  "nav_route": "book/{id}",
  "components": [
    {"id": "cover-img", "type": "Display:Image", "data_source": "book.coverUrl"},
    {"id": "title", "type": "Display:Text", "data_source": "book.title"},
    {"id": "read-now-btn", "type": "Trigger:Button", "action": "nav:reader/{bookId}"}
  ],
  "states": {
    "loading": "skeleton cover + 3-line title",
    "empty": "N/A (có id = must have data)",
    "error": "ErrorView + Retry",
    "offline": "banner + cached if any",
    "success": "full layout"
  },
  "user_flow": [
    "Enter from feed tap → fetch book → render success → tap read-now → nav reader"
  ]
}
```

## 4. Acceptance criteria formula

### Given-When-Then (preferred)

```
Given <precondition state>
When <user action hoặc system event>
Then <observable outcome + measurable>
```

Ví dụ:
```
Given user ở book-detail screen, book đã load thành công
When user tap "Read now" button
Then nav sang reader/{bookId} trong < 300ms
  AND reading progress được track từ page 1
```

### Measurable statement (alternative)

```
<Subject> <action> <object> <measurable constraint>
```

Ví dụ:
```
Book cover image load trong < 1s trên 3G
Error state hiển thị retry button mọi API fail code 4xx/5xx
```

### Rule bắt buộc
1. **AC chỉ bind confirmed REQ** — không AC cho inferred/unresolved
2. **Measurable** — có số/threshold/state transition
3. **Test hint rõ** — unit / UI / integration / E2E
4. **Coverage matrix** — mỗi confirmed REQ có ≥ 1 AC

### Red flags
- "Feature works correctly" — không measurable
- "User can see the book" — không state cụ thể
- "Fast enough" — thiếu threshold

## 5. Change Request flow

Khi downstream (Designer / Tech Lead / Coder) phát hiện PRD gap:

1. Downstream tạo `briefs/<slug>/change-requests/CR-<id>.md`
2. BA nhận notification → đánh giá:
   - Spec thực sự thiếu → update `requirements.md` version mới
   - Spec có nhưng không rõ → clarify + enrich
   - Downstream hiểu sai → reject CR với explanation
3. PM đánh giá impact deadline nếu expand scope
4. Orchestrator mark downstream artifact "needs re-validate"

## 6. Dependency

- `knowledge/input-analysis/*` — 5 rules file (extraction, confluence, figma, screenshot, reconciliation)
- `agents/product-analyst.md` — role spec
- `agents/workflows/feature-full-flow.md` — Stage 1 Discovery
- `skills/business-analyze` — procedure dispatcher phase spec/design/reconcile

## 7. Last updated

- Date: 2026-10-22
- Dependency version: harness v0.21.0
- Review trigger: khi spec source format mới (Linear, Notion) hoặc BA tooling đổi
