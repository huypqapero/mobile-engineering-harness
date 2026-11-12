# Phân loại, gom nhóm, xếp lane (Phase 3)

Input: `bugs.json`, `scout.json`, `context/spec.md`, `context/figma-index.json`. Output: `plan.json` (gate bằng `bfo_state.py check-plan`) + `confirm-checklist.md`. Các bước chạy tuần tự, bước sau dùng kết quả bước trước.

## Bước 0 — So 1-1 với spec (spec verdict)

Jira không phải lúc nào cũng đúng: tester có thể hiểu nhầm, kỳ vọng vượt spec, hoặc test trên build/config khác. **Chỉ fix khi chắc chắn là bug.** Với từng bug, đặt 3 cột cạnh nhau:

| Tester nói (actual/expected) | Spec/Figma nói (trích nguyên văn + mục/node) | Code đang làm (file:line từ scout) |

| Kết quả so | Verdict | Xử lý |
|---|---|---|
| Spec/Figma nói rõ X, app làm khác X, tester đòi đúng X | `confirmed` | fix (`code`/`ui`/`content`), ghi `spec_ref` |
| Spec/Figma nói rõ, app đã đúng, tester kỳ vọng khác | — | `not-a-bug`, trích căn cứ |
| Spec im lặng / mơ hồ / spec ↔ Figma lệch / tester đòi thứ ngoài spec / nghi môi trường test (remote config, build cũ, ad test) / bug chỉ là ý kiến UX | nghi ngờ | `needs-confirm` + `question`, **không fix, không chặn** |
| Spec ghi "PO confirm"/TBD | nghi ngờ | `spec-gap` (hỏi PO) |

Nguồn so theo quy ước repo (mặc định UI theo Figma live, hành vi theo Confluence) + file decisions-outside-spec. Không tự suy ra "chắc là bug" từ cảm giác UX; không có căn cứ trích được → nghi ngờ. `check-plan` chặn mọi bug fixable thiếu `spec_verdict: confirmed` + `spec_ref`.

## Bước 1 — `kind`: bug này có sửa trong batch được không?

| kind | Khi nào | Vào batch? |
|---|---|---|
| `code` | Logic/flow/state/điều hướng/crash/remote config/ads wiring sai so với spec | Có |
| `ui` | Layout/màu/text/icon/spacing lệch Figma live, thêm/bỏ phần tử theo Figma/spec | Có |
| `content` | Chuỗi dịch, text cố định, asset, giá trị default config — không đổi logic | Có |
| `spec-gap` | Spec mâu thuẫn Figma, spec ghi "PO confirm", yêu cầu mới chưa có trong spec/Figma | Không — câu hỏi PO |
| `needs-confirm` | Bước 0 ra "nghi ngờ": có thể hiểu nhầm/ngoài spec, cần user/BA/tester xác nhận | Không (tạm) — vào `confirm-checklist.md`, fix ở lane sau khi được trả lời |
| `needs-info` | Không xác định được màn/hành vi mong đợi, không có repro | Không — hỏi reporter |
| `duplicate` | Trùng root cause *và* triệu chứng với bug khác | Không — ghi `reason: duplicate of <KEY>` |
| `not-a-bug` | Hành vi đúng spec/decisions-outside-spec | Không — trích căn cứ |
| `external` | Lỗi trong lib/SDK bên ngoài (lib FO, ad SDK) mà app không chỉnh được bằng config | Không — ghi ai xử lý |
| `already-fixed` | Scout thấy fix đã merge vào base sau ngày tạo bug, hoặc PR đang mở xử lý đúng bug này | Không — ghi PR/commit, đề nghị QA test lại |
| `conflict` | Hai bug trong batch đòi kết quả trái nhau (vd một bug đòi bỏ phần tử, bug khác đòi phần tử đó hoạt động) | Không — cả hai bug, hỏi user/PO chọn |

Bug trích spec/hành vi cũ: so với spec live (version trong `spec.md`) và file decisions-outside-spec trước khi xếp `not-a-bug` hay `code`.

Bug gắn label "Bug" nhưng thực chất là thiếu tính năng có trong spec (vd "Thiếu login demo" khi spec mô tả popup Login Demo) → vẫn `code`/`ui` nếu spec + Figma đủ rõ; chỉ `spec-gap` khi thiếu căn cứ.

## Bước 2 — `verify`: chứng minh fix bằng gì?

Chọn mức **thấp nhất đủ chứng minh**. Bug lai lấy mức cao nhất.

| verify | Dùng khi | Evidence bắt buộc | Thiết bị |
|---|---|---|---|
| `none` | Đổi text/dịch, bỏ phần tử đơn giản không ảnh hưởng logic, default config, đổi resource; đúng/sai nhìn được ngay trong diff | diff + compile (+ lint resource nếu là strings) | Không |
| `unit` | Logic thuần ở ViewModel/UseCase/Repository/mapper: điều kiện, tính toán, state reducer, đọc remote config | unit test regression (happy + ≥1 edge) PASS | Không |
| `preview` | UI tĩnh có/thêm được `@Preview`: layout, màu, spacing, ẩn/hiện phần tử theo state | preview PNG trước/sau + board so Figma (`compare-ui-board`/`ui-diff-review`) | Không |
| `device` | Cần runtime thật: player/video, ads (load/show/lifecycle/âm thanh đè ad), IAP, quyền hệ thống, notification, share sheet, deeplink, process death/hide app, mạng mất, animation theo thời gian, crash chỉ lộ khi chạy | ARTEMIS screenshot/video + logcat theo checklist | Có — xếp hàng |

Gợi ý nhanh:
- Từ khoá `crash`, `ad`/`ads`, `âm thanh`, `phát lại`/`replay`, `ngắt internet`, `hide app`/`back về app`, `quyền`, `animation`, `share`, `IAP`/`mua` → thường `device`.
- Bug `device` vẫn phải có `unit` nếu phần logic test được (vd điều kiện ẩn nút theo remote key) — lane chạy unit trước, job device chỉ để xác nhận runtime.
- `preview` bắt buộc màn có/được thêm `@Preview` dùng production Content.
- UI tĩnh không có preview (layout XML, màn của lib) và thay đổi nhìn được trong diff (đổi text, ẩn view, đổi dimen) → `none` + checklist test tay **không chặn PR** (ghi vào PR + `B/device-test-queue.md`). Chỉ chọn `device` khi chính hành vi runtime là thứ cần chứng minh — tránh dồn mọi bug vào hàng chờ thiết bị và PR draft.
- Crash/ANR chưa có stack trace hoặc dòng code nghi vấn confidence `low` → `verify: device` + `repro_first: true` (leader chạy job repro lấy logcat trước khi lane fix).

## Bước 3 — Gom `group` (đơn vị FIX)

Một group = một root cause / một patch. Gom khi:
1. `scout.json` chỉ cùng `file:line` nghi vấn hoặc cùng hàm, **hoặc**
2. Cùng cơ chế (vd 3 bug "tắt key remote X nhưng vẫn hiện" ở 3 màn cùng đọc 1 config provider), **hoặc**
3. Cùng component dùng chung (vd mọi lỗi của `NativeFullAd` composable).

Không gom chỉ vì cùng màn nếu root cause khác — đặt chung lane là đủ. Mỗi group ghi `files` (file sẽ sửa, phải tồn tại ở base; file mới → `new_files_ok: true`), `shared_files` (DI, NavHost, `strings.xml`, routes, Analytics… từ scout — script tính cả vào kiểm chồng file) và `cause` (giả thuyết 1 câu).

Fix **độc lập** (group riêng, lane riêng nếu có thể): crash Highest, bug đụng shared contract, bug rủi ro cao (payment/IAP, migration) — để PR nhỏ, review và revert dễ.

## Bước 4 — Xếp `lane` (= worktree = PR)

1. Ghép group vào lane theo **feature package** (vd `features/player/`), mỗi lane ≤ 8 bug (script cảnh báo khi vượt).
2. Hai lane sửa chung file → script báo lỗi; chọn: gộp chung lane (ưu tiên), hoặc `after: [<lane trước>]` (lane sau rebase lên branch lane trước, PR stack). Lane đã merge vào base (`status=done` hoặc `merged=base`) không còn tính chồng file: chạy `check-plan --batch B` khi thêm lane mới sau khi batch đã có PR merge.
3. Shared file (DI module, NavHost, `strings.xml`, Analytics, `build.gradle.kts`) chỉ nên nằm ở 1 lane; nhiều lane cần → lane đó chạy cuối bằng `after`.
4. Lane chỉ có bug `none`/`unit`/`preview` xong sớm, PR ready ngay; lane có bug `device` mở PR **draft** tới khi job device pass. Muốn PR ready sớm → tách bug `device` ra lane riêng.
5. Thứ tự ưu tiên chạy: lane có Highest/crash trước (đặt tên `L1`, `L2`… theo ưu tiên; `next-lanes` sắp tự nhiên, `L2` trước `L10`).
6. Bug cần migration DB, tính năng lớn (vd cả một màn mới) hoặc đụng contract dùng chung → lane riêng và nêu trong "điểm cần user quyết" của `plan-summary.md`.

## UI-diff — finding từ report `ui-diff`

Bug `UI-<screen-slug>-<n>` (`intake-and-context.md` §1b) đã được `ui-diff` so ảnh actual với `design.png` của màn nên **bước 0 so spec đã có căn cứ**: `kind: ui`, `verify: preview`, `spec_verdict: confirmed`, `spec_ref` = `spec_ref_hint` trong `bugs.json`. Finding `confidence: low` hoặc `design.png` không rõ (nghi ảnh sai trạng thái) → `needs-confirm` + `question`. Gom group theo màn / component (cùng `source_hint`, cùng file); mỗi finding vẫn có `evidence.json` riêng. Không có Jira: không vào `jira-sync`.

## `plan.json`

```json
{
  "issues": {
    "PROJ-50": {"title": "[Player] Bỏ nút Share", "kind": "ui", "verify": "preview",
                  "group": "player-actions", "screen": "3.5", "figma_node": "17:6324",
                  "spec_verdict": "confirmed", "spec_ref": "Figma 17:6324: cột action không có Share",
                  "reason": "PlayerScreen còn ShareButton"},
    "PROJ-48": {"title": "Crash Watch ad", "kind": "code", "verify": "device",
                  "group": "unlock-ad-crash", "spec_verdict": "confirmed",
                  "spec_ref": "Crash luôn là bug (không cần spec)", "reason": "Crash runtime khi load reward ad"},
    "PROJ-23": {"title": "Quality hiện 360/480/720", "kind": "needs-confirm",
                  "reason": "Spec 3.6 chỉ liệt kê Auto/HD, không nói ẩn mức thấp",
                  "question": "Có ẩn 360/480 không, hay tester kỳ vọng ngoài spec?"},
    "PROJ-53": {"title": "Thiếu login demo", "kind": "spec-gap",
                  "reason": "Spec: tài khoản demo lấy từ remote config SDK — key nào? hỏi PO"}
  },
  "groups": {
    "player-actions": {"issues": ["PROJ-50"], "files": ["app/src/main/java/.../player/PlayerScreen.kt"],
                       "cause": "Cột action còn Share"},
    "unlock-ad-crash": {"issues": ["PROJ-48"], "files": ["app/src/main/java/.../unlock/UnlockViewModel.kt"],
                        "cause": "Reward ad gọi show khi chưa load xong"}
  },
  "lanes": {
    "L1": {"groups": ["unlock-ad-crash"], "slug": "unlock-ad-crash"},
    "L2": {"groups": ["player-actions"], "slug": "player-ui"}
  }
}
```

Field bắt buộc: issue fixable → `kind, verify, group, reason, spec_verdict: "confirmed", spec_ref` (+ `repro_first` tuỳ chọn); issue loại → `kind, reason` (không `group`), `needs-confirm` thêm `question`; group → `issues, files, cause` (+ `shared_files`, `new_files_ok`); lane → `groups` (+ `after`, `slug`). Đường dẫn file repo-relative. Mọi key trong `bugs.json` phải có trong `issues` (`check-plan --bugs` bắt). Key issue: Jira `PROJ-123`, `TASK-<slug>` cho việc không có Jira (slug chữ thường, ≥1 chữ cái), hoặc `UI-<screen-slug>-<n>` cho finding ui-diff (script bỏ qua cả hai khi `jira-sync`).

## `confirm-checklist.md` — câu hỏi không chặn tiến độ

Mỗi bug `needs-confirm`/`spec-gap`/`conflict` một mục, đủ ngữ cảnh để user trả lời **không cần mở Jira/code**:

```
### [ ] PROJ-23 — [Detail film][Quality] Đang hiển thị các option 360/480/720
- Tester báo: <actual> → mong đợi <expected>
- Spec nói: "<trích nguyên văn>" (Confluence v<N>, mục <x>) · Figma: <node / không có>
- App hiện tại: <hành vi + file:line>
- Vì sao nghi ngờ: <hiểu nhầm? spec im lặng? ngoài scope? môi trường test?>
- Câu hỏi: <1 câu, trả lời được bằng chọn A/B>
- A. Fix theo Jira — phạm vi: <file/màn>, rủi ro <thấp/vừa>, verify <tier>
- B. Không fix — đóng/không phải bug, lý do gửi tester: <1 câu>
- Đề xuất của dev: <A|B> vì <…>
- Trả lời: ___
```

Thứ tự: bug ưu tiên cao trước; gom câu hỏi trùng chủ đề (vd mọi câu "tắt remote key") thành một mục có nhiều key.

## Không chặn tiến độ — trả lời bất đồng bộ

- Lane của bug `confirmed` chạy ngay; checklist chỉ là output, leader **không chờ** trả lời. Khi user nói "fix luôn bug chắc chắn" coi như duyệt plan cho các lane đó (tương đương `--yes`).
- User trả lời 1 mục (bất kỳ lúc nào, có thể trong session sau qua `resume <batch>`):
  - **A (fix)** → issue thành `code`/`ui`/`content` + `spec_verdict: confirmed`, `spec_ref: "User xác nhận <ngày>: <tóm tắt>"`, tạo group + lane **mới** (`C1`, `C2`…; không nhét vào lane đang chạy); đụng file của lane đang chạy → `after: [<lane đó>]`. `check-plan` → `load-plan` (lane đang chạy giữ nguyên trạng thái) → `next-lanes`.
  - **B (không fix)** → `not-a-bug`, `reason` = câu trả lời; ghi vào báo cáo để gửi tester/BA.
  - Đánh dấu `[x]` + ghi câu trả lời trong `confirm-checklist.md`; ghi `S issue B <KEY> answer="<tóm tắt>"` để `next-wave` nhận ra ticket đã trả lời.
- Lane chờ câu trả lời/quyết định ngoài (không phải lỗi agent) → `S lane B <L> status=blocked note=…`; trả lời xong `status=planned` (hoặc tiếp tục agent). Lane bị huỷ/gộp vào lane khác → `S lane-remove B <L> --plan B/plan.json`, gán lại group mồ côi vào lane còn lại rồi `check-plan` + `load-plan` (không sửa `plan.json` tay để gỡ lane).
- Chưa trả lời khi đóng batch → liệt kê trong báo cáo cuối, batch vẫn đóng được.

## Decision board — `B/decisions-pending.md`

Mỗi quyết định cần PO/BA/user có **một ID** (`D1`, `D2`… tăng dần, không tái dùng). Gom câu hỏi trùng chủ đề (nhiều bug cùng hỏi "tắt remote key X") vào một ID. Chi tiết từng bug vẫn ở `confirm-checklist.md`; board chỉ là chỉ mục:

```
| ID | Câu hỏi (1 dòng) | Bug | Lựa chọn | Đề xuất | Trạng thái |
| D1 | Ẩn hay disable nút Retry khi offline? | PROJ-12, -13 | A. ẩn / B. disable | A | open |
| D2 | Quality có ẩn 360/480? | PROJ-23 | A. ẩn / B. giữ | B | answered A · 261110 · PO (ảnh sheet) |
```

- Mỗi tin gửi user chỉ liệt kê dòng `open` **mới hoặc đổi** (ID + câu hỏi + lựa chọn + đề xuất), không nhắc lại dòng đã gửi trừ khi user hỏi; user trả lời theo ID ("D1=A, D2=B"). Quyết định nằm trong ảnh/sheet → chép nguyên văn nguồn vào cột Trạng thái.
- Có câu trả lời → cập nhật `answered <lựa chọn> · <ngày> · <nguồn>`, áp dụng như §Không chặn tiến độ (mục `[x]` trong checklist, bug vào lane `C<n>` hoặc `not-a-bug`), sửa `spec_ref` thành `D<id>`.
- Quyết định `answered` đổi hành vi so với spec → giao `general-purpose` ghi DEC vào file decisions-outside-spec của repo (id DEC kế tiếp theo quy ước repo; ghi ID board, ngày, nguồn, bug liên quan) trong **một PR docs của batch** (draft, không chặn lane). Repo không có file đó → ghi trong báo cáo cuối.

## Quyết định đổi sau khi PR đã ready

PO/BA đổi quyết định cho bug mà PR đã `gh pr ready` (hoặc Jira đã Resolved). Chưa merge:
1. `gh pr ready <pr> --undo` (về draft); `S lane B <L> status=running ready=no`; `S jira-sync B` rồi đưa các issue bị ảnh hưởng về **In Progress**.
2. Ghi quyết định vào board (ID mới hoặc `answered` đổi), cập nhật `spec_ref`/`verify` trong plan, `check-plan` + `load-plan`.
3. SendMessage `bug-fixer` của lane (agent đã kết thúc → spawn mới kèm brief + diff hiện tại): quyết định mới, issue ảnh hưởng, cập nhật `fix-design.md`; lane chạy lại gate fresh-with-main.
4. Evidence cũ của issue thành stale: device job đã pass không còn giá trị — `device-request` lại với APK mới nếu tier `device`.
5. `bug-reviewer` review vòng mới (đếm lại từ vòng 1 cho thay đổi do quyết định) → APPROVE → `gh pr ready` + Resolved.

PR đã merge rồi → không hạ draft: lane mới (`C<n>`, PR mới từ base), issue về **Reopened/In Progress**.

## Trình user (trước Phase 4) — ghi `B/plan-summary.md`

```
Batch 261107-1904-proj — 52 bug: 41 vào batch / 11 loại
| Lane | PR dự kiến | Bug | Verify | Ghi chú |
| L1 | fix/proj-unlock-ad-crash | PROJ-48, -10 | device | crash Highest, PR riêng |
| L2 | fix/proj-player-ui | -50, -23 | preview, unit | |
Bị loại: PROJ-53 spec-gap (câu hỏi PO), ...
Device: 9 bug cần thiết bị → hàng chờ trên emulator-5554
```

Cuối bảng: mục **Cần user quyết** (bug `conflict`, migration, tính năng lớn, bug confidence low vẫn giữ trong batch) và cảnh báo version spec nếu có.

Bug bị loại (`not-a-bug`, `duplicate`, `already-fixed`, `external`, `needs-info`) ghi 1 dòng căn cứ trong `plan-summary.md`; câu hỏi cần trả lời nằm ở `confirm-checklist.md`.
