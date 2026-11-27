# Phase 1: collector

## Context

Skill được gọi theo hai đường:

- **slash**: người gõ `/bug-fix status`. Hook `UserPromptSubmit` nhận `prompt` thô.
- **model**: agent tự gọi tool `Skill`. Hook `PreToolUse` (matcher `Skill`) nhận `tool_input.skill` và `tool_input.args`.

Transcript cũ ở `~/.claude/projects/*/*.jsonl` chứa `<command-name>` (slash) và `tool_use` tên `Skill` (model). Thử trên máy owner: 38 phiên, 149 slash, 18 model.

## Files

- `scripts/skill-telemetry/telemetry.py` (mới): subcommand `hook`, `backfill`, `inventory`, `report`, `sync`.
- `scripts/skill-telemetry/test_telemetry.py` (mới).
- `scripts/install-telemetry-hook.sh` (mới): patch `~/.claude/settings.json` (user-level, vì skill dùng ở mọi repo).

## Event schema v1

| Field | Ý nghĩa |
|---|---|
| `v` | 1 |
| `id` | sha1 ngắn, dùng để chống trùng |
| `ts` | ISO 8601 UTC |
| `kind` | `skill` hoặc `inventory` |
| `login` | GitHub login (cache 24h từ `gh api user`); override bằng `MEH_TELEMETRY_LOGIN` |
| `git_email` | `git config user.email` |
| `repo` | `owner/repo` từ remote `origin`, không có thì tên thư mục |
| `skill`, `args` | Tên skill và phần đối số |
| `source` | `slash`, `model`, `backfill-slash`, `backfill-model` |
| `prompt` | slash: prompt đã gõ. model: prompt gần nhất của người trong phiên |
| `session` | session id của Claude Code |
| `skills` | chỉ có ở `inventory`: danh sách skill đã cài |

Lưu tại `${MEH_TELEMETRY_DIR:-~/.meh-telemetry}/events/<yyyy-mm>.jsonl`.

## Steps

1. Viết `telemetry.py` (stdlib), che credential trước khi ghi.
2. Hook: luôn exit 0, không in stdout, lock file khi ghi.
3. Inventory: một lần mỗi ngày cho skill user-level + plugin, một lần mỗi ngày mỗi repo cho skill project-level.
4. Backfill từ transcript, chống trùng theo `id`.
5. Script cài hook: `install | uninstall | status`, `--dry-run`.
6. Unit test.

## Validation

- `cd scripts/skill-telemetry && python3 -m unittest -v`
- `scripts/install-telemetry-hook.sh status`
- Gõ một slash skill trong phiên mới, kiểm tra dòng mới trong file events.

## Rollback

`scripts/install-telemetry-hook.sh uninstall`, xoá `~/.meh-telemetry`.
