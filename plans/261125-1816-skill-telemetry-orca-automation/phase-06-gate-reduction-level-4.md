# Phase 6: Orca mức 4, giảm điểm chờ người

## Requirements

| Điểm chờ | Tự động khi |
|---|---|
| Merge PR | `bug-reviewer` APPROVE + CI xanh + khớp fast-path trong `CLAUDE.md`; dùng `gh pr merge --auto` |
| Test tay | Bug có bước tái hiện rõ → `artemis-android` verify |
| Duyệt plan batch | `--yes` mặc định cho bug được spec xác nhận |

Giữ cho người: PO trả lời Q&A, quyết định phát hành, scope guard, merge ngoài fast-path.

## Open

User chưa chốt có cho auto-merge fast-path không. Cần branch protection yêu cầu CI trước khi bật.
