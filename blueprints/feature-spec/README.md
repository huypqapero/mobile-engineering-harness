# Blueprint: Feature Spec

Format chung cho `docs/specs/<feature>.md` trong product. Một format cho cả spec viết tay lẫn spec sinh bởi
`skills/android-spec-ingest` (Confluence + Figma), để orchestrator, `android-feature` và workflow feature đọc
giống nhau.

## Ai dùng

| Thành phần | Đọc / ghi |
|---|---|
| `skills/android-spec-ingest` | Ghi spec từ Confluence page + Figma frame |
| `skills/android-orchestrator` | Step 0 đọc `status`; Step 2/4 đọc AC, màn hình, open questions |
| `skills/android-feature` | Step 1 lấy AC + 5 UI states mỗi màn |
| `workflows/feature-development.md`, `workflows/parallel-feature-development.md` | Entry conditions + Stage 1 |
| `agents/architect.md` | Tách spec nhiều feature thành feature plan, giữ `Sources` + `Open questions` |

## Mục bắt buộc

6 heading cấp 2 theo đúng thứ tự trong [`template.md`](template.md): `Mô tả`, `Acceptance criteria`,
`Màn hình & UI states`, `API / data`, `Open questions`, `Sources`. Mỗi màn có bảng đủ 5 state
`loading / empty / error / offline / success` (ARCH-008); state không có dữ liệu vẫn có hàng, trỏ tới open question.

## Open questions và `status`

- Chỗ suy luận ghi `[INFERRED → OQ-n]`, chỗ thiếu ghi `[MISSING → OQ-n]`. Mỗi marker trỏ tới một dòng `OQ-n`.
- Phép thử: làm theo một mặc định hợp lý mà khả năng cao phải bỏ đi vì đổi scope, contract hoặc danh sách file
  → `Blocking: yes` (cụ thể hoá blocker "spec thiếu critical info" của `workflows/feature-development.md` Stage 1:
  thiếu endpoint/field AC cần, chưa rõ feature cần auth không, feature flag, nguồn mâu thuẫn, TBD đổi scope,
  điều hướng ra tới màn chưa có trong nguồn lẫn repo). Bảng ví dụ đầy đủ: `skills/android-spec-ingest/SKILL.md` Step 6.
- Còn lại `Blocking: no` và bắt buộc ghi `Mặc định nếu chưa trả lời` (OQ đã có `Trả lời` thì để `—`). Mặc định ghi rõ không phải đoán:
  implementer xác nhận với backend DTO/docs hoặc code hiện có, reviewer kiểm.
- Mỗi OQ một quyết định; gap gộp nhiều ý thì tách.
- UI state thiếu trong design là `Blocking: no`. Implementer render theo mặc định ARCH-008 và reviewer kiểm.
  State có thể không áp dụng (empty trên màn form) vẫn giữ hàng, OQ non-blocking hỏi xác nhận.
- Điều hướng vào màn không nêu là `Blocking: no`; architect xác định từ nav graph hiện có.
- Một OQ có thể được nhiều marker trỏ tới.
- Còn dòng `Blocking: yes` → frontmatter `status: draft`. Agent dừng, hỏi user, không đoán. Gate này chỉ áp dụng
  cho spec có field `generated_by`; spec cũ không có frontmatter giữ hành vi cũ.
- User trả lời → agent ghi câu trả lời vào cột `Trả lời`, đổi `Blocking: no`, thay marker bằng nội dung đã chốt,
  rồi chuyển `status: ready` khi hết OQ blocking.

## Spec viết tay

Vẫn hợp lệ. Để `generated_by: manual`, mục `Sources` ghi link tài liệu gốc nếu có. Spec cũ chưa theo template
vẫn dùng được như trước; template chỉ là chuẩn khuyến nghị cho spec mới.
