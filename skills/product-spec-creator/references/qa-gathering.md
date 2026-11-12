# Q&A gom thông tin dựng spec

Mục tiêu: lấp ô trống của checklist dev-ready bằng ít lượt hỏi nhất. Đây là Q&A để
DỰNG spec, không phải bộ Q&A review spec (việc đó là skill `create-qa`, ngoài harness).

## Nguyên tắc

- **Theo lô**: 3–6 câu/lô, cùng một module hoặc chủ đề. Tối đa 4 câu/lần khi dùng
  `AskUserQuestion`; câu hỏi mở gom thành list đánh số trong 1 tin nhắn.
- **Câu chặn trước**: thiếu thì không vẽ được flow hoặc không code được (luồng chính,
  điều kiện vào màn, mô hình tiền tệ, nguồn dữ liệu). Câu chi tiết hỏi sau.
- **Luôn kèm đề xuất**: mỗi câu có phương án mặc định hợp lý theo pattern app phổ
  biến cùng thể loại → user chỉ cần "OK" hoặc sửa. Ghi phương án đề xuất là "(Recommended)".
- **Dev tự viết spec** (không có PO): đề xuất chính là quyết định nếu user không phản
  đối; vẫn đánh `[PO confirm]` các điểm ảnh hưởng doanh thu / pháp lý / dữ liệu user.
- **Không hỏi lại** điều input đã trả lời. Cập nhật bản nháp ngay sau mỗi lô.
- **Không bịa**: user bỏ qua câu → giữ đề xuất, đánh `[PO confirm] đề xuất: …`.

## Thứ tự lô

1. **Khung app**: **nền tảng (Android / iOS / cả hai)** — hỏi TRƯỚC, vì đổi sau phải sửa
   đăng nhập, billing, quyền, back trên mọi màn; thể loại app, danh sách module, flow
   first open, bottom nav, mô hình kiếm tiền (coin / IAP / subscription / free).
   Có iOS → hỏi luôn: Sign in with Apple (bắt buộc nếu có Google/Facebook login), ATT
   (cần nếu SDK dùng IDFA).
2. **Nguồn dữ liệu**: service/CMS trả gì, cái gì lưu local, cái gì fake, cái gì remote.
3. **Từng module**: chạy checklist dev-ready theo loại màn
   (`description-blocks.md`), mỗi ô trống thành 1 câu.
4. **Số liệu → key remote**: mọi con số (giá, giới hạn, thời gian, số lượng) — default
   bao nhiêu, có cần đổi từ xa không.
5. **Event tracking**: màn nào cần `_view`, hành động nào cần đo, param gì.
6. **Edge case xuyên màn**: mất mạng, ra nền/quay lại, kill app giữa chừng, bấm liên tục,
   đổi ngôn ngữ, xoay màn hình.

## Mẫu câu hỏi tốt

- "Continue watching rỗng (user chưa xem phim nào) thì ẩn khối hay hiện placeholder?
  Đề xuất: ẩn khối, các khối dưới đẩy lên."
- "Popup Episodes mở thì video pause hay chạy tiếp? Đề xuất: pause, đóng popup phát tiếp."
- "Giới hạn mở khoá bằng ad mỗi ngày? Đề xuất: 5 tập/ngày, reset 0h giờ máy, key
  `unlock_episode_ad_daily_limit`."
- "Explore Now mở từ Search (đang ở tab For You) thì về tab nào?"

Tránh: "Màn Home có logic gì?" (quá mở), câu không có đề xuất, hỏi chi tiết pixel mà
design đã thể hiện.

## Khi nào dừng

Dừng khi không còn câu chặn, hoặc user bảo chốt. Phần còn lại để `[PO confirm]` và liệt
kê ở cuối câu trả lời theo dạng: `Màn — câu hỏi — đề xuất đang dùng`.
