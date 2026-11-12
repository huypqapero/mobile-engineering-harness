# Evals: bug-fix-orchestrator

Bộ kiểm hành vi của leader/lane theo quy trình trong `SKILL.md`. Mỗi ca là một tình huống có assertion kiểm được trên transcript; không cần repo thật hay Jira thật (agent mô tả hành động, không thực thi).

| File | Nội dung |
|---|---|
| `evals.json` | Ca hành vi, schema `references/eval-schemas.md` của skill-creator (`prompt`, `expected_output`, `assertions[{id,text}]`) |
| `trigger-queries.json` | Prompt nên / không nên kích hoạt skill (`should_trigger`) cho `run_eval.py` |

## Chạy

Từ thư mục `~/.claude/skills/skill-creator` (venv: `~/.claude/skills/.venv/bin/python3`):

```bash
# 1. Trigger accuracy của description
python3 -m scripts.run_eval --eval-set <harness>/skills/bug-fix-orchestrator/evals/trigger-queries.json \
  --skill-path <harness>/skills/bug-fix-orchestrator --runs-per-query 3
# 2. Tối ưu description (tuỳ chọn): scripts/run_loop.py cùng eval-set
# 3. Hành vi: với mỗi ca trong evals.json, chạy song song with_skill và without_skill (cùng một lượt),
#    lưu transcript vào <workspace>/iteration-N/eval-<id>-<name>/{with_skill,without_skill}/outputs/,
#    chấm bằng agents/grader.md của skill-creator -> grading.json, rồi scripts/aggregate_benchmark.py
```

Ca `with_skill` phải được nạp đủ `SKILL.md` và `references/`. Pass khi mọi assertion của ca đúng; `without_skill` dùng làm baseline so sánh.

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

Thêm ca mới khi sửa quy trình: một hành vi, 3–4 assertion khách quan (hành động cụ thể, không "viết tốt").
