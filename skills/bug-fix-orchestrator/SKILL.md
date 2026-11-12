---
name: bug-fix-orchestrator
description: "Alias của skill `bug-fix` mode batch: leader điều phối fix nhiều bug Android/KMP từ Jira (JQL, board, sprint, ≥ 2 key) hoặc report ui-diff, nhiều đợt (wave), lane worktree song song, hàng chờ thiết bị, đồng bộ Jira. Dùng khi user nói /bug-fix-orchestrator, 'fix batch bug Jira', 'fix các bug sprint này', 'sửa N bug cùng lúc', 'resume batch', 'status batch', 'sync Jira theo PR đã merge', 'fix theo report ui-diff'."
user-invocable: true
argument-hint: "<jql | board-url | KEY KEY ... | ui-diff summary.json> [--spec <confluence>] [--figma <url>] [--repo <path>] [--max-lanes 3] [--yes] | status [batch] | resume <batch> | sync-jira [batch]"
---

# bug-fix-orchestrator (alias)

Alias của `bug-fix` mode `batch`. Đọc `../bug-fix/SKILL.md` rồi làm theo `../bug-fix/references/mode-batch.md`
(intake, classify, lane, thiết bị: các file cùng thư mục `references/`). Script state `bfo` ở
`../bug-fix/scripts/`; không còn gì riêng ở thư mục này.
