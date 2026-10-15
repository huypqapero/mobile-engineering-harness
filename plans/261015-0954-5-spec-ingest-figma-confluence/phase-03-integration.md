# Phase 3 — Wire vào orchestrator, android-feature, workflows

Rule chung: thêm nhánh tuỳ chọn, không đổi luồng khi không có link/không bật nguồn.

### Task 3.1 — android-orchestrator
- Target: `skills/android-orchestrator/SKILL.md`.
- Steps: thêm `### Step 0 — Spec intake (optional ingest)` trước Step 1 (điều kiện chạy = nguồn bật + có link; có link mà nguồn tắt → in ngay 1 dòng lý do rồi flow cũ; chạy `android-spec-ingest`; spec `status: draft` → dừng hỏi user, cập nhật OQ theo câu trả lời rồi đi tiếp; không link → flow cũ); Step 2 `INPUT` ghi rõ spec = `docs/specs/<feature>.md` (viết tay hoặc ingest); Step 4 prompt architect giữ `Sources` + `Open questions` sang từng feature plan; thêm `android-spec-ingest` vào Prerequisites; thêm 1 dòng Common mistakes.
- Verify: `grep -c "android-spec-ingest" skills/android-orchestrator/SKILL.md` ≥ 3; `grep -q "Step 0 — Spec intake" skills/android-orchestrator/SKILL.md` exit 0.

### Task 3.2 — android-feature
- Target: `skills/android-feature/SKILL.md` (Inputs + Prerequisites + Step 1).
- Steps: Inputs thêm 1 dòng "có link + nguồn bật → chạy `android-spec-ingest` trước"; spec có thể sinh từ ingest (`generated_by`); đọc `## Sources` + `## Open questions`, OQ blocking → BLOCKED; design ref = `docs/specs/<feature>/design/`.
- Verify: `grep -c "android-spec-ingest\|Open questions" skills/android-feature/SKILL.md` ≥ 2.

### Task 3.3 — Workflows + architect + AGENTS.md
- Target: `workflows/feature-development.md` (Entry conditions, Input artifacts), `workflows/parallel-feature-development.md` (Entry conditions, Input artifacts), `agents/architect.md` (Spec decomposition: giữ Sources/OQ), `AGENTS.md` (bảng Task routing + danh sách skill).
- Verify: `grep -l "android-spec-ingest" workflows/feature-development.md workflows/parallel-feature-development.md agents/architect.md AGENTS.md | wc -l` = 4.

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
