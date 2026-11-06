# Skill audit — `skills/bug`

## Giả định & scope
- Target: `/Users/kohuyn/StudioProjects/mobile-engineering-harness/skills/bug` (project scope).
- Target model: không chỉ định → đánh giá theo frontier model mặc định.
- Audit chỉ đọc + báo cáo, không sửa file skill.

## Inventory bề mặt
| File | Dòng | Vai trò |
|---|---|---|
| `SKILL.md` | 50 | Dispatcher, chọn mode fix/triage |
| `references/mode-fix.md` | 129 | Pipeline bugfix-fast-path |
| `references/mode-triage.md` | 124 | Classify 3 nhánh code/design/spec |

Không có `scripts/`. Không có hook inject. Skill **untracked** (`?? skills/bug/`) → mới tạo, chưa có git history để truy provenance.

## Session evidence
- `session_usage.py`: **0 invocations / 0 sessions** (exit 1, 1244 transcript matched nhưng không transcript nào trigger skill `bug`).
- Kết luận: chưa có bằng chứng runtime nào. `unused_skill_files` liệt kê cả 2 reference chỉ vì 0 lần chạy — không phải finding thật. Audit dưới đây thuần tĩnh.

## Structural + lint
- `quick_validate.py`: **PASS** (description < 1024 char, các file < 300 dòng, link hợp lệ).
- `lint_cruft.py --routing`: **0 High, 0 Medium, 2 Low**.

## Kiểm chứng cross-reference (semantic)
Tất cả đều resolve → không có dangling reference:
- `agents/{tech-lead,coder,architect,product-analyst,qa}.md` ✓
- `agents/workflows/{bugfix-fast-path,bug-triage}.md` ✓
- `agents/lesson-miner.md` ✓ (là agent thật)
- `agents/tech-lead.md §Step 7` → khớp dòng 154 "Step 7 — Bug triage" ✓
- `skills/{coding-review,feature,coding-diagnose}` ✓
- `knowledge/product/input-analysis/requirement-extraction-rules.md` → file vật lý **không còn** (đã cutover sang team-knowledge MCP, commit `ca550ef`) **nhưng** đi kèm KB locator `[KB → product/input-analysis, kb_search "..."]`. Đây là convention repo (CLAUDE.md dùng y hệt: `path [KB → scope, kb_search "..."]`) → **không tính lỗi**.

## Findings

### F1 — step-choreography (Low) · lint-confirmed
- `references/mode-fix.md:20` (5 "Step" headers), `references/mode-triage.md:19` (4 headers).
- Signal: nhiều Step header không có câu khẳng định thứ tự bắt buộc.
- Đánh giá: thuộc **keep-list** — thứ tự ở đây mã hoá dependency thật (triage → implement → verify → close; Coder đọc triage report của Step 1). Không phải cruft.
- Confidence: **Low** (author flag). Đề xuất: thêm một câu "các Step chạy tuần tự, mỗi step tiêu thụ output của step trước" để vừa làm rõ cho reader vừa dọn lint, thay vì xoá đánh số.

### F2 — anchor `§Step 7` fragile, lặp 3 nơi (Low) · semantic
- `SKILL.md:39`, `mode-fix.md` (block prompt), `mode-triage.md` (block prompt).
- Hiện resolve đúng (tech-lead.md:154). Rủi ro: anchor theo số thứ tự section — nếu `tech-lead.md` chèn/đổi số section, cả 3 chỗ gãy âm thầm mà lint không bắt.
- Confidence: **Low** (maintainability). Đề xuất: trỏ bằng tiêu đề ổn định ("§ Bug triage (từ QA)") thay vì số "Step 7".

### F3 — `priority: P0` là field frontmatter phi chuẩn (Low) · informational
- `SKILL.md:4`. `quick_validate` tolerate (không chặn), nhưng không phải field skill metadata chuẩn và không ảnh hưởng activation ở Claude Code.
- Confidence: **Low**. Giữ nếu là convention nội bộ harness; nếu không, bỏ để tránh hiểu nhầm là có tác dụng routing. Không tự quyết — cần xác nhận đây có phải convention harness.

### F4 — Inputs lặp giữa SKILL.md và reference (Low) · semantic
- `SKILL.md:31-35` tóm tắt Inputs rồi "Chi tiết: xem reference"; `mode-fix.md:7-16` / `mode-triage.md:8-16` lặp lại gần đủ. Khi chạy 1 mode, cả SKILL.md + reference cùng nạp vào một context → Inputs xuất hiện 2 lần.
- Confidence: **Low**. Split hiện tại (summary + pointer) chấp nhận được; chỉ cân nhắc rút gọn block ở SKILL.md thành 1 dòng pointer nếu muốn giảm trùng.

## Proposed hunks (tùy chọn — toàn bộ Low, không bắt buộc)

F1 — `references/mode-fix.md`, ngay trước `## Procedure`:
```diff
+> Các Step chạy tuần tự; mỗi step tiêu thụ output của step trước (triage report → Coder → QA verify → close).
+
 ## Procedure
```
(tương tự cho `references/mode-triage.md`)

F2 — thay anchor số bằng tiêu đề, ví dụ `SKILL.md:39`:
```diff
-- Step 1 luôn là **Tech Lead triage** (`agents/tech-lead.md §Step 7`).
+- Step 1 luôn là **Tech Lead triage** (`agents/tech-lead.md` § Bug triage (từ QA)).
```

## Kết luận
Skill `bug` **khỏe mạnh**: structural valid, 0 High/0 Medium lint, mọi cross-reference resolve. Chỉ còn 4 finding Low mang tính polish/maintainability, không có finding nào buộc phải sửa. Dispatcher gọn, routing cụ thể (mô tả rõ fix vs triage), không dính pressure/threat/booster language.

## Câu hỏi chưa giải quyết
1. `priority: P0` (F3) có phải convention nội bộ harness không? Nếu có thì giữ; nếu không nên bỏ.
2. Có muốn mình chạy `optimize skills/bug --apply` để áp các hunk F1/F2 không, hay để nguyên (vì toàn Low)?
