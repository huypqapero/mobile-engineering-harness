# Layered Kernel-Plugin Architecture

Kiến trúc tiêu chuẩn cho **mọi SDK publish artifact** trong harness. Enforce qua Gradle module split + Konsist rule. Thiết kế này cho phép mở rộng use case mới mà **không sửa core**.

Consume bởi: `library-architect` (Stage 3 contract), `architect` (Stage 5 module layout), `coder` (Stage 6 impl), Konsist test.

---

## LAYER-001 — 5-Layer model

```
┌──────────────────────────────────────────────────────────────┐
│ L4 — INTEGRATION           (consumer-facing adapters)       │
│  • Event bridge        • Boot handler    • Action handler   │
│  • Permission UX       • Analytics adapter                  │
│  • 3rd-party bridge (FCM, Firebase, Timber, Mixpanel)       │
├──────────────────────────────────────────────────────────────┤
│ L3 — POLICY                (filtering + preemption)         │
│  • Condition engine    • Preemption resolver                │
│  • Frequency cap       • Quiet hours                        │
│  • Permission check    • Rate limiter                       │
├──────────────────────────────────────────────────────────────┤
│ L2 — COMPOSITION           (grouping + lifecycle)           │
│  • Scenario            • Group            • Snooze          │
│  • Lifecycle state machine                                  │
├──────────────────────────────────────────────────────────────┤
│ L1 — TYPE RESOLVERS        (expand primitive)               │
│  • Daily / Weekly / Hourly   • Interval                     │
│  • AfterEvent / NthDay       • Cron (optional)              │
├──────────────────────────────────────────────────────────────┤
│ L0 — KERNEL                (bất biến, nhỏ nhất)             │
│  • schedule(id, at: Instant, payload)                       │
│  • cancel(id)         • fire(id)                            │
│  • state store        • dispatcher adapter                  │
└──────────────────────────────────────────────────────────────┘
```

Tên layer có thể đổi theo domain (vd network client: L1 = `Converter`, L2 = `Call`, L3 = `Auth/Retry`, L4 = `Platform adapter`). Nguyên tắc 5 layer giữ nguyên:

| Layer | Responsibility | Có thể skip? |
|---|---|---|
| **L0 Kernel** | Primitive atomic | Không — mọi SDK phải có |
| **L1 Resolvers** | Expand primitive → core input | Có — nếu SDK không có "type expansion" |
| **L2 Composition** | Group / lifecycle | Có — nếu SDK đơn-đối-tượng |
| **L3 Policy** | Filter / preempt / rate-limit | Có — nếu SDK không cần filter |
| **L4 Integration** | Platform / 3rd-party adapter | Có — nếu SDK pure logic |

---

## LAYER-002 — Rule bất biến

### Dependency direction

```
L4 depends-on L3, L2, L1, L0
L3 depends-on L2, L1, L0
L2 depends-on L1, L0
L1 depends-on L0
L0 depends-on NOTHING (pure Kotlin + stdlib + coroutine)
```

**Cấm**:
- L0 import L1+ (kernel không biết layer trên tồn tại).
- Bypass layer: L4 gọi thẳng L0 skip L2/L3 → cấm trừ khi L2/L3 không tồn tại cho use case đó.
- Circular reference giữa cùng layer: cấm, chia nhỏ hoặc extract chung lên layer dưới.

### Communication direction

- **Downward call** (L_N → L_(N-1)): qua public API của layer dưới.
- **Upward emit** (L_(N-1) → L_N): qua **Event bus** / `Flow` / Listener. Layer dưới không gọi layer trên trực tiếp.

### Konsist enforcement

Mỗi SDK publish phải có Konsist test file `KonsistLayerRuleTest.kt`:

```kotlin
@Test
fun `L0 kernel must not depend on L1+`() {
    Konsist.scopeFromModule("core")
        .classes()
        .assertFalse { it.hasImportOf(
            "kernel.resolver.*", "kernel.scenario.*",
            "kernel.policy.*", "kernel.integration.*"
        )}
}
```

Fail test = block merge.

---

## LAYER-003 — 3 SPI mandatory

Mỗi SDK layered phải có **tối thiểu 3 SPI** (xem `pattern-catalog.md §PAT-SPI`):

### SPI-A: Type Resolver (L1 extension)
**Dùng khi**: SDK có "input type" phong phú có thể mở rộng (vd `Trigger`, `MediaFormat`, `Converter`).

```kotlin
// Core expose:
interface TypeResolver<T : Type> {
    fun resolve(input: T, ctx: ResolveContext): KernelInput
}

// Core registry:
class ResolverRegistry {
    fun <T : Type> register(cls: KClass<T>, resolver: TypeResolver<T>)
}
```

Consumer: `.register(LunarCalendarTrigger::class, LunarResolver())` → không sửa SDK.

### SPI-B: Pipeline Interceptor (L3 extension)
**Dùng khi**: SDK có "fire pipeline" / "dispatch pipeline" trước khi commit action.

```kotlin
interface Interceptor {
    val order: Int
    suspend fun intercept(chain: Chain): Result
}
```

Consumer: `.addInterceptor(OnlyWhenWifi())` → thêm policy không fork SDK.

### SPI-C: Event Listener (L4 observer)
**Dùng khi**: Consumer cần observe lifecycle event (analytics, debug, bridge).

```kotlin
val events: SharedFlow<SdkEvent>

// OR explicit listener:
interface SdkListener {
    fun onFired(e: FireEvent) {}
    fun onBlocked(e: BlockEvent) {}
}
```

Rule:
- Default empty methods cho forward-compat.
- Flow preferred, listener acceptable khi cần Java interop.

---

## LAYER-004 — Module layout Gradle

Mapping layer → Gradle module:

```
my-sdk/
├── core/                 (L0, pure Kotlin, commonMain)
│   ├── src/commonMain/
│   └── src/androidMain/  (optional, platform adapter)
├── scheduler/            (L1, depends :core)
│   └── src/commonMain/
├── scenario/             (L2, depends :scheduler + :core)
├── policy/               (L3, depends :scenario + :scheduler + :core)
├── integration/          (L4, depends all)
│   ├── core-defaults/    (DataStore, NotificationManagerCompat)
│   ├── firebase/         (optional adapter)
│   └── timber/           (optional adapter)
├── testing/              (:lib-testing, cross-layer, in-memory fakes)
└── samples/
    ├── minimal/          (dùng L0 + L1 thôi)
    └── full/             (dùng cả 5 layer)
```

**Rule**:
- Consumer có thể depend `implementation("mysdk-scheduler")` để chỉ dùng L0+L1, tree-shake L2-L4.
- Default artifact (`"mysdk"`) depend L0+L1+L2+L3 (common path), L4 adapter opt-in.
- `:core` không bao giờ import module khác (`core` phải compile standalone).

### Gradle convention plugin

Convention plugin `mysdk-layer-conventions.gradle.kts` enforce:
- `explicitApi()` mode cho mọi module (`internal` opt-in rõ ràng).
- BCV plugin apply.
- Konsist test task auto-add.
- Resource prefix `lib_mysdk_` cho Android module.

---

## LAYER-005 — Extension flow

Khi consumer gặp use case mới (vd "trigger push khi user hoàn thành task 1 ngày sau"):

### Flow 1: Use case fit L1 (type mới)
```
1. Consumer tạo class `TaskCompletedTrigger(taskId, delay)` implement Trigger
2. Tạo `TaskCompletedResolver` implement TypeResolver<TaskCompletedTrigger>
3. .register(TaskCompletedTrigger::class, TaskCompletedResolver())
4. SDK không sửa.
```

### Flow 2: Use case fit L3 (policy mới)
```
1. Consumer tạo `OnlyWhenWifiInterceptor` implement FireInterceptor
2. .addInterceptor(OnlyWhenWifiInterceptor(), order = 500)
3. SDK không sửa.
```

### Flow 3: Use case fit L4 (bridge mới)
```
1. Consumer subscribe `events: SharedFlow<SdkEvent>` → forward sang Firebase Analytics.
2. HOẶC tạo adapter module `mysdk-firebase-analytics` dùng SPI-C.
3. SDK không sửa.
```

### Flow 4: Use case KHÔNG fit SPI → raise
```
1. Nếu use case cần modify core (L0) → raise Library Architect
2. Library Architect eval: thêm SPI mới (ưu tiên) hoặc expand L0 (chỉ khi cần primitive mới)
3. Expand L0 = MAJOR bump (xem SDK-002 Stability)
```

---

## LAYER-006 — Example mapping cho reminder SDK

Áp dụng mô hình cho reminder SDK (use case thực tế):

| Component | Layer | Pattern (ref `pattern-catalog.md`) |
|---|---|---|
| `ReminderJob(id, at: Instant, payload)` | L0 | PAT-CORE-002 Command |
| `ReminderCore.schedule(job)` | L0 | PAT-CORE-001 Hexagonal |
| `StateStore` port | L0 | PAT-CORE-003 Repository |
| `Clock` port | L0 | PAT-SPI-005 Port |
| `NotificationPresenter` port | L0 | PAT-SPI-005 Port |
| `Trigger` sealed hierarchy | L1 | PAT-CORE-004 Value Object |
| `TriggerResolver<T>` SPI | L1 | PAT-SPI-001 Strategy + Registry |
| `DailyResolver`, `WeeklyResolver` | L1 | Built-in strategy |
| `AfterEventResolver`, `NextDayAfterEventResolver` | L1 | Built-in strategy |
| `Scenario(id, priority, reminders)` | L2 | PAT-CORE-004 Value Object |
| `ScenarioState` sealed | L2 | PAT-EVENT-003 State Machine |
| `Snooze` API | L2 | PAT-ENTRY-002 (Facade method) |
| `Condition` + `Conditions.allOf/anyOf/not` | L3 | PAT-SPI-004 Specification Composite |
| `FireInterceptor` chain | L3 | PAT-SPI-002 Chain of Responsibility |
| `PreemptionPolicy` + resolver | L3 | PAT-SPI-001 Strategy + Policy Object |
| `FrequencyCapInterceptor`, `QuietHoursInterceptor` | L3 | Built-in interceptor |
| `BootReceiver` + reschedule | L4 | Platform adapter |
| `AppOpenTracker` (ProcessLifecycle) | L4 | Platform adapter |
| Notification action handler (snooze/done button) | L4 | PAT-SPI-003 Observer |
| `ReminderListener` + `events: SharedFlow` | L4 | PAT-SPI-003 Observer |
| `firebase-analytics-adapter` module | L4 | PAT-SPI-005 Adapter |

**Entry Facade** `ReminderKit`:
- Expose minimal method set (`register`, `unregister`, `schedule`, `cancel`, `events`, `state`).
- Internal delegate: Facade → Orchestrator (Mediator) → L2 → L1 → L0.

**Diagram tổng**:
```
   Consumer ──▶ ReminderKit (Facade, L4 wrapper)
                       │
                       ▼
              ┌────────────────┐
              │  Orchestrator  │ (Mediator)
              └┬──────┬──────┬┘
    interceptor │      │      │ resolver
    chain      ▼       ▼      ▼ registry
   [L3 Policy chain] → [L2 Scenario] → [L1 Resolver] → [L0 Kernel]
                                                            │
                                                            ▼
                                             ┌──────────────────┐
                                             │ Ports (Hexagonal)│
                                             └┬────┬────┬───────┘
                                 StateStore   │Clock│Presenter
                                              ▼    ▼    ▼
                                           DataStore / NotificationMgr
                                           (adapter default)
```

---

## LAYER-007 — Testing per layer

Mỗi layer có test suite riêng (xem `testing-kit-rules.md`):

| Layer | Test type | Fake dùng |
|---|---|---|
| L0 Kernel | Unit test pure | `FakeClock`, `InMemoryStore`, `RecordingPresenter` |
| L1 Resolver | Unit test resolver logic | `FakeResolveContext` |
| L2 Composition | Unit test state machine | `FakeKernel` (stub schedule/cancel) |
| L3 Policy | Unit test interceptor chain | `FakeInterceptorChain` |
| L4 Integration | Integration test với adapter thật | Robolectric cho Android class |
| Cross-layer | E2E flow smoke | `TestReminderKit` build từ `:lib-testing` |

**Rule**: layer N không được test instrumented class của layer M (N ≠ M). Mỗi test file isolate layer.

---

## LAYER-008 — Backward compat strategy per layer

Stability tier khác nhau theo layer:

| Layer | Stability | Lý do |
|---|---|---|
| L0 Kernel | **Strict freeze sau 1.0** | Expand = cascade mọi layer |
| L1 Resolver registry | Strict freeze (SPI stable) | Consumer custom resolver phụ thuộc |
| L1 Built-in resolver | Flexible (add resolver OK, remove = deprecate) | — |
| L2 Composition | Flexible với deprecation window | Scenario shape có thể evolve |
| L3 Policy | Flexible | Interceptor SPI stable, built-in interceptor có thể add/deprecate |
| L4 Integration | Loose (per-adapter version) | Adapter follow 3rd-party API version |

**Rule**: BCV check áp dụng cho L0 + mọi SPI (bất kể layer). L4 adapter module có BCV check riêng.

---

## Pair với

- `sdk-mindset.md` — 3 guarantee + anti-pattern
- `pattern-catalog.md` — pattern canonical mỗi layer dùng
- `essentials.md §LIB-SCOPE` — boundary rule
- `testing-kit-rules.md` — test per layer
- `brainstorm-process.md` §Step 6 — layer decomposition workflow
- Agent: `agents/library-architect.md` §Phase 0
- Workflow: `agents/workflows/library-flow.md` §Stage 5
