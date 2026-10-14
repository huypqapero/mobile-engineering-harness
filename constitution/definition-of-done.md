# Definition of Done

Một task chỉ hoàn thành khi đáp ứng toàn bộ dưới đây. Không có "pass khi check không chạy được" — phải document limitation.

## Completion Criteria

### Code

- [ ] Code compile sạch (`:composeApp:assembleDebug` hoặc `:<touched>:build`)
- [ ] Không warning Kotlin mới trong file đã sửa
- [ ] Không public API thay đổi ngoài scope được duyệt
- [ ] File < 400 dòng; nếu lớn hơn phải tách
- [ ] Không `TODO` / `FIXME` mới trừ khi link tới issue

### Architecture

- [ ] Zero violation `architecture-rules.md` MUST
- [ ] Konsist test pass (`./gradlew konsistTest`)
- [ ] Dependency graph không đảo chiều
- [ ] Platform SDK chỉ xuất hiện trong `data/{androidMain,iosMain}/`

### Concurrency

- [ ] Zero violation `concurrency-rules.md` MUST
- [ ] CancellationException re-throw đúng
- [ ] Dispatcher inject được, không hardcode trong common
- [ ] `collectAsStateWithLifecycle()` ở Compose

### Testing

- [ ] Unit test cho behavior mới / sửa behavior
- [ ] Test chạy xanh ở module touched (`./gradlew :<module>:test`)
- [ ] Không disable test hoặc sửa assertion để pass
- [ ] Edge case: null, empty, error, cancellation (nếu áp dụng)

### Quality gates

- [ ] `./gradlew detekt` pass hoặc baseline đã update có chủ ý
- [ ] `./gradlew lint` không error mới
- [ ] Build smoke pass

### Documentation

- [ ] Spec update nếu behavior khác spec (`docs/specs/`)
- [ ] Remote config key / analytics event mới → update registry trước
- [ ] CLAUDE.md / README không bị stale

### Report

Mọi task phải kết bằng report theo mẫu dưới.

## Report Template

```
Status: VERIFIED | VERIFIED_WITH_LIMITATIONS | BLOCKED | FAILED

Summary:
<1-2 câu outcome, không process>

Files changed:
- path/to/File1.kt (+40/-5)
- path/to/File2.kt (new)

Architecture compliance:
- ARCH-001 domain purity: PASS
- ARCH-003 ViewModel deps: PASS
- ARCH-007 MVI 1-chiều: PASS
<liệt kê rule đã verify, không list toàn bộ>

Concurrency compliance:
- CORO-001 scope: PASS
- CORO-004 cancellation: PASS

Verification:
- compile: PASS
- konsist: PASS
- detekt: PASS
- unit_tests: PASS (12 new, 0 fail)
- build: PASS

Limitations:
- iOS build chưa test (không có runner macOS trong env này)
- UI test chưa viết (chưa có fixture)

Open questions:
- Có cần cache paginated result không? (depend content pipeline spec)
```

## Completion states

| State | Nghĩa |
|---|---|
| **VERIFIED** | Mọi gate MUST pass, không limitation |
| **VERIFIED_WITH_LIMITATIONS** | MUST pass, có limitation đã công bố (ví dụ: iOS chưa test được trong env) |
| **BLOCKED** | Không thực hiện được check cần thiết, task chưa xong — cần user hoặc context mới |
| **FAILED** | Có lỗi chưa khắc phục |

## Anti-patterns bị cấm khi report

- Tuyên bố DONE khi test fail hoặc không chạy
- Disable test / sửa assertion / `@Ignore` để pass
- "Build pass locally" không có command cụ thể
- "Rules compliant" không list rule nào
- Dấu diếm limitation
- Report dài giải thích process thay vì outcome

## Khi nào BLOCKED thay vì tiếp tục

- Konsist/Detekt tool chưa setup trong project → ghi BLOCKED, đề xuất setup trước
- Dependency bị conflict version → BLOCKED, không hack qua
- Spec yêu cầu behavior không chốt (ví dụ: open item) → BLOCKED, hỏi user
- Build fail do code có sẵn trong repo (không phải code mới) → ghi rõ, không gộp fix ngoài scope
