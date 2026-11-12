# Ví dụ chuẩn: 1 module hoàn chỉnh

Rút gọn từ spec AAP884 (app xem phim ngắn). Dùng làm thước đo độ chi tiết, không copy
nội dung sang app khác.

### 5. My List

**Flow:** Bottom nav My List / See all ở Continue watching (Home) → My List (tab History | Saved series)

| Screen | Description | UI |
| --- | --- | --- |
| **Saved series** | **Mô tả:** Các phim user đã lưu (Save ở For You / Detail film, My List ở banner Home, Add to My list ở popup Recommended).<br>**Logic:**<br>• Có data: lưới thẻ (poster 3:4, "EP.x/ EP.tổng", tên, nút Watch, icon bookmark), sắp theo lưu gần nhất<br>• Không có data: "Your list is currently empty" + nút Explore Now + lưới phim gợi ý (danh sách Most popular)<br>**Logic click button:**<br>• Bấm thẻ / Watch → Detail film, phát tập đang xem dở (chưa xem → tập 1)<br>• Bấm bookmark → bỏ lưu, xoá phim khỏi danh sách<br>• Bấm phim gợi ý → Detail film<br>• Explore Now → tab Home<br>• Back thiết bị → sang tab History | app_5-3.png app_5-4.png |
| **History** | **Mô tả:** Các phim user đã xem.<br>**Logic:**<br>• Có data: lưới thẻ sắp theo xem gần nhất (poster, tập đang xem, tên, nút Watch)<br>• Không có data: "Your history list is currently empty" + Explore Now + lưới phim gợi ý<br>• Mở từ See all ở Home → luôn chọn tab History; mở từ bottom nav → giữ tab đã chọn lần trước<br>**Logic click button:**<br>• Bấm thẻ / Watch → Detail film, phát tập đang xem dở<br>• Explore Now → tab Home<br>• Back thiết bị → tab Home | app_5-1.png app_5-2.png |

## Vì sao đạt chuẩn

- Mỗi màn có cả trạng thái **có data** và **rỗng**, text rỗng ghi nguyên văn.
- Nguồn vào màn liệt kê đủ (dev biết phải gọi lưu từ những chỗ nào).
- Mọi phần tử bấm được có kết quả, kể cả device back.
- Quy tắc "giữ tab lần trước" vs "luôn mở History" được nói rõ theo nguồn vào.
- Dữ liệu gợi ý chỉ rõ lấy danh sách nào (Most popular), không để dev đoán.

## Ví dụ hàng popup có nhánh điều kiện

| **Popup Unlock episode** | **Mô tả:** Hiện khi user sang tập bị khoá **và không đủ coin**.<br>• Đủ coin → không hiện popup: tự trừ coin, phát tập, toast "−{giá} coins" [PO confirm có toast không]<br>**Logic:**<br>• "Unlock the Next Episode!" — "Use {giá} Coins to watch the next episode now!"<br>• Giá theo `unlock_first_episode` + `unlock_episode_logic` (xem **Burn coin**)<br>• Nút Watch ad to unlock chỉ hiện khi bật `unlock_episode_by_ad` và còn lượt trong ngày (`unlock_episode_ad_daily_limit`, reset 0h giờ máy)<br>**Logic click button:**<br>• Watch ad to unlock → nút loading (không bấm lặp) → show ad → xem hết → mở khoá vĩnh viễn, không trừ coin, phát tập<br>• Thoát ad giữa chừng → không mở khoá, quay lại popup<br>• Ad không load → toast "Ad not available, please try again later"<br>• Unlock now → popup IAP<br>• Bấm ngoài / vuốt xuống → đóng, dừng ở tập trước | app_3-15.png |
