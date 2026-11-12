# CAPTURE — từ video / screenshot / research app mẫu ra observed notes

Đọc video **qua frame**, không xem video trực tiếp. Tái dùng script của skill `ui-diff`
(`~/.claude/skills/ui-diff/scripts/`), không viết mới. Python: `python3`
(cần Pillow + ffmpeg trong PATH).

## 0. Chuẩn bị

- Ghi mỗi video vào bảng: tên file, thời lượng, độ phân giải (`ffprobe -v error -show_entries
  format=duration -show_entries stream=width,height -of compact <video>`).
- Run dir trong scratchpad: `<run>/v<N>/frames`, `<run>/v<N>/sheets`, `<run>/picks`.
- Video không bật **Show taps** (Android Developer options / iOS AssistiveTouch) → mọi
  "bấm vào X" là [suy luận]. Lần quay sau khuyên user bật để tăng độ chính xác.

## 1. Cắt frame + dedup

```bash
python3 ~/.claude/skills/ui-diff/scripts/extract_frames.py \
  --video "<video>" --out <run>/v<N>/frames --interval 1
```
- `--interval 1` cho app nhiều màn ngắn (onboarding, quiz); 2 cho video dài > 5 phút.
- Kết quả thực tế: video 3:23 → 203 frame → giữ 99 sau dedup. `frames.json` có `t_sec`.
- Toast / feedback chỉ hiện < 1s bị sót → cắt lại đoạn đó với `--interval 0.5`.

## 2. Contact sheet có nhãn

```bash
python3 ~/.claude/skills/ui-diff/scripts/contact_sheet.py \
  --dir <run>/v<N>/frames --out <run>/v<N>/sheets --cols 8 --per 32 --thumb 150 \
  --prefix v<N> --glob "screen_*.png"
```
32 frame/sheet đủ đọc bố cục và tiêu đề; KHÔNG đủ đọc text nhỏ (để bước 5).

## 3. Phân loại màn trên sheet

Đọc lần lượt mọi sheet, lập bảng nháp `slug | video | khoảng #index | trạng thái thấy`:
- Gom frame liên tiếp cùng màn; tách **trạng thái** (default / đã chọn / sai / đúng /
  loading / sheet mở) thành dòng riêng khi layout đổi.
- Đặt slug theo nhóm: `fo-NN-*` (first open/onboarding), `pw-*` (paywall), `home-*`,
  `lib-*`, `ls-*` (màn trong bài/flow chính), `end-*` (kết thúc flow). Slug này về sau là
  tên ảnh `<screen-slug>[-<state>].png` cho harness.
- Đánh dấu frame **không dùng được**: dialog hệ thống che, đang chuyển cảnh (2 màn chồng
  nhau), skeleton loading, màn ngoài app (store, settings máy).

## 4. Chọn frame sạch nhất + board xác nhận

Mỗi dòng bảng chọn 1 frame: đúng màn, trạng thái rõ, không transition/ad/bàn phím che
(trừ khi chính trạng thái là bàn phím). Copy về `<run>/picks/<slug>.png`, rồi dựng board:

```bash
python3 ~/.claude/skills/ui-diff/scripts/contact_sheet.py \
  --dir <run>/picks --out <run>/picks-overview --cols 8 --per 32 --thumb 150 --prefix picks
```
Đọc board, sửa pick sai rồi mới đi tiếp. Lỗi hay gặp (đã gặp thật): chọn nhầm frame
skeleton cho màn paywall; chọn frame dialog hệ thống đang animate (2 lớp chồng) thay vì
màn app phía sau. Không có frame sạch cho trạng thái → giữ, ghi "frame transition".

## 5. Đọc chi tiết từng màn → observed notes

Mở `picks/<slug>.png` cỡ đầy đủ; khi cần, mở frame lân cận (±1–3 index) để suy chuyển
cảnh. > ~20 màn → chia nhóm theo slug, mỗi nhóm 1 subagent (song song, cùng format),
ghi `plans/<plan-dir>/observed/<nhóm>.md`. Format mỗi màn:

```
### <slug> — <tên màn>
- Nguồn: v<N> #<idx…> (t=<giây>s…)
- Loại: full-screen | tab | bottom-sheet | dialog | overlay | toast | system
- Bố cục (trên → dưới): ...
- Text nguyên văn: "..." (không đọc rõ → "[mờ]")
- Trạng thái thấy: ...
- Điều hướng & tương tác: mỗi ý [thấy] / [suy luận] + độ tin cậy cao/vừa/thấp
- Logic suy luận: [suy luận] ...
- Câu hỏi mở: ...
```

Suy luận được từ chuỗi frame: điều hướng trước/sau, nút disabled → enabled khi chọn,
single vs multi select, thanh tiến độ, thời lượng màn (auto-advance), số liệu đổi giữa 2
lần xuất hiện (XP, streak, %), điều kiện biến thể (vd 100% đúng → "Perfect Lesson").
KHÔNG suy được: remote config, nhánh lỗi/mất mạng, màn không quay tới, logic server.

## 6. Nguồn khác

- **Screenshot rời**: bỏ bước 1, chạy từ bước 2 với `--dir <thư mục ảnh>`.
- **Research store** (không có video, hoặc bổ sung): store listing (mô tả, screenshot,
  "What's new", review 1–2 sao để biết điểm đau) → ghi observed với nguồn = URL, mọi
  điều hướng là [suy luận] độ tin cậy thấp.
- **Research pattern thể loại**: 2–3 app top cùng thể loại → bảng pattern chung, dùng làm
  đề xuất mặc định ở brainstorm và Q&A. Chỉ lấy hành vi / pattern, không chép tên, text,
  branding, asset.

## 7. Đầu ra bước CAPTURE

- `observed/*.md` (theo format trên) + `picks/*.png` + `picks-overview/*.jpg`.
- Bảng tổng: nhóm → danh sách màn → câu hỏi mở. Chuyển sang `brainstorm.md`.
