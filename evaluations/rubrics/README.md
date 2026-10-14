# Evaluation Rubrics

Shared scoring rubric cho eval scenarios. Dùng để consistent compare "no harness" vs "with harness" output.

Scenario-specific rubric inline trong `evaluations/templates/eXX-*.md`. Rubric chung dưới đây reusable.

## Score scale

| Score | Verdict | Criteria |
|---|---|---|
| **90-100** | VERIFIED | Blueprint-worthy; 0 BLOCKER, ≤ 1 HIGH |
| **75-89** | VERIFIED_WITH_LIMITATIONS | 0 BLOCKER; HIGH/MEDIUM clean, LOW acceptable |
| **60-74** | NEEDS_REWORK | ≥ 1 HIGH violation; architecture mostly ok |
| **40-59** | FAIL | ≥ 1 BLOCKER violation; needs significant rework |
| **< 40** | REJECT | Multiple BLOCKER; fundamental misunderstanding |

## Dimension weights (default)

Mỗi scenario có thể override weight, nhưng baseline:

| Dimension | Weight | What |
|---|---|---|
| **Architecture compliance** | 25% | ARCH-001..014, MOD-001..003 |
| **MVI correctness** | 20% | State/Intent/Effect split, mutable guard, nav as Effect |
| **Concurrency safety** | 15% | CORO-001..010 |
| **UI states coverage** | 10% | 5 state render (loading/empty/error/offline/success) nếu có remote |
| **Test quality** | 15% | Behavior-driven name, strong assertion, Fake-first, deterministic |
| **Code quality** | 10% | File < 400, naming, KOT-001..012 |
| **Simplicity (YAGNI)** | 5% | Không trivial abstraction, không gold-plating |

Total: 100%.

## Severity classification

| Severity | Example | Impact score |
|---|---|---|
| **BLOCKER** | ARCH-001 violation, `GlobalScope.launch`, `MutableStateFlow` public | -30 per occurrence |
| **HIGH** | `collectAsState()` không lifecycle, mapper dùng `!!`, missing isOffline branch | -10 per occurrence |
| **MEDIUM** | Hardcoded color/dimension, `assertNotNull` weak | -5 per occurrence |
| **LOW** | Naming suboptimal, comment missing | -2 per occurrence |

## Rubric: Architecture compliance

Checklist (tick → +item score):

- [ ] ARCH-001 `domain` thuần, no platform import — **BLOCKER if violated**
- [ ] ARCH-002 `presenter` không import `data.*` — **BLOCKER**
- [ ] ARCH-003 ViewModel chỉ UseCase hoặc Repository interface — **BLOCKER**
- [ ] ARCH-004 Repository impl extend `BaseRepository` — HIGH
- [ ] ARCH-005 Mapper là `object` + extension — HIGH
- [ ] ARCH-006 Feature package self-contained — HIGH
- [ ] ARCH-007 ViewModel extend `BaseViewModel` — **BLOCKER**
- [ ] ARCH-008 5 UI states coverage — HIGH
- [ ] ARCH-009 Nav route `@Serializable sealed` — HIGH
- [ ] ARCH-010 Platform SDK chỉ ở `data/{androidMain,iosMain}/` — **BLOCKER**
- [ ] ARCH-011 DI binding đúng lifecycle (`factory` vs `single`) — MEDIUM
- [ ] ARCH-012 File < 400 lines — MEDIUM
- [ ] ARCH-013 Null-safe mapping, no `!!` ngoài giải thích — HIGH
- [ ] ARCH-014 Mini-player persistent (product-specific) — HIGH

## Rubric: MVI correctness

- [ ] State immutable `data class` hoặc `sealed interface` — HIGH
- [ ] `MutableStateFlow` không expose public — **BLOCKER**
- [ ] `Channel<Effect>(BUFFERED)` + `.receiveAsFlow()` cho effect — HIGH
- [ ] Nav là Effect, không State — HIGH
- [ ] 1 Intent = 1 user action (không bundle) — MEDIUM
- [ ] Internal intent cho async result modeling (nếu applicable) — LOW
- [ ] State transition deterministic qua Intent — HIGH

## Rubric: Concurrency safety

- [ ] CORO-001 Scope rõ (viewModelScope / inject), no GlobalScope — **BLOCKER**
- [ ] CORO-002 Dispatcher inject qua interface — HIGH
- [ ] CORO-003 `supervisorScope` vs `coroutineScope` đúng purpose — MEDIUM
- [ ] CORO-004 Preserve `CancellationException` — **BLOCKER**
- [ ] CORO-005 StateFlow / Channel / Flow đúng chỗ — HIGH
- [ ] CORO-006 `collectAsStateWithLifecycle()` — HIGH
- [ ] CORO-007 `stateIn(WhileSubscribed)` cho shared Flow — MEDIUM
- [ ] CORO-008 Timeout + retry policy sensible — MEDIUM
- [ ] CORO-009 Thread-safe shared mutable state — HIGH
- [ ] CORO-010 Test with `runTest` + `TestDispatcher` — HIGH

## Rubric: UI states coverage

Only applicable khi screen có remote data:

- [ ] Loading state visible — HIGH
- [ ] Empty state visible — HIGH
- [ ] Error state visible — HIGH
- [ ] Offline state visible — HIGH
- [ ] Success state renders data — HIGH

## Rubric: Test quality

- [ ] Behavior-driven test name — MEDIUM
- [ ] Strong assertion (specific value) — HIGH
- [ ] Fake preferred over Mock — MEDIUM
- [ ] `runTest` + injected `TestDispatcher` — HIGH
- [ ] No real `delay()` — HIGH
- [ ] Edge case coverage: null, empty, error, cancellation — HIGH
- [ ] No `@Ignore` without issue link — HIGH
- [ ] Test runs < 500ms each — LOW

## Rubric: Code quality (KOT)

- [ ] KOT-001 Naming consistent (PascalCase/camelCase) — LOW
- [ ] KOT-002 No `!!` ngoài giải thích — HIGH
- [ ] KOT-003 Immutable `val` + `data class` — HIGH
- [ ] KOT-004 Visibility `internal` by default — MEDIUM
- [ ] KOT-005 Sealed types đúng purpose — MEDIUM
- [ ] KOT-009 Exception specificity — HIGH
- [ ] KOT-011 Resource string, no hardcode — MEDIUM
- [ ] File < 400 lines — MEDIUM

## Rubric: Simplicity (YAGNI)

- [ ] No trivial 1-1 UseCase — MEDIUM
- [ ] No interface 1 impl không test fake — LOW
- [ ] No dead code / unused param — LOW
- [ ] No gold-plating (logging, caching, retry ngoài spec) — MEDIUM

## Baseline vs harness comparison

Report format cho eval run:

```markdown
# Eval E0X Report — <scenario>

## Baseline (no harness)
Score: XX/100
Verdict: NEEDS_REWORK | FAIL | ...
Violations:
- BLOCKER: N
- HIGH: M
- MEDIUM: K
- LOW: L

Top issues:
1. ...
2. ...

## With harness
Score: YY/100
Verdict: VERIFIED | ...
Violations:
- BLOCKER: N'
- HIGH: M'
- ...

Top improvements:
1. ...
2. ...

## Delta
- Score: +XX points (relative +Y%)
- BLOCKER: -N
- HIGH: -M

Target: ≥ 30% improvement in Architecture + MVI dimensions.
```

## Rubric evolution

Khi phát hiện pattern đánh giá chưa cover:
1. Add check vào rubric
2. Bump version `rubrics/VERSION`
3. Re-run baseline với rubric mới (fairness)

## Reference

- `.harness/evaluations/templates/`
- `.harness/constitution/architecture-rules.md`
- `.harness/constitution/concurrency-rules.md`
- `.harness/constitution/kotlin-conventions.md`
- `.harness/skills/android-code-review/SKILL.md §Severity levels`
