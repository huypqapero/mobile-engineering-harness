# Skill telemetry

Ghi lại ai trong team đã cài skill nào, dùng skill nào, bao nhiêu lần, và gọi skill bằng prompt như thế nào. Mục đích là chọn skill nào nên cải thiện và tự động hoá trước, dựa trên số liệu thật thay vì phỏng đoán.

Code: `scripts/skill-telemetry/telemetry.py` (Python stdlib). Hook: `scripts/install-telemetry-hook.sh`.

## Ghi những gì

| Trường | Nội dung |
|---|---|
| `login` | GitHub login từ `gh api user` (cache 24 giờ) |
| `git_email` | `git config --global user.email` |
| `repo` | `owner/repo` của remote `origin`, không có thì tên thư mục |
| `skill`, `args` | Tên skill và phần đối số |
| `source` | `slash` (người gõ `/skill`), `model` (agent tự gọi tool Skill), `backfill-*` (nhập từ transcript cũ) |
| `prompt` | **Toàn văn** prompt. Với `slash` là chính lệnh đã gõ; với `model` là prompt gần nhất người gõ trong phiên |
| `session`, `ts` | Session id của Claude Code, thời điểm (UTC) |
| `skills` | Chỉ ở event `inventory`: danh sách skill đã cài (user, plugin, project), ghi mỗi ngày một lần |

Không ghi: prompt không gọi skill, nội dung file, output của agent, token/chi phí.

> **Lưu ý cho team:** prompt gọi skill được lưu nguyên văn và đẩy lên repo telemetry private. Chỉ những chuỗi trông giống credential (GitHub/OpenAI/Anthropic/AWS/Google/Slack token, JWT, `Bearer ...`, `password=...`, private key) được thay bằng `[REDACTED:<loại>]`. Link nội bộ, key Jira, mô tả bug vẫn được giữ. Đừng dán dữ liệu khách hàng nhạy cảm vào prompt gọi skill.

## Cài đặt

Tự động, mỗi máy một lần:

- `bootstrap.sh` cài hook và chạy `backfill` (nhập lượt dùng cũ từ transcript, chỉ còn khoảng 30 ngày gần nhất). Bỏ qua bằng `MEH_TELEMETRY=0 bash bootstrap.sh`.
- Skill `harness-init` chạy lại bước cài hook cho máy chưa cài qua `bootstrap.sh` (ví dụ dùng harness dạng submodule).

Cài tay hoặc kiểm tra:

```bash
mehcli telemetry install     # idempotent
mehcli telemetry status      # hook đang trỏ tới script nào
mehcli telemetry backfill
```

Nhiều bản harness trên cùng máy (bản cài qua bootstrap, checkout để phát triển, submodule) không tạo hook trùng: `install` giữ hook đang có nếu script của nó còn tồn tại, trỏ lại vào bản đang cài nếu script cũ đã mất, và gộp hook trùng thành một.

Tắt tạm trong một shell mà không gỡ: `export MEH_TELEMETRY=0` trước khi chạy `claude`.

Hook được thêm vào `~/.claude/settings.json` (cấp user, áp dụng mọi repo) cho 3 sự kiện: `UserPromptSubmit`, `PreToolUse` (matcher `Skill`), `SessionStart`. Lần cài đầu tạo bản sao `settings.json.bak-telemetry`. Hook luôn thoát với mã 0, không in gì ra phiên, timeout 5 giây; lỗi ghi vào `~/.meh-telemetry/hook-errors.log`.

Dữ liệu cục bộ: `~/.meh-telemetry/events/<yyyy-mm>.jsonl`. Đổi thư mục bằng `MEH_TELEMETRY_DIR`.

## Xem báo cáo

```bash
mehcli telemetry report                         # 30 ngày gần nhất, dữ liệu máy này
mehcli telemetry report --since 0 --prompts 5   # toàn bộ, 5 mẫu prompt mỗi skill
mehcli telemetry report --login huypqapero      # một người
mehcli telemetry report --json                  # cho dashboard
mehcli telemetry inventory                      # skill đang cài trên máy này
```

Báo cáo gồm: skill dùng nhiều nhất (tổng, slash, model, ai dùng, lần cuối), theo từng người, mẫu prompt mỗi skill, skill đã cài nhưng chưa dùng, và lệnh có sẵn của Claude Code (`/clear`, `/compact`...) tách riêng khỏi skill.

## Gom về repo private của team

```bash
mehcli telemetry sync --repo <owner>/<skill-telemetry> --dry-run   # xem sẽ đẩy bao nhiêu event
mehcli telemetry sync --repo <owner>/<skill-telemetry>
```

`sync` clone repo vào `~/.meh-telemetry/remote`, gộp event vào `data/<login>/<yyyy-mm>.jsonl` (không trùng id, che credential lần nữa), commit `chore(telemetry): sync <login> (...)` rồi push. Xem báo cáo cả team:

```bash
mehcli telemetry report --data ~/.meh-telemetry/remote/data
```

Repo telemetry phải để **private** và chỉ cấp quyền đọc cho người cần xem.

## Gỡ

```bash
mehcli telemetry uninstall
rm -rf ~/.meh-telemetry
```

`scripts/uninstall-all.sh` chỉ gỡ phần cài theo project, không gỡ hook telemetry (vì hook là cấp user, dùng chung mọi repo).

## Test

```bash
cd scripts/skill-telemetry && python3 -m unittest -v
```
