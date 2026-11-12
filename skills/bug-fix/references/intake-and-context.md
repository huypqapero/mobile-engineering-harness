# Intake + context pack + scout cache (Phase 1–2)

Mục tiêu: lấy đủ dữ liệu **một lần**, ghi vào batch dir để mọi agent đọc lại thay vì tự fetch/scout.

```
B/ (= <repo>/plans/bugfix-batch-<id>/)
├── manifest.json, state.json        # bfo_state.py
├── bugs.json                        # bug đã normalize
├── context/
│   ├── spec.md                      # Confluence snapshot (markdown) + header version
│   ├── figma-index.json             # màn → node id → preview FQN → screenshot
│   ├── references.md                # tóm tắt docs tham chiếu của repo + đường dẫn
│   ├── spec-delta.md                # mục spec đổi giữa version repo ghi và version live
│   └── main-health.md               # kết quả health check origin/main
├── scout.json, scout-report.md      # bug-scout
├── plan.json, confirm-checklist.md  # Phase 3 (+ decisions-pending.md: bảng ID quyết định)
├── context/ui-diff/<screen-slug>/   # actual.png + design.png chép từ run ui-diff (§1b)
└── evidence/<KEY>/                  # evidence.json (lane + device verifier), jira/ (đính kèm Jira)
```

## 1. Jira

Input chấp nhận:

| Input | Cách lấy |
|---|---|
| JQL | `jira_search(jql, fields="summary,description,status,priority,labels,components,issuetype,created", limit=50)`, phân trang bằng `start_at` tới hết `total` |
| URL board `RapidBoard.jspa?rapidView=<id>&projectKey=<P>` | Sprint đang chạy: `jira_get_sprints_from_board(board_id, state="active")` → `jira_get_sprint_issues`; hoặc JQL `project = <P> AND issuetype = Bug AND statusCategory != Done AND sprint in openSprints()` |
| `selectedIssue=<KEY>` trong URL | Đó là 1 issue ví dụ — hỏi user muốn cả board/sprint hay chỉ issue đó nếu không rõ |
| Danh sách key | `jira_get_issue` từng key (song song) |

`jira_search` có `description` đã đủ cho phần lớn bug — **không** gọi `jira_get_issue` cho từng issue. Chỉ gọi (`fields="description,attachment", include="comments", comment_limit=10, update_history=false`) cho bug thiếu expected/repro hoặc cần comment/ảnh. Không đưa `attachment` vào `jira_search` (kèm email + avatar người báo, phình output). Đính kèm: bug có attachment (ảnh/video/log) → `jira_download_attachments` vào `B/evidence/<KEY>/jira/` và ghi đường dẫn vào `attachments`; scout/lane đọc từ đó, không tự tải lại.

Normalize → `bugs.json`:

```json
{"PROJ-50": {"title": "[Player] Bỏ nút Share trong màn xem phim", "priority": "Medium",
  "screen_hint": "Player", "actual": "...", "expected": "...", "repro": "...",
  "frequency": "Always", "attachments": ["evidence/PROJ-50/jira/a.png"], "comments": ["..."],
  "url": "https://jira.../browse/PROJ-50"}}
```

- `screen_hint` lấy từ tiền tố `[...]` của title (`[For you][Ad native full]` → For You / Ad native full).
- Description thường có "Kết quả thực tế / Kết quả mong đợi" → tách `actual`/`expected`.
- Thiếu cả `expected` lẫn tham chiếu spec/Figma, hoặc không biết màn nào → `needs-info` ở Phase 3.
- Bỏ field rác (`customfield_*` null, devSummary). Không chép email/tên reporter vào file.
- **Video chỉ có link ngoài** (streamable, drive… agent không xem được) và description không đủ bước/kỳ vọng → `needs-info` + câu hỏi cho QA: mô tả bước, build, logcat. Không để scout suy đoán từ video.
- **Bug reopen** (QA test lại, status Reopened hoặc comment "vẫn lỗi") → hỏi QA build/commit SHA đã test trước khi xếp job repro; build cũ hơn fix đã merge → `already-fixed`, đề nghị test lại bản mới.

## 1b. Report `ui-diff` (không Jira)

Input: `<run>/summary.json` (hoặc thư mục run) do skill `ui-diff` sinh (`fix_priority[]`: `screen`, `region`, `severity`, `type`, `actual`, `expected`, `source_hint`, `confidence`; ảnh `<run>/screens/<screen>/{actual,design}.png`).

```bash
S import-ui-diff B <run>/summary.json        # ghi/gộp B/bugs.json, chép ảnh vào B/context/ui-diff/<screen-slug>/
```

- Mỗi finding = 1 bug key `UI-<screen-slug>-<n>` (`n` đếm theo màn; chạy lại với run mới giữ key của finding trùng `screen|region|type|actual|expected`, finding mới nối số tiếp). `bugs.json` mang `kind_hint: ui`, `verify_hint: preview`, `spec_verdict_hint: confirmed`, `spec_ref_hint` (ảnh `design.png` của màn là căn cứ), `attachments` trỏ ảnh actual/design, `source_hint` (file nghi vấn từ ui-diff), `url: null`.
- Không có Jira: bỏ qua bước Jira (§1) và mọi transition ở `mode-batch.md` §Jira status. Spec Confluence chỉ đọc khi finding cần (hành vi); UI lấy theo Figma/`design.png`.
- Các bước sau như batch thường: scout 1 lần (đưa `source_hint` + `screen` cho `bug-scout`), phân loại (`classify-and-plan.md` §UI-diff), lane, `evidence/<KEY>/evidence.json` riêng cho từng finding, `next-wave` lấy finding chưa PASS.

## 2. Spec (Confluence)

- Ưu tiên `page_id` (URL `display/<SPACE>/<Title>` → `confluence_get_page(title, space_key)` 1 lần để lấy id; về sau dùng id). Docs của repo có thể ghi sẵn page id.
- MCP không ghi file, nên **không chép lại cả trang**. `B/context/spec.md` = header (`pageId`, `version` lấy từ metadata, `fetched_at`) + các mục spec liên quan tới bug trong batch (trích nguyên văn, theo `screen_hint`). Cache `plans/bugfix-cache/spec-<pageId>.md` giữ cùng header; so field `version`: bằng nhau → dùng lại, không fetch.
- **Preflight spec drift (luôn làm ở Phase 1, trước khi chốt bug "chờ BA")**: lấy `version` live của trang rồi so với version ghi trong docs của repo (`docs/references/*spec*summary*`, header map spec↔code, decisions). Bằng nhau → xong. Lệch → ghi cảnh báo vào `spec.md` + `plan-summary.md` và giao `general-purpose` dùng `confluence_get_page_diff` giữa hai version (hoặc đọc lại trang) → `B/context/spec-delta.md`: chỉ các mục đổi liên quan bug đang `needs-confirm` / `spec-gap` / `not-a-bug` / `already-fixed`, mỗi mục trích nguyên văn + số version. Bug "chờ BA" đã có câu trả lời trong delta → chuyển lại `confirmed` + `spec_ref` version mới; bug trích spec cũ → kiểm lại với bản live. Map spec↔code của repo có thể cũ ở các mục đổi.
- Spec link tới trang con / sheet ads / sheet tracking: chỉ fetch khi bug cần (vd bug ads → sheet kịch bản ads). Google Sheet không đọc được qua MCP → ghi link vào context, không đoán nội dung.
- Thứ tự ưu tiên khi lệch: lấy theo quy ước của repo (vd `docs/references/README.md`). Mặc định: **UI theo Figma live, hành vi theo Confluence**.

## 3. Figma

1. Repo có screen registry (đọc ở `R`; vd `docs/references/*screen-registry.json`, `docs/design-refs/figma-refs.json` của `ui-fix-loop`) → dựng `figma-index.json`: `{screen_id: {name, section, node_id, figma_url, screenshot, previews: [{fqn, source}]}}`. Map field theo tên gần nghĩa (`figma_node_id`/`node_id` → `node_id`; `previews[].fqn`/`preview_fqn` → `previews`; `previews[].source`/`source_files` → `source`). `screen_hint` của bug ↔ `screen_id`: khớp tên màn hoặc section (không phân biệt hoa thường, bỏ dấu); không khớp → để trống, scout điền. Không gọi Figma ở bước này.
2. Không có registry → `get_figma_data(fileKey, nodeId=<page node>, depth=1)` để lấy danh sách frame (tên + node id) rồi map tên frame ↔ `screen_hint`. Không tải cả cây file.
3. Node chi tiết + ảnh thật chỉ tải **trong lane** cho bug tier `preview` (`get_figma_data` node màn, `download_figma_images` vào thư mục trong repo/evidence). Lỗi `403 Token expired` → báo user cập nhật token, không retry vòng.

## 4. Docs tham chiếu của repo

Đọc trong `R` (không phải main checkout) `docs/references/README.md` (hoặc tương đương) rồi các file nó trỏ tới: map spec↔Figma↔code, decisions-outside-spec, spec summary. Ghi `context/references.md` gồm: đường dẫn từng file, quy ước ưu tiên nguồn, lệnh render preview (variant flavor), lưu ý build (key cần trong `local.properties`). Lane đọc file này thay vì tự tìm.

Nếu repo có quy định "dev tự quyết hành vi ngoài spec phải ghi vào file decisions trong cùng PR" → đưa vào brief lane.

## 5. Main health (Phase 0, và sau mỗi PR của batch được merge)

Main hỏng thì mọi lane không chạy được gate chung. Giao `general-purpose` (không phải leader) chạy trong `R` (hoặc worktree detached tại `<remote>/<base>` mới nhất):
1. Compile test source của module chính (vd `./gradlew :app:compile<Variant>UnitTestKotlin`) + test wiring DI/smoke nếu repo có (vd `DiWiringTest`). Lệnh cụ thể lấy từ `context/references.md`.
2. Ghi `B/context/main-health.md`: commit, lệnh, PASS/FAIL, 10 dòng lỗi đầu, commit nghi ngờ (`git log` các PR vừa merge, ngoài batch cũng tính).
3. FAIL → báo user ngay + đề xuất lane `main-fix` (`kind: code`, `verify: unit`, chạy đầu; các lane cần gate `after` nó). Lane không bị ảnh hưởng vẫn chạy; lane bị chặn gate ghi rõ gate nào hỏng do main trong PR.

## 6. Scout cache (dùng lại giữa các batch)

Vị trí: `<repo>/plans/bugfix-cache/scout-<project>.json` + `.md` (không commit nếu repo ignore `plans/`).

```json
{"base_commit": "9aafa55", "updated": "2026-11-07T19:30:00",
 "areas": {"features/player": {"files": ["..."], "entry_points": ["..."], "previews": ["FQN"],
           "notes": "PssdkPlayerHost dựng player; unlock popup ở ..."}}}
```

Trước Phase 2:
1. Area cần cho batch = area của các `screen_hint` (qua map spec↔code hoặc tên package).
2. `git diff --name-only <cache.base_commit> <base_commit>` → area có file đổi = **stale**; area chưa có trong cache = **new**.
3. Scout đọc ở `R` (tạo ở Phase 0; main checkout có thể ở branch khác hoặc có file sửa dở).
4. Spawn `bug-scout` với: toàn bộ bug, danh sách area stale/new cần scout, phần cache còn dùng được (đưa thẳng nội dung, agent không cần đọc lại).
5. Sau scout: merge area mới vào cache, `base_commit` = commit của batch.

Cache chỉ giúp tìm file nhanh; root cause của từng bug vẫn phải được lane xác nhận bằng dòng code thật.

## Brief cho `bug-scout`

```
Repo (đọc tại đây): <repo>-worktrees/bfo-<batch-id>-scout  (detached @ <base_commit>, KHÔNG sửa)
Batch: <B>   Bugs: B/bugs.json   Spec: B/context/spec.md
Figma index: B/context/figma-index.json   References: B/context/references.md
Cache dùng lại (không scout lại các area này): <dán area + notes>
Area cần scout: <list>   Bug giao cho agent này: <tất cả | danh sách khi chia theo area>
Việc đang làm (tránh trùng): B/context/in-flight.md (PR mở, worktree khác)
Mỗi bug thêm so 1-1 spec: spec_quote (trích nguyên văn + mục/node, hoặc "spec không nói"), code_behavior (file:line),
  spec_verdict_hint: confirmed | not-a-bug | suspect + 1 câu lý do (leader chốt ở Phase 3)
Output: B/scout.json (hoặc B/scout-<area>.json khi chia) + B/scout-report.md theo agents/bug-scout.md
Ngôn ngữ báo cáo: tiếng Việt. Timezone Asia/Saigon.
```
