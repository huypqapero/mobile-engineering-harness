# Phase 4: Orca mức 2, skill `/autopilot`

## Requirements

Skill harness mới `skills/autopilot/`. Mỗi lần chạy:

1. Đọc trạng thái: verdict Q&A, `briefs/*/brief.yaml`, `plans/reports/orchestration-*.md`, state `/bug-fix`, `gh pr list`, nguồn trạng thái feature (Jira epic hoặc `features.yaml`, chưa chốt).
2. Chọn bước kế cho từng feature:

| Khi thấy | Tự chạy |
|---|---|
| Q&A Ready | `/business-prepare-feature` |
| Brief validate xong | `/coding-orchestrator` |
| PR feature merged | QA E2E qua ARTEMIS, bug vào `/bug-fix` batch |
| Bug PASS + merged | `/release` |
| Cần người | `orca orchestration gate-create` + thông báo |

3. Idempotent: chạy lại không lặp việc đã giao.

Chạy bằng Orca automation 20 phút một lần trên worktree có sẵn.

## Depends on

Phase 3 (automation chạy ổn), số liệu telemetry để chọn thứ tự.

## Open

Nguồn trạng thái feature; mapping decision gate ↔ câu trả lời người về lại skill.
