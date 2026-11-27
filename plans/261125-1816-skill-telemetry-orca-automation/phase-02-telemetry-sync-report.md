# Phase 2: sync + report

## Requirements

- `telemetry.py sync --repo <owner/repo>`: clone/pull repo telemetry private vào `~/.meh-telemetry/remote`, gộp event cục bộ vào `data/<login>/<yyyy-mm>.jsonl` theo `id`, che credential lần nữa, commit `chore(telemetry): sync <login>`, push. Có `--dry-run`.
- `telemetry.py report [--data <dir>] [--since 30] [--login <x>] [--prompts N] [--json]`:
  - Skill dùng nhiều nhất (tổng, slash/model, số người, lần cuối).
  - Theo từng login: tổng + top skill.
  - Skill đã cài nhưng chưa dùng trong khoảng thời gian.
  - Mẫu prompt gần nhất cho mỗi skill.
- Dashboard: artifact Data đọc output `--json` (làm sau khi có repo và dữ liệu team).

## Steps

1. Code `sync` và `report` trong `telemetry.py`, test phần gộp và tổng hợp.
2. User tạo repo private (hành động bên ngoài, cần xác nhận), chạy `sync` lần đầu.
3. Orca automation hằng ngày chạy `sync` trên máy từng người (phase 3).
4. Dashboard từ `report --json --data ~/.meh-telemetry/remote/data`.

## Validation

- Test gộp: chạy 2 lần không tăng số dòng.
- `report` trên dữ liệu backfill của owner ra đúng top skill như số đếm thủ công.

## Risk

Repo chứa prompt toàn văn: chỉ để private, ghi rõ trong `docs/skill-telemetry.md`.
