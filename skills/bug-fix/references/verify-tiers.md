# Mức verify dùng chung (mode note + mode batch)

Mỗi bug có đúng một mức: `none` / `unit` / `preview` / `device`. Chọn mức **thấp nhất đủ chứng minh**, bug lai lấy mức cao nhất. Bảng chọn chi tiết + từ khoá: `classify-and-plan.md` §Bước 2 (batch); mode note chọn theo cùng bảng này ở bước Investigate của `note-worker-protocol.md`.

| Mức | Chứng minh bằng | Thiết bị |
|---|---|---|
| `none` | Diff + compile (+ lint resource cho strings); sai/đúng nhìn được ngay trong diff | Không |
| `unit` | Unit test regression (happy + ≥ 1 edge) cho ViewModel/UseCase/Repository/mapper; lỗi flow/điều hướng thì kèm `file:line` + call chain (`A.kt:12 → B.kt:40`) trong evidence | Không |
| `preview` | Quy tắc bên dưới | Không |
| `device` | Fix + unit tới mức test được, rồi xếp hàng thiết bị (`device-queue.md`); mode note: hoãn, ghi vào `DEVICE-TEST-QUEUE.md` | Có (hoãn / xếp hàng) |

Ánh xạ T1–T4 cũ của bug-note: `T1-code` → `unit` (hoặc `none` nếu nhìn được trong diff), `T2-ui` → `preview`, `T3-flow` → `unit` (hoặc `none`) kèm call chain, `T4-device` → `device`.

## `preview` — UI theo Figma (một lần ở đây, hai mode tham chiếu)

Dùng cho bug nhìn thấy trên màn có (hoặc thêm được) `@Preview` dùng production Content.

1. **Tra Figma của màn trước khi tự tìm**: registry `<repo>/docs/design-refs/figma-refs.json` của skill `ui-fix-loop` (`uifix_state.py ref-get --refs docs/design-refs/figma-refs.json --screen <màn>`) → `figma_url`, `node_id`, `preview_fqn`, `source_files`. Chưa có entry → scout + `ref-add` theo `ui-fix-loop` §Bước 0 (làm một lần / màn, lần sau dùng lại). Batch đã có `B/context/figma-index.json` thì ưu tiên nó, nhưng màn mới vẫn `ref-add` vào registry của repo.
2. **Render** preview trước (base) và sau (fix) bằng runner `testing-preview` hoặc `android preview render ":app@<variant>" --fqn=<FQN>`.
3. **Board + chấm**: ghép board [actual | Figma] bằng `compare-ui-board`, chấm bằng `ui-diff-review` — ngưỡng của repo, mặc định **95**. (Không dùng skill `ui-diff` mode video-to-figma: nó chỉ so video quay app với Figma.)
4. **Còn lệch (điểm < ngưỡng) → `ui-fix-loop`**: tối đa **3 vòng** fix → render lại → compare lại cho mỗi bug; không dừng sau 1 vòng. `STUCK` / hết 3 vòng chưa đạt → verify không PASS: báo kèm board + finding còn lại (mode note: `NEEDS_INPUT`; mode batch: `DONE_WITH_CONCERNS`, issue không lên `verified`).
5. **Evidence**: `preview-before.png`, `preview-after.png`, `board.png`, kết quả `ui-diff-review` (`result.json`/findings) vào thư mục evidence, liệt kê trong `artifacts` của `evidence.json`; AC "khớp Figma" trỏ `board.png`.

## Evidence chung

Cả hai mode ghi `evidence.json` theo `skills/bug/schemas/evidence.schema.json` và kiểm bằng `skills/bug/scripts/validate_evidence.py` (batch: `validate_evidence.py <batch dir>`; note: `validate_evidence.py --evidence-dir <dir> [--base-commit <sha>]`). Không có artifact thì AC không được `PASS`; mức `device` giữ `NEEDS_VERIFICATION` tới khi chạy thiết bị. Redact token/email/sđt.
