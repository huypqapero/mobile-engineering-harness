---
name: ui-fix-loop
description: Sửa UI Android Compose cho khớp design Figma theo vòng lặp "chỉ ra bug UI -> fix -> render lại -> compare lại", tối đa 3 vòng fix cho mỗi bug, chạy được nhiều bug song song. Khi scout phải TỰ LƯU link Figma (fileKey + node-id), spec, source file, preview FQN vào registry để lần sau chỉ cần tìm source là compare được; có node Figma thì tải asset (icon/mascot) bằng framelink-figma. Render bằng `android preview render` (Android CLI), chấm điểm bằng ui-diff-review (ngưỡng 95). Dùng khi user nói "fix UI theo design", "update UI cho khớp figma", "fix diff từ ui-diff report", "chỉnh màn X cho đạt >95%". Không dùng để chỉ so sánh (dùng ui-diff-review) hay verify E2E/device (dùng Artemis).
---

# ui-fix-loop

> Bug UI -> **fix** -> **render preview** -> **compare** -> (chưa đạt) fix -> compare ... **tối đa 3 vòng fix / 1 bug**.
> Nhiều bug chạy song song. Figma node được lưu thành reference nên mọi lần sau chỉ cần biết source là so được.

Trả lời bằng ngôn ngữ của user. Không bịa số px/dp; lấy từ Figma data hoặc đo.

## Phân vai (DRY, không copy lại)

| Việc | Skill / tool |
|---|---|
| Chấm điểm + verdict + checklist trục + đo màu | `ui-diff-review` (`verdict.py`, `sample_region.py`) |
| Dựng board actual\|expected | `compare-ui-board/scripts/create_board.py` |
| Render Compose headless ra PNG | `android preview render` (xem `testing-preview/references/android-reference.md`) |
| Lấy node + tải asset Figma | MCP `framelink-figma`: `get_figma_data`, `download_figma_images` |
| Viết/sửa `@Preview`, Compose | `coding-compose` |
| Registry Figma ref + đếm 3 vòng | `scripts/uifix_state.py` (skill này) |

`SKILL_DIR` = thư mục skill này. Python: `~/.claude/skills/.venv/bin/python3` nếu có, else `python3`.

## Đầu vào

Một danh sách bug UI. Mỗi bug = 1 vùng/lệch cụ thể trên 1 màn, ví dụ `lvl-icons: màn level thiếu icon bar-chart trên 5 row`. Nguồn bug: user chỉ ra, hoặc `findings.json` / `report.md` của `ui-diff-review` (mỗi finding `lệch` thành 1 bug; gộp các finding cùng root cause/cùng file).
Nếu chưa có bug mà chỉ có màn -> chạy `ui-diff-review` trước để ra findings.

## Bước 0 — SCOUT & LƯU REFERENCE (bắt buộc, làm 1 lần / màn)

Refs lưu ở **repo**: `<repo>/docs/design-refs/figma-refs.json` (commit được, không chứa secret). Nếu màn đã có ref -> đọc lại bằng `ref-get`, bỏ qua scout.

1. **Figma**: lấy URL frame của màn (có `node-id`). Chưa có -> hỏi user 1 lần (mỗi màn). Lưu ngay:
   ```bash
   python3 $SKILL_DIR/scripts/uifix_state.py ref-add --refs docs/design-refs/figma-refs.json \
     --screen level --url "https://www.figma.com/design/<fileKey>/...?node-id=21-171"
   ```
   Script tách `fileKey` + `node_id` (`21-171` -> `21:171`).
2. **Design data**: `get_figma_data(fileKey, nodeId)` -> màu, font, cỡ, bo góc, spacing, tên node con (icon/ảnh). Lưu bản tóm tắt vào `<RUN>/refs/<screen>/figma-data.json` (RUN ngoài repo).
3. **Design ảnh chuẩn**: `download_figma_images(fileKey, nodes=[{nodeId, fileName:"<screen>-design.png"}], localPath="docs/design-refs/<screen>", pngScale=2)`. Ghi đè `design.png` cũ nếu design đổi.
4. **Spec**: tìm trong `docs/`, `briefs/`, `plans/` theo tên màn/feature; thêm `--spec <path>`.
5. **Source**: `rg` composable của màn (Screen/Content/Row/Card, string resource, drawable), thêm `--source <path>` (lặp nhiều lần), `--module :app`.
6. **Preview**: `android preview list :app --format=json`; tìm FQN preview của màn. Chưa có -> tạo `@Preview` (AndroidX annotation `androidx.compose.ui.tooling.preview.Preview`) render đúng production `Screen(state, onAction)` với fixture cố định, `widthDp=360, heightDp=800`, theme thật, ở file preview cạnh màn (theo `coding-compose`). Thêm `--preview-fqn`.
7. **Asset thiếu**: nếu bug là icon/mascot/hình thiếu -> xác định node con trong `get_figma_data` (vector -> `.svg`, ảnh -> `.png` kèm `imageRef`), tải bằng `download_figma_images` rồi chuyển thành drawable đúng quy ước repo (vector `res/drawable`, hoặc ImageVector nếu repo dùng). Không dùng asset thay thế khi Figma có asset thật.

Kết quả: mỗi màn có entry đầy đủ `figma_url, file_key, node_id, spec, source_files, module, preview_fqn`. Đây là thứ "tìm source là compare được".

## Vòng lặp cho MỖI bug

Khởi tạo: `uifix_state.py bug-new --state-dir <RUN>/bugs --id <bug-id> --screen <screen> --desc "<mô tả>"` (mặc định `--max-rounds 3 --threshold 95`).

```
BASELINE: render -> board -> chấm  --bug-record --kind baseline
   |
   v  (score < 95)
┌─> FIX (sửa đúng bug, source theo ref) -> RENDER -> BOARD -> CHẤM -> bug-record --kind fix
│        exit 0 PASS -> xong | exit 2 -> lặp | exit 3 STUCK -> dừng, báo
└────────────────────────────────────────────────────────────────┘
```

**Render** (1 lệnh, output ngoài repo):
```bash
android preview render :app --fqn=<preview_fqn> --component-tree --format=json \
  --output=<RUN>/bugs/<bug-id>/r<N>/
```
Module có product flavor (lỗi `Variant 'debug' does not exist`) thì thay `:app` bằng `":app@<flavorBuildType>"`, ví dụ `":app@appDevDebug"`, ở cả `list` lẫn `render`. Chi tiết ở `testing-preview/references/android-reference.md`, mục "Product flavors".
`<N>` = 0 baseline, 1..3 các vòng fix. Đọc JSON ra đường dẫn PNG; PNG rỗng/lỗi build -> sửa lỗi build/preview trong cùng vòng (không tính là vòng fix mới nếu chưa render được), không bịa ảnh. `component-tree` dùng để xác định source location của node lệch.

**Board + chấm**: ghép bằng `create_board.py --mode pair --actual <render.png> --expected docs/design-refs/<screen>/<screen>-design.png`, rồi chạy quy trình `ui-diff-review` (đọc board 1 lượt, checklist trục, pass 2 zoom + `sample_region.py` khi nghi màu/component). Luật bỏ qua giữ nguyên: khác ngôn ngữ, data/state, status bar không trừ điểm. Với preview dùng fixture, state/data của fixture lệch design = không trừ; chỉnh fixture cho gần design nếu cần so cho công bằng.

**Ghi vòng**:
```bash
python3 $SKILL_DIR/scripts/uifix_state.py bug-record --state-dir <RUN>/bugs --id <bug-id> \
  --kind fix --score <0-100> --board <board.png> --note "<đã sửa gì, còn lệch gì>"
python3 ~/.claude/skills/ui-diff-review/scripts/verdict.py --score <n> --threshold 95 \
  --screen <screen> --board <board.png> --out <RUN>/bugs/<bug-id>/r<N>/result.json --reason "..."
```

**Quy tắc fix**
- Mỗi vòng chỉ sửa finding còn `lệch`, theo thứ tự severity rồi confidence. Sửa tối thiểu, đúng pattern/token của repo (theme/colors/dimens có sẵn), không refactor ngoài phạm vi.
- Mỗi vòng dùng **bằng chứng render mới**; không dùng lại ảnh vòng trước.
- Không giảm yêu cầu để đạt điểm: không đổi fixture để giấu lệch, không hạ ngưỡng, không xóa element lệch.
- Hết 3 vòng chưa đạt (`STUCK`): dừng, báo finding còn lại + nguyên nhân (cần quyết định design/PO, asset thiếu, lệch do runtime mà preview không tái hiện...). Không tự mở vòng thứ 4.
- Lệch cần quyết định sản phẩm (vd progress `1/3` vs `1/2`, native-ad có render không) -> không tự sửa; ghi `needs-decision`, đưa user.

## Chạy song song nhiều bug

- Gom bug theo file source: bug cùng file/composable -> **cùng 1 lane** (tuần tự) để không đè sửa nhau.
- Lane khác file -> giao subagent song song, mỗi lane = 1 bug-id, chỉ được sửa file đã khai báo. Ưu tiên mỗi lane 1 git worktree (`ak:worktree`) rồi merge sau; nếu dùng chung working tree thì phải disjoint file.
- `android preview render` đi qua Gradle -> **chạy render tuần tự** giữa các lane trong cùng working tree (Gradle khóa project). Worktree riêng thì render song song được nhưng tốn RAM; tối đa 2-3 lane cùng lúc.
- Prompt giao subagent phải có: bug-id, screen, đường dẫn refs entry, file được sửa, ngưỡng 95, max 3 vòng, RUN dir, và yêu cầu kết thúc bằng `Status: DONE|DONE_WITH_CONCERNS|BLOCKED` + bảng điểm từng vòng. Controller giữ việc merge và báo cáo.
- Dùng `uifix_state.py bug-status --state-dir <RUN>/bugs` để xem tổng.

## Quy tắc môi trường

- Chỉ sửa code khi user đã yêu cầu fix (task này đã là yêu cầu fix). Không commit/push nếu user chưa yêu cầu. Không đụng file ngoài phạm vi bug.
- Không chạy dev server/process nền không cần; nếu bật `--daemon` của preview thì tắt khi xong (theo `process-management.md`).
- `android` CLI thiếu -> cài theo `testing-preview/references/android-reference.md`. Module preview không list ra FQN (Compose Multiplatform dùng annotation JetBrains) -> theo mục "Multiplatform preview annotation" trong file đó.
- Preview **không** chứng nhận hành vi runtime (animation, ad, navigation, device). Lệch chỉ có ở runtime -> ghi "không kiểm bằng preview", chuyển Artemis nếu user muốn; không coi là PASS cho toàn bộ màn.

## Báo cáo cuối

Bảng `bug | màn | baseline | v1 | v2 | v3 | trạng thái (PASS/STUCK/needs-decision)`, danh sách file đã sửa, asset đã tải/thêm, link `figma-refs.json`, finding còn lại kèm lý do. Kết thúc bằng `Status:` và câu hỏi còn mở.

## Gotchas

- Lệch scale: design Figma export 360x800 (pngScale 2 -> 720x1600); preview `widthDp=360,heightDp=800` cho cùng tỉ lệ. Board tự cân, nhưng đừng so ảnh khác tỉ lệ khung.
- Font/skeleton khác nhau do preview không có font hệ thống thiết bị -> chỉ trừ điểm khi lệch rõ ràng ở cỡ/đậm/casing, và xác nhận bằng crop zoom.
- Link Figma phải trỏ đúng frame (có `node-id`); link file gốc không đủ.
- Đừng ghi plan-id/finding-id vào comment code hay commit (`review-audit-self-decision.md`).
