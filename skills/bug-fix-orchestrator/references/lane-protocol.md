# Lane protocol (agent `bug-fixer`: 1 lane = 1 worktree = 1 PR)

Các bước chạy tuần tự; bước sau dùng output bước trước. `S` = `<SKILL_DIR>/scripts/bfo`, `B` = batch dir tuyệt đối, `WT` = worktree của lane.

## Brief (leader điền mọi `<…>` rồi spawn `bug-fixer`, run_in_background)

```
Bạn là lane <L> của batch <batch-id> (skill bug-fix-orchestrator).
Repo (main checkout, KHÔNG sửa): <abs repo>   Remote: <remote>   Base: <base-branch> @ <base_commit>
Stack lên branch: <branch của lane trong after | -->
Batch dir: <B>   State: S = <SKILL_DIR>/scripts/bfo (gọi bằng đường dẫn tuyệt đối)
Logcat repro (nếu bug repro_first): <B>/evidence/<KEY>/device/logcat.txt
Bug của lane (group → issue → verify):
<dán từ plan.json: key, title, kind, verify, actual/expected, screen, figma_node, preview_fqn>
Scout của các bug này: <dán phần scout.json tương ứng: suspect file:line, call chain, files, unknowns>
Files được phép sửa: <lane.files>
References: <B>/context/references.md   Spec: <B>/context/spec.md (mục liên quan: <…>)
Build/test: <vd ./gradlew :app:compileAppDevDebugKotlin, :app:testAppDevDebugUnitTest, detekt nếu có>
Preview: <vd android preview render ":app@appDevDebug" --fqn=…>
Quy định repo: <CLAUDE.md, decisions-outside-spec phải cập nhật trong PR nếu tự quyết hành vi>
Ngôn ngữ PR/báo cáo: tiếng Việt. Timezone Asia/Saigon.
Làm theo <SKILL_DIR>/references/lane-protocol.md từng bước; kết thúc bằng status block của agents/bug-fixer.md.
```

## 1. Worktree

```bash
cd <repo> && git fetch <remote> <base>
WT=<repo>-worktrees/bfo-<batch-id>-<L>            # ngoài repo để Gradle/IDE không quét
BRANCH=fix/<project-lower>-<lane-slug>
git worktree add "$WT" -b "$BRANCH" <remote>/<base>     # stack: <remote>/<branch lane trước>
```
Copy input build bị gitignore có ở main checkout (chỉ file tồn tại): `local.properties`, `.env`, `keystore.properties`, `google-services.json` nếu ignored. Không bao giờ commit chúng.
`S lane B <L> status=running branch=$BRANCH worktree=$WT`

## 2. Chốt root cause từng group (mindset Architect)

- Đọc đúng dòng scout chỉ ra, xác nhận bằng code thật: ghi `file:line` + trích dòng sai + vì sao sai so với spec/Figma. Scout sai → tự tìm lại trong phạm vi area, ghi chú cho leader.
- Liệt kê file sẽ sửa. File ngoài `lane.files` → **dừng**, status `NEEDS_CONTEXT` (file + lý do). Không sửa trước khi leader trả lời.
- Đổi domain contract / migration / shared contract → `BLOCKED`, nêu lý do (scope guard).
- Bug hóa ra spec-gap → `S issue B <KEY> status=blocked note="spec-gap: <câu hỏi>"`, bỏ qua bug đó, làm tiếp bug khác.

## 3. Fix (mindset Coder)

- Làm theo **Chuẩn fix** của `agents/bug-fixer.md` (đọc rule project → `fix-design.md` → fix đúng root cause ở đúng layer → không dùng mẫu fix ngọn). Fix gốc vượt phạm vi lane → `NEEDS_CONTEXT`/`BLOCKED` kèm `fix-design.md`, không vá tạm.
- UI: lấy số liệu từ Figma node (`get_figma_data` node của màn; asset bằng `download_figma_images` vào đúng thư mục res). Không bịa dp/màu.
- Mỗi issue: `S issue B <KEY> status=fixing` khi bắt đầu, `status=fixed fix_commit=<sha>` khi xong.
- Không `git stash`; cần cất tạm → commit WIP rồi squash trước khi push.

### Log đo lường (bug thời gian / đếm, verify `device`)

Ảnh chụp lệch vài giây nên không đo được thời lượng hay số lần. Bug có yếu tố thời gian (delay, countdown, animation, timeout, cooldown quảng cáo) hoặc đếm (số lần hiện, retry) → thêm log ngay trong commit fix:
- Mức debug qua logger sẵn có của repo (vd Timber), tag riêng ổn định `<Feature>Metric`, mỗi mốc một dòng `event=<tên> value=<giá trị>`. Không log PII/token; không thêm logger/tree mới.
- `device-checklist.md` ghi lệnh đo (`logcat -c` rồi `logcat -v time -s <TAG>`), mốc bắt đầu/kết thúc và ngưỡng PASS (vd chênh timestamp ≥ N s, dung sai); verifier kết luận bằng hiệu timestamp.

## 4. Gate "fresh with main" (trước build APK, dispatch device job và push)

Nhánh lane cũ so với base là nguyên nhân verify trên code lạc hậu (APK thiếu fix đã merge) và push vào PR đã đóng. Trong `WT`:

```bash
git fetch <remote> <base>
git log --oneline HEAD..<remote>/<base> -- <lane.files + shared_files>     # base có commit mới đụng file của lane?
git log --oneline HEAD..<remote>/<base> | head                              # PR của batch (lane after) đã merge vào base?
```

- Lane stack (`after`) mà PR lane trước **đã merge** vào base → `git merge <remote>/<base>`, đổi PR base sang `<base>` (`gh pr edit <pr> --base <base>`).
- Base có commit đụng file của lane, hoặc PR liên quan đã vào base → `git merge <remote>/<base>` (không rebase nếu đã push), giải conflict, chạy lại compile + unit test module bị đụng.
- Sau mỗi lần merge, APK cũ vô hiệu: build lại trước khi `device-request`.
- Trước **mỗi lần push** khi đã có PR: `gh pr view <pr> --json state,mergedAt`. `OPEN` → push. `MERGED`/`CLOSED` → **không** push vào branch đó; tạo branch mới từ `<remote>/<base>`, cherry-pick commit mới, mở PR mới ("Tiếp theo #<pr cũ>"), cập nhật `S lane B <L> pr=<url mới>` và báo leader.

## 5. Verify theo tier (1 vòng; fail thì fix lại tối đa 2 lần rồi `FAILED`)

| verify | Làm |
|---|---|
| `none` | compile; strings → kiểm đủ mọi `values-*` liên quan; ghi diff tóm tắt vào evidence; UI tĩnh không preview → checklist test tay vào PR + `B/device-test-queue.md` (không chặn PR) |
| `unit` | viết/sửa unit test regression (happy + ≥1 edge) cho ViewModel/UseCase; chạy test module bị đụng |
| `preview` | render preview trước (base) và sau (lane) bằng `testing-preview` runner hoặc `android preview render`; ghép board với ảnh Figma (`compare-ui-board`) và chấm (`ui-diff-review`, ngưỡng theo repo, mặc định 95). Lệch còn lại → `ui-fix-loop` (≤ 3 vòng) |
| `device` | chạy phần `unit` nếu có logic; build APK lane (`assemble<Variant>`) sau gate §4, ghi path; `S device-request B <KEY> --lane <L> --apk <path> --head <sha>`; viết checklist device (bước → kết quả mong đợi, điều kiện: remote key, mạng, quyền, ads test) vào `evidence/<KEY>/device-checklist.md`. **Không tự chạy thiết bị.** |

Gate chung trước push (sau gate fresh-with-main): compile variant chính + unit test module bị đụng PASS; detekt/konsist nếu repo cấu hình (`./gradlew tasks --all | grep -E "detekt|konsist"`). Không tắt/skip test để qua gate. Tự kiểm diff theo checklist A–J của `coding-review`, ghi `self-review.md` vào evidence mỗi bug.

## 6. Evidence (mỗi issue)

`B/evidence/<KEY>/evidence.json` theo `skills/bug/schemas/evidence.schema.json`:
- `issue`, `commit` = **`manifest.base_commit`** (validator pin batch), `fix_commit` = sha fix, `verdict`
- `bug_type`, `verification` (`compile`, `unit`, `preview`, `device`: PASS/FAIL/SKIP)
- `artifacts` (đường dẫn tương đối trong `evidence/<KEY>/`: `diff.txt`, `test-report.txt`, `preview-before.png`, `preview-after.png`, `board.png`, `device-checklist.md`…)
- `acceptance_criteria`: mỗi AC (từ expected + spec) có `result` + `evidence` trỏ artifact có thật
- Tier `device`: AC runtime để `NEEDS_VERIFICATION`, `verdict: NEEDS_VERIFICATION` — device verifier cập nhật sau.

Không fabricate: không có artifact thì AC không được `PASS`. Redact token/email/sđt.

## 7. Commit, push, PR

```bash
cd "$WT"
git add <chỉ file source/test/res đã sửa>          # không git add -A
git diff --cached | grep -iE '^\+.*(api[_-]?key|secret|password|token)' && echo STOP
git commit -m "fix(<scope>): <mô tả>" -m "Refs: <KEY>[, <KEY>]"   # 1 commit / group, không nhắc AI
git push -u <remote> "$BRANCH"
gh pr create --base <base | branch lane trước> --head "$BRANCH" --draft \
  --title "fix(<scope>): <tóm tắt> [<KEY>, …]" --body-file <file tạm ngoài repo>
```
- PR luôn mở **draft**; chỉ ready khi `bug-reviewer` APPROVE và không còn bug `pending_device` (leader làm).
- PR body (tiếng Việt): bảng bug (key + link Jira · kind · verify · root cause `file:line` · fix · kết quả verify) → mục **"⚠️ Cần test trên thiết bị"** với checklist (nếu có) → "Evidence (local): `B/evidence/`" → nếu stack: "Stack trên #<pr> — merge PR đó trước".
- Label `needs-device-test` khi có bug device (`gh label create` một lần nếu chưa có; lỗi thì bỏ qua label).
- `S lane B <L> status=pr_open pr=<url>`; mỗi issue không phải device: `S issue B <KEY> status=pr_open pr=<url>` (issue device giữ `pending_device`).

## 8. Kết thúc

Giữ worktree (device verifier cài APK của lane, leader dọn sau khi PR merge). Dừng process nền bạn tự start (watcher, server); **không** chạy `./gradlew --stop` — lệnh đó dừng daemon chung của mọi lane đang build. Trả status block của `agents/bug-fixer.md`. Finding `[auto-apply]` của `bug-reviewer` (kể cả khi verdict `APPROVE`) → áp dụng đúng dòng thay thế ngay, chạy lại gate, push. Leader sẽ gửi review của `bug-reviewer`: `REQUEST_CHANGES` → sửa đúng finding (kể cả `auto-apply`) trong cùng worktree, cập nhật `fix-design.md`/`self-review.md`, push, báo lại (tối đa 2 vòng).
