# Plan — gộp `bug-note` + `bug-fix-orchestrator` thành `bug-fix`

Status: implemented — chờ controller review (chưa commit) · Branch: `feat/bug-fix` (stack trên PR #13 `huypqapero/bug-fix-orchestrator-retro-improvements`) · Owner: harness

## Outcome

Một skill `bug-fix`, chọn mode theo input:

| Mode | Kích hoạt | Nguồn |
| --- | --- | --- |
| `note` (default) | Bug gõ trong chat; hoặc đúng **1** key / link issue Jira (kéo nội dung ticket về làm mô tả) | `bug-note` |
| `batch` | JQL, link board / sprint / filter, hoặc **≥ 2** key Jira; chạy **nhiều đợt (wave)**: đợt sau lấy ticket chưa có evidence PASS | `bug-fix-orchestrator` (bản #13) |
| `status` / `resume` | Chung cả 2 mode | — |

## Quyết định đã chốt (user, 2026-11-12)

1. Tên `bug-fix`; làm trọn gói.
2. 1 key → note; ≥ 2 key / JQL / board → batch.
3. Xếp chồng lên PR #13 (mang theo mọi cải tiến retro).

## Requirements

1. **Skill `skills/bug-fix/`** — `SKILL.md` chỉ chọn mode + vai + rule chung (≤ ~120 dòng, như dispatcher `skills/bug/SKILL.md`); procedure nằm ở `references/`:
   - `mode-note.md` (từ `bug-note/SKILL.md`) + `note-worker-protocol.md` (từ `bug-note/references/worker-protocol.md`)
   - `mode-batch.md` (từ `bug-fix-orchestrator/SKILL.md` bản #13) + các reference batch (`intake-and-context.md`, `classify-and-plan.md`, `lane-protocol.md`, `device-playbook.md`) giữ nội dung #13
   - `device-queue.md` dùng chung 2 mode
   - `evals/` của #13 chuyển theo, thêm case chọn mode (chat text → note; 1 key → note; JQL / ≥ 2 key → batch)
2. **Evidence chung**: cả 2 mode ghi `evidence.json` theo `skills/bug/schemas/evidence.schema.json`. Note mode: `plans/reports/bugs/<BUG-ID>-<slug>/evidence.json`. `skills/bug/scripts/validate_evidence.py` thêm chế độ validate 1 thư mục evidence (`--evidence-dir <dir> [--base-commit <sha>]`) bên cạnh chế độ batch dir hiện có; có test.
3. **Mức verify chung**: `none / unit / preview / device` cho cả 2 mode (bỏ T1–T4 của bug-note: T1-code→`unit` hoặc `none`, T2-ui→`preview`, T3-flow→`unit`/`none` kèm `file:line` + call chain trong evidence, T4-device→`device`).
4. **Khoá thiết bị chung**: module `scripts/devices.py` (stdlib, khoá file `<git-common-dir>/bug-fix/devices.json`, ghi nguyên tử + `fcntl` lock), holder dạng `note:<BUG-ID>` hoặc `batch:<batch-id>:<JOB>`. `bug_queue.py device-lock/unlock/release` và `bfo_state.py device-dispatch/done/release` đều đi qua module này → 2 mode không bao giờ giữ cùng 1 serial; bỏ yêu cầu leader tự `--exclude` thiết bị của note (vẫn giữ `--exclude` cho task ARTEMIS ngoài).
5. **Nhiều đợt (wave) theo evidence ticket**: `bfo_state.py` thêm lệnh `next-wave <batch>` — liệt kê ticket chưa có `evidence.json` verdict `PASS` (thiếu, `FAIL`, `NEEDS_VERIFICATION`) và ticket `needs-confirm` đã được trả lời, kèm lý do; manifest ghi `wave` cho mỗi issue; `board` hiện cột wave + verdict. `mode-batch.md` mô tả vòng: plan wave N → chạy → validate → `next-wave` → wave N+1 (tái dùng scout cache).
6. **State + đường dẫn**: script ở `skills/bug-fix/scripts/` (`bug_queue.py`, `bfo_state.py`, `bfo` wrapper, `devices.py`, test). State note chuyển `<git-common-dir>/bug-note/queue.json` → `<git-common-dir>/bug-fix/queue.json`, tự đọc file cũ nếu file mới chưa có (migrate 1 lần). Batch dir `plans/bugfix-batch-<id>/` giữ nguyên. Mọi lệnh trong skill gọi `python3` / wrapper `bfo` — không có `~/.claude/skills/.venv` (sửa luôn chỗ Phase 6 cũ).
7. **Alias tương thích**: `skills/bug-note/SKILL.md` và `skills/bug-fix-orchestrator/SKILL.md` thành stub ngắn (giữ `name`, description ghi "alias của `bug-fix` mode note / batch"), body trỏ `../bug-fix/SKILL.md`; xoá references / scripts / evals cũ (đã chuyển). `skills/bug/SKILL.md` + `references/mode-fix.md`: `--parallel` → `bug-fix` mode batch.
8. **Agent + chỉ mục**: cập nhật `agents/bug-fixer.md`, `bug-reviewer.md`, `bug-scout.md` (tên skill, đường dẫn protocol / script); `CLAUDE.md` (gộp 2 dòng routing thành `/bug-fix`), `AGENTS.md` (bảng task + mục lục file), `CHANGELOG.md` `[Unreleased]` (Changed: gộp; ghi alias + migrate state).

9. **UI theo Figma — note mode ngang batch** (bổ sung 2026-11-12): bug mức `preview` ở note mode theo đúng quy tắc của batch (`lane-protocol.md` mức `preview`): render preview trước/sau, board với ảnh Figma (`compare-ui-board`) + chấm `ui-diff-review` ngưỡng của repo (mặc định 95); còn lệch → chuyển `ui-fix-loop` (≤ 3 vòng) thay vì dừng sau 1 vòng; tra Figma của màn qua registry `docs/design-refs/figma-refs.json` (của `ui-fix-loop`) trước khi tự tìm. Viết quy tắc này **một lần** trong reference dùng chung (vd mục `preview` của `device-queue.md` hoặc file `verify-tiers.md`), 2 mode tham chiếu, không lặp.
10. **Nguồn bug từ report `ui-diff`** (bổ sung 2026-11-12): batch nhận thêm input `<ui-diff run>/summary.json` (hoặc thư mục run). Mỗi mục `fix_priority[]` (`screen`, `region`, `severity`, `type`, `actual`, `expected`, `source_hint`, `confidence`) → 1 bug `kind=ui`, `verify=preview`, key dạng `UI-<screen-slug>-<n>`, kèm ảnh `<run>/screens/<screen>/{actual,design}.png` làm ảnh expected/actual trong context; không có Jira (bỏ bước Jira status). Gom lane theo màn / component; mỗi finding có `evidence.json` riêng; đợt sau (`next-wave`) lấy finding chưa PASS. Lệnh mới trong `bfo_state.py` (vd `import-ui-diff <batch> <summary.json>`) sinh `bugs.json` đúng format hiện có; có test với 1 `summary.json` mẫu. Trigger trong description: "fix theo report ui-diff", "sửa hết lệch UI từ ui-diff".

## Done means

- `skills/bug-fix/` tồn tại đủ phần trên; 2 skill cũ chỉ còn stub `SKILL.md`.
- Tất cả test PASS bằng `python3` hệ thống: `test_bfo_state.py` (bản #13 + test mới cho khoá chung và `next-wave`), `test_bug_queue.py` (mới: new/claim/waiters/device-lock qua khoá chung/migrate state), `test_devices.py`, test validator `--evidence-dir`.
- Test liên mode: note giữ serial X → batch `device-dispatch` không cấp X; batch giữ Y → note `device-lock Y` bị từ chối.
- `grep -rn "skills/bug-note/\|skills/bug-fix-orchestrator/\|bug-note/scripts\|bug-fix-orchestrator/scripts\|\.venv"` ngoài stub, CHANGELOG lịch sử và `plans/` = 0 kết quả.
- Không mất cải tiến nào của #13 (so `git diff` nội dung reference / script trước-sau khi chuyển: chỉ khác đường dẫn / tên + phần thêm mới).

## Out of scope

Viết lại 2 script state thành 1; đổi chuẩn fix của `bug-fixer`; đổi `bug --mode fix|triage` (trừ alias `--parallel`); merge PR.

## Risks

- #13 còn có thể đổi trước khi merge → rebase `feat/bug-fix` lên đầu nhánh #13.
- State note đang chạy dở ở repo app → migrate đọc file cũ, không xoá file cũ.
