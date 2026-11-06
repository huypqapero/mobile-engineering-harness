# bug — `--mode fix --parallel`

Batch bugfix orchestrator cho N bug (Jira/list). Fetch → triage cluster → **scout 1 lần/batch** → decide/plan → fix lane song song GIỮA cluster (tuần tự TRONG cluster) → verify matrix per-issue → **evidence validator deterministic** → aggregate → bundle signoff. State bền vững tại `plans/bugfix-batch-<id>/`, **resume được** sau gián đoạn.

> Đơn vị **FIX = bug group** (cùng root cause → 1 patch/review/build), đơn vị **VERIFY + DONE = từng Jira issue** (mỗi bug có evidence riêng). Dùng khi ≥ 3 bug chia được ≥ 2 cluster độc lập file. Bug chụm 1 vùng → `mode-fix` tuần tự.
>
> `--parallel` **chỉ chạy khi gọi tường minh** (có `--jql` hoặc danh sách bug ID). KHÔNG auto-fire giữa session — "fix bug X" đơn lẻ luôn route `mode-fix` (single).

## Inputs

Bắt buộc (1 trong 2):
- **`--jql "<query>"`**: vd `project = AAP AND status = Open AND labels = bug`
- **Bug list**: ID + evidence, vd `BUG-101 BUG-102 BUG-103`

Optional:
- `--source <jira|github|list>` (default jira) · `--batch-id <id>` (resume batch cũ)
- `--max-concurrent <N>` (default = số cluster SAFE) · `--device-pool <serial,serial>` (e2e lane)

## State layout (bền vững + resume)

```
plans/bugfix-batch-<id>/
├── manifest.json        # batch_id, base_commit (git), created_at, source, status
├── bugs.json            # bug đã normalize (id, symptom, repro, evidence, type)
├── groups.json          # cluster → bug ids, owned files, shared files, suspected cause
├── scout.json           # architecture + intent snapshot (pin base_commit) — scout 1 lần
├── plan.json            # per-group: root cause, fix strategy, risk, AC, file ownership
├── state.json           # state machine mỗi group + mỗi issue (resume đọc file này)
├── results/<group>.json # diff summary, tests added, review verdict
└── evidence/<ISSUE>/     # artifact thật: screenshot, report.xml, log, evidence.json
```

**Resume**: khi `--batch-id` trỏ batch cũ, đọc `state.json`, **skip phase đã `done`**, verify `manifest.base_commit` == git HEAD hiện tại (khác → scout stale, re-scout). Checkpoint ghi `state.json` sau **mỗi phase thành công**.

## Procedure

### Phase 1 — Intake + collect (deterministic)

Fetch bug qua `mcp-atlassian jira_search` (hoặc github/list). Normalize mỗi bug: `{id, symptom, repro, expected, actual, evidence_links, affected_screen?}`. Bug thiếu repro/evidence → đánh `NEEDS_INFO`, **loại khỏi batch** (không guess). → `bugs.json`. Gate: mỗi bug vào batch có đủ field tối thiểu.

### Phase 2 — Triage cluster (Tech Lead)

```
Role = Tech Lead. Đọc agents/tech-lead.md §Step 7 + agents/workflows/bug-triage.md.
Input: bugs.json.
Task:
1. Dedupe bug trùng.
2. Cluster theo GIẢ THUYẾT root cause chung + file-touch overlap (KHÔNG chỉ theo tên màn).
3. Mỗi cluster = 1 lane. Gán owned files + shared files (DI, NavHost, strings, Analytics).
4. Loại bug cross-cutting domain contract rộng → route --mode triage riêng.
Output: groups.json (cluster → bug ids, cause hypothesis, confidence, owned/shared files).
```
Gate (**Triage**): mỗi bug có group hoặc lý do chưa phân nhóm; nếu không → `NEEDS_INFO`.

### Phase 3 — Global scout (CHẠY 1 LẦN/batch)

```
Role = coding-scout (+ coding-diagnose read-only). permissionMode = plan (read-only).
Input: groups.json + ADR/spec + base git revision.
Task (1 assignment phủ TẤT CẢ group — tiết kiệm token, không scout lặp):
1. Map architecture, intent, data flow, state ownership cho mọi vùng bug.
2. Tách rõ observed behavior / intended behavior / hypothesis (chống sửa triệu chứng).
3. Confirm/bác bỏ cause hypothesis mỗi group + liệt kê relevant files + unknowns.
Rule: read-only, KHÔNG propose đổi code ngoài scope, KHÔNG tự spawn agent.
Output: scout.json (pin base_commit, per-group: intent, relevant_files, data_flow,
         suspected_root_cause, confidence, unknowns).
```
Gate (**Scout**): snapshot hợp lệ tại base_commit; group thiếu confidence → scout bổ sung có mục tiêu (KHÔNG re-scout toàn bộ).

### Phase 4 — Decide + plan (Tech Lead/Architect = role Orchestrator)

Với mỗi group: đối chiếu bug ↔ scout, chốt root cause, files, AC per issue, risk, test strategy, dependency + file ownership. High-risk (security/ADR-011/migration/cross-feature) → `NEEDS_APPROVAL`, raise user. → `plan.json`. Gate (**Plan**): mỗi group có cause hypothesis + scope + test plan.

### Phase 5 — Fix + review (lane song song GIỮA cluster)

```
Role = Orchestrator. Input: plan.json + scout.json (phần liên quan group).
Task:
1. Group SAFE (owned files không overlap group khác) → chạy SONG SONG, mỗi group 1 git
   worktree .worktrees/bugfix-<group>. Group đụng shared file → aggregation tuần tự (Phase 7).
2. TRONG mỗi lane: spawn Coder fix TẤT CẢ bug của group bằng 1 patch (cùng root cause),
   add regression test. Rồi Reviewer (coding-review) check side-effect/logic/edge.
3. Auto-fix loop Coder↔Reviewer: MAX 2 lần. Fail lần 2 → STOP lane, đánh FAILED,
   Orchestrator reassess root cause (nghi scout sai), KHÔNG loop tiếp. Không ảnh hưởng lane khác.
Rule: KHÔNG sửa file ngoài owned scope; phát hiện phải đổi shared contract → raise, re-cluster.
Output: results/<group>.json (diff, tests added, review verdict).
```
Gate (**Review**): 0 blocker finding/group. Gate (**Build**): `./gradlew compileDebugKotlin` pass.

> Lane auto-fix cap = **2** (chặt hơn single `mode-fix` = 3): batch tốn hơn, reassess cause sớm thay vì đốt retry.

### Phase 6 — Verify per-issue (matrix)

Mỗi **Jira issue** (không phải group) verify riêng theo **Verify matrix** (`mode-fix.md §Verify matrix`): UI→`/testing-preview`, logic→unit, luồng→e2e, crash/ANR→repro+logcat, ads→lifecycle, animation→video. e2e/ARTEMIS lane nhận `device_serial` từ `--device-pool`; 1 emulator → e2e dồn tuần tự cuối. Artifact ghi `evidence/<ISSUE>/` + sinh `evidence.json` (schema: `skills/bug/schemas/evidence.schema.json`). Gate (**Test**): test bắt buộc per-issue pass.

### Phase 7 — Evidence validation (deterministic, SCRIPT)

```bash
~/.claude/skills/.venv/bin/python3 skills/bug/scripts/validate_evidence.py \
  plans/bugfix-batch-<id>
```
Script kiểm **cơ học** (không dựa prompt): mỗi issue có `evidence.json` hợp schema, artifact **tồn tại thật** trên disk, `verdict` set, mỗi acceptance criterion có `evidence` trỏ file có thật, `commit` == `manifest.base_commit`. Exit ≠ 0 → Gate **Evidence** FAIL → issue giữ `NEEDS_VERIFICATION`. PASS → mới cho qua Completion.

### Phase 8 — Aggregation + integration + bundle signoff

1. Merge shared-file edit từ các lane **tuần tự** (lane 1 commit → lane 2 rebase → …), build + Konsist + Detekt sau mỗi merge; conflict → raise Tech Lead.
2. QA regression trên branch integrated (bug cũ không tái phát, không side-effect chéo cluster).
3. Signoff `plans/reports/bugfix-batch-signoff-<id>.md`. Gate (**Completion**): mọi issue `VERIFIED` (AC + evidence đạt) **mới** mark Done. Thiếu → giữ `NEEDS_VERIFICATION`, KHÔNG tự Done, KHÔNG tự update Jira Done (cần user cho phép). Mọi bug close feed `lesson-miner`.

## State machine

Success: `COLLECTED → TRIAGED → SCOUTED → PLANNED → FIXED → REVIEWED → VERIFIED → DONE`.
Exception: `BLOCKED` · `NEEDS_INFO` (bug thiếu data) · `NEEDS_APPROVAL` (high-risk) · `NEEDS_VERIFICATION` (evidence chưa đủ) · `FAILED` (auto-fix cap 2 vượt). Chuyển bước **chỉ khi gate tương ứng pass**; ghi `state.json` mỗi lần.

## Isolation rules

- **SAFE** (song song): cluster owned-file riêng, shared-file edit append-only.
- **UNSAFE** (tuần tự): 2 cluster sửa cùng ViewModel/repository/migration; bug sửa domain contract → tách `--mode triage`, không vào batch.
- 1 group chung root cause → **1 Coder sở hữu patch** (không 2 agent cùng sửa 1 cluster).

## Hard rules (bắt buộc)

- Build pass KHÔNG chứng minh bug fixed — phải có evidence per-issue.
- KHÔNG fabricate test/evidence. KHÔNG Done khi chưa VERIFIED. KHÔNG sửa code ngoài scope.
- KHÔNG chạy job song song trên cùng 1 emulator. KHÔNG update Jira Done khi chưa được phép.
- Stop sau 2 lần auto-fix thất bại → reassess cause. Checkpoint sau mỗi phase.

## Token/wall guide

| Mode | Cost | Wall |
|---|---|---|
| Tuần tự N bug | N× | N× |
| Parallel (C cluster SAFE, scout 1 lần) | 1.3–1.5× N | ~C lane song song |

## Khi NÀO không dùng

- < 3 bug, hoặc mọi bug chụm 1 cluster → `mode-fix` tuần tự.
- Bug chưa có evidence → fetch/triage trước (`NEEDS_INFO`).
- Bug cross-cutting domain contract → `--mode triage`.
- Chỉ 1 emulator + toàn bug e2e-heavy → cân nhắc tuần tự (e2e không song song được).
