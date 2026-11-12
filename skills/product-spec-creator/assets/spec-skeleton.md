# <APPCODE> - Phase <N>: <Tên phase>

*Quy ước: `[PO confirm]` = điểm cần PO xác nhận / bổ sung.*

## A. TỔNG QUAN

| Mục | Nội dung |
| --- | --- |
| **Version** | 1.0.0 (bản đầu tiên, không có baseline) |
| **Nền tảng** | <Android / iOS / Android + iOS (KMP)>, min version <…> |
| **Các tính năng chính** | • 1.1 <Module> (<màn>, <màn>)<br>• 1.2 <Module><br>• 1.3 <Module> |
| **Logic chung** | • <quy tắc áp dụng nhiều màn> |

**Flow tổng:** <Màn đầu> → <Màn> → <Màn có điều kiện> (chỉ khi bật `<key>`, mặc định tắt) → <Màn chính>. Bottom nav <n> tab: **<Tab 1> · <Tab 2> · <Tab 3>**.

**Thay đổi so với bản tham khảo** (nguồn: <video / app / design gốc>):

| Màn / cụm | Quyết định | Nguồn | Lý do |
| --- | --- | --- | --- |
| <màn> | Giữ / Đổi: … / Bỏ / Lấp trống / Thêm mới | <video vN #idx / research> | <…> |

**Changelog:**

* v1.0.0 — bản đầu

**Quyết định UI chung:**

* Màu / token: <tên token> `<#hex>` — <dùng ở đâu>
* Ảnh: tỉ lệ <x:y>; size theo vị trí: <vị trí> <w×h>dp
* Component dùng chung: <Component>, <Component>

## B. MÔ TẢ CHI TIẾT

### 1. <Module>

**Flow:**

<ảnh flow `<appcode>_flow_<module>.png` hoặc mermaid>

| Screen | Description | UI |
| --- | --- | --- |
| **<Tên màn>** | **Mô tả:** <màn là gì, mở khi nào><br>**Flow:** <A> → <màn này> → <B> \| <C><br>**Logic:**<br>• <bố cục từ trên xuống><br>• <khối>: <nguồn dữ liệu>, tối đa <n>, <sắp xếp>; rỗng → <hành vi><br>**Logic click button:**<br>• <Phần tử> → <kết quả><br>• Back thiết bị → <đâu><br>**Remote config:** `<key>` = <v1> → <hành vi> · <v2> → <hành vi> (default) | <appcode>_1-1.png |
| **Popup <tên>** | **Mô tả:** <điều kiện bật><br>**Logic:**<br>• <...><br>**Logic click button:**<br>• <Nút> → <kết quả><br>• Bấm ngoài / vuốt xuống → <đóng, trạng thái nền><br>Khi popup mở: <pause / không pause> | <appcode>_1-2.png |
| **<Hàng logic>** | **Logic:**<br>• <công thức / quy tắc dùng chung> |  |

**Quy ước điều hướng chung:**

* Bấm vào 1 <item> ở bất kỳ đâu → <màn>, <trạng thái mở>
* Back thiết bị ở tab <X> → <tab gốc>; Back ở tab gốc → thoát app

### 2. <Module>

...

## C. TỔNG HỢP REMOTE CONFIG

| Key | Default | Ghi chú |
| --- | --- | --- |
| `<key>` | <default> | <giá trị → hành vi> |

## D. EVENT TRACKING

| Màn | Trigger | Event name |
| --- | --- | --- |
| **<Màn>** | Vào màn | `<man>_view` |
|  | Bấm <phần tử> | `<man>_<doi_tuong>_click` |
