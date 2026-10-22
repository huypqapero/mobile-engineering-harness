# SDK Pattern Catalog

Design pattern canonical cho SDK publish artifact. Mỗi SDK component phải map tới ≥ 1 pattern trong file này. Pattern không có trong catalog → **không được dùng** cho public API (consumer-facing). Internal có thể dùng pattern khác tự do.

Consume bởi: `library-architect` (Stage 3 Contract design), `architect` (Stage 5 module layout), `coder` (Stage 6 impl), `reviewer` (Stage 7 API diff).

---

## Rule áp dụng catalog

1. **Mỗi public component phải chú thích pattern** trong `library-contract.md §Public API surface`:
   ```markdown
   - `ReminderScheduler` (interface) — Facade, Ref: OkHttpClient
   - `TriggerResolver<T>` (SPI) — Strategy + Registry, Ref: Retrofit CallAdapter
   - `FireInterceptor` (SPI) — Chain of Responsibility, Ref: OkHttp Interceptor
   ```

2. **Pattern không trong catalog → không approve**. Nếu cần pattern mới, raise với Library Architect + add vào catalog qua PR, không ship ad-hoc.

3. **1 component có thể combine 2-3 pattern** (ví dụ Facade + Builder + Component Registry) nhưng phải list cả 3, không giấu.

---

## PAT-ENTRY — Entry point & lifecycle

### PAT-ENTRY-001 — Facade
**Dùng cho**: Entry class duy nhất của SDK (vd `ReminderKit`, `MyLib`).
**Shape**: 1 public class hide N internal class, consumer `import` chỉ chạm 1 package.
**Ref**: OkHttp (`OkHttpClient`), Glide (`Glide`), Sentry (`Hub`), WorkManager (`WorkManager.getInstance()`).
**Rule**:
- Public API bề mặt < 15 symbol trên Facade.
- Internal class không được `public`.
- Consumer không bao giờ `import` package `internal`/`impl`.

### PAT-ENTRY-002 — Builder (Kotlin DSL optional)
**Dùng cho**: Config object immutable, construct Facade.
**Shape**: `MyLib.Builder().setX(a).setY(b).build()` hoặc Kotlin DSL `MyLib.create { x = a; y = b }`.
**Ref**: OkHttp `.Builder()`, Retrofit `.Builder()`, Firebase `FirebaseOptions.Builder()`.
**Rule**:
- Builder không mutate sau `build()`.
- Default sensible, required field explicit tên trong error message khi miss.
- Kotlin DSL preferred cho discoverability qua IDE.

### PAT-ENTRY-003 — Component Registry (Firebase pattern)
**Dùng cho**: SDK đa feature cần lazy init, feature A fail không chết feature B.
**Shape**: Core module quản lifecycle, feature module register vào core qua `ComponentContainer`.
**Ref**: Firebase SDK (`ComponentContainer`), Datadog SDK (`Feature`), Sentry SDK (`Integration`).
**Rule**:
- Dùng khi SDK ≥ 3 feature độc lập.
- Mỗi feature có interface + impl + lifecycle hook (`onInitialize`, `onShutdown`).
- Core không biết feature cụ thể, chỉ biết interface.

### PAT-ENTRY-004 — Named Instance / Multi-Instance
**Dùng cho**: Consumer cần ≥ 2 instance SDK cùng process (vd work profile vs personal, dev vs prod endpoint).
**Shape**: `MyLib.get("default")` + `MyLib.get("profileA")` return instance khác nhau với config khác.
**Ref**: FirebaseApp.getInstance(name), OkHttp instance per module.
**Rule**:
- Cấm `object Singleton` cứng khi SDK có khả năng cần multi-instance.
- Instance name = string key, caller tự quản.

---

## PAT-CORE — Core domain

### PAT-CORE-001 — Hexagonal / Ports & Adapters
**Dùng cho**: Core business logic của SDK.
**Shape**:
```
┌────────────────────────┐
│  Core logic (pure)     │
│  không biết I/O        │
└──┬────┬────┬───────────┘
   │ Port Port Port
   ▼    ▼    ▼
Adapter Adapter Adapter
(DataStore) (Clock) (Notification)
```
**Ref**: Clean Architecture (Robert Martin), Spring Hexagonal.
**Rule**:
- Core module `commonMain` pure Kotlin, không import Android/iOS SDK.
- Mọi I/O qua port (interface).
- Mỗi port có default adapter + consumer override được.

### PAT-CORE-002 — Command
**Dùng cho**: Request là object (`ScheduleJob`, `CancelJob`), dễ queue, log, replay.
**Shape**: `interface Command<R> { fun execute(ctx): R }` hoặc data class pure.
**Ref**: WorkManager `Request`, RxJava Scheduler command.
**Rule**:
- Command là value object (immutable), có `id` để trace.
- Command không phụ thuộc executor concrete.

### PAT-CORE-003 — Repository + Unit of Work
**Dùng cho**: State persistence (DataStore, Room, in-memory).
**Shape**: `interface StateStore { suspend fun save(x); suspend fun load(id) }` + `UnitOfWork` cho batch transactional.
**Ref**: Jetpack Room, Spring Data Repository.
**Rule**:
- Repository interface ở core, impl ở adapter module.
- Default impl ship kèm (DataStore cho Android), consumer swap sang Room/Realm được.

### PAT-CORE-004 — Value Object (Data class immutable)
**Dùng cho**: ID, enum lite, config value.
**Shape**: `data class ReminderId(val value: String)` + inline value class nếu primitive wrap.
**Ref**: Kotlin inline class, DDD Value Object.
**Rule**:
- Equality by field, không identity.
- Immutable (val only).
- Nếu public → freeze field hoặc chuyển interface.

---

## PAT-SPI — Extension points (quan trọng nhất)

### PAT-SPI-001 — Strategy + Registry
**Dùng cho**: Mở rộng kiểu/thuật toán runtime (`TriggerResolver<T>`, `RetryPolicy`, `CacheStrategy`).
**Shape**:
```kotlin
interface TypeResolver<T : Type> {
    fun resolve(input: T, ctx: Context): Result
}

class ResolverRegistry {
    fun <T : Type> register(cls: KClass<T>, resolver: TypeResolver<T>)
    fun <T : Type> resolve(input: T): Result
}
```
**Ref**: Retrofit `CallAdapter.Factory` + `Converter.Factory`, Glide `ComponentRegistry`.
**Rule**:
- Registry explicit, không ServiceLoader reflection.
- Consumer `.register(MyType::class, MyResolver())` tường minh.
- Built-in resolver ship cùng SDK; consumer có thể override.

### PAT-SPI-002 — Chain of Responsibility (Interceptor)
**Dùng cho**: Pipeline xử lý trước khi commit action (fire notification, send request, dispatch event).
**Shape**:
```kotlin
interface Interceptor {
    val order: Int
    suspend fun intercept(chain: Chain): Result
}

interface Chain {
    val request: Request
    suspend fun proceed(request: Request): Result
}
```
**Ref**: OkHttp Interceptor, Retrofit, ASP.NET Middleware.
**Rule**:
- Order explicit (int), không rely vào insertion order.
- Mỗi interceptor có short-circuit: trả `Result.Blocked` không `proceed`.
- Default chain ship kèm, consumer `.addInterceptor(custom)`.

### PAT-SPI-003 — Observer qua Flow (Pub-Sub)
**Dùng cho**: Lifecycle event, state change (`FireEvent`, `AuthStateChanged`).
**Shape**:
```kotlin
val events: SharedFlow<ReminderEvent>
val state: StateFlow<ReminderState>

sealed interface ReminderEvent {
    data class Fired(...) : ReminderEvent
    data class Blocked(...) : ReminderEvent
}
```
**Ref**: Kotlin Coroutines Flow, RxJava Observable, LiveData.
**Rule**:
- Hot (`StateFlow`/`SharedFlow`) cho state hiện tại; cold `Flow` cho stream pull.
- Cấm `setListener(cb)` callback style (xem `sdk-mindset.md §SDK-004`).
- Replay cache có giới hạn (vd 10 event gần nhất).

### PAT-SPI-004 — Specification + Composite (Rule)
**Dùng cho**: Composable predicate (`Condition.and(a, b)`, `Condition.not(c)`).
**Shape**:
```kotlin
fun interface Condition {
    suspend fun evaluate(ctx: Context): Boolean
}

object Conditions {
    fun allOf(vararg: Condition): Condition
    fun anyOf(vararg: Condition): Condition
    fun not(c: Condition): Condition
}
```
**Ref**: DDD Specification pattern, Spring Data Specification.
**Rule**:
- Primitive condition ship built-in, consumer compose qua `allOf/anyOf/not`.
- Consumer không cần class mới cho rule phổ biến, chỉ compose.

### PAT-SPI-005 — Port (Dependency Inversion)
**Dùng cho**: I/O boundary (`Clock`, `Logger`, `NotificationPresenter`, `StateStore`, `PermissionChecker`).
**Shape**: Interface với default impl + Null Object (xem PAT-DEFAULT).
**Ref**: Hexagonal Architecture, Dagger `@Binds`.
**Rule**:
- Mọi side-effect qua port.
- Default impl ship cùng SDK trong module `:core-defaults` hoặc inline.
- Consumer override via `.setPort(...)` trên Builder.

### PAT-SPI-006 — Snapshot / Memento lite (Custom State Provider)
**Dùng cho**: SDK đọc state consumer tại thời điểm eval (vd Condition cần biết "user có premium không").
**Shape**:
```kotlin
interface CustomStateProvider {
    suspend fun snapshot(): Map<String, Any?>
}
```
**Ref**: Memento pattern, React Context.
**Rule**:
- Snapshot immutable, không reference live object.
- Consumer bơm state qua port, SDK không truy cập business state trực tiếp.

---

## PAT-EVENT — Event & observability

### PAT-EVENT-001 — Observer / Pub-Sub (Flow)
Xem PAT-SPI-003.

### PAT-EVENT-002 — Event Sourcing lite
**Dùng cho**: History log (`FireHistory`, `AuditLog`) cho analytics replay, debug.
**Shape**: Append-only log + bounded replay (vd last 100 event).
**Ref**: Event Sourcing (Fowler), Kafka log compaction.
**Rule**:
- Log size bounded (config `historyLimit`).
- Replay API cho consumer late-attach analytics.
- Không là full event-sourcing (không rebuild state từ event).

### PAT-EVENT-003 — State Machine (Sealed)
**Dùng cho**: Lifecycle state có transition rõ (`ScenarioState: Pending → Active → Completed`).
**Shape**: `sealed interface State` + transition function pure.
**Ref**: Statemachine Compose, Kotlin sealed.
**Rule**:
- Transition compile-time safe qua exhaustive `when`.
- Invalid transition = compile error hoặc throw tại runtime với log rõ.

### PAT-EVENT-004 — Decorator cho Logging/Metric
**Dùng cho**: Wrap base impl với cross-cutting (log, timing, metric).
**Shape**: `LoggingDispatcher(delegate: Dispatcher) : Dispatcher`.
**Ref**: OkHttp `LoggingInterceptor`, Guice AOP.
**Rule**:
- Decorator opt-in qua Builder flag hoặc `.withLogging()`.
- Cost 0 khi off (decorator không add).

---

## PAT-DEFAULT — Default & fallback

### PAT-DEFAULT-001 — Null Object
**Dùng cho**: Default impl cho port khi consumer không override (`NoopLogger`, `NoopAnalytics`).
**Shape**: Impl không-op, không throw, không log.
**Ref**: Null Object Pattern (Fowler).
**Rule**:
- Ship cùng SDK core.
- Default trong Builder: `logger: Logger = NoopLogger`.
- Consumer không set = không crash + không spam log.

### PAT-DEFAULT-002 — Policy Object
**Dùng cho**: Configurable retry/backoff/timeout (`RetryPolicy`, `BackoffPolicy`).
**Shape**: `data class RetryPolicy(val max: Int, val backoff: Backoff)` + preset: `RetryPolicy.exponential(5)`, `RetryPolicy.none`.
**Ref**: Spring `RetryTemplate`, Resilience4j.
**Rule**:
- Preset ship kèm cho case phổ biến.
- Consumer custom qua `RetryPolicy(...)` constructor.

### PAT-DEFAULT-003 — Decorator fallback
**Dùng cho**: Chain fallback khi primary fail (vd AlarmManager exact → WorkManager inexact).
**Shape**: `FallbackDispatcher(primary, secondary) : Dispatcher`.
**Ref**: Circuit Breaker, Hystrix fallback.
**Rule**:
- Fallback trigger explicit (exception type, permission denied).
- Metric emit khi fallback kích hoạt.

---

## PAT-CONFIG — Configuration

### PAT-CONFIG-001 — Builder + Immutable Config
Xem PAT-ENTRY-002.

### PAT-CONFIG-002 — Kotlin DSL
**Dùng cho**: Config nested (vd `MyLib.create { retry { max = 5; backoff = exponential } }`).
**Shape**: Receiver lambda + `@DslMarker`.
**Ref**: Ktor DSL, Gradle Kotlin DSL.
**Rule**:
- Mark `@DslMarker` tránh scope leak.
- IDE discoverable qua autocomplete.

### PAT-CONFIG-003 — Feature Flag (Toggle)
**Dùng cho**: Feature chưa stable, feature optional nặng dep.
**Shape**: `config.enableCron: Boolean = false`.
**Ref**: LaunchDarkly, OpenFeature.
**Rule**:
- Default = tắt.
- Feature cần dep nặng (vd Cron parser) tách module optional, bật flag = add dep gradle.

---

## PAT-ANTI — Anti-pattern cấm (nhắc lại từ sdk-mindset.md)

Pattern **không được dùng** cho public API SDK (xem chi tiết `sdk-mindset.md §SDK-004`):

| Anti-pattern | Thay bằng pattern trong catalog |
|---|---|
| Singleton cứng `object Lib` | PAT-ENTRY-002 Builder + PAT-ENTRY-004 Named Instance |
| Service Locator global | PAT-SPI-005 Port + DI consumer |
| Inheritance extension (`abstract class`) | PAT-SPI-001 Strategy + PAT-DEFAULT-001 Null Object |
| God Config class | PAT-CONFIG-002 Kotlin DSL nested |
| `setListener(cb)` callback | PAT-SPI-003 Observer qua Flow |
| Reflection auto-discovery | PAT-SPI-001 Strategy explicit `.register()` |
| `data class` public không freeze | PAT-CORE-004 Value Object + interface + factory |

---

## SPI Contract Rules

Mọi SPI (PAT-SPI-001..006) phải tuân:

1. **Stability tier**: mỗi SPI tag `@Stable` / `@Experimental` / `@Internal`.
2. **BCV coverage**: SPI nằm trong public API dump, BCV gate CI.
3. **Versioning**: SPI breaking change = MAJOR bump + RFC + consumer sign-off.
4. **Default impl ship kèm**: SPI không được chỉ expose interface, phải có ≥ 1 default (built-in resolver, default interceptor).
5. **Documentation**: KDoc + `@sample` link vào `samples/` module.
6. **TestingKit coverage**: mỗi SPI có fake/test-double trong `:lib-testing` (xem `testing-kit-rules.md`).

---

## Pattern selection by SDK type (nhắc từ essentials)

Pattern bắt buộc theo loại SDK (gộp từ `essentials.md §Pattern selection matrix`):

| SDK type | Pattern bắt buộc |
|---|---|
| Network client | PAT-SPI-002 Interceptor, PAT-SPI-005 Port (HttpClient), PAT-DEFAULT-002 RetryPolicy |
| Cache | PAT-SPI-001 Strategy (eviction), PAT-SPI-003 Observer (invalidate), PAT-EVENT-004 Decorator |
| Auth / session | PAT-SPI-003 Observer (`StateFlow<AuthState>`), PAT-SPI-001 Strategy (token refresh), PAT-ENTRY-001 Facade |
| Analytics | PAT-SPI-005 Adapter (Firebase wrap), PAT-DEFAULT-001 Null Object, PAT-SPI-003 Observer (debug stream) |
| Storage / persistence | PAT-SPI-001 Strategy (serializer, migration), PAT-EVENT-004 Decorator (encryption), PAT-ENTRY-001 Facade |
| Logging | PAT-SPI-002 Chain (sink chain), PAT-SPI-001 Strategy (format), PAT-EVENT-004 Decorator (filter) |
| Payment / billing | PAT-ENTRY-001 Facade, PAT-SPI-003 Observer (`Flow<PaymentStatus>`), PAT-SPI-001 Strategy (provider) |
| UI / Compose | Slot API, `@Immutable`/`@Stable`, Composition locals, PAT-ENTRY-001 Facade |
| Reminder / scheduler | PAT-SPI-001 TriggerResolver, PAT-SPI-002 FireInterceptor, PAT-SPI-003 Observer, PAT-SPI-004 Condition Specification |
| Util / pure logic | Minimal: PAT-ENTRY-001 Facade + sealed ADT cho error |

---

## Pair với

- `sdk-mindset.md` — triết lý SDK + anti-pattern cấm
- `layered-architecture.md` — 5-layer apply pattern ở đâu
- `essentials.md §LIB-PATTERN` — rule pattern per lib type
- `testing-kit-rules.md` — mỗi SPI phải có TestingKit coverage
- `brainstorm-process.md` — Phase 0 trước apply pattern
