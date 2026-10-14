---
name: android-debug
description: Diagnose Android bugs — reproduce, isolate, prove root cause before fixing. Trigger khi task fix bug, crash, ANR, memory leak, flaky test, hoặc investigate unexpected behavior.
priority: P2
---

# Skill: android-debug

Procedure chi tiết: `workflows/fix-bug.md`. Skill focus kỹ thuật Android/Kotlin specific.

## Trigger

- Crash report (Crashlytics, Play Console)
- ANR (Application Not Responding)
- Memory leak suspect (LeakCanary)
- Flaky test (fail không deterministic)
- UI jank / performance regression
- Compose recomposition excessive
- Coroutine zombie / cancellation leak
- Platform-specific behavior (iOS vs Android divergence trong CMP)

## Prerequisites

1. `.harness/workflows/fix-bug.md` — 5-stage orchestration
2. `.harness/knowledge/coroutines/essentials.md` cho cancellation/scope issue
3. `.harness/knowledge/compose/essentials.md` cho recomposition/stability

## Debug techniques

### D-01 — Reproduce deterministic

Trước mọi fix, bug phải repro được. Rules:

- Minimal steps < 10 interactions
- Same env (device model, OS version, build variant)
- Record repro trong plan/report
- Nếu không repro → stop, không fix guess

Tools:
- Device emulator snapshot (consistent state)
- Instrumented test với fixed input
- Screen recording cho visual bug
- `adb` for state manipulation

### D-02 — Isolate scope

Narrow bug location:

```bash
# Git bisect nếu có baseline xanh
git bisect start
git bisect bad HEAD
git bisect good <known-good-commit>
# Follow prompts, test each middle commit
```

- Comment out code để shrink surface
- Reduce input (binary search)
- Try different device/OS → narrow platform-specific
- Clear cache/data → separate state vs code bug

### D-03 — Logging + breakpoint

```kotlin
Log.d("BookVM", "loadBook id=$id, state=${state.value}")
```

**Rules**:
- Dùng tag ngắn stable (`"BookVM"` không `"BookDetailViewModel.kt - loadBook function"`)
- Log sau fix → **remove** (hoặc downgrade `Log.v` + wrap `BuildConfig.DEBUG`)
- Không log PII (token, email, phone)
- Timber production vs stdout debug: optional, phụ thuộc convention project

Breakpoint:
- IntelliJ/Android Studio debugger cho stepping
- Conditional breakpoint cho reproduce specific state
- Watch expression cho state value monitoring

### D-04 — Prove root cause

Không fix mù. Mỗi fix cần evidence:

- Bug-first test fail → sau fix PASS
- Log trace path showing wrong state
- Debugger step confirming hypothesis
- Classify (xem `workflows/fix-bug.md §Stage 3`):
  - **Logic**: wrong state transition, missing branch
  - **Concurrency**: race, cancellation leak, zombie coroutine
  - **State**: lost on config change, incorrect SavedStateHandle
  - **Compose**: recomposition skip, unstable param
  - **Data**: null leak, mapper bug, DTO shape change
  - **Platform**: lifecycle event ordering, permission edge

### D-05 — Platform-specific debug

#### Android

- `adb logcat` → view runtime log
- `adb shell dumpsys meminfo <package>` → memory
- `adb shell dumpsys gfxinfo <package>` → frame rendering
- Android Studio Profiler: CPU, memory, network, energy

#### iOS (CMP)

- Xcode Console → runtime log
- Instruments → Time Profiler, Allocations, Network
- Simulator vs Device (behavior khác)

#### Common

- Firebase Crashlytics → prod crash
- Firebase Performance → startup time, trace
- Firebase Analytics → event flow

### D-06 — Common bug patterns

| Symptom | Likely cause | Technique |
|---|---|---|
| UI not update after state change | Not observing with lifecycle | `collectAsStateWithLifecycle()` |
| State lost on rotation | Not using `SavedStateHandle` | Nav args qua `SavedStateHandle` |
| Coroutine không cancel | `GlobalScope.launch` hoặc detached scope | Dùng `viewModelScope` |
| Flow emit duplicate | Missing `distinctUntilChanged()` | Add operator |
| Compose recompose excessive | Unstable lambda/data class | Use `remember`, method reference |
| Memory leak | Static ref to Context/View | Weak ref, lifecycle-aware |
| ANR | Blocking main thread > 5s | Move to IO dispatcher |
| Crash on nav | Route not registered | Verify `AppNavHost` composable mapping |
| 401 after sign in | Token refresh race | Serialize refresh với `Mutex` |
| App crash on resume | Config change recreate killed state | SavedStateHandle restore |

### D-07 — Coroutine debugging

Enable debug mode:

```kotlin
// Debug build only
System.setProperty("kotlinx.coroutines.debug", "on")
```

Dumps coroutine stack trace với name:

```kotlin
viewModelScope.launch(CoroutineName("loadBook")) {
    ...
}
```

Khi crash → stack trace show "loadBook" context.

### D-08 — Compose recomposition debugging

```kotlin
@Composable
fun BookRow(book: Book) {
    SideEffect {
        Log.d("Recompose", "BookRow ${book.id}")
    }
    // ...
}
```

Count recompose per screen. Nếu > expected → investigate stability.

Compose compiler report:
```
./gradlew assembleDebug -PenableComposeCompilerReports=true
```

Sinh file `*-stability.txt` show class stability. Unstable → wrap `@Stable` hoặc convert sang data class immutable.

## Failure classifier (R-04)

Trước khi start fix, **classify failure**. Classification wrong → wrong fix path.

### Categories

| Category | Pattern | Who fixes | Example |
|---|---|---|---|
| **build** | Compile error, dep conflict, Gradle config | Implementer | Missing import, type mismatch, Gradle sync fail |
| **code** | Logic bug, NPE, race, wrong state | Implementer + Test Engineer | Null leak, concurrency, UI not update |
| **test** | Flaky, wrong assertion, test setup bug | Test Engineer + Reviewer | `assertEquals("expected", actualDifferent)`, flaky timing |
| **device** | ADB offline, emulator timeout, device busy | **User (infra)** | `adb: device not found`, device lock conflict |
| **infra** | OOM, disk full, network timeout CI | **User (infra)** | Gradle OOM, no space left, DNS fail |
| **env** | JDK/Kotlin/SDK version mismatch | **User (setup)** | `Unsupported Kotlin version`, SDK path missing |

### Fingerprint

Hash cho detect "same error loop" (xem `knowledge/auto-fix/essentials.md`):

```python
fingerprint = sha1(f"{task_name}:{exception_class}:{stack_top_3_frames_normalized}")
```

Normalize = strip line number, keep class + method name.

### Routing matrix

```yaml
# Routing per classification
build:
  retry_tier: implementer
  retry_strategy: fix_immediate_error → check_surrounding_context
  max_attempts: 3
code:
  retry_tier: implementer + test_engineer
  retry_strategy: fix_cause → add_regression_test
  max_attempts: 3
test:
  retry_tier: test_engineer + reviewer
  retry_strategy: REVIEW_ASSERTION_CORRECTNESS_FIRST (not "make it pass")
  max_attempts: 2
device:
  retry_tier: NONE                  # Not code fix
  escalate: user
  pattern: "Please restart ADB / reconnect device"
infra:
  retry_tier: NONE
  escalate: user
  pattern: "Clean disk / scale VPS / check network"
env:
  retry_tier: NONE
  escalate: user
  pattern: "Update toolchain to <version>"
```

### Classification procedure

1. Read error message + stack trace + context
2. Match pattern:
   - "cannot find symbol" / "unresolved reference" → **build**
   - "NullPointerException" / "IllegalStateException" / "race" / "deadlock" → **code**
   - Test fail với clear expected/actual → **test**
   - `adb: no devices` / "emulator timeout" → **device**
   - "OutOfMemoryError" / "No space left" / connection timeout → **infra**
   - "Unsupported Java version" / "SDK not found" → **env**
3. Compute fingerprint
4. Check `plans/<date>/fix-attempts.yaml`:
   - If fingerprint lặp without progress → ESCALATE
   - If `current_attempts >= max_fix_attempts` → ESCALATE
5. Else apply classification routing + append attempt

### Example classification

```
STACK:
java.lang.NullPointerException: Attempt to invoke virtual method 'getUser' on null
	at BookDetailViewModel.loadBook(BookDetailViewModel.kt:42)
	at BookDetailViewModel$loadBook$1.invokeSuspend(BookDetailViewModel.kt:40)

CLASSIFY: code (NPE, business logic layer)
FINGERPRINT: sha1("BookDetailViewModel.loadBook:NullPointerException:...")
ROUTE: implementer (fix cause: null check or non-null contract) + test-engineer (regression test)
```

```
STACK:
Execution failed for task ':composeApp:compileDebugKotlin'.
> Compilation error. See log for more details.
e: file:///.../LoginScreen.kt:15 unresolved reference: LoginState

CLASSIFY: build (compile error, missing import or new file not visible)
ROUTE: implementer (add import or create missing file)
```

```
STACK:
adb: no devices/emulators found

CLASSIFY: device
ROUTE: ESCALATE user — "Please connect device or start emulator"
```



### Fix tại cause hay tại symptom?

**Luôn fix cause**:
- UI crash do null → fix data layer non-null contract (không chỉ null-check UI)
- Race → add proper synchronization (không retry)
- Memory leak → fix reference, không giảm Heap size

**Exception**: tạm workaround ở symptom khi cause fix tốn > 1 ngày + có user impact critical → thêm comment + issue link.

### Khi bug không repro được

1. Collect more info từ user (device, steps, timing)
2. Add defensive logging + release build
3. Monitor Crashlytics / telemetry
4. **Không fix guess** — document "cannot reproduce" trạng thái

### Khi suspect flaky test

1. Run 10 lần local → confirm flakiness
2. Isolate: timing dependency? Shared state? Thread?
3. Fix cause (không retry):
   - Timing: dùng `advanceTimeBy` thay `delay()` thật
   - Shared state: fresh fake per test
   - Thread: inject dispatcher

### Khi bug cross-module

- Reproduce ở integration level trước
- Isolate per module via disable + mock
- Fix tại module gốc, không spread patch

## Common mistakes

| Mistake | Fix |
|---|---|
| Fix bằng try/catch nuốt exception | Fix cause, không mask |
| Null-check UI khi data layer phải non-null | Fix contract data, không UI defense |
| Disable test đang fail | Fix hoặc delete; không disable |
| "Temporary" fix không issue link | Add TODO(#issue) + plan proper fix |
| Fix multiple bugs 1 PR | Reviewer khó verify, split |
| Add defensive null-check "để chắc" | Trust type system; non-null = non-null |
| Hard-reset state khi UI edge case | Fix state transition logic đúng |
| Add retry cho logic bug | Retry chỉ cho transient (network), không cho logic |

## Required policies

- Workflow `fix-bug.md` orchestration
- CORO-004 preserve cancellation
- KOT-002 null safety
- KOT-009 exception specificity
- Không `@Ignore` test không issue link

## Output contract

- Bug repro deterministic + minimal steps
- Root cause classified (logic/concurrency/state/compose/data/platform)
- Evidence stated (log/test/debugger output)
- Fix tại cause level
- Bug-first test PASS sau fix
- Regression test added
- Related features không regression

## Anti-patterns bị cấm

- Fix bằng try/catch mask
- Null-check UI thay vì fix data layer
- Add retry cho logic bug
- "Should work" claim không có evidence
- Random fix thử-sai không hypothesis
- Fix + refactor + feature trong 1 PR
