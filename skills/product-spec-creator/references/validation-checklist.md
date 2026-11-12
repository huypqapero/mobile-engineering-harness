# Validation checklist

Severity: **ERROR** = dev không code được / code sai · **WARN** = dev phải đoán ·
**INFO** = trình bày.

## Tự động (`scripts/check_spec.py`)

| Check | Severity |
|---|---|
| Thiếu mục bắt buộc: Tổng quan, Mô tả chi tiết, Remote config, Event tracking | ERROR |
| Module đánh số (`### N.`) ở B không có bảng `Screen \| Description \| UI` | WARN |
| Hàng màn/popup (có ảnh UI) không có `**Mô tả:**` lẫn `**Logic:**` | ERROR |
| Hàng logic (cột UI trống) không có `**Mô tả:**` lẫn `**Logic:**` | WARN |
| Key trong backtick ở B không có trong bảng Remote config hay Event (bỏ qua field JSON) | WARN |
| Key ở bảng Remote config không nhắc ở đâu ngoài chính bảng đó | INFO |
| Key remote thiếu default / trùng | ERROR |
| Event trùng tên / không phải snake_case | ERROR |
| Thứ tự khối Description sai (vd Logic click button trước Logic) | WARN |
| Liệt kê từng `PO confirm` kèm tên hàng + ngữ cảnh (bỏ qua đoạn gạch ngang backlog) | INFO |

Key INFO "không được nhắc" thường là dấu hiệu của lỗi duyệt tay bên dưới: màn dùng key
đó bị thiếu hàng, hoặc màn ghi số cứng thay vì dẫn key.

## Duyệt tay (script không bắt được)

**ERROR**
- Phần tử bấm được trên design / trong Logic không có dòng kết quả ở Logic click button.
- Màn không có đường vào (không màn nào điều hướng tới) hoặc ngõ cụt (không có back).
- Màn/popup là đích điều hướng ("Rate us → Popup rate") nhưng không có hàng riêng.
- Hai chỗ mâu thuẫn (Flow nói A → B, Logic click button nói A → C).
- Cộng/trừ tiền tệ không nói rõ thời điểm và chống cộng trùng.
- Số cụ thể bịa ra, không có nguồn và không đánh `[PO confirm]`.

**WARN**
- List/feed thiếu: số lượng tối đa, sắp xếp, trạng thái rỗng.
- Thiếu hành vi mất mạng / lỗi tải ở màn dùng dữ liệu service.
- Text UI không ghi nguyên văn.
- Màn ghi số cứng ("+10 Coins") trùng default của một key remote mà không dẫn key đó.
- Màn chính không có event nào (kiểm lại với bảng D; có thể chủ đích nếu track ở nơi khác).
- Popup không nói cách đóng và trạng thái sau khi đóng.
- Màn có media không nói pause/resume khi popup/ra nền.
- Màn chưa có design không được đánh dấu.

**INFO**
- Tên màn tham chiếu không khớp tên hàng (vd "Player" vs "Detail film").
- Cột UI trống không ghi `[design pending]`.
- Event màn chính thiếu `<màn>_view`.

## Mẫu báo cáo

```markdown
| Severity | Màn | Vấn đề | Đề xuất sửa |
| --- | --- | --- | --- |
| ERROR | Popup IAP | Không nói mua xong mà vẫn thiếu coin thì làm gì | Thêm: chưa trừ coin, giữ popup với số coin mới |
```

Kết luận: **READY** (0 ERROR) · **NEEDS WORK** (có ERROR) · kèm số WARN.
