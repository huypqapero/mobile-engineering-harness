# Evals: bug-fix

Bộ kiểm hành vi của leader/lane/worker theo quy trình trong `SKILL.md` và `references/` (chọn mode, mode note, mode batch). Mỗi ca là một tình huống có assertion kiểm được trên transcript; không cần repo thật hay Jira thật (agent mô tả hành động, không thực thi).

| File | Nội dung |
|---|---|
| `evals.json` | Ca hành vi, schema `references/eval-schemas.md` của skill-creator (`prompt`, `expected_output`, `assertions[{id,text}]`) |
| `trigger-queries.json` | Prompt nên / không nên kích hoạt skill (`should_trigger`) cho `run_eval.py` |

## Chạy

Từ thư mục `~/.claude/skills/skill-creator` (python3 hệ thống):

```bash
# 1. Trigger accuracy của description
python3 -m scripts.run_eval --eval-set <harness>/skills/bug-fix/evals/trigger-queries.json \
  --skill-path <harness>/skills/bug-fix --runs-per-query 3
# 2. Tối ưu description (tuỳ chọn): scripts/run_loop.py cùng eval-set
# 3. Hành vi: với mỗi ca trong evals.json, chạy song song with_skill và without_skill (cùng một lượt),
#    lưu transcript vào <workspace>/iteration-N/eval-<id>-<name>/{with_skill,without_skill}/outputs/,
#    chấm bằng agents/grader.md của skill-creator -> grading.json, rồi scripts/aggregate_benchmark.py
```

Ca `with_skill` phải được nạp đủ `SKILL.md` và `references/` (ca 0–6 là mode batch, 7–10 chọn mode, 11 wave, 12 preview ở note mode, 13 khoá thiết bị liên mode, 14 report ui-diff). Pass khi mọi assertion của ca đúng; `without_skill` dùng làm baseline so sánh.

## Ánh xạ ca -> hành vi

| id | Hành vi kiểm |
|---|---|
| 0 | Device job FAIL: leader giao `bug-fixer`, không tự điều tra log |
| 1 | PR merge vào branch stack, head không là tổ tiên base: không chuyển Reviewing |
| 2 | Lane cần file mà PR mở khác đang sửa: `after`/chuyển bug, không mở rộng `files` |
| 3 | PO đổi quyết định khi PR đã ready: hạ draft, Jira In Progress, sửa, review lại |
| 4 | Trước khi giao job: luôn `assemble`, không so mtime |
| 5 | User merge trước khi device pass: Reviewing ngay, job vẫn chạy; fail thì PR mới + reopen |
| 6 | Gate fresh-with-main và PR đã merged: không push vào branch cũ |
| 7 | Bug gõ trong chat: mode note, đăng ký + spawn worker nền, trả lời ngay |
| 8 | Đúng 1 key Jira: mode note, kéo ticket làm mô tả |
| 9 | Link board: mode batch, preflight rồi init |
| 10 | ≥ 2 key Jira: mode batch, không spawn nhiều worker note |
| 11 | Đợt sau: `next-wave`, ghi `answer`, `--start`, tái dùng scout cache |
| 12 | Note mode, `preview` còn lệch: `ui-fix-loop` ≤ 3 vòng, registry `figma-refs.json` |
| 13 | Khoá thiết bị chung: note bị từ chối khi batch giữ serial |
| 14 | Report ui-diff: `import-ui-diff`, bug `UI-<screen>-<n>`, không Jira |

Thêm ca mới khi sửa quy trình: một hành vi, 3–4 assertion khách quan (hành động cụ thể, không "viết tốt").
