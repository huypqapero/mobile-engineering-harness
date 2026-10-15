# Phase 4 — Fixture dry-run + release notes

### Task 4.1 — Dry-run bằng fixture (ngoài repo)
- Goal: chứng minh skill + template sinh spec đúng và orchestrator đọc được mà không sửa tay.
- Steps:
  1. Tạo `/tmp/spec-ingest-dryrun/`: `confluence-page.json` (dạng response REST v2, body storage có mô tả + AC + 1 open question), `figma-nodes.json` (1 frame màn Login có loading/error/success, thiếu empty/offline), `overlay.yaml` bật cả hai nguồn.
  2. Subagent mới (không thấy plan) đọc `skills/android-spec-ingest/SKILL.md` + template, coi fixture là kết quả fetch, ghi `/tmp/spec-ingest-dryrun/docs/specs/login.md`.
  3. Subagent mới khác đóng vai architect/orchestrator Step 2 + Step 4 đọc spec đó và báo: tìm được AC, 5 states, OQ, Sources không; cần sửa tay gì không.
- Verify (mechanical, sửa theo kongming sau lần chạy đầu: fixture login có gap thật nên `ready` là kỳ vọng sai):
  (A) login: 6 heading có đủ; hàng empty/offline trỏ `OQ-` (= 2); `status: draft`; OQ blocking chỉ thuộc nhóm API/auth/flag/AC/điều hướng ra (kỳ vọng 3: lockout, quên mật khẩu, ghi nhớ đăng nhập); không OQ blocking cho UI state hay điều hướng vào; Sources có page `884512`, version `7`, node `1:2`; dòng injection không có trong spec.
  (B) fixture dương `orders` (màn danh sách, API rõ, không TBD): `status: ready` ngay lần đầu.
  (C) re-entry: subagent mới nhận câu trả lời cho OQ blocking của (A), theo Step 8 → `status: ready`, không còn `Blocking: yes`.
  (D) subagent mới đóng vai orchestrator Step 0/2/4 + android-feature Step 1 với spec (A sau C) và (B) → báo "không cần sửa tay" cho single/team/parallel-features.

### Task 4.2 — CHANGELOG + README
- Target: `CHANGELOG.md` (entry `[0.13.0] — 2026-10-15` trên 0.11.0), `README.md` (mục `### Spec ingest từ Confluence + Figma (v0.13.0+)` sau `### Agent orchestration`; 1 dòng v0.13.0 trong Release history).
- Verify: `grep -q "\[0.13.0\]" CHANGELOG.md && grep -q "v0.13.0" README.md && echo ok` in `ok`.

## Failure Protocol
If any Verify step does not meet its stated pass condition, STOP this phase.
Do not improvise a fix, retry blindly, or reason around the failure.
Spawn the `kongming` subagent for next-step counsel and pass:
- the phase and task id,
- what you attempted (the steps you ran),
- the exact command and its full output,
- the pass condition it failed to meet.
Apply kongming's guidance, then re-run the Verify step.
If `kongming` cannot be spawned in this environment, STOP and report the same
failure evidence to the user. Never continue by self-reasoning.
