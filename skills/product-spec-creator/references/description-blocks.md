# Ngữ pháp các khối Description + checklist dev-ready

Thứ tự cố định: **Mô tả → Flow → Logic → Logic click button → Remote config → ghi chú**.

## Mô tả

1–2 câu: màn là gì, mở từ đâu / khi nào, mục đích với user.
> **Mô tả:** Hiện ngay trên màn **Detail film** khi user xem hết tập cuối của phim.

## Flow

Mũi tên `→` cho đường đi, `|` cho nhánh, điều kiện trong ngoặc.
> **Flow:** Onboarding 3 → Survey → Age verification (nếu bật `age_verification`) / Home
> **Flow:** Home / For You (icon tìm kiếm) → Search → Kết quả | Không có kết quả

## Logic

Bullet, mỗi bullet một quy tắc. Thứ tự gợi ý:
1. **Bố cục** từ trên xuống ("header → chip → banner → Continue watching → ...").
2. **Từng khối UI**: nội dung, nguồn dữ liệu, số lượng tối đa, sắp xếp, định dạng.
3. **Điều kiện hiển thị**: khi nào ẩn/hiện, khi nào disable ("chưa chọn: nút ✓ mờ").
4. **Trạng thái**: rỗng, lỗi, mất mạng, đang load, đã/chưa làm.
5. **Thời gian / tự động**: auto-slide 5s, ẩn controls sau 10s, đếm ngược, reset 0h giờ máy.
6. **Lưu trữ**: lưu gì, ở đâu xuất hiện lại, có hỏi lại không ("chỉ hiện 1 lần").
7. **Tương tác với media/hệ thống**: popup mở thì pause video hay không, timer dừng không.
8. **Giới hạn nền tảng**: khác biệt theo version OS, quyền hệ thống; app nhiều nền tảng →
   chỉ ghi nhánh Android / iOS khi hành vi khác, phần quy đổi chung nằm ở bảng
   **Khác biệt nền tảng** (phần A).

Mẫu câu tốt (cụ thể, kiểm được):
- "Continue watching: tối đa 10 phim, cuộn ngang, thanh tiến độ + "EP.x / tổng"; user chưa xem phim nào → ẩn khối này"
- "Không có banner (CMS không trả phim) → ẩn cả khối, các khối dưới đẩy lên; header và chip giữ nguyên"
- "Bấm Claim liên tục hoặc Claim + bấm ngoài cùng lúc → chỉ cộng 1 lần"
- "Ad không load → toast "Ad not available, please try again later", không cộng tiến độ"
- "Số lượt xem là fake data"

Tránh: "hiển thị danh sách phim" (thiếu nguồn, số lượng, rỗng), "xử lý lỗi phù hợp", "như design" khi design không thể hiện hành vi.

## Logic click button

Mỗi phần tử bấm được = 1 dòng `Phần tử → kết quả`. Kết quả gồm: điều hướng, thay đổi
dữ liệu, thay đổi UI, toast/feedback, event (nếu muốn nhắc).
- "Save → lưu phim vào My List › Saved series, icon đổi đỏ; bấm lại → bỏ lưu"
- "Watch ad to unlock → nút loading (không bấm lặp) → show ad → xem hết → mở khoá, phát tập"
- "Bấm ngoài / vuốt xuống → đóng popup, không gửi report"
- Gồm cả cử chỉ: vuốt ngang/dọc, long press, **device back**.

Nhánh kết quả theo điều kiện viết lồng:
- "Bấm tập kế tiếp bị khoá → đủ coin → tự trừ coin và phát · thiếu coin → popup Unlock episode"

## Remote config (trong màn)

Chỉ khi màn phụ thuộc key. Ghi từng giá trị → hành vi:
> `age_verification` = true → hiện màn · false → bỏ qua, Onboarding xong vào thẳng Home (default)

## Ghi chú cuối

- Hành vi khi popup mở (pause/không pause), kích thước cố định ("popup cao 3/4 màn hình").
- `[PO confirm]` + "đề xuất: …" cho giả định của dev.
- Quyết định đã chốt có ngày ("PO chốt 09/11") khi đảo ngược quyết định trước.

---

## Checklist dev-ready theo loại màn

Áp dụng cho MỌI màn:
- [ ] Vào từ đâu (Flow) và device back đi đâu.
- [ ] Mọi phần tử bấm được có kết quả.
- [ ] Mọi text cố định ghi nguyên văn trong ngoặc kép.
- [ ] Nguồn dữ liệu từng khối (service/CMS / local / remote / fake).
- [ ] Trạng thái rỗng, lỗi tải, mất mạng (hoặc ghi rõ "không áp dụng").
- [ ] Số có thể đổi → key remote có default.

**List / feed / lưới:** số item tối đa, sắp xếp, phân trang/cuộn vô hạn, item hiển thị
gì (ảnh tỉ lệ, dòng text, max dòng), bấm item → đâu, rỗng → gì, refresh khi quay lại.

**Detail / player / media:** autoplay, khi hết (tự sang tiếp?), tua, chất lượng/tốc độ/
phụ đề, lưu tiến độ, pause khi popup/ra nền, ẩn controls sau bao lâu, khoá nội dung.

**Form / input:** focus + bàn phím khi vào, validation từng ô + text lỗi, giới hạn ký tự
+ bộ đếm, khi nào nút submit sáng, submit lỗi mạng, giữ nội dung khi đổi lựa chọn.

**Popup / bottom sheet:** điều kiện bật, chiều cao, đóng bằng gì (✕/ngoài/vuốt/back),
đóng thì trạng thái nền thế nào, popup chồng popup quay về đâu, chỉ hiện 1 lần/ngày?

**Onboarding / first open:** chỉ lần đầu? lưu trạng thái gì, skip được không, màn có
điều kiện (remote), lần mở sau đi thẳng đâu.

**Tiền tệ / thưởng / mở khoá:** công thức cộng/trừ, khi nào cộng (sau xác nhận thành
công), chống cộng trùng (bấm liên tục), giới hạn/ngày + giờ reset, tiến độ có lưu không,
số dư không đủ → nhánh nào, nguồn số liệu (remote JSON + default khi lỗi).

**Thanh toán (IAP):** giá lấy từ store theo ID gói (không hardcode), gói mặc định chọn,
mua xong vẫn thiếu → gì, huỷ thanh toán → quay về đâu.

**Quyền hệ thống:** khác biệt theo nền tảng / version OS (Android 13+ thông báo, iOS luôn
xin; ATT chỉ iOS), từ chối quyền → gì, cách kiểm khi
không có popup xin quyền.

**Settings:** mỗi mục mở gì; mục mở app ngoài (email/store) → điền sẵn gì, không có app → toast.
