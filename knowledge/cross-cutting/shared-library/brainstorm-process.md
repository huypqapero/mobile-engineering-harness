# SDK Brainstorm Process — 10-Step Top-Down

Quy trình brainstorm **bắt buộc trước khi draft Library Contract**. Thay thế thói quen bottom-up (bắt đầu từ API shape). Áp dụng cho mọi SDK publish artifact.

Consume bởi: `library-architect` (Phase 0 trước Stage 3), `architect` (hiểu context khi plan).

---

## BRAIN-001 — Khi nào chạy

**Bắt buộc** cho:
- Lib mới chưa tồn tại (greenfield `/library-new`)
- Lib extract từ product khi scope mở rộng beyond 2 consumer (clean-slate mode `/library-extract`)
- Lib hiện có cần MAJOR refactor API `>= 2.0`

**Không bắt buộc** cho:
- Patch/bugfix lib có contract chốt
- Extract mode lift-and-shift (giữ API gần nguyên)

**Output**: 3 artifact ở `plans/<date>-<slug>/`:
- `brainstorm.md`
- `use-case-matrix.md`
- `straw-man-personas.md`

Thiếu 1/3 → BLOCK Stage 3 Contract design.

---

## BRAIN-002 — 10 Step Top-Down

Chạy tuần tự. Mỗi step có deliverable + gate.

### Step 1 — Mission statement

**Hành động**: Viết 1 câu, 1 clause, không "và".

**Format**:
```
<Verb> <object> <qualifier>.
```
Ví dụ:
- ✅ "Fire local Android notification theo rule có điều kiện với priority preemption."
- ❌ "Schedule notification theo giờ và theo scenario và handle gate." (3 "và")
- ❌ "Make life easier for devs." (vague)

**Gate**: Có "và" / có "or" / có "etc" → fail, rewrite.

### Step 2 — Non-goals explicit (≥ 5 item)

**Hành động**: List ≥ 5 việc SDK **không** làm. Mỗi item có lý do.

**Format**:
```markdown
- ❌ FCM remote push — out of scope, consumer tự wire; SDK này chỉ local scheduled.
- ❌ Geofence trigger — kéo Google Play Services, battery concern, permission UX khác.
- ❌ Deeplink router — chỉ store deeplink trong payload, consumer intercept.
- ❌ Rich notification UI (BigPicture) — consumer customize NotificationPresenter port.
- ❌ Localization string lookup — consumer pass pre-localized text.
```

**Gate**: < 5 non-goal → fail (SDK scope chưa đủ sharp). Mỗi item không có lý do → fail.

### Step 3 — Consumer persona (≥ 5)

**Hành động**: List ≥ 5 consumer. Mỗi persona gồm:
- Tên consumer (app thật hoặc straw-man)
- Primary use case
- Scale (user count, push/day estimate)
- Constraint (battery sensitive? offline-first? min SDK?)

**Rule**:
- ≥ 2 real consumer (team đã confirm sẽ tích hợp)
- ≥ 3 straw-man khi real < 5 (xem BRAIN-004)
- Tổng ≥ 5

**Gate**: Dưới 5 → BLOCK pipeline, không tiếp Step 4. Trả về `/library-new` trigger check fail.

### Step 4 — Use case inventory (≥ 15 use case)

**Hành động**: Enumerate ≥ 15 use case canonical, tag matrix 3 trục (chi tiết Step 5).

**Nguồn**:
- Canonical app trên thị trường (Google Keep, Todoist, Any.do, Samsung Reminder, Microsoft To Do, Habitica, Headspace...)
- Straw-man persona (Step 3) → mỗi persona ≥ 2 use case
- Edge case gợi ý từ Library Architect

**Deliverable**: `use-case-matrix.md` dạng bảng (xem Step 5).

**Gate**: < 15 use case → nghi ngờ coverage không đủ. 15-25 là sweet spot.

### Step 5 — Use case matrix 3 trục

Tag mỗi use case theo 3 trục để map vào layer sau:

**Trục A — Trigger source**:
- `wall-clock-absolute` (vd "9:00 sáng mai")
- `elapsed-duration` (vd "30 phút sau register")
- `calendar-aligned` (vd "mỗi thứ 2 lúc 9h")
- `business-event` (vd "sau khi user hoàn thành task")
- `user-action` (vd "snooze từ notification")
- `system-event` (vd "khi boot", "khi có wifi")
- `location` (vd "khi về nhà")

**Trục B — Trigger pattern**:
- `one-shot`
- `fixed-interval-repeat`
- `calendar-repeat`
- `cron-like`
- `decay-escalation`

**Trục C — Gate semantic**:
- `per-reminder-condition` (if/then rule)
- `cross-scenario-priority` (preemption)
- `global-frequency-cap`
- `quiet-hours`
- `permission-gate`
- `none`

**Format matrix**:
```markdown
| ID | Use case | Source | Pattern | Gate | Scope decision |
|---|---|---|---|---|---|
| UC-01 | Nhắc user mở app sau 24h không mở | business-event | one-shot | per-reminder-condition | IN L1 |
| UC-02 | Push hoá đơn hằng ngày 9h | calendar-aligned | calendar-repeat | quiet-hours | IN L1 |
| UC-03 | Reminder lịch âm | wall-clock-absolute | one-shot + custom-calendar | none | CONSUMER-OWN (via SPI) |
| UC-04 | Snooze từ notification | user-action | one-shot | none | IN L2 |
| UC-05 | Preempt khi scenario critical | — | — | cross-scenario-priority | IN L3 |
| ... | ... | ... | ... | ... | ... |
```

**Gate**:
- Mỗi use case có đủ 3 trục tag.
- Mỗi use case có scope decision (IN L_N / OUT / CONSUMER-OWN với SPI nào).

### Step 5.5 — Intersection audit + Cross-cutting lens

Catch **unknown unknowns** — use case nằm ở giao giữa 2 trục mà không UC nào bao phủ, hoặc concern cross-cutting (UX host, lifecycle recovery, DI boundary) không nằm trên trục nào.

**Phần A — Intersection audit (axis cartesian)**:

1. Chọn 2 trong 3 trục làm plane. Với mỗi SDK, chọn tối thiểu 2 plane có risk cao nhất.
2. List top 5 cell `(axis_X=value_i, axis_Y=value_j)` risky nhất — cell có interaction phi thường, không trivial, dễ miss.
3. Mỗi cell phải có **≥ 1 UC đại diện** trong matrix Step 5, hoặc document lý do "intentionally not covered" với bằng chứng.

**Ví dụ cho permission-kit**:

| Plane | Cell risky | UC đại diện | Trạng thái |
|---|---|---|---|
| caller-surface × ux-host | `suspend-call × rationale-needed` | UC-21 | Phải thêm nếu chưa có |
| caller-surface × lifecycle | `preview-mock × recheck-on-resume` | — | Intentional skip (không hợp lý) |
| permission-type × caller | `composite-permission × flow-observe` | UC-11 | Có |
| lifecycle × ux-host | `cross-process × rationale-needed` | UC-22 | Phải thêm nếu chưa có |
| caller-surface × error-path | `suspend-call × host-null-fallback` | — | Phải thêm nếu chưa có |

**Phần B — Cross-cutting concern lens (10 lens chuẩn)**:

Mỗi concern dưới đây phải có answer `COVERED by UC-N | OUT with reason | CONSUMER-OWN via SPI-X` cho **mỗi caller-surface** đã tag ở Step 5.

| # | Cross-cutting concern | Câu hỏi lens | Default miss rate |
|---|---|---|---|
| 1 | UX host (dialog, popup, bottom sheet) | Nếu SDK cần user UI confirm trong flow, caller surface S host popup thế nào? | High — thường miss cho non-UI caller |
| 2 | Process death recovery | Nếu OS kill process giữa flow, state restore thế nào? Caller nhận result ra sao? | High |
| 3 | Config change (rotation, dark mode) | Flow in-flight khi Activity recreate — resume hay restart? | Medium |
| 4 | DI framework boundary | Hilt/Koin/manual — SDK inject vào graph nào? Scope nào? | Medium |
| 5 | Thread/dispatcher | Suspend/callback chạy dispatcher nào? Caller phải switch không? | Low |
| 6 | Lifecycle timing (onCreate, onStart, onResume) | SDK register resource ở lifecycle nào? Caller gọi quá sớm → crash? | High |
| 7 | Error propagation | Exception vs sealed result vs Flow error — pattern thống nhất? | Medium |
| 8 | Cancellation | Caller cancel scope giữa chừng — resource cleanup, host dismiss? | Medium |
| 9 | Test host | Caller code test được không cần Android runtime? | Low (TestingKit cover) |
| 10 | Multiple caller concurrency | 2 caller gọi SDK cùng lúc — serialize, parallel, hay reject? | High |

**Hành động**:
1. Với mỗi concern trong 10 lens, viết 1 dòng answer per caller-surface.
2. Nếu answer là `TBD` hoặc `assumed trivial` → treat as gap, thêm UC đại diện vào matrix Step 5.
3. Document kết quả thành section "## Step 5.5 — Intersection audit + Cross-cutting lens" trong `brainstorm.md`.

**Deliverable**: Section mới trong `brainstorm.md` có 2 bảng (intersection audit + cross-cutting lens).

**Gate**:
- Tối thiểu 2 plane được audit.
- Mọi cross-cutting concern có answer rõ cho mỗi caller-surface (không TBD, không "assumed trivial").
- UC mới phát hiện từ audit đã added vào `use-case-matrix.md`.
- Số UC sau audit ≥ số UC trước audit (chỉ thêm, không bớt).

### Step 6 — Scope decision

**Hành động**: Dựa trên matrix Step 5, mỗi use case gán 1 trong 4 nhãn:

| Nhãn | Nghĩa | Hành động |
|---|---|---|
| `IN L0` | Core kernel primitive | Code trong `:core` module |
| `IN L1-L4` | Built-in feature theo layer | Code trong module tương ứng |
| `OUT` | Không thuộc scope SDK | Document lý do, add vào non-goals (Step 2) |
| `CONSUMER-OWN via SPI-X` | Consumer tự impl qua extension point X | Verify SPI-X đã có trong contract |

**Gate**:
- Mỗi use case `CONSUMER-OWN` phải trace về SPI cụ thể trong `layered-architecture.md §LAYER-003`.
- Không use case nào status "chưa biết" → nếu còn, quay lại Step 2 reduce scope.

### Step 7 — Layer decomposition

**Hành động**: Gom use case theo layer, verify tỉ lệ layer healthy.

**Healthy ratio** (heuristic):
- L0 Kernel: 2-4 use case (primitive atomic)
- L1 Resolvers: 5-8 use case (type expansion)
- L2 Composition: 2-5 use case
- L3 Policy: 3-6 use case
- L4 Integration: 2-5 use case

**Red flag**:
- L0 > 5 use case → kernel bloat, cần tách primitive
- L3 > 10 use case → policy quá nhiều, nhiều cái có thể là CONSUMER-OWN qua SPI
- L4 = 0 → có thể không cần, nhưng kiểm tra platform adapter đã có chưa

**Deliverable**: Section "Layer decomposition" trong `brainstorm.md`.

### Step 8 — Primitive identification (L0)

**Hành động**: Chốt API tối thiểu của L0 kernel.

**Rule**:
- L0 chỉ có 3-5 method (schedule, cancel, fire, state, history).
- L0 nhận input "đã resolved" (`Instant` absolute, không phải `Daily(9, 0)`).
- L0 không biết Scenario, Condition, Preemption.
- L0 pure Kotlin + stdlib + coroutine, không Android/iOS.

**Deliverable**: Section "L0 Kernel primitive" trong `brainstorm.md`:
```kotlin
interface Kernel {
    fun schedule(job: Job)                 // job.at: Instant absolute
    fun cancel(id: String)
    val events: SharedFlow<KernelEvent>
    fun state(id: String): JobState
}

data class Job(val id: String, val at: Instant, val payload: Payload)
```

**Gate**: L0 interface < 10 method. Mỗi method mô tả 1 primitive, không composite.

### Step 9 — SPI contract design

**Hành động**: List mọi SPI cần expose. Mỗi SPI gồm:
- Tên interface
- Mục đích
- Stability tier (`@Stable` / `@Experimental`)
- Default impl ship kèm
- Example custom plugin

**Format**:
```markdown
### SPI-A: TriggerResolver<T>
- Mục đích: Expand `Trigger` custom thành `Instant` cho kernel.
- Stability: @Stable from 1.0
- Default: DailyResolver, WeeklyResolver, HourlyResolver, IntervalResolver,
  AfterEventResolver, NextDayAfterEventResolver
- Example custom: LunarCalendarTrigger → LunarResolver (consumer impl)

### SPI-B: FireInterceptor
- Mục đích: Pipeline pre-fire, consumer thêm policy custom.
- Stability: @Stable from 1.0
- Default: ConditionInterceptor, PreemptionInterceptor, QuietHoursInterceptor,
  FrequencyCapInterceptor
- Example custom: OnlyWhenWifiInterceptor, GdprConsentInterceptor

### SPI-C: ReminderListener
- Mục đích: Observer passive, consumer bridge sang analytics/debug.
- Stability: @Stable from 1.0
- Default: empty (NoOp)
- Example custom: FirebaseAnalyticsListener, DebugLogListener
```

**Gate**:
- Có ≥ 3 SPI (type-resolver / interceptor / listener minimum).
- Mỗi SPI có ≥ 2 default impl.
- Mỗi SPI có ≥ 1 example custom (trace về straw-man persona).

### Step 10 — Backward compat strategy

**Hành động**: Document stability tier per layer + versioning rule.

**Deliverable**: Section "Backward compat strategy" trong `brainstorm.md`:
- L0 + SPI: strict freeze sau 1.0.
- L1-L3 built-in: flexible với deprecation window (1 minor WARNING → 1 minor ERROR → remove MAJOR).
- L4 adapter: loose per-adapter version.
- Experimental API: `@RequiresOptIn` annotation.

**Gate**: Mỗi layer có stability tier rõ. BCV plan cho L0 + SPI.

---

## BRAIN-003 — Deliverable summary

3 file bắt buộc produce:

### `plans/<date>-<slug>/brainstorm.md`

```markdown
# Brainstorm: <SDK name>

## 1. Mission statement
<1 câu, không "và">

## 2. Non-goals (≥ 5)
- ❌ ...

## 3. Consumer personas (≥ 5)
Link: `straw-man-personas.md`

## 4-5. Use case inventory
Link: `use-case-matrix.md`

## 6. Scope decision summary
- L0: N use case
- L1: N use case
- ...
- OUT: N
- CONSUMER-OWN: N via N SPI

## 7. Layer decomposition
<diagram + table>

## 8. L0 Kernel primitive
```kotlin
<interface>
```

## 9. SPI contract design
<list SPI với stability tier>

## 10. Backward compat strategy
<stability tier per layer>
```

### `plans/<date>-<slug>/use-case-matrix.md`

Table matrix 3-axis (Step 5).

### `plans/<date>-<slug>/straw-man-personas.md`

Chi tiết persona (Step 3 + BRAIN-004).

---

## BRAIN-004 — Straw-man persona rule

Khi real consumer < 5, straw-man lấp đủ.

**Rule tạo straw-man**:
- Mỗi straw-man có use case **khác biệt rõ** so với real consumer.
- Khác biệt theo ≥ 1 trong 3 trục (Step 5).
- Document consumer giả định: tên fictional (vd "MedicationReminderApp"), use case, scale, constraint.

**Mục đích**: Test extensibility SDK. Nếu SPI design chỉ phục vụ 2 real consumer giống nhau → bias feature-first. Thêm 3 straw-man khác domain = mental test "SDK có plug được không".

**Ví dụ cho reminder SDK**:

| # | Persona | Domain | Use case điểm nhấn | Trục khác biệt |
|---|---|---|---|---|
| 1 | App thật A | Finance | Nhắc hoá đơn hằng ngày | real |
| 2 | App thật B | Fitness | Nhắc tập luyện mỗi tuần | real |
| 3 | Straw-man: MedReminder | Health | Lịch âm trigger + strict timing (uống thuốc) | source: `calendar-aligned` + lunar + L1 custom resolver |
| 4 | Straw-man: HabitForge | Habit tracking | Decay escalation (nhắc 1h, 3h, 1 ngày nếu miss) | pattern: `decay-escalation` + L1 custom resolver |
| 5 | Straw-man: StudyBuddy | Education | Preempt khi exam mode: tắt mọi push khác | gate: `cross-scenario-priority` + L3 custom interceptor |

**Rule verify**: Mỗi straw-man **phải plug được** qua SPI đã design (Step 9). Không plug được → refactor SPI trước Stage 3 Contract.

---

## BRAIN-005 — Mental test "5 persona × 3 lens"

Trước khi lock contract, Library Architect chạy mental test. Mỗi persona hỏi **3 câu lens khác nhau** để catch unknown unknowns, không chỉ test SPI pluggability.

### Lens 1 — SPI plug (nguyên bản)

**Câu hỏi**: "Nếu consumer N muốn use case X, họ cần đụng vào SDK không?"
- ✅ Consumer plug qua SPI, SDK không sửa → GREEN.
- ❌ Consumer phải fork SDK hoặc wait upstream → RED.

### Lens 2 — Cross-cutting UX / lifecycle support

**Câu hỏi**: "Persona N chạy trong caller-surface S (`suspend-call`, `flow-observe`, etc). Nếu flow cần UX host (dialog, popup) hoặc gặp lifecycle event (process death, rotation), SDK handle thế nào mà **không ép persona N tự dựng UI/state restore logic**?"
- ✅ SDK có cơ chế (registered host, state store, lifecycle bridge) handle transparent → GREEN.
- ⚠️ SDK fallback về cho consumer handle nhưng document rõ pattern → YELLOW.
- ❌ Persona N phải tự wire mọi thứ, SDK không hỗ trợ → RED.

### Lens 3 — Error / cancel / concurrency path

**Câu hỏi**: "Persona N khi flow fail (host null, permission revoke runtime, caller cancel scope, 2 caller cùng request) — kết quả trả về cho persona có **actionable** không? Có bị stuck/leak không?"
- ✅ Sealed result rõ (`Granted/Denied/Cancelled/HostUnavailable`), resource cleanup, concurrency serialize → GREEN.
- ⚠️ Có kết quả nhưng semantic chưa rõ, cần Contract làm rõ → YELLOW.
- ❌ Caller treo, scope leak, undefined behavior → RED.

### Gate

Chạy test cho ≥ 5 persona × 3 lens = ≥ 15 verdict. Minimum:
- Lens 1: ≥ 4/5 GREEN
- Lens 2: ≥ 4/5 GREEN (YELLOW đếm là partial pass nếu document path rõ)
- Lens 3: ≥ 4/5 GREEN

Fail bất kỳ lens → quay lại Step 5.5 (intersection audit), Step 7-9 (layer/primitive/SPI). Không approve Contract.

---

## BRAIN-006 — Timeline

| Step | Time estimate |
|---|---|
| Step 1-3 (mission, non-goals, persona) | 2-4h |
| Step 4-5 (use case matrix) | 4-8h |
| Step 5.5 (intersection audit + cross-cutting lens) | 1-3h |
| Step 6-7 (scope + layer) | 2-4h |
| Step 8-10 (primitive + SPI + compat) | 4-8h |
| Mental test (5 persona × 3 lens) | 1-2h |
| **Total Phase 0** | **0.5-1 tuần** |

Nếu > 1 tuần = scope quá rộng, có thể cần split thành ≥ 2 SDK (xem `sdk-mindset.md §SDK-006`).

---

## BRAIN-007 — Cross-cutting concern catalog (reference)

10 concern bắt buộc hỏi ở Step 5.5. SDK consumer thường miss khi chỉ nhìn qua lăng kính "SPI plug". Catalog này áp dụng cho mọi SDK Android/KMP publish artifact.

### C1 — UX host

Flow SDK cần hiển thị UI (dialog, bottom sheet, snackbar). Ai host?
- Caller UI (Composable, View) → host trực tiếp.
- Caller non-UI (ViewModel, Service, WorkManager) → SDK cần `UiHost` SPI được register bởi UI layer (vd Composable root dùng `DisposableEffect`).
- Pattern: `HostRegistry` trong Facade, mutable `AtomicReference<Host?>`, lifecycle-scoped register.

### C2 — Process death recovery

OS kill process giữa flow. State in-memory mất. Caller cần biết:
- SDK persist state qua `StateStore` port (SharedPreferences/DataStore).
- Khi restart, SDK auto re-check và emit event mới cho Flow observer.
- Suspend caller không nhận result của flow cũ (continuation chết), phải re-check status và decide retry.

### C3 — Config change (rotation, theme, locale)

Activity recreate nhưng Application alive. Flow in-flight:
- SDK giữ scope ở Application-level (singleton controller) → survive config change.
- Composable caller rejoin qua `rememberSaveable` hoặc Flow collect.
- ViewModel scope survive config change by default.

### C4 — DI framework boundary

Consumer dùng Hilt/Koin/Manual. SDK không được opinionated:
- Expose plain constructor + factory function. Không annotation.
- Cung cấp sample module cho Hilt (`@InstallIn(SingletonComponent::class)`) + Koin (`module { single { ... } }`).
- Không cấu trúc internal state đòi hỏi DI graph cụ thể.

### C5 — Thread / dispatcher

Suspend/callback contract:
- SDK chạy internal work trên `Dispatchers.Default` (CPU) hoặc `Dispatchers.IO` (storage).
- Suspend caller nhận result trên dispatcher của caller scope (standard coroutine behavior).
- UI callback (vd `OnHostShow`) chạy `Dispatchers.Main.immediate`.
- Document rõ trong Contract §Threading.

### C6 — Lifecycle timing

Register resource với Android lifecycle:
- `ActivityResultRegistry` phải register **trước** `Activity.onStart` (sau `onCreate` OK).
- `LifecycleObserver` register trong `onCreate`, remove trong `onDestroy`.
- Composable `DisposableEffect` manage register/unregister tự động.
- SDK throw clear error nếu caller gọi sai lifecycle (vd `IllegalStateException("Call PermissionKit.initialize() in Activity.onCreate() before setContent")`).

### C7 — Error propagation

Pattern thống nhất:
- Expected failure → sealed result (`PermissionResult.Denied`, `ScheduleResult.Rejected`).
- Programmer error → `IllegalStateException` / `IllegalArgumentException` throw.
- Infra error (network, storage) → suspend throw hoặc Flow emit error (document rõ).
- Không mix `null` return + exception + sealed trong cùng API.

### C8 — Cancellation

Caller scope cancel giữa chừng:
- `suspendCancellableCoroutine` + `invokeOnCancellation` cleanup resource.
- UI host dismiss khi continuation cancel.
- In-flight request với OS (vd `ActivityResultLauncher.launch`) không cancel được → resource leak nếu không unregister. SDK phải unregister trong `invokeOnCancellation`.
- Return `PermissionResult.Cancelled` thay vì throw `CancellationException` nếu đã tiêu thụ pending state.

### C9 — Test host

Caller code test được không cần Android runtime:
- `:lib-testing` artifact ship `Fake*` cho mọi port L0.
- `TestXxxKit` driver pre-wire fake, caller dùng 1 dòng.
- Compose Preview có `PreviewProvider` mock state.
- Rule TEST-004: không depend Mockito/Mockk.

### C10 — Multiple caller concurrency

2+ caller gọi SDK cùng lúc:
- Nếu operation idempotent read-only (vd `status()`) → parallel safe.
- Nếu operation mutate shared state (vd `request()`) → serialize qua `Mutex`.
- Document policy trong Contract §Concurrency.
- Testing: parallel coroutine test case trong `:lib-testing`.

---

## Deliverable updates

Section mới trong `plans/<date>-<slug>/brainstorm.md` sau "## 4-5. Use case inventory":

```markdown
## 5.5. Intersection audit + Cross-cutting lens

### Intersection audit
<bảng 2-plane × ≥ 5 cell, mỗi cell có UC đại diện hoặc document skip>

### Cross-cutting lens (10 concern × mỗi caller-surface)
<bảng answer rõ, không TBD>

### UC mới phát hiện
<list UC-X thêm vào use-case-matrix.md>
```

Mental test table (Step BRAIN-005) mở rộng 3 lens:

```markdown
| Persona | Lens 1 SPI plug | Lens 2 UX/lifecycle | Lens 3 error/cancel/concurrency |
|---|---|---|---|
| ...     | GREEN           | GREEN               | GREEN                           |
```

---

## Pair với

- `sdk-mindset.md` §SDK-001 — ≥ 5 consumer rule
- `pattern-catalog.md` — pattern map vào SPI
- `layered-architecture.md` — layer decomposition template
- `testing-kit-rules.md` — mỗi SPI phải có TestingKit
- Agent: `agents/library-architect.md` §Phase 0 Brainstorm
- Workflow: `agents/workflows/library-flow.md` §Phase 0
- Skill: `skills/library-new/SKILL.md` §Step 0
