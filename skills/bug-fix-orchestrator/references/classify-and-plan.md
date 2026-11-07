# Phân loại, gom nhóm, xếp lane (Phase 3)

Input: `bugs.json`, `scout.json`, `context/spec.md`, `context/figma-index.json`. Output: `plan.json` (gate bằng `bfo_state.py check-plan`) + `questions-for-po.md`. Các bước chạy tuần tự, bước sau dùng kết quả bước trước.

## Bước 1 — `kind`: bug này có sửa trong batch được không?

| kind | Khi nào | Vào batch? |
|---|---|---|
| `code` | Logic/flow/state/điều hướng/crash/remote config/ads wiring sai so với spec | Có |
| `ui` | Layout/màu/text/icon/spacing lệch Figma live, thêm/bỏ phần tử theo Figma/spec | Có |
| `content` | Chuỗi dịch, text cố định, asset, giá trị default config — không đổi logic | Có |
| `spec-gap` | Spec mâu thuẫn Figma, spec ghi "PO confirm", yêu cầu mới chưa có trong spec/Figma | Không — câu hỏi PO |
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
2. Hai lane sửa chung file → script báo lỗi; chọn: gộp chung lane (ưu tiên), hoặc `after: [<lane trước>]` (lane sau rebase lên branch lane trước, PR stack).
3. Shared file (DI module, NavHost, `strings.xml`, Analytics, `build.gradle.kts`) chỉ nên nằm ở 1 lane; nhiều lane cần → lane đó chạy cuối bằng `after`.
4. Lane chỉ có bug `none`/`unit`/`preview` xong sớm, PR ready ngay; lane có bug `device` mở PR **draft** tới khi job device pass. Muốn PR ready sớm → tách bug `device` ra lane riêng.
5. Thứ tự ưu tiên chạy: lane có Highest/crash trước (đặt tên `L1`, `L2`… theo ưu tiên; `next-lanes` sắp tự nhiên, `L2` trước `L10`).
6. Bug cần migration DB, tính năng lớn (vd cả một màn mới) hoặc đụng contract dùng chung → lane riêng và nêu trong "điểm cần user quyết" của `plan-summary.md`.

## `plan.json`

```json
{
  "issues": {
    "AAP884-50": {"title": "[Player] Bỏ nút Share", "kind": "ui", "verify": "preview",
                  "group": "player-actions", "screen": "3.5", "figma_node": "17:6324",
                  "reason": "Spec: màn xem phim không có Share; PlayerScreen còn ShareButton"},
    "AAP884-48": {"title": "Crash Watch ad", "kind": "code", "verify": "device",
                  "group": "unlock-ad-crash", "reason": "Crash runtime khi load reward ad"},
    "AAP884-53": {"title": "Thiếu login demo", "kind": "spec-gap",
                  "reason": "Spec: tài khoản demo lấy từ remote config SDK — key nào? hỏi PO"}
  },
  "groups": {
    "player-actions": {"issues": ["AAP884-50"], "files": ["app/src/main/java/.../player/PlayerScreen.kt"],
                       "cause": "Cột action còn Share"},
    "unlock-ad-crash": {"issues": ["AAP884-48"], "files": ["app/src/main/java/.../unlock/UnlockViewModel.kt"],
                        "cause": "Reward ad gọi show khi chưa load xong"}
  },
  "lanes": {
    "L1": {"groups": ["unlock-ad-crash"], "slug": "unlock-ad-crash"},
    "L2": {"groups": ["player-actions"], "slug": "player-ui"}
  }
}
```

Field bắt buộc: issue fixable → `kind, verify, group, reason` (+ `repro_first` tuỳ chọn); issue loại → `kind, reason` (không `group`); group → `issues, files, cause` (+ `shared_files`, `new_files_ok`); lane → `groups` (+ `after`, `slug`). Đường dẫn file repo-relative. Mọi key trong `bugs.json` phải có trong `issues` (`check-plan --bugs` bắt).

## Trình user (trước Phase 4) — ghi `B/plan-summary.md`

```
Batch 261107-1904-aap884 — 52 bug: 41 vào batch / 11 loại
| Lane | PR dự kiến | Bug | Verify | Ghi chú |
| L1 | fix/aap884-unlock-ad-crash | AAP884-48, -10 | device | crash Highest, PR riêng |
| L2 | fix/aap884-player-ui | -50, -23 | preview, unit | |
Bị loại: AAP884-53 spec-gap (câu hỏi PO), ...
Device: 9 bug cần thiết bị → hàng chờ trên emulator-5554
```

Cuối bảng: mục **Cần user quyết** (bug `conflict`, migration, tính năng lớn, bug confidence low vẫn giữ trong batch) và cảnh báo version spec nếu có.

`questions-for-po.md`: mỗi bug loại 1 mục — key, câu hỏi cụ thể, đoạn spec/Figma mâu thuẫn, đề xuất mặc định của dev.
