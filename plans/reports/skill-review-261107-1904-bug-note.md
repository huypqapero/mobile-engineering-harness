# Review skill `bug-note` (~/.claude/skills/bug-note)

Phạm vi: SKILL.md (100 dòng), references/worker-protocol.md (131), scripts/bug_queue.py. Chỉ đọc, chưa sửa.

## Kết luận

`bug-note` hợp cho mục đích của nó: ghi bug liên tục trong chat, mỗi bug 1 worker nền → 1 PR. Cơ chế claim file (WAIT/STACK) và queue dùng chung qua `git-common-dir` chắc chắn. Có 1 lỗi mức cao (stash), 2 lỗi trung bình (công cụ so UI sai, khóa thiết bị có thể bị cướp), và vài điểm khiến nó không phù hợp cho batch Jira — đó là lý do tách sang `bug-fix-orchestrator`.

## Trạng thái sửa (2026-11-07 20:10)

Đã sửa finding 1–3 trực tiếp trong `~/.claude/skills/bug-note` (bản sao lưu trước khi sửa ở scratchpad của session):
1. Worker không dùng `git stash`; thay bằng commit WIP trên branch của bug, squash trước khi push.
2. Tier `T2-ui` dùng `compare-ui-board` + `ui-diff-review` (ngưỡng 95) thay cho `ui-diff`.
3. `device-lock` không cho chiếm khóa khi bug giữ khóa chưa xong, dù giữ bao lâu. Bị chặn thì bug tự chuyển `waiting` với `blocked_by` = bug giữ khóa, worker báo `WAITING` thay vì poll 20 phút; leader resume khi bug kia xong. Thêm `device-release <serial>` để gỡ khóa treo bằng tay. Đã test kịch bản lock/busy/resume/release trong repo tạm.

## Findings

| # | Mức | Vị trí | Vấn đề | Đề xuất |
|---|---|---|---|---|
| 1 | Cao | worker-protocol.md §5 | Worker dùng `git -C "$WT" stash` / `stash pop`. Stash stack dùng chung mọi worktree của repo → worker song song có thể pop nhầm thay đổi của worker khác (mất hoặc trộn code). | Thay bằng commit WIP trên branch của bug, squash trước khi push. |
| 2 | Trung bình | worker-protocol.md §2 (bảng tier `T2-ui`), §6 | Dùng skill `ui-diff` để so preview ↔ Figma, nhưng `ui-diff` hiện chỉ có mode `video-to-figma`. Worker sẽ phải đoán hoặc rơi vào fallback. | Dùng `compare-ui-board` (ghép board) + `ui-diff-review` (chấm điểm) như `ui-fix-loop`. |
| 3 | Trung bình | bug_queue.py `cmd_device_lock` | Khóa thiết bị quá 30 phút bị coi là stale và cho bug khác chiếm, kể cả khi holder vẫn đang chạy → 2 worker trên 1 emulator. Không biết task ARTEMIS ngoài queue. Worker chờ khóa bằng vòng retry 60s × 20 phút → tốn token. | Không tự cướp; báo leader. Leader điều phối thiết bị theo sự kiện (như `bfo_state.py device-dispatch --exclude`). |
| 4 | Trung bình | SKILL.md §Roles, worker prompt | Worker là `general-purpose`, không nạp rule harness (Coder/Architect, MVI, Clean Architecture) → chất lượng fix phụ thuộc prompt. | Dùng agent harness `bug-fixer` (đã tạo) cho worker. |
| 5 | Trung bình | worker-protocol.md §2 | Mỗi worker tự scout từ đầu; không đọc spec/Figma/docs references chung → N bug cùng màn scout N lần. | Với batch: dùng `bug-fix-orchestrator` (scout 1 lần + cache). Với bug-note: cho worker đọc `docs/references/` + scout cache nếu có. |
| 6 | Thấp | bug_queue.py `cmd_set` | Nhận key/status bất kỳ; gõ sai status làm `active-count`/`waiters` đếm sai. | Validate status theo danh sách cố định. |
| 7 | Thấp | SKILL.md description | Trigger `'bug:'`, `'lỗi:'` rộng, dễ kích hoạt khi user chỉ đang kể lỗi. | Giữ `/bug-note`, `note bug`, `ghi bug`; bỏ `bug:`/`lỗi:` hoặc yêu cầu đầu câu. |
| 8 | Thấp | worker-protocol.md §1, §8 | Base cố định `main`; repo có nhiều remote (vd AIP699 có `origin` = AAP884 và `aip699`) → worker có thể chọn sai remote. | Leader xác định remote + base một lần, truyền vào prompt (đã có chỗ `<origin remote name>`, nên ghi rõ cách chọn). |
| 9 | Thấp | vị trí skill | Skill chỉ nằm ở `~/.claude/skills/`, không có trong harness repo → không version, team không dùng chung. | Nếu muốn dùng chung: chuyển vào `skills/bug-note/` của harness và symlink như các skill khác. |

## Những gì nên giữ

- Claim file: bug đang `fixing` chặn, bug `pr_open` thì stack; bug `waiting` không chặn ai → không deadlock.
- State ngoài repo (`<git-common-dir>/bug-note/`), file lock, ghi atomic.
- `sync-merged` không xóa worktree còn thay đổi tracked.
- Tier verify + hàng chờ test thiết bị (`DEVICE-TEST-QUEUE.md`) — `bug-fix-orchestrator` dùng lại ý tưởng này ở dạng 4 tier none/unit/preview/device.

## Vị trí

Đã chuyển vào harness: `skills/bug-note/` (2026-11-07 20:10). Finding 9 đã xử lý. Finding 4 đã xử lý: worker spawn agent `bug-fixer` (fallback `general-purpose` nhập vai khi agent chưa đăng ký).
