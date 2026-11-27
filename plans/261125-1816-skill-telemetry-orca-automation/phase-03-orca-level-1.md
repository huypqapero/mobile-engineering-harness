# Phase 3: Orca mức 1

## Context

Orca 1.4.224 đã cài, runtime `ready`. CLI dùng được: `/Applications/Orca.app/Contents/Resources/bin/orca` (symlink `/usr/local/bin/orca` đang hỏng). Các repo app đã đăng ký trong Orca.

## Requirements

Mỗi repo app có automation (giữ phiên bằng `--workspace <worktree> --reuse-session`):

| Tên | Lịch | Prompt |
|---|---|---|
| `<app> sáng` | weekdays 08:15 Asia/Saigon | `/bug-fix status`, liệt kê việc chờ người |
| `<app> resume` | `*/30 * * * *` | `/bug-fix resume` |
| `<app> sync-jira` | `0 */2 * * *` | `/bug-fix sync-jira` |
| `telemetry sync` | daily 18:00 | `python3 <harness>/scripts/skill-telemetry/telemetry.py sync --repo <repo>` |

`--precheck` bỏ qua lần chạy khi repo không có batch/queue đang dở.

## Steps

1. Script `scripts/orca-automations.sh apply --repo <name> --level 1` tạo/cập nhật automation idempotent.
2. Allowlist lệnh an toàn trong settings để phiên không đứng ở hộp xác nhận quyền.
3. Thử trên 1 app (`automations run`), kiểm `--reuse-session` có giữ agent nền của `/bug-fix`.
4. Nhân rộng sang các app còn lại.

## Validation

`orca automations runs` có lần chạy thành công; `/bug-fix status` thể hiện việc đã chạy tiếp.

## Rollback

`orca automations remove <id>`.
