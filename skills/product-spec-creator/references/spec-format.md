# Khung tài liệu spec Screen + Description

Học từ spec AAP884 (Phase 1: Build App). Bỏ phần stakeholder, link quản trị, ads.

## Khung tổng thể

```
Quy ước: [PO confirm] = điểm cần PO xác nhận / bổ sung.

A. TỔNG QUAN
   - Version
   - Các tính năng chính (1.1 … 1.N)
   - Flow tổng + điều hướng chính (bottom nav / tab)
   - Quyết định UI chung (màu/token, tỉ lệ ảnh, component dùng chung)
   - Logic chung toàn app (nếu có)
B. MÔ TẢ CHI TIẾT
   ### 1. <Module>   → **Flow:** + bảng Screen | Description | UI
   ### 2. <Module>   → ...
   (Quy ước điều hướng chung — đặt sau module đầu tiên mà nó áp dụng)
C. TỔNG HỢP REMOTE CONFIG
D. EVENT TRACKING
```

Tiêu đề module ở B đánh số khớp danh sách "Các tính năng chính" ở A (A ghi 1.3 For You →
B có `### 3. For You & ...`).

## A. Tổng quan

| Mục | Viết gì |
|---|---|
| **Version** | `1.0.0`; bản đầu ghi "bản đầu tiên, không có baseline". Bản sau ghi baseline + danh sách thay đổi. |
| **Nền tảng** | Android / iOS / cả hai (KMP, Flutter…) + min version. Cả hai → bắt buộc bảng **Khác biệt nền tảng** (dưới). |
| **Khác biệt nền tảng** | Chỉ khi nhiều nền tảng: bảng `Khái niệm trong spec \| Android \| iOS` quy đổi 1 lần các khái niệm chung — back (iOS: vuốt cạnh; modal không có back), `{store}` trong text UI, billing / restore / quản lý subscription, đăng nhập (iOS có Google → bắt buộc Sign in with Apple, App Store 4.8), mở link, quyền thông báo, tracking (ATT chỉ iOS), mail, đổi ngôn ngữ, xoá tài khoản. Hàng ở B viết theo khái niệm chung, chỉ ghi nhánh riêng khi hành vi thật sự khác. |
| **Các tính năng chính** | List đánh số `1.1 Tên module (màn con, màn con)`. Là mục lục của B. |
| **Flow tổng** | Một dòng mũi tên: `Splash → Language → Onboarding → ... → Home`. Màn có điều kiện ghi rõ: `Age verification (chỉ khi bật \`age_verification\`, mặc định tắt)`. Kèm danh sách tab bottom nav theo đúng thứ tự. |
| **Quyết định UI chung** | Chỉ những gì dev cần để code: token màu (tên + hex), tỉ lệ/size ảnh chuẩn theo vị trí, danh sách component dùng chung, đổi tên tab so với bản tham khảo. Kèm lý do ngắn nếu khác bản gốc. |
| **Motion** | Khi app có animation: bảng token (thời lượng Quick / Standard / Slow / Celebrate, easing Standard / Enter / Exit / Bounce, Shake, spring kéo thả) + quy tắc chuyển màn, phản hồi đúng/sai, giảm chuyển động, hiệu năng, điều cấm (CTA nhấp nháy ở paywall) + bảng asset Lottie (`anim_*` · màn · kích thước · thời lượng · lặp). Hàng ở B chỉ thêm bullet "Motion:" cuối khối Logic, tham chiếu token / asset. Nguyên tắc chọn số: skill `ak-motion-design`. |
| **Logic chung** | Quy tắc áp dụng nhiều màn (vd reload dữ liệu khi quay lại app, định dạng số lượt xem). |
| **Thay đổi so với bản tham khảo** | Khi có app mẫu / design gốc: bảng `Màn / cụm \| Quyết định \| Nguồn \| Lý do` lấy từ bảng brainstorm đã chốt (`brainstorm.md`). |
| **Changelog** | Mỗi version: các màn đổi (đúng tên hàng in đậm) → lát build cần build/test lại. Tên hàng là khoá truy vết, đổi tên hàng cũng phải ghi. |

## B. Mô tả chi tiết

Mỗi module:

```markdown
### 2. Home & Discover

**Flow:**

![<appcode>_flow_<module>.png](<link hoặc path>)   ← hoặc mermaid flowchart nếu chưa có ảnh

| Screen | Description | UI |
| --- | --- | --- |
| **Home** | **Mô tả:** ...<br>**Flow:** ...<br>**Logic:**<br>• ...<br>**Logic click button:**<br>• ... → ... | appcode_2-1.png appcode_2-2.png |
```

### Loại hàng trong bảng

| Loại | Đặt tên hàng | Khi nào |
|---|---|---|
| Màn | `**Home**`, `**Detail film (Player)**` | Màn full screen / tab. Tên trong ngoặc = tên trên design nếu khác. |
| Popup / sheet | `**Popup Unlock episode**`, `**Popup Quality / Speed / Subtitle**` | Dialog, bottom sheet. Gộp nhiều popup cùng dạng vào 1 hàng được. |
| Hàng logic | `**Bảng coin**`, `**Burn coin · Mở khoá tập**`, `**Hộp quà đếm ngược (For You / Detail film)**` | Quy tắc nghiệp vụ dùng ở nhiều màn, không có màn riêng. Cột UI để trống. |
| Biến thể | `**Earn coin · Quà lần đầu**` | Dùng `·` để nhóm hàng cùng chủ đề. |

### Định dạng ô trong Markdown

- Xuống dòng trong ô: `<br>`. Bullet cấp 1: `• `; cấp 2: `◦ ` (thụt bằng `&nbsp;&nbsp;` nếu cần).
- Bảng con trong ô (remote config theo màn): viết dạng dòng
  `` `key` = true → bật màn X · false → bỏ qua màn X (default) ``. Bảng đầy đủ nằm ở C.
- JSON dài: chỉ ghi tên key trong ô, đưa JSON vào hàng logic riêng hoặc mục C.
- Ô quá dài (> ~40 dòng): tách màn thành nhiều hàng theo trạng thái
  (`**For You**`, `**For You · Native full ad**`) thay vì nhồi.

### Quy ước điều hướng chung

Đoạn bullet ngắn sau module đầu, gom các luật lặp lại ở nhiều màn để không viết lại:
- Bấm vào 1 item (phim/sản phẩm) ở bất kỳ đâu → mở màn nào, ở trạng thái nào
  (vd tập đang xem dở, chưa xem → tập 1).
- Device back ở từng tab → đi đâu; back ở tab gốc → thoát app.
- Dữ liệu đã xem/đã lưu xuất hiện lại ở những đâu.

## C. Tổng hợp remote config

```markdown
| Key | Default | Ghi chú |
| --- | --- | --- |
| `age_verification` | false | true: bật màn Age verification · false: tắt (default) |
| `unlock_episode_logic` | 10 | Mỗi tập khoá tiếp theo cộng thêm 10 coin (tập 4: 20, tập 5: 30…) |
| `coin_challenge_config` | `{ "watch_1_ad": 10, ... }` | JSON — chi tiết ở hàng **Bảng coin** |
```

- Gồm MỌI key nhắc trong B. Ghi chú mô tả từng giá trị (enum) và ví dụ tính toán.
- Key JSON: ghi hành vi khi thiếu field / JSON lỗi (dùng default).
- Giá trị ngoài miền hợp lệ → xử lý thế nào (đánh `[PO confirm]` nếu là giả định).
- Thời điểm đọc key (khi mở app / mỗi lần vào màn) nếu ảnh hưởng hành vi.

## D. Event tracking

```markdown
| Màn | Trigger | Event name |
| --- | --- | --- |
| **Home** | Vào màn | `home_view` |
|  | Bấm Watch now ở banner | `home_banner_watch_click` |
| **Report** | Gửi report thành công (param: reason, series_id, episode) | `report_submit` |
```

- Đặt tên: `<màn>_<đối tượng>_<hành động>`, snake_case, hành động ∈ `view`, `click`,
  `submit`, `start`, `complete`, `success`, `fail`, `claim`, `change`.
- Param ghi trong cột Trigger: `(param: a, b — b chỉ khi ...)`.
- Event nghiệp vụ (thành công/thất bại) bắn khi kết quả xác định, không bắn lúc bấm.
- Mỗi màn chính tối thiểu có `<màn>_view`.
- Giữ gọn: `_view` + 1–3 event cho hành động quyết định phễu (chọn gói, mua, hoàn thành, bỏ dở).
  Không bắn event cho mọi nút; thông tin phụ đưa vào param. Spec ~50 màn nên ở mức 40–80
  event (pilot không giới hạn ra 175 event cho 58 màn — quá tải cho dev và analytics).

## Quy ước đặt tên file UI

`<appcode>_<số module>-<thứ tự>.png`, biến thể chèn thêm số: `aap884_2-1.png`,
`aap884_2-1-1.png` (Home không banner). Flow: `<appcode>_flow_<module>.png`.
