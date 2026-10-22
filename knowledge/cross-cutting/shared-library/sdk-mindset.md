# SDK Mindset — ADR Set

ADR áp dụng cho **mọi lib publish artifact** trong harness. Khác `essentials.md` ở chỗ: `essentials` là checklist rule, file này là **triết lý mindset** quyết định thái độ thiết kế trước khi mở file code.

Consume bởi: `library-architect` (bắt buộc đọc trước khi draft Library Contract), `architect` (khi plan lib module), `reviewer` (khi review API diff).

---

## SDK-001 — SDK ≠ Feature-first Module

**Decision**: Mọi artifact publish qua Maven/Nexus/GitHub Packages được treat như **SDK**, không phải "shared module". SDK có đối tượng là **≥ 5 consumer** (bao gồm straw-man persona), feature-first mindset bị cấm.

**Lý do**:
- Shared module trong monorepo chỉ cần phục vụ 1-2 app đã biết → OK sửa khi phát sinh.
- SDK publish ra ngoài phục vụ ≥ 5 consumer trong đó N chưa biết trước → sửa core = N consumer migrate = cost N×.
- Feature-first API ôm scope "làm cho app A xong" → bị patch mỗi lần app B/C/D phát sinh nhu cầu khác → nợ kỹ thuật tăng cấp số nhân.

**Thực thi**:
- Khi scope lock trigger check (Stage 1 library-flow) → bắt buộc verify ≥ 5 consumer (real + straw-man).
- Dưới 5 → BLOCKED, không spawn pipeline. Dùng monorepo shared module thay thế (`library-extract` khi đủ consumer).

**Hệ quả**:
- Mất thêm thời gian Phase 0 brainstorm (0.5-1 tuần).
- Đổi lại: không phải refactor core sau 1.0.

---

## SDK-002 — 3 Guarantee bắt buộc

SDK phải thoả **cả 3**. Thiếu 1 = anti-SDK, downgrade thành shared module.

### Stability
- Public API freeze sau `1.0.0`. Mọi thay đổi = **thêm** symbol mới, không sửa/xoá symbol cũ.
- Freeze qua `binary-compatibility-validator` (Kotlin BCV) gate CI. API dump commit vào git.
- Breaking change `>= 1.0` yêu cầu RFC + consumer sign-off (xem `essentials.md §LIB-GOV`).

### Configurability
- Mọi hành vi quan trọng configurable qua Builder/DSL immutable.
- Default sensible: lib hoạt động không cần set gì khi không bắt buộc (ví dụ default dispatcher, default clock, default retry).
- Required field chỉ khi lib không thể default an toàn (ví dụ `apiKey`).
- Feature toggle default = tắt. Consumer explicit opt-in.

### Extensibility
- Có điểm cắm **SPI (Service Provider Interface)** declarative cho mọi hành vi khả năng được thay thế: resolver, interceptor, listener, port, strategy.
- Consumer plug SPI mà **không fork lib**, không extend abstract class.
- Mỗi SPI có stability tier riêng (xem `pattern-catalog.md §SPI contract rules`).

**Thực thi**:
- Library Architect verify cả 3 guarantee trong Contract review (Stage 3).
- Thiếu 1 → raise finding, không approve contract.

---

## SDK-003 — Feature-first vs SDK-first (bảng đối chiếu)

Dùng bảng này khi phân vân "có phải SDK thật không". Tất cả cột phải nghiêng về SDK-first.

| Dimension | Feature-first (shared module) | SDK-first (bắt buộc) |
|---|---|---|
| **Audience** | 1-2 consumer đã biết | ≥ 5 consumer, N chưa biết |
| **API stability** | Thay đổi được | Immutable sau 1.0, chỉ add |
| **Khi phát sinh use case lạ** | Patch lib | Consumer plug SPI, lib không biết |
| **Config** | Hardcode / 1-2 flag | Everything configurable, Builder DSL |
| **DI** | Lib tự khởi tạo | Consumer bơm port, lib agnostic |
| **Lifecycle** | Theo app | Lazy init, multi-instance, process-safe |
| **Dependency injection framework** | OK bind Hilt/Koin | Lib không ép framework DI |
| **Testing** | Test lib | Test lib + ship **TestingKit** cho consumer |
| **Documentation** | README + comment | README + CHANGELOG + migration guide + sample module |
| **Release cadence** | Follow sprint | Separate release train, SemVer strict |

**Rule**: nếu > 2 cột cột trái, downgrade từ SDK → shared module, không publish artifact.

---

## SDK-004 — Anti-pattern cấm cứng

Những pattern này cấm trong SDK publish. Reviewer + Library Architect raise finding ngay khi phát hiện.

### Anti-pattern Lifecycle & Scope

| Anti-pattern | Lý do cấm | Thay bằng |
|---|---|---|
| `object MyLib { fun init(ctx) }` cứng singleton | Multi-instance impossible, test leak state | Factory + Builder → `MyLib.create(config)` return instance |
| **Service Locator global** (static registry) | Hidden coupling, test khó isolate | DI qua port, consumer wire |
| **Inheritance cho extension** (`abstract class BasePlugin`) | Fragile base class, consumer trói buộc, upgrade lib = break consumer | Interface SPI + Null Object default |
| **God Config** (1 class 50 field) | Khó discover, option không orthogonal | Nested config theo domain + Kotlin DSL |

### Anti-pattern Observability

| Anti-pattern | Lý do cấm | Thay bằng |
|---|---|---|
| `setListener(callback)` | Leak callback, không cancel, 1 subscriber | `Flow<Event>` / `StateFlow<State>` |
| Hardcode Logger `println` / `Log.d` | Không swap, không silent | `Logger` port, default `NoopLogger` |
| Hardcode Analytics Firebase | Lib bị ép transitive dep | `AnalyticsPort` + adapter module optional |

### Anti-pattern Async & Resource

| Anti-pattern | Lý do cấm | Thay bằng |
|---|---|---|
| `Thread.sleep`, `Looper.getMainLooper()` hack | Test block, không determistic | `Clock` port + `TestDispatcher` + coroutine |
| `GlobalScope.launch` | Leak scope, không cancel theo lib lifecycle | Scope inject qua config |
| Reflection auto-discovery (ServiceLoader) | Khó debug, ProGuard/R8 strip, không IDE-complete | Explicit `.register(...)` call |
| `Thread.currentThread().contextClassLoader` | Fragile cross-platform | Explicit injection |

### Anti-pattern API shape

| Anti-pattern | Lý do cấm | Thay bằng |
|---|---|---|
| `data class` public không freeze field | Thêm field = binary break | `interface` + factory function HOẶC `@ConsistentCopyVisibility` + versioning plan |
| `enum class` public cho state machine | Thêm variant = binary break (exhaustive consumer `when`) | `sealed interface` + explicit `@Deprecated` lifecycle |
| `Context`-dependent trong KMP common | Phá cross-platform | expect/actual bridge hoặc tách androidMain |
| `api(libs.firebase)` không có lý do | Transitive leak | `implementation` + ship adapter module `<lib>-firebase` optional |

**Thực thi**:
- Library Architect check list này trong Contract review.
- Reviewer check lại trong code review.
- Konsist rule enforce một số (ví dụ no `object Singleton` cho type có `@LibraryPublicApi`).

---

## SDK-005 — Khi nào áp dụng

**Áp dụng cho**:
- Mọi lib publish artifact (Maven Central / internal Nexus / GitHub Packages)
- Mọi module trong monorepo được tag `library` (ngay cả khi chưa publish, chuẩn bị publish)
- Mọi code chia sẻ ≥ 2 team hoặc ≥ 2 product

**Không áp dụng cho**:
- Internal module trong single-product monorepo chỉ 1 team dùng → OK feature-first
- Util < 200 LoC chia sẻ 1-2 project tạm thời → giữ shared module, chưa cần SDK mindset
- Build logic (buildSrc, convention plugin) → có pattern riêng, không phải SDK runtime

**Grey zone**:
- Shared module 2 app cùng team → treat như SDK-light (áp dụng SDK-002 Stability + Configurability, giãn Extensibility)
- Khi evolve lên ≥ 3 app hoặc ≥ 2 team → nâng cấp full SDK mindset

---

## SDK-006 — Boundary & responsibility (nhắc lại từ essentials)

Nhắc lại rule bất biến (duplicate từ `essentials.md §LIB-SCOPE` để agent đọc file này không miss):

- 1 SDK = 1 responsibility, viết 1 câu không "và".
- Có "và" → tách thành ≥ 2 SDK. Không gộp.
- Tên class/field/resource không chứa concept product-specific.

Nếu Library Architect phân vân scope lock, đọc `brainstorm-process.md §Step 1-3` để chạy 10-step top-down trước khi commit boundary.

---

## Enforcement checklist

Library Architect check 7 câu trước khi approve Library Contract:

- [ ] **SDK-001**: Verified ≥ 5 consumer (real + straw-man persona documented)?
- [ ] **SDK-002 Stability**: BCV plugin configured + API dump commit plan?
- [ ] **SDK-002 Configurability**: Builder/DSL designed, defaults sensible?
- [ ] **SDK-002 Extensibility**: ≥ 1 SPI designed (TriggerResolver / FireInterceptor / EventListener / Port)?
- [ ] **SDK-003**: Scored > 7/10 cột SDK-first, không drift feature-first?
- [ ] **SDK-004**: Anti-pattern list đã review, không vi phạm?
- [ ] **SDK-006**: Responsibility 1 câu không "và" đã lock?

Checklist này pass → tiếp Stage 4-9 library-flow. Fail → raise user, không tự quyết scope cut.

---

## Pair với

- `essentials.md` — rule checklist cứng (API, config, dep, publish, pattern per lib type)
- `pattern-catalog.md` — design pattern canonical cho mỗi SDK component
- `layered-architecture.md` — 5-layer kernel-plugin model
- `brainstorm-process.md` — 10-step top-down trước code
- `testing-kit-rules.md` — TestingKit mandatory
- Agent: `agents/library-architect.md`
- Workflow: `agents/workflows/library-flow.md`
