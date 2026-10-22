# TestingKit Rules

Rule bắt buộc cho artifact `:lib-testing` ship kèm mọi SDK publish. Không có TestingKit → không được release 1.0.

Consume bởi: `library-architect` (Contract có TestingKit section), `coder` (impl TestingKit cùng SDK), `qa` (verify TestingKit coverage), consumer (import `testImplementation`).

---

## TEST-001 — Tại sao mandatory

Lib publish không có TestingKit buộc consumer phải:
- Tự mock mọi port (Logger, Clock, Analytics, StateStore, Presenter) → brittle test.
- Reverse-engineer internal state qua reflection → bị R8 strip.
- Dùng Mockito/Mockk mock public interface → chậm + fragile.

Hệ quả: consumer giảm test coverage, bug lọt ra prod. **SDK cost → N consumer cost**.

TestingKit giải quyết:
- Ship fake impl cho mọi port (SDK biết rõ internal, viết fake đúng semantic).
- Ship test driver (`TestScheduler`, `TestClock`) cho time control.
- Ship assertion helper cho state verify.
- Consumer `testImplementation("mysdk-testing:1.0.0")` → tích hợp < 10 dòng.

---

## TEST-002 — Artifact shape

### Gradle module
```
my-sdk/
├── core/
├── scheduler/
├── scenario/
├── policy/
├── integration/
└── testing/              ← ARTIFACT :lib-testing
    ├── build.gradle.kts
    └── src/commonMain/kotlin/
        ├── fakes/
        │   ├── FakeClock.kt
        │   ├── InMemoryStateStore.kt
        │   ├── RecordingNotificationPresenter.kt
        │   ├── FakeAppOpenTracker.kt
        │   └── RecordingAnalytics.kt
        ├── drivers/
        │   ├── TestReminderKit.kt
        │   └── TestScheduler.kt
        └── asserts/
            └── ReminderAsserts.kt
```

### Gradle config
```kotlin
// testing/build.gradle.kts
plugins { kotlin("multiplatform"); id("maven-publish") }

kotlin {
    androidTarget()
    jvm()  // JVM target cho pure Kotlin test
    sourceSets {
        commonMain.dependencies {
            api(project(":core"))         // Fake impl port của core
            api(project(":scheduler"))    // Fake resolver context
            api("io.kotest:kotest-assertions-core:...")
        }
    }
}
```

### Maven artifact
```
com.myorg:my-sdk-testing:1.0.0
```

Consumer:
```kotlin
testImplementation("com.myorg:my-sdk-testing:1.0.0")
```

---

## TEST-003 — Thành phần bắt buộc

Mỗi SDK TestingKit phải có 4 nhóm:

### Group A: Fakes (port replacement)

Mỗi port trong SDK core (xem `pattern-catalog.md §PAT-SPI-005`) phải có fake:

| Port | Fake | Behavior |
|---|---|---|
| `Clock` | `FakeClock` | Manual advance: `fakeClock.advance(1.hour)` |
| `StateStore` | `InMemoryStateStore` | HashMap-backed, không persist disk |
| `Logger` | `RecordingLogger` | Capture log vào list, assert được |
| `Analytics` | `RecordingAnalytics` | Capture event vào list |
| `NotificationPresenter` | `RecordingNotificationPresenter` | Capture `fire()` call, không gọi `NotificationManager` thật |
| `PermissionChecker` | `FakePermissionChecker` | Mutable state cho test grant/deny |
| `AppOpenTracker` | `FakeAppOpenTracker` | Mutable `lastAppOpen: Instant` cho test |

**Rule**:
- Fake impl semantic đúng SDK (không chỉ no-op).
- Fake có API observe (`recordedCalls: List<Call>`) cho assertion.
- Fake thread-safe nếu port concurrent.

### Group B: Test drivers

Driver cao level cho consumer test SDK flow:

```kotlin
class TestReminderKit(
    val clock: FakeClock = FakeClock(Instant.parse("2026-01-01T00:00:00Z")),
    val store: InMemoryStateStore = InMemoryStateStore(),
    val presenter: RecordingNotificationPresenter = RecordingNotificationPresenter(),
    val listener: RecordingAnalytics = RecordingAnalytics()
) {
    val scheduler: ReminderScheduler  // built with fakes injected

    fun advanceTime(duration: Duration) {
        clock.advance(duration)
        // Drive internal scheduler tick
    }

    fun firedReminders(): List<FiredReminder> = presenter.fired
    fun blockedReminders(): List<BlockedReminder> = presenter.blocked
}
```

**Rule**:
- Driver pre-wire mọi fake với default sensible.
- `advanceTime()` drive internal clock + flush worker queue → mimic WorkManager tick.
- Consumer dùng < 10 dòng setup:
  ```kotlin
  val kit = TestReminderKit()
  kit.scheduler.schedule(reminder(at = "2026-01-01T09:00Z"))
  kit.advanceTime(10.hours)
  assertThat(kit.firedReminders()).hasSize(1)
  ```

### Group C: Assertion helpers

```kotlin
object ReminderAsserts {
    fun assertFired(presenter: RecordingNotificationPresenter, id: String)
    fun assertBlocked(presenter: RecordingNotificationPresenter, id: String, reason: String)
    fun assertFireOrder(presenter: RecordingNotificationPresenter, vararg ids: String)
    fun assertNoFire(presenter: RecordingNotificationPresenter, within: Duration)
}
```

**Rule**:
- Message assertion phải rõ (khi fail trả `expected X but got Y`).
- Dùng Kotest/AssertK/Truth → consumer có thể combine với assertion library riêng.

### Group D: Builder helper (reduce boilerplate)

```kotlin
fun reminder(
    id: String = "test-${randomId()}",
    at: String = "2026-01-01T09:00:00Z",
    payload: NotificationPayload = NotificationPayload.default()
): Reminder = Reminder(id, Trigger.At(Instant.parse(at)), payload = payload)

fun scenario(
    id: String = "test-scenario",
    priority: Int = 10,
    reminders: List<Reminder> = listOf(reminder())
): Scenario = Scenario(id, priority, reminders)
```

**Rule**: Builder helper default sensible, consumer override field cần test.

---

## TEST-004 — Dependencies rule

TestingKit module dependency policy:

| Dep | Scope | Lý do |
|---|---|---|
| `project(":core")` + `project(":scheduler")` + ... | `api` | Fake impl SDK port, consumer import type từ TestingKit |
| `kotlinx-coroutines-test` | `api` | TestDispatcher cho time control |
| `kotest-assertions-core` HOẶC `assertk` HOẶC `truth` | `api` | Assertion helper (chọn 1, document rõ) |
| `org.robolectric:robolectric` | `implementation` (optional target androidMain) | Khi fake cần Android context (hiếm) |
| Mockito/Mockk | **CẤM** | TestingKit cung cấp fake tay viết, không bị force consumer dùng mock framework |

**Rule**: TestingKit không depend production dep nặng (Firebase, Retrofit, OkHttp). Mock HTTP qua `MockEngine` của Ktor hoặc tự fake.

---

## TEST-005 — Coverage requirement

TestingKit coverage phải ≥ các mục dưới:

| Component SDK | TestingKit coverage |
|---|---|
| Mọi port L0 | Fake impl ship |
| Mọi SPI (TriggerResolver, FireInterceptor, Listener) | FakeContext để test custom plugin |
| Mọi primary flow Facade | Driver API (vd `TestReminderKit`) |
| State machine (ScenarioState) | Assertion helper (`assertState(...)`) |
| Flow emission | `TestFlowCollector` để assert sequence |

**Rule**: public symbol SDK có N → TestingKit coverage ≥ 80% N (mỗi public component dùng được trong test).

---

## TEST-006 — Self-test

TestingKit module **phải có test riêng** (meta-test):

```kotlin
// testing/src/commonTest/kotlin/
class FakeClockTest {
    @Test fun advance_moves_time_forward() { ... }
}

class TestReminderKitTest {
    @Test fun default_setup_fires_scheduled_reminder() { ... }
    @Test fun advance_time_triggers_fire() { ... }
}
```

**Rule**:
- Mỗi fake có test unit riêng verify semantic.
- Mỗi driver có test smoke verify integration.
- CI run `./gradlew :testing:test` song song với SDK test.

---

## TEST-007 — API stability

TestingKit API stability tier:

| Component | Stability |
|---|---|
| Fake impl class name | **Strict freeze** sau 1.0 (consumer import name) |
| Fake behavior (semantic) | **Strict freeze** - không được change silently |
| Driver API (`TestReminderKit`) | **Strict freeze** - method signature stable |
| Builder helper (`reminder()`) | Flexible với default change (nhưng add param = default = compat) |
| Internal helper (private) | Free change |

**Rule**: BCV gate apply cho `:testing` module như core. Breaking testing API = MAJOR bump SDK.

---

## TEST-008 — Documentation

TestingKit phải có:

### README section trong SDK README
```markdown
## Testing

Add TestingKit cho test code consumer:

```kotlin
testImplementation("com.myorg:my-sdk-testing:1.0.0")
```

Quickstart:
```kotlin
val kit = TestReminderKit()
kit.scheduler.schedule(reminder(id = "test", at = "2026-01-01T09:00Z"))
kit.advanceTime(10.hours)
assertFired(kit.presenter, "test")
```
```

### KDoc trên mọi public fake/driver
```kotlin
/**
 * In-memory [Clock] cho test. Manual control thời gian qua [advance].
 *
 * @sample samples.FakeClockUsage
 */
class FakeClock(initial: Instant) : Clock { ... }
```

### Sample module
`samples/testing-sample/` chạy được, demo TestingKit cho 3-5 scenario phổ biến.

---

## TEST-009 — CI gate

CI pipeline SDK phải:

```yaml
- run: ./gradlew :testing:build
- run: ./gradlew :testing:test                 # TestingKit self-test
- run: ./gradlew :testing:apiCheck             # BCV cho testing module
- run: ./gradlew :samples:testing-sample:test  # Verify sample compile + run
```

Fail bất kỳ → block release.

---

## TEST-010 — Checklist Library Architect verify

Stage 3 Contract review check:

- [ ] TestingKit section có trong `library-contract.md`
- [ ] Fake liệt kê đủ cho mọi port L0
- [ ] Driver API design cho mỗi primary flow
- [ ] Assertion helper design
- [ ] Dependency policy TestingKit tuân TEST-004
- [ ] Stability tier TestingKit chốt (TEST-007)
- [ ] Sample module `testing-sample` planned

Thiếu bất kỳ → block Contract approve.

---

## TEST-011 — Anti-pattern TestingKit

| Anti-pattern | Thay bằng |
|---|---|
| TestingKit chỉ expose Mockito helper | Ship fake impl viết tay |
| Fake impl no-op (không semantic) | Fake impl mirror production semantic |
| Driver API phức tạp > 20 LoC setup | Driver pre-wire default, consumer override selective |
| TestingKit depend production dep nặng | Testing dep minimal (coroutines-test + 1 assertion lib) |
| TestingKit không có self-test | Bắt buộc meta-test |
| Breaking testing API không bump SDK major | BCV gate áp dụng testing module |

---

## Pair với

- `sdk-mindset.md` §SDK-002 — TestingKit là 1 phần Stability guarantee (consumer test không break)
- `pattern-catalog.md` §PAT-SPI-005 — Port design cho fake replacement
- `layered-architecture.md` §LAYER-007 — Testing per layer
- `essentials.md §LIB-TEST` — Testability rule
- `brainstorm-process.md` §Step 8-9 — SPI phải có TestingKit coverage plan
- Agent: `agents/library-architect.md` §TestingKit section
- Workflow: `agents/workflows/library-flow.md` §Stage 7b
