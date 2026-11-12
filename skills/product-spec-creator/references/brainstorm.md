# BRAINSTORM — từ observed app mẫu tới quyết định trước khi viết spec

Đầu vào: observed notes (`video-capture.md`) + research pattern (nếu có). Đầu ra: bảng
quyết định user đã chốt → mục "Thay đổi so với bản tham khảo" ở phần A của spec.

## 1. Bảng quyết định theo module

Mỗi module (nhóm slug) một bảng; mỗi màn / cụm màn một dòng:

```
| Màn / cụm | Quyết định | Nguồn | Lý do | Ảnh hưởng |
| --- | --- | --- | --- | --- |
| Onboarding · 12 câu khảo sát | Đổi: rút còn 6 câu | video v1 #20–51 | 12 câu ~70s, drop-off cao | Bớt 6 màn; giữ kết quả chấm điểm |
| Widget promo | Bỏ | video v1 #70–71 | Ngoài scope phase 1 | — |
| Practice tab | Lấp trống | video không quay | Tab có trên bottom nav | Cần Q&A / research |
| Daily challenge | Thêm mới | research 3/3 app top | Tăng retention | Màn mới, key remote mới |
```

Quyết định ∈ **Giữ** · **Đổi** (ghi đổi gì) · **Bỏ** · **Lấp trống** (app mẫu có nhưng
video không quay tới: tab chưa mở, trạng thái lỗi/rỗng) · **Thêm mới**.

App mẫu quay trên nền tảng khác app đích (vd video iOS, app đích Android hoặc KMP): KHÔNG
tự bỏ màn "chỉ của iOS / Android" (ATT, Sign in with Apple, widget) trước khi biết nền
tảng đích — hỏi nền tảng đích trước khi lập bảng.

## 2. Đề xuất tính năng mới

- Nguồn hợp lệ: pattern lặp lại ở ≥ 2 app top cùng thể loại, review người dùng app mẫu,
  hoặc lỗ hổng rõ trong flow app mẫu (vd không có cách xem lại bài đã học).
- Mỗi đề xuất: giá trị cho user, màn / thay đổi cần có, rủi ro scope. Tối đa 3–5 đề xuất
  mỗi lượt — nhiều hơn thì user không chốt nổi.
- Không thêm mới chỉ vì "app khác có": phải nói được nó giải quyết gì trong flow này.

## 3. Chốt với user

- Trình bày bảng theo module; hỏi theo lô bằng `AskUserQuestion` (mỗi câu = 1 cụm quyết
  định, phương án đề xuất đứng đầu kèm "(Recommended)"). Tính năng mới: multiSelect.
- Chưa chốt → không viết spec cho phần đó. User bỏ qua → giữ đề xuất, đánh `[PO confirm]`.
- Quyết định đã chốt là input cố định cho Q&A + viết spec; đổi lại sau → ghi Changelog.

## 4. Chuyển sang spec

- Bảng đã chốt → mục **Thay đổi so với bản tham khảo** (phần A), giữ cột Nguồn + Lý do.
- Màn **Giữ / Đổi / Thêm mới** → hàng trong bảng Screen | Description | UI.
- Màn **Lấp trống** → hàng có `[PO confirm]` hoặc đưa vào Q&A trước.
- Màn **Bỏ** → không viết; nếu là backlog → gạch ngang `~~…~~ (backlog)`.
- Text nguyên văn của app mẫu chỉ dùng làm tham chiếu ý; text trong spec phải viết lại
  cho sản phẩm mới (không chép copy, tên thương hiệu, nhân vật của app mẫu).
