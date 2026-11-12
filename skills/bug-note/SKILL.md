---
name: bug-note
description: "Alias của skill `bug-fix` mode note: ghi bug liên tục trong chat, mỗi bug 1 worker nền fix trong worktree riêng rồi mở PR (bug chung file thì chờ hoặc stack PR). Dùng khi user nói /bug-note, 'note bug', 'ghi bug', 'bug:', 'lỗi:', báo liên tiếp nhiều bug trong chat hoặc hỏi trạng thái các bug đã ghi."
user-invocable: true
argument-hint: "<bug description> | status | cancel <BUG-ID>"
---

# bug-note (alias)

Alias của `bug-fix` mode `note`. Đọc `../bug-fix/SKILL.md` rồi làm theo `../bug-fix/references/mode-note.md`
(worker: `../bug-fix/references/note-worker-protocol.md`). Script, state và khoá thiết bị đều ở
`../bug-fix/scripts/`; không còn gì riêng ở thư mục này.
