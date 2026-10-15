---
feature: <feature-name>                 # kebab-case, trùng tên file docs/specs/<feature-name>.md
status: ready                           # ready | draft (còn OQ Blocking: yes → agent dừng hỏi user)
generated_by: manual                    # manual | android-spec-ingest
generated_at: ""                        # ISO 8601 khi sinh từ ingest, ví dụ 2026-10-15T09:54:00+07:00
---

<!--
Template spec chung cho docs/specs/<feature>.md (viết tay hoặc sinh bởi skills/android-spec-ingest).
Giữ nguyên thứ tự và tên 6 heading cấp 2 bên dưới; orchestrator, android-feature và workflows đọc theo heading.

Marker cho chỗ không lấy trực tiếp từ nguồn:
  [INFERRED → OQ-n]  agent suy luận từ ngữ cảnh, cần user xác nhận
  [MISSING → OQ-n]   nguồn không có dữ liệu
Mỗi marker trỏ tới đúng một dòng trong "## Open questions"; một OQ có thể được nhiều marker trỏ tới.
Blocking: yes chỉ khi làm theo một mặc định hợp lý sẽ phải bỏ đi vì đổi scope, contract hoặc danh sách file
(ví dụ: thiếu endpoint, nguồn mâu thuẫn, TBD đổi scope, điều hướng ra tới màn chưa có, feature flag).
Còn lại Blocking: no và bắt buộc ghi "Mặc định nếu chưa trả lời". Mỗi OQ một quyết định.
Còn dòng Blocking: yes → status: draft. Hết → status: ready.
-->

# Spec: <Feature Name>

## Mô tả

<1-3 đoạn: user là ai, vấn đề gì, outcome quan sát được. Phạm vi IN / OUT nếu nguồn có nêu.>

## Acceptance criteria

- [ ] AC-1: <hành vi quan sát được, kiểm thử được>
- [ ] AC-2: <...>

## Màn hình & UI states

### Screen: <ScreenName>

Frame: `<figma node id hoặc "không có">` · Ảnh: `docs/specs/<feature>/design/<frame-slug>.png` (nếu export)

| State | Nội dung hiển thị | Nguồn | Trạng thái |
|---|---|---|---|
| loading | <skeleton / spinner / ...> | <Figma node / Confluence mục / -> | found |
| empty | <...> | - | [MISSING → OQ-1] |
| error | <message + retry> | <...> | found |
| offline | <...> | - | [MISSING → OQ-2] |
| success | <layout chính> | <...> | found |

Components: <danh sách component dùng trong frame, ví dụ PrimaryButton, TextField>

Copy text:

```text
<text nguyên văn từ Figma/Confluence, mỗi dòng một chuỗi>
```

Điều hướng: <từ đâu vào, đi đâu ra>

## API / data

| Thao tác | Endpoint / nguồn dữ liệu | Request | Response chính | Ghi chú |
|---|---|---|---|---|
| <Đăng nhập> | `POST /auth/login` | `email, password` | `token, user` | <auth / cache / feature flag> |

Analytics / remote config (nếu nguồn có nêu): <event, key>

## Open questions

| ID | Câu hỏi | Blocking | Nguồn gap | Mặc định nếu chưa trả lời | Trả lời |
|---|---|---|---|---|---|
| OQ-1 | Màn <ScreenName> hiển thị gì khi danh sách rỗng? | no | Figma: không có frame empty | Empty state mặc định ARCH-008 | |
| OQ-2 | Màn <ScreenName> xử lý offline thế nào? | no | Figma: không có frame offline | Offline state mặc định ARCH-008 | |

## Sources

| Nguồn | Link | ID | Version | Fetched at |
|---|---|---|---|---|
| Confluence | <page URL> | page `<id>` | `<version.number>` hoặc `unknown` | <ISO 8601> |
| Figma | <file URL> | file `<fileKey>`, node `<12:34>` | `<file version>` / lastModified `<ISO 8601>` | <ISO 8601> |

Spec viết tay: ghi "manual" và link tài liệu gốc nếu có.
