# Engineering Principles

Nguyên tắc xuyên suốt áp dụng cho mọi task, mọi skill, mọi module trong {{PRODUCT_NAME}}. Cấp độ dưới:

- **MUST** — bắt buộc, vi phạm chặn task
- **SHOULD** — mặc định áp dụng, lệch cần lý do kỹ thuật
- **MAY** — tùy context
- **FORBIDDEN** — không làm nếu không có ngoại lệ được phê duyệt

## Clean Code

- **MUST** đặt tên self-documenting; biến/hàm nói lên ý định, không chú thích thừa
- **MUST** hàm chỉ làm 1 việc, side-effect rõ ràng
- **MUST** file < 400 dòng (rule #12 project), tách khi vượt
- **FORBIDDEN** chú thích "removed", "deprecated", TODO phase number, "added for X" — kể trong PR, không trong code

## SOLID

- **SRP** — ViewModel chỉ orchestrate state; Repository chỉ bridge data source; UseCase chỉ 1 business operation
- **OCP** — mở rộng qua composition hoặc Strategy, không sửa core logic cũ
- **LSP** — subtype giữ contract của supertype
- **ISP** — interface nhỏ, mục đích đơn; không interface "god"
- **DIP** — `domain` sở hữu interface; `data` implement; `presenter` consume. Không đảo chiều.

## KISS / DRY / YAGNI

- **MUST** chọn giải pháp đơn giản nhất đáp ứng yêu cầu
- **MUST** không tạo abstraction (interface, UseCase, Mapper) nếu chưa có 2+ consumer thật
- **MUST** không viết error handling, fallback, validation cho scenario không thể xảy ra
- **SHOULD** 3 dòng tương tự ok hơn 1 abstraction sớm
- **FORBIDDEN** feature flag, backwards-compat shim, placeholder cho requirement giả định

## Decision Priority khi conflict

Thứ tự giải quyết khi nguyên tắc đụng nhau:

1. **Correctness** — code chạy đúng với contract đã có
2. **Readability** — người kế thừa đọc hiểu nhanh
3. **Maintainability** — thay đổi tương lai không phải refactor rộng
4. **Testability** — behavior quan sát được qua test
5. **Performance** — optimize khi có evidence đo được
6. **Cleverness** — không bao giờ

Ví dụ cụ thể: Clean Architecture khuyên tạo UseCase cho mọi operation; nhưng với operation chỉ gọi 1 method repo không có logic transform/orchestrate → bỏ UseCase, ViewModel gọi thẳng repo qua interface không vi phạm layer. Rule #3 project chỉ cấm gọi Repository impl, không cấm interface.

## Composition over Inheritance

- **MUST** ưu tiên composition cho behavior sharing
- **SHOULD** dùng sealed interface/class cho state modeling, không inheritance tree sâu
- **FORBIDDEN** inheritance xuyên module boundary

## Explicit over Implicit

- **MUST** dependency qua constructor injection, không service locator
- **MUST** scope của coroutine rõ (viewModelScope, repositoryScope, …), không `GlobalScope`
- **MUST** state ownership rõ ở 1 nơi, không duplicate

## Immutability by Default

- **MUST** data class với `val`, state model immutable
- **MUST** `UiState` là `data class` hoặc `sealed interface` immutable
- **FORBIDDEN** expose `MutableStateFlow` ra ngoài ViewModel (rule project)

## Verification over Instruction

Rule phải có cách verify. Rule không map được tới Konsist test, Detekt rule, hoặc unit test → chuyển sang SHOULD, không bắt buộc.

Mỗi rule trong `architecture-rules.md` và `concurrency-rules.md` có `Verification:` chỉ ra test tương ứng.
